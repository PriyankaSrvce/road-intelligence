"""Build temporal road-condition datasets and time-based splits."""

import pandas as pd

from condition.config import WEATHER_COLUMNS


def build_temporal_table(
    scores: pd.DataFrame, weather: pd.DataFrame
) -> pd.DataFrame:
    """Merge weather and derive within-segment temporal features and targets."""
    required_scores = {"road_segment_id", "survey_date", "score"}
    required_weather = {"survey_date", *WEATHER_COLUMNS}
    missing_scores = required_scores.difference(scores.columns)
    missing_weather = required_weather.difference(weather.columns)
    if missing_scores:
        raise ValueError(f"scores is missing columns: {', '.join(sorted(missing_scores))}")
    if missing_weather:
        raise ValueError(
            f"weather is missing columns: {', '.join(sorted(missing_weather))}"
        )

    score_rows = scores.copy()
    weather_rows = weather.copy()
    score_rows["survey_date"] = pd.to_datetime(score_rows["survey_date"])
    weather_rows["survey_date"] = pd.to_datetime(weather_rows["survey_date"])

    duplicate_dates = score_rows.duplicated(
        ["road_segment_id", "survey_date"], keep=False
    )
    if duplicate_dates.any():
        repeats = score_rows.loc[
            duplicate_dates, ["road_segment_id", "survey_date"]
        ].drop_duplicates()
        details = ", ".join(
            f"{row.road_segment_id}/{row.survey_date.date()}"
            for row in repeats.itertuples(index=False)
        )
        raise ValueError(f"Repeated survey dates within segment: {details}")

    survey_counts = score_rows.groupby("road_segment_id")["survey_date"].size()
    short_segments = survey_counts[survey_counts < 2].index.tolist()
    if short_segments:
        raise ValueError(
            f"Segments must have at least 2 surveys: {short_segments}"
        )

    merged = score_rows.merge(
        weather_rows[["survey_date", *WEATHER_COLUMNS]],
        on="survey_date",
        how="left",
        validate="many_to_one",
    )
    missing_weather_dates = merged.loc[
        merged[WEATHER_COLUMNS].isna().any(axis=1), "survey_date"
    ].drop_duplicates()
    if not missing_weather_dates.empty:
        dates = ", ".join(date.date().isoformat() for date in missing_weather_dates)
        raise ValueError(f"Missing weather for dates: {dates}")

    merged = merged.sort_values(
        ["road_segment_id", "survey_date"], kind="stable"
    ).reset_index(drop=True)
    groups = merged.groupby("road_segment_id", sort=False)
    merged["prev_score"] = groups["score"].shift(1)
    merged["days_since_prev"] = (
        merged.groupby("road_segment_id", sort=False)["survey_date"]
        .diff()
        .dt.total_seconds()
        .div(86400)
    )
    merged["deterioration_rate"] = (
        merged["prev_score"] - merged["score"]
    ) / merged["days_since_prev"]
    merged["prev_rate"] = merged.groupby("road_segment_id", sort=False)[
        "deterioration_rate"
    ].shift(1)
    merged["next_score"] = groups["score"].shift(-1)
    return merged


def time_split(
    table: pd.DataFrame, train_fraction: float = 0.7
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split rows at a chronological survey-date boundary."""
    if "survey_date" not in table.columns:
        raise ValueError("table must include a survey_date column")
    if not 0 <= train_fraction <= 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if train_fraction in {0, 1}:
        raise ValueError("train_fraction leaves an empty train or test split")

    dates = pd.Series(pd.to_datetime(table["survey_date"].dropna().unique())).sort_values()
    split_index = int(len(dates) * train_fraction)
    if split_index < 1 or split_index >= len(dates):
        raise ValueError("train_fraction leaves an empty train or test split")

    train_dates = dates.iloc[:split_index]
    test_dates = dates.iloc[split_index:]
    train = table.loc[pd.to_datetime(table["survey_date"]).isin(train_dates)].copy()
    test = table.loc[pd.to_datetime(table["survey_date"]).isin(test_dates)].copy()
    if train.empty or test.empty:
        raise ValueError("train_fraction leaves an empty train or test split")
    return train, test
