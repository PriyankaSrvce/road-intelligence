import pandas as pd
import pytest

from condition.ratings import (
    make_rating_template,
    mean_rating,
    ratings_wide,
    validate_ratings,
)


def valid_sheet():
    return pd.DataFrame(
        {
            "road_segment_id": ["s1", "s1", "s2", "s2"],
            "rater": ["A", "B", "A", "B"],
            "rating": [5, 3, 4, 2],
            "notes": ["", "", "", ""],
        }
    )


def test_template_shape_and_columns():
    template = make_rating_template(["s1", "s2", "s3"], ["A", "B"])

    assert template.shape == (6, 4)
    assert template.columns.tolist() == ["road_segment_id", "rater", "rating", "notes"]
    assert template["rating"].isna().all()
    assert (template["notes"] == "").all()


@pytest.mark.parametrize(
    ("segment_ids", "raters"),
    [
        ([], ["A"]),
        (["s1"], []),
        (["s1", "s1"], ["A"]),
        (["s1"], ["A", "A"]),
    ],
)
def test_template_rejects_empty_or_duplicate_inputs(segment_ids, raters):
    with pytest.raises(ValueError):
        make_rating_template(segment_ids, raters)


def test_validate_ratings_accepts_valid_sheet_and_returns_integer_ratings():
    result = validate_ratings(valid_sheet())

    assert result["rating"].tolist() == [5, 3, 4, 2]
    assert pd.api.types.is_integer_dtype(result["rating"])


@pytest.mark.parametrize("rating", [None, 0, 6, 3.5])
def test_validate_ratings_rejects_invalid_values(rating):
    sheet = valid_sheet()
    sheet["rating"] = sheet["rating"].astype(object)
    sheet.loc[0, "rating"] = rating

    with pytest.raises(ValueError, match="Ratings"):
        validate_ratings(sheet)


def test_validate_ratings_rejects_missing_column():
    with pytest.raises(ValueError, match="rating"):
        validate_ratings(valid_sheet().drop(columns="rating"))


def test_validate_ratings_rejects_duplicate_pair():
    sheet = pd.concat([valid_sheet(), valid_sheet().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="unique"):
        validate_ratings(sheet)


def test_validate_ratings_does_not_modify_input():
    sheet = valid_sheet()
    sheet["rating"] = sheet["rating"].astype(float)
    original = sheet.copy(deep=True)

    validate_ratings(sheet)

    pd.testing.assert_frame_equal(sheet, original)


def test_ratings_wide_shape_and_values():
    wide = ratings_wide(validate_ratings(valid_sheet()))

    assert wide.shape == (2, 3)
    assert wide.columns.tolist() == ["road_segment_id", "A", "B"]
    assert wide.set_index("road_segment_id").to_dict(orient="index") == {
        "s1": {"A": 5, "B": 3},
        "s2": {"A": 4, "B": 2},
    }


def test_mean_rating_returns_segment_averages():
    means = mean_rating(validate_ratings(valid_sheet()))

    assert means.columns.tolist() == ["road_segment_id", "mean_rating"]
    assert means.set_index("road_segment_id")["mean_rating"].to_dict() == {
        "s1": 4.0,
        "s2": 3.0,
    }
