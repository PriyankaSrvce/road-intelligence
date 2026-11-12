import pandas as pd
import pytest

from condition.temporal import build_temporal_table, time_split


def sample_inputs():
    dates = pd.to_datetime(["2025-01-01", "2025-01-08", "2025-01-15"])
    scores = pd.DataFrame(
        {
            "road_segment_id": ["S1"] * 3,
            "survey_date": dates,
            "score": [90.0, 83.0, 76.0],
        }
    )
    weather = pd.DataFrame(
        {"survey_date": dates, "rainfall_mm": [0.0, 5.0, 10.0], "temp_c": [20, 21, 22]}
    )
    return scores, weather


def test_temporal_features_and_target_on_three_surveys():
    scores, weather = sample_inputs()

    table = build_temporal_table(scores, weather)

    assert table.loc[1, "deterioration_rate"] == pytest.approx(1.0)
    assert table.loc[2, "deterioration_rate"] == pytest.approx(1.0)
    assert table.loc[1, "days_since_prev"] == pytest.approx(7.0)
    assert pd.isna(table.loc[0, "prev_score"])
    assert pd.isna(table.loc[0, "prev_rate"])


def test_next_score_is_following_survey_and_last_is_missing():
    scores, weather = sample_inputs()

    table = build_temporal_table(scores, weather)

    assert table["next_score"].tolist()[:2] == [83.0, 76.0]
    assert pd.isna(table.loc[2, "next_score"])


def test_build_temporal_table_rejects_missing_weather_dates():
    scores, weather = sample_inputs()

    with pytest.raises(ValueError, match="2025-01-15"):
        build_temporal_table(scores, weather.iloc[:2])


def test_build_temporal_table_rejects_repeated_dates():
    scores, weather = sample_inputs()
    scores = pd.concat([scores, scores.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Repeated survey dates"):
        build_temporal_table(scores, weather)


def test_build_temporal_table_rejects_segment_with_one_survey():
    scores, weather = sample_inputs()
    scores.loc[2, "road_segment_id"] = "S2"

    with pytest.raises(ValueError, match="at least 2 surveys"):
        build_temporal_table(scores, weather)


def test_build_temporal_table_does_not_modify_inputs():
    scores, weather = sample_inputs()
    original_scores = scores.copy(deep=True)
    original_weather = weather.copy(deep=True)

    build_temporal_table(scores, weather)

    pd.testing.assert_frame_equal(scores, original_scores)
    pd.testing.assert_frame_equal(weather, original_weather)


def test_time_split_is_chronological_and_non_random():
    scores, weather = sample_inputs()
    scores = pd.concat([scores, scores.assign(road_segment_id="S2")], ignore_index=True)
    table = build_temporal_table(scores, weather)

    train, test = time_split(table, train_fraction=2 / 3)

    assert train["survey_date"].max() < test["survey_date"].min()
    assert train["survey_date"].nunique() == 2
    assert test["survey_date"].nunique() == 1


@pytest.mark.parametrize("fraction", [0.0, 1.0])
def test_time_split_rejects_empty_side(fraction):
    scores, weather = sample_inputs()
    table = build_temporal_table(scores, weather)

    with pytest.raises(ValueError, match="empty"):
        time_split(table, train_fraction=fraction)
