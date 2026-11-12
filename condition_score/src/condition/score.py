"""Road segment condition scoring."""

import pandas as pd

from condition.config import SCORE_BANDS, SCORE_K, SEVERITY_WEIGHTS
from condition.rubric import add_severity


def segment_score(detections: pd.DataFrame, n_images: int) -> float:
    """Calculate a clipped 0-100 condition score for one segment."""
    if n_images < 1:
        raise ValueError("n_images must be at least 1")

    required_columns = ("damage_type", "area_ratio", "confidence")
    missing_columns = [column for column in required_columns if column not in detections.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    if detections.empty:
        return 100.0

    classified = add_severity(detections)
    included = classified.loc[classified["severity"].notna()]
    damage_load = sum(
        SEVERITY_WEIGHTS[row.severity] * row.area_ratio * row.confidence
        for row in included.itertuples()
    ) / n_images
    score_floor = min(lower for _, lower, _ in SCORE_BANDS)
    score_ceiling = max(upper for _, _, upper in SCORE_BANDS)
    return float(max(score_floor, min(score_ceiling, 100 - SCORE_K * damage_load)))


def score_to_band(score: float) -> str:
    """Return the configured score band, assigning shared edges to the higher band."""
    score_floor = min(lower for _, lower, _ in SCORE_BANDS)
    score_ceiling = max(upper for _, _, upper in SCORE_BANDS)
    if not score_floor <= score <= score_ceiling:
        raise ValueError("score must be between 0 and 100")

    for band, lower, upper in SCORE_BANDS:
        if lower <= score <= upper:
            return band
    raise ValueError(f"No score band configured for score: {score}")


def score_segments(
    detections: pd.DataFrame, images_per_segment: pd.DataFrame
) -> pd.DataFrame:
    """Return scores and bands for surveyed road segments."""
    detection_columns = (
        "road_segment_id",
        "damage_type",
        "area_ratio",
        "confidence",
    )
    image_columns = ("road_segment_id", "n_images")
    missing_detections = [
        column for column in detection_columns if column not in detections.columns
    ]
    missing_images = [
        column for column in image_columns if column not in images_per_segment.columns
    ]
    if missing_detections:
        raise ValueError(
            f"Missing required detections columns: {', '.join(missing_detections)}"
        )
    if missing_images:
        raise ValueError(
            f"Missing required images_per_segment columns: {', '.join(missing_images)}"
        )

    known_segments = images_per_segment["road_segment_id"]
    unknown_detections = ~detections["road_segment_id"].isin(known_segments)
    if unknown_detections.any():
        unknown_ids = detections.loc[unknown_detections, "road_segment_id"].unique()
        raise ValueError(f"Unknown road_segment_id values: {unknown_ids.tolist()}")

    rows = []
    for segment_id, n_images in images_per_segment[
        ["road_segment_id", "n_images"]
    ].itertuples(index=False, name=None):
        segment_detections = detections.loc[
            detections["road_segment_id"] == segment_id
        ]
        score = segment_score(segment_detections, n_images)
        rows.append(
            {
                "road_segment_id": segment_id,
                "score": score,
                "band": score_to_band(score),
            }
        )
    return pd.DataFrame(rows, columns=["road_segment_id", "score", "band"])
