"""UrbanRoadAI – Road Condition Scoring and Risk Prediction.

Provides two main functions:
  score_segment()   – compute a 0-100 condition score for one segment/survey
  predict_risk()    – estimate short-term risk from condition history

The scoring formula and band thresholds match docs/shared_decisions.md:
  0-25   Good
  26-50  Fair
  51-75  Poor
  76-100 Very Poor

IMPORTANT SCIENTIFIC LIMITATIONS (see docs/condition-assessment.md):
  - The score is based on VISIBLE SURFACE DEFECTS detected by the YOLO model.
  - Bounding-box area is NOT equal to actual pavement damage area.
  - Scores cannot independently determine structural pavement health,
    subgrade strength, or material composition.
  - The prediction model is experimental (rule-based) and should not be
    cited as a validated remaining-useful-life forecast.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Class weights – reflect relative damage severity.
# Pothole and alligator crack are more severe than single cracks.
# ---------------------------------------------------------------------------
CLASS_WEIGHTS = {
    0: 1.0,   # longitudinal_crack
    1: 1.0,   # transverse_crack
    2: 2.0,   # alligator_crack
    3: 3.0,   # pothole
}

SEVERITY_MULTIPLIER = {
    "low": 0.5,
    "moderate": 1.0,
    "high": 1.5,
}

# Minimum detection confidence to include in scoring.
SCORING_CONF_THRESHOLD = 0.30

# ---------------------------------------------------------------------------
# Score bands (from shared_decisions.md §5)
# ---------------------------------------------------------------------------
BANDS = [
    (0,  25, "good"),
    (26, 50, "fair"),
    (51, 75, "poor"),
    (76, 100, "very_poor"),
]


def _band(score: float) -> str:
    for lo, hi, label in BANDS:
        if lo <= score <= hi:
            return label
    return "very_poor"


# ---------------------------------------------------------------------------
# Segment-level condition scoring
# ---------------------------------------------------------------------------

def score_segment(
    detections: list[dict],
    segment_length_m: float,
    conf_threshold: float = SCORING_CONF_THRESHOLD,
) -> dict:
    """Compute a condition score for one road segment from its detections.

    Parameters
    ----------
    detections : list[dict]
        Rows from the damage_detections table (or from to_db_rows()).
        Each must have: class_id, confidence, area_ratio, severity.
    segment_length_m : float
        Length of the segment in metres.
    conf_threshold : float
        Detections below this confidence are excluded from scoring.

    Returns
    -------
    dict with: score (0-100), band, n_defects, defect_density,
               class_counts, formula_explanation.

    Scoring formula:
        weighted_sum = Σ (class_weight × severity_mult × confidence)
        density      = n_filtered / (segment_length_m / 100)   [per 100 m]
        area_sum     = Σ area_ratio   (capped at 1.0)

        raw_score = (
            0.40 × min(weighted_sum / 5.0, 1.0) +
            0.30 × min(density      / 3.0, 1.0) +
            0.30 × min(area_sum     / 0.5, 1.0)
        ) × 100

    Each component is normalised to [0, 1] before weighting.
    The denominators (5.0, 3.0, 0.5) are calibrated so that a segment
    with moderate damage receives a score around 50.
    """
    # Filter by confidence threshold.
    filtered = [d for d in detections if d.get("confidence", 0) >= conf_threshold]
    n_defects = len(filtered)

    # Count per class.
    class_counts = {}
    for d in filtered:
        cid = d.get("class_id", -1)
        class_counts[cid] = class_counts.get(cid, 0) + 1

    if n_defects == 0 or segment_length_m <= 0:
        return {
            "score": 0.0,
            "band": "good",
            "n_defects": 0,
            "defect_density": 0.0,
            "class_counts": class_counts,
            "formula_explanation": "No defects detected above confidence threshold.",
        }

    # Weighted sum.
    weighted_sum = 0.0
    for d in filtered:
        cid = d.get("class_id", 0)
        sev = d.get("severity", "moderate") or "moderate"
        conf = d.get("confidence", 0.5)
        weighted_sum += CLASS_WEIGHTS.get(cid, 1.0) * SEVERITY_MULTIPLIER.get(sev, 1.0) * conf

    # Density.
    density = n_defects / (segment_length_m / 100.0)

    # Area sum.
    area_sum = min(sum(d.get("area_ratio", 0) or 0 for d in filtered), 1.0)

    # Composite score.
    comp_weighted = min(weighted_sum / 5.0, 1.0)
    comp_density  = min(density / 3.0, 1.0)
    comp_area     = min(area_sum / 0.5, 1.0)

    raw_score = (0.40 * comp_weighted + 0.30 * comp_density + 0.30 * comp_area) * 100
    score = round(min(max(raw_score, 0), 100), 1)

    return {
        "score": score,
        "band": _band(score),
        "n_defects": n_defects,
        "defect_density": round(density, 2),
        "class_counts": class_counts,
        "formula_explanation": (
            f"weighted_sum={weighted_sum:.2f}, density={density:.2f}/100m, "
            f"area_sum={area_sum:.4f} → components: W={comp_weighted:.2f}, "
            f"D={comp_density:.2f}, A={comp_area:.2f} → score={score}"
        ),
    }


# ---------------------------------------------------------------------------
# Experimental risk prediction (rule-based)
# ---------------------------------------------------------------------------

ROAD_TYPE_RISK = {
    "primary": 0.10,
    "secondary": 0.05,
    "tertiary": 0.00,
    "residential": -0.05,
}


def predict_risk(
    condition_history: list[dict],
    road_type: str = "tertiary",
    horizon_days: int = 180,
) -> dict:
    """Estimate short-term deterioration risk for one segment.

    This is an EXPERIMENTAL rule-based model, not a validated prediction.
    It uses:
      - The latest condition score (higher → higher risk).
      - The trend between repeated surveys (worsening → higher risk).
      - Road type (higher-traffic roads degrade faster).

    Returns
    -------
    dict with: risk_prob (0-1), horizon_days, model_version, explanation.
    """
    if not condition_history:
        return {
            "risk_prob": 0.5,
            "horizon_days": horizon_days,
            "model_version": "rule_v1",
            "explanation": "No condition history available; default moderate risk.",
        }

    # Sort by survey date.
    history = sorted(condition_history, key=lambda r: r.get("survey_date", ""))

    latest_score = history[-1].get("score", 50)

    # Base risk from latest score (normalised to 0-1).
    base_risk = latest_score / 100.0

    # Trend component (positive = worsening).
    trend = 0.0
    if len(history) >= 2:
        first_score = history[0].get("score", 50)
        trend = (latest_score - first_score) / 100.0   # [-1, 1]

    # Road type adjustment.
    type_adj = ROAD_TYPE_RISK.get(road_type, 0.0)

    # Composite risk.
    risk_prob = 0.60 * base_risk + 0.25 * max(trend, 0) + 0.15 * (0.5 + type_adj)
    risk_prob = round(min(max(risk_prob, 0.0), 1.0), 3)

    return {
        "risk_prob": risk_prob,
        "horizon_days": horizon_days,
        "model_version": "rule_v1",
        "explanation": (
            f"base_risk={base_risk:.2f} (latest score {latest_score}), "
            f"trend={trend:+.2f}, road_type_adj={type_adj:+.2f} → risk={risk_prob}"
        ),
    }

