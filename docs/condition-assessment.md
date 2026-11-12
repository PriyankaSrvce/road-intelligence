# Condition Assessment & Risk Prediction

## Overview

UrbanRoadAI computes a **condition score** (0–100) for each road segment per survey, classifies it into a **condition band**, and produces an **experimental risk prediction** for maintenance prioritization.

## Condition Scoring Formula

### Input

For each segment-survey pair:
- `detections[]` — all damage detections from images on that segment during that survey.
- `segment_length_m` — length of the road segment in metres.

### Filtering

Detections with `confidence < conf_threshold` (default: 0.30) are excluded.

### Three Components

#### 1. Weighted Severity Sum (40% weight)

Each detection contributes:

```
contribution = class_weight × severity_multiplier × confidence
```

**Class Weights:**

| Class ID | Name | Weight | Rationale |
|----------|------|--------|-----------|
| 0 | longitudinal_crack | 1.0 | Linear crack, moderate concern |
| 1 | transverse_crack | 1.0 | Linear crack, moderate concern |
| 2 | alligator_crack | 2.0 | Interconnected — indicates fatigue |
| 3 | pothole | 3.0 | Most severe — safety hazard |

**Severity Multipliers:**

| Severity | Multiplier | Area Ratio Threshold |
|----------|-----------|---------------------|
| low | 0.5 | < 1% of image area |
| moderate | 1.0 | 1–5% of image area |
| high | 1.5 | > 5% of image area |

> ⚠️ **Limitation:** Severity is derived from bounding-box area ratio, which is NOT equal to actual damaged pavement area. The bounding box includes non-damaged pixels.

#### 2. Defect Density (30% weight)

```
density = n_filtered_defects / (segment_length_m / 100)
```

Expressed as defects per 100 metres. Higher density = worse condition.

#### 3. Area Sum (30% weight)

```
area_sum = min(Σ area_ratio, 1.0)
```

Sum of all bounding-box area ratios, capped at 1.0.

### Composite Score

Each component is normalised to [0, 1] before weighting:

```
comp_weighted = min(weighted_sum / 5.0, 1.0)
comp_density  = min(density / 3.0, 1.0)
comp_area     = min(area_sum / 0.5, 1.0)

raw_score = (0.40 × comp_weighted + 0.30 × comp_density + 0.30 × comp_area) × 100
```

The denominators (5.0, 3.0, 0.5) are calibrated so that a segment with moderate damage receives a score around 50.

**Score range:** 0 (no defects) to 100 (severely damaged).

## Condition Bands

| Score Range | Band | Interpretation |
|------------|------|---------------|
| 0–25 | **Good** | Minimal visible defects |
| 26–50 | **Fair** | Some defects, monitoring recommended |
| 51–75 | **Poor** | Significant defects, repair needed |
| 76–100 | **Very Poor** | Severe damage, urgent intervention |

Bands are frozen in `docs/shared_decisions.md §5`. Changes require team agreement.

## Repeated-Survey Comparison

When a segment has condition history from multiple surveys, we can observe:
- **Stable:** Score change ≤ ±2 points.
- **Improving:** Score decreased (fewer/smaller defects detected).
- **Worsening:** Score increased (more/larger defects detected).

The dashboard displays this as a trend indicator (⬆️ Worsened / ⬇️ Improved / ➡️ Stable).

## Experimental Risk Prediction

### Model Type

**Rule-based** (`model_version = "rule_v1"`). This is NOT a machine-learning model — it is a simple weighted formula that combines three factors.

### Factors

#### 1. Base Risk (60% weight)

```
base_risk = latest_score / 100
```

Direct normalisation of the most recent condition score.

#### 2. Trend (25% weight)

```
trend = (latest_score - first_score) / 100
```

Only positive trends (worsening) contribute. If trend ≤ 0, this component is 0.

#### 3. Road Type Adjustment (15% weight)

| Road Type | Adjustment | Rationale |
|-----------|-----------|-----------|
| primary | +0.10 | Higher traffic → faster degradation |
| secondary | +0.05 | Moderate traffic |
| tertiary | 0.00 | Baseline |
| residential | −0.05 | Lower traffic |

### Composite Risk

```
risk_prob = 0.60 × base_risk + 0.25 × max(trend, 0) + 0.15 × (0.5 + type_adj)
```

**Output range:** 0.0 (lowest risk) to 1.0 (highest risk).

### Maintenance Prioritization

Segments are ranked by `risk_prob` descending. Higher risk = higher priority for intervention.

## Scientific Limitations

> **These limitations must be stated in any presentation or report.**

1. **Image-based only:** Scores cannot determine structural pavement health, subgrade strength, material composition, or pavement layer thickness.
2. **Bounding-box proxy:** Area ratios use bounding-box area, which includes non-damaged pixels. True damaged area is smaller.
3. **No calibration to PCI/IRI:** The 0–100 score is custom and has NOT been calibrated against standard pavement indices (PCI, IRI, PSI).
4. **Rule-based prediction:** The risk model is experimental and should not be cited as a validated remaining-useful-life forecast.
5. **Single viewpoint:** Each image captures one perspective. Multiple viewpoints would improve accuracy.
6. **Environmental factors:** Wet surfaces, shadows, and debris can cause false positives or negatives.

