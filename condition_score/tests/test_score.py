import pandas as pd
import pytest

from condition.config import MIN_CONFIDENCE
from condition.score import score_segments, score_to_band, segment_score


def detection(damage_type="D40", area_ratio=0.03, confidence=0.8):
    return pd.DataFrame(
        {
            "damage_type": [damage_type],
            "area_ratio": [area_ratio],
            "confidence": [confidence],
        }
    )


def test_empty_detections_score_perfect():
    empty = pd.DataFrame(columns=["damage_type", "area_ratio", "confidence"])

    assert segment_score(empty, 1) == 100.0


def test_high_d40_detection_has_expected_score():
    assert segment_score(detection(), 1) == pytest.approx(42.4)


def test_adding_a_detection_never_raises_score():
    one = detection()
    two = pd.concat([one, one], ignore_index=True)

    assert segment_score(two, 1) <= segment_score(one, 1)


def test_increasing_area_ratio_never_raises_score():
    scores = [
        segment_score(detection(area_ratio=area_ratio), 1)
        for area_ratio in (0.005, 0.01, 0.02, 0.03, 0.5, 1.0)
    ]

    assert all(earlier >= later for earlier, later in zip(scores, scores[1:]))


def test_more_images_gives_equal_or_higher_score():
    detections = detection()

    assert segment_score(detections, 2) >= segment_score(detections, 1)


def test_score_is_clipped_to_zero_for_huge_damage():
    huge_damage = detection(area_ratio=1.0, confidence=1.0)

    assert segment_score(huge_damage, 1) == 0.0


def test_low_confidence_detections_do_not_change_score():
    base = detection()
    ignored = pd.concat(
        [base, detection(confidence=MIN_CONFIDENCE - 0.01)], ignore_index=True
    )

    assert segment_score(ignored, 1) == segment_score(base, 1)


def test_segment_score_validates_image_count_and_columns():
    with pytest.raises(ValueError, match="n_images"):
        segment_score(detection(), 0)
    with pytest.raises(ValueError, match="confidence"):
        segment_score(pd.DataFrame({"damage_type": ["D40"], "area_ratio": [0.03]}), 1)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "Good"),
        (80, "Good"),
        (79.99, "Fair"),
        (60, "Fair"),
        (59.99, "Poor"),
        (40, "Poor"),
        (39.99, "Very Poor"),
        (0, "Very Poor"),
    ],
)
def test_score_to_band_boundaries(score, expected):
    assert score_to_band(score) == expected


@pytest.mark.parametrize("score", [-1, 101])
def test_score_to_band_rejects_out_of_range_scores(score):
    with pytest.raises(ValueError):
        score_to_band(score)


def test_score_segments_returns_ordered_scores_and_bands():
    detections = pd.DataFrame(
        {
            "road_segment_id": ["mild", "severe"],
            "damage_type": ["D40", "D40"],
            "area_ratio": [0.006, 0.5],
            "confidence": [0.8, 0.8],
        }
    )
    images_per_segment = pd.DataFrame(
        {
            "road_segment_id": ["clear", "mild", "severe"],
            "n_images": [1, 1, 1],
        }
    )

    result = score_segments(detections, images_per_segment)

    assert result["road_segment_id"].tolist() == ["clear", "mild", "severe"]
    assert result["score"].tolist() == pytest.approx([100.0, 94.24, 0.0])
    assert result["band"].tolist() == ["Good", "Good", "Very Poor"]
    assert result["score"].is_monotonic_decreasing


def test_score_segments_rejects_unknown_segment_and_preserves_inputs():
    detections = pd.DataFrame(
        {
            "road_segment_id": ["missing"],
            "damage_type": ["D40"],
            "area_ratio": [0.03],
            "confidence": [0.8],
        }
    )
    images_per_segment = pd.DataFrame(
        {"road_segment_id": ["known"], "n_images": [1]}
    )
    detections_before = detections.copy(deep=True)
    images_before = images_per_segment.copy(deep=True)

    with pytest.raises(ValueError, match="Unknown road_segment_id"):
        score_segments(detections, images_per_segment)

    pd.testing.assert_frame_equal(detections, detections_before)
    pd.testing.assert_frame_equal(images_per_segment, images_before)
