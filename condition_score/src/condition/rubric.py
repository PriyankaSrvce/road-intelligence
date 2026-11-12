"""Severity classification for road damage detections."""

import pandas as pd

from condition.config import MIN_CONFIDENCE, SEVERITY_RUBRIC, SEVERITY_LEVELS


def classify_severity(
    damage_type: str, area_ratio: float, confidence: float
) -> str | None:
    """Classify a damage detection by its area ratio and confidence."""
    if not 0 <= area_ratio <= 1:
        raise ValueError("area_ratio must be between 0 and 1")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if damage_type not in SEVERITY_RUBRIC:
        raise ValueError(f"Unknown damage type: {damage_type!r}")
    if confidence < MIN_CONFIDENCE:
        return None

    low_upper, moderate_upper = SEVERITY_RUBRIC[damage_type]
    if area_ratio < low_upper:
        return SEVERITY_LEVELS[0]
    if area_ratio < moderate_upper:
        return SEVERITY_LEVELS[1]
    return SEVERITY_LEVELS[2]


def add_severity(
    df: pd.DataFrame,
    type_col: str = "damage_type",
    area_col: str = "area_ratio",
    conf_col: str = "confidence",
) -> pd.DataFrame:
    """Return a copy of the DataFrame with a computed severity column."""
    required_columns = (type_col, area_col, conf_col)
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    result = df.copy()
    severities = [
        classify_severity(damage_type, area_ratio, confidence)
        for damage_type, area_ratio, confidence in zip(
            result[type_col], result[area_col], result[conf_col]
        )
    ]
    result["severity"] = pd.Series(severities, index=result.index, dtype=object)
    return result
