def test_package_imports():
    import condition

    assert condition is not None


def test_score_bands_cover_zero_to_one_hundred_without_gaps():
    from condition.config import SCORE_BANDS

    bounds = sorted((lower, upper) for _, lower, upper in SCORE_BANDS)

    assert bounds[0][0] == 0
    assert bounds[-1][1] == 100
    assert all(current[1] == following[0] for current, following in zip(bounds, bounds[1:]))


def test_detection_columns_include_required_fields():
    from condition.config import DETECTION_COLUMNS

    assert "confidence" in DETECTION_COLUMNS
    assert "area_ratio" in DETECTION_COLUMNS
