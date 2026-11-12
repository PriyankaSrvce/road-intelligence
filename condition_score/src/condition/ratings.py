"""Helpers for preparing and summarizing human condition ratings."""

from pathlib import Path

import pandas as pd

from condition.config import RATING_MAX, RATING_MIN


def read_segment_ids(path: str | Path) -> list[str]:
    """Read segment IDs, removing surrounding spaces and trailing commas."""
    return [
        segment_id
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if (segment_id := line.strip().rstrip(",").strip())
    ]


def _clean_names(names: list[str], field_name: str) -> list[str]:
    cleaned = [name.strip().rstrip(",").strip() for name in names]
    cleaned = [name for name in cleaned if name]
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")

    seen = set()
    duplicates = []
    for name in cleaned:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        raise ValueError(
            f"{field_name} contains duplicate names: {', '.join(duplicates)}"
        )
    return cleaned


def make_rating_template(
    segment_ids: list[str], raters: list[str]
) -> pd.DataFrame:
    """Create one blank rating row for each segment and rater pair."""
    segment_ids = _clean_names(segment_ids, "segment_ids")
    raters = _clean_names(raters, "raters")

    return pd.DataFrame(
        [
            {
                "road_segment_id": segment_id,
                "rater": rater,
                "rating": float("nan"),
                "notes": "",
            }
            for segment_id in segment_ids
            for rater in raters
        ],
        columns=["road_segment_id", "rater", "rating", "notes"],
    )


def validate_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a long rating sheet and return a cleaned copy."""
    required_columns = ("road_segment_id", "rater", "rating")
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    missing_ratings = df["rating"].isna()
    blank_strings = df["rating"].map(
        lambda value: isinstance(value, str) and not value.strip()
    )
    missing_ratings |= blank_strings
    if missing_ratings.any():
        missing_pairs = df.loc[
            missing_ratings, ["road_segment_id", "rater"]
        ].itertuples(index=False, name=None)
        pairs = ", ".join(f"{segment}/{rater}" for segment, rater in missing_pairs)
        raise ValueError(f"Missing ratings for: {pairs} (Ratings are required)")

    if df.duplicated(subset=["road_segment_id", "rater"]).any():
        raise ValueError("Each (road_segment_id, rater) pair must be unique")

    numeric_ratings = pd.to_numeric(df["rating"], errors="coerce")
    invalid_ratings = (
        numeric_ratings.isna()
        | (numeric_ratings % 1 != 0)
        | (numeric_ratings < RATING_MIN)
        | (numeric_ratings > RATING_MAX)
    )
    if invalid_ratings.any():
        raise ValueError(
            f"Ratings must be whole numbers from {RATING_MIN} to {RATING_MAX}"
        )

    result = df.copy()
    result["rating"] = numeric_ratings.astype(int)
    return result


def ratings_wide(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot validated long ratings into one column per rater."""
    wide = df.pivot(
        index="road_segment_id", columns="rater", values="rating"
    ).reset_index()
    wide.columns.name = None
    return wide


def mean_rating(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the average rating for each road segment."""
    return (
        df.groupby("road_segment_id", as_index=False)["rating"]
        .mean()
        .rename(columns={"rating": "mean_rating"})
    )
