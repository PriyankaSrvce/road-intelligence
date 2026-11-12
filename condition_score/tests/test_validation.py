import numpy as np
import pandas as pd
import pytest

from condition.validation import (
    interpret_agreement,
    plot_score_vs_rating,
    rater_agreement,
    score_vs_rating,
)


def test_two_raters_with_perfect_agreement_have_kappa_one():
    ratings = pd.DataFrame(
        {
            "road_segment_id": [f"S{i}" for i in range(1, 7)],
            "A": [1, 2, 3, 4, 5, 3],
            "B": [1, 2, 3, 4, 5, 3],
        }
    )

    result = rater_agreement(ratings)

    assert result["method"] == "quadratic_weighted_cohen_kappa"
    assert result["value"] == pytest.approx(1.0)
    assert result["n_raters"] == 2
    assert result["n_segments"] == 6


def test_three_raters_high_agreement_has_high_icc_and_random_is_low():
    strong = pd.DataFrame(
        {
            "road_segment_id": [f"S{i}" for i in range(1, 11)],
            "A": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
            "B": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
            "C": [1, 2, 2, 2, 3, 4, 4, 4, 5, 5],
        }
    )
    random_ratings = pd.DataFrame(
        {
            "road_segment_id": [f"S{i}" for i in range(1, 21)],
            "A": [1, 5, 2, 4, 3, 1, 4, 2, 5, 3, 2, 5, 1, 3, 4, 5, 2, 4, 1, 3],
            "B": [4, 2, 5, 1, 3, 5, 1, 4, 2, 3, 1, 4, 5, 2, 3, 1, 5, 2, 4, 3],
            "C": [2, 4, 1, 5, 3, 4, 2, 1, 5, 3, 5, 1, 4, 2, 3, 4, 1, 5, 2, 3],
        }
    )

    strong_result = rater_agreement(strong)
    random_result = rater_agreement(random_ratings)

    assert strong_result["details"]["ICC2k"] > 0.9
    assert strong_result["details"]["ICC3k"] > 0.9
    assert random_result["details"]["ICC2k"] < 0.5


@pytest.mark.parametrize(
    ("ratings", "message"),
    [
        (pd.DataFrame({"road_segment_id": [f"S{i}" for i in range(5)], "A": [1] * 5}), "2 raters"),
        (
            pd.DataFrame(
                {"road_segment_id": ["S1", "S2", "S3"], "A": [1, 2, 3], "B": [1, 2, 3]}
            ),
            "5 segments",
        ),
        (
            pd.DataFrame(
                {
                    "road_segment_id": [f"S{i}" for i in range(5)],
                    "A": [1, 2, None, 4, 5],
                    "B": [1, 2, 3, 4, 5],
                }
            ),
            "missing",
        ),
    ],
)
def test_rater_agreement_validation_errors(ratings, message):
    with pytest.raises(ValueError, match=message):
        rater_agreement(ratings)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.39, "poor"),
        (0.40, "fair"),
        (0.59, "fair"),
        (0.60, "good"),
        (0.74, "good"),
        (0.75, "excellent"),
    ],
)
def test_interpret_agreement_thresholds(value, expected):
    assert interpret_agreement(value) == expected


def correlated_frames(reverse=False):
    segment_ids = [f"S{i}" for i in range(1, 11)]
    scores = pd.DataFrame(
        {"road_segment_id": segment_ids, "score": np.arange(10, dtype=float)}
    )
    rating_values = np.arange(10, dtype=float)
    if reverse:
        rating_values = rating_values[::-1]
    means = pd.DataFrame(
        {"road_segment_id": segment_ids, "mean_rating": rating_values}
    )
    return scores, means


@pytest.mark.parametrize(("reverse", "expected"), [(False, 1.0), (True, -1.0)])
def test_score_vs_rating_spearman_perfect_relationship(reverse, expected):
    scores, means = correlated_frames(reverse)

    result = score_vs_rating(scores, means)

    assert result["rho"] == pytest.approx(expected)
    assert result["n"] == 10


def test_score_vs_rating_confidence_interval_contains_rho_and_is_reproducible():
    scores, means = correlated_frames()
    scores.loc[4, "score"] = 4.2
    means.loc[6, "mean_rating"] = 6.4

    result = score_vs_rating(scores, means)
    repeated = score_vs_rating(scores, means)
    lower, upper = result["confidence_interval"]

    assert lower <= result["rho"] <= upper
    assert result["confidence_interval"] == repeated["confidence_interval"]


def test_score_vs_rating_rejects_fewer_than_five_matches():
    scores, means = correlated_frames()

    with pytest.raises(ValueError, match="5 matching"):
        score_vs_rating(scores.iloc[:4], means)


def test_plot_score_vs_rating_creates_png(tmp_path):
    scores, means = correlated_frames()
    output = tmp_path / "plot.png"

    plot_score_vs_rating(scores, means, str(output))

    assert output.exists()
    assert output.read_bytes().startswith(b"\x89PNG")
