import pandas as pd
import pytest

from condition.rubric import add_severity, classify_severity


@pytest.mark.parametrize(
    ("damage_type", "low_ratio", "moderate_ratio", "high_ratio"),
    [
        ("D00", 0.005, 0.020, 0.040),
        ("D10", 0.005, 0.020, 0.040),
        ("D20", 0.005, 0.025, 0.050),
        ("D40", 0.002, 0.010, 0.030),
    ],
)
def test_each_damage_type_classifies_all_severities(
    damage_type, low_ratio, moderate_ratio, high_ratio
):
    assert classify_severity(damage_type, low_ratio, 0.9) == "Low"
    assert classify_severity(damage_type, moderate_ratio, 0.9) == "Moderate"
    assert classify_severity(damage_type, high_ratio, 0.9) == "High"


@pytest.mark.parametrize(
    ("damage_type", "area_ratio", "expected"),
    [
        ("D00", 0.010, "Moderate"),
        ("D00", 0.030, "High"),
        ("D40", 0.005, "Moderate"),
        ("D40", 0.020, "High"),
    ],
)
def test_exact_boundaries(damage_type, area_ratio, expected):
    assert classify_severity(damage_type, area_ratio, 0.9) == expected


def test_confidence_threshold():
    assert classify_severity("D00", 0.02, 0.29) is None
    assert classify_severity("D00", 0.02, 0.30) == "Moderate"


@pytest.mark.parametrize("damage_type", ["D00", "D10", "D20", "D40"])
def test_severity_never_decreases_as_area_ratio_increases(damage_type):
    severity_rank = {"Low": 0, "Moderate": 1, "High": 2}
    severities = [
        classify_severity(damage_type, area_ratio, 0.9)
        for area_ratio in (step / 1000 for step in range(1001))
    ]

    assert all(
        severity_rank[earlier] <= severity_rank[later]
        for earlier, later in zip(severities, severities[1:])
    )


@pytest.mark.parametrize(
    ("damage_type", "area_ratio", "confidence"),
    [
        ("unknown", 0.02, 0.9),
        ("D00", 1.5, 0.9),
        ("D00", -0.1, 0.9),
        ("D00", 0.02, 1.2),
    ],
)
def test_invalid_inputs_raise_value_error(damage_type, area_ratio, confidence):
    with pytest.raises(ValueError):
        classify_severity(damage_type, area_ratio, confidence)


def test_add_severity_returns_copy_and_preserves_input():
    detections = pd.DataFrame(
        {
            "damage_type": ["D00", "D00", "D40", "D20", "D10"],
            "area_ratio": [0.005, 0.02, 0.02, 0.05, 0.02],
            "confidence": [0.9, 0.9, 0.9, 0.9, 0.29],
        }
    )
    original = detections.copy(deep=True)

    result = add_severity(detections)

    assert result is not detections
    pd.testing.assert_frame_equal(detections, original)
    assert result["severity"].tolist() == ["Low", "Moderate", "High", "High", None]


def test_add_severity_raises_for_missing_required_column():
    detections = pd.DataFrame({"damage_type": ["D00"], "area_ratio": [0.02]})

    with pytest.raises(ValueError, match="confidence"):
        add_severity(detections)
