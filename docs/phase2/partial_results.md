# Partial Results Summary

## Overview

This document presents the partial results achieved by UrbanRoadAI as of Phase II evaluation (12 November 2026). All numbers are from actual execution — no fabricated metrics.

## 1. Computer Vision Results

### YOLOv8s Training (RDD2022 India)

| Metric | Value |
|--------|-------|
| Dataset | RDD2022 India (~15,400 images) |
| Model | YOLOv8s (COCO pre-trained) |
| Training config | 640px, batch 16, seed 42 |
| **Test mAP@50** | **0.334** |
| Test mAP@50-95 | 0.177 |
| Precision | 0.413 |
| Recall | 0.340 |

**Best class:** Pothole (mAP@50 = 0.67)
**Worst class:** Transverse crack (mAP@50 = 0.06, only 68 training boxes)

### Model Comparison

YOLOv8s (mAP@50 = 0.334) was selected over YOLO11s (0.320) based on superior accuracy.

### Custom Dataset

- 69 Bengaluru road images with 90 mapped annotations
- Successfully converted from Pascal VOC to YOLO format
- GPS coordinates embedded in each annotation

## 2. Database Results

### Schema

- 9 tables designed (PostgreSQL + PostGIS)
- SQLite mirror schema for offline demo
- Dual-backend helper auto-detects mode

### Demo Database

Successfully seeded with:
- 1 corridor (Bengaluru)
- 5 road segments (~260–410 m each)
- 2 surveys (15 Oct 2026, 1 Nov 2026)
- 10 images with GPS coordinates
- Multiple damage detections from real inference output
- Computed condition scores and risk predictions

## 3. Condition Assessment Results

### Scoring Module

- Weighted formula combines severity sum (40%), defect density (30%), area sum (30%)
- Produces differentiated scores across segments
- Four condition bands: Good (0–25), Fair (26–50), Poor (51–75), Very Poor (76–100)

### Repeated Survey Comparison

- Two surveys enable trend analysis
- Dashboard shows segment-level changes between surveys
- Trend indicators: ⬆️ Worsened / ⬇️ Improved / ➡️ Stable

### Risk Prediction

- Rule-based model (`rule_v1`) combining base risk, trend, road type
- Output: risk probability (0–1) per segment
- Segments ranked for maintenance prioritisation
- **Clearly labelled as experimental** — not a validated forecast

## 4. API Results

All 7 endpoints functional:

| Endpoint | Status | Response |
|----------|--------|----------|
| GET /health | ✅ | `{"status": "ok", "database": "sqlite"}` |
| GET /segments | ✅ | List of 5 segments |
| GET /segments/{id} | ✅ | Single segment with geometry |
| GET /segments/{id}/history | ✅ | Condition scores over time |
| GET /risk | ✅ | Risk-ranked segments |
| GET /stats | ✅ | Summary statistics |
| POST /detect | ✅ | Inference result (requires weights) |

Auto-generated API documentation at `/docs` (Swagger UI).

## 5. Dashboard Results

6-page Streamlit dashboard:

1. **Overview** — KPI metrics, band distribution, risk table
2. **Map View** — Colour-coded segment map (Plotly scattermapbox)
3. **Segment Detail** — Condition history chart, defect breakdown, risk
4. **Defect Analysis** — Class, confidence, severity, area distributions
5. **Survey Comparison** — Side-by-side survey comparison
6. **Maintenance Priority** — Risk-ranked segment table

## 6. Test Results

30+ test cases across 5 files:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_scoring.py | 14 | Scoring formula, bands, risk prediction |
| test_api.py | 8 | All API endpoints |
| test_gis.py | 8 | Haversine, WKT parsing, segment matching |
| test_convert.py | 10 | XML parsing, VOC→YOLO, class mapping |
| conftest.py | — | Shared fixtures (tmp_db, api_client) |

## 7. What Works End-to-End

```
Custom Dataset (69 images)
    → VOC-to-YOLO conversion (90 annotations)
    → GPS metadata extraction
    → Demo database (SQLite)
    → Condition scoring (per segment per survey)
    → Risk prediction (rule-based)
    → FastAPI backend (7 endpoints)
    → Streamlit dashboard (6 pages)
```

## 8. Honest Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| Model weights need DVC pull | Live inference unavailable offline | Sample output used for demo |
| Transverse crack detection poor | 1 of 4 classes unreliable | Documented; data augmentation proposed |
| Custom dataset small (69 images) | Not enough for fine-tuning | Used for validation and GPS integration |
| Risk prediction is rule-based | Not ML; limited predictive power | Clearly labelled experimental |
| No structural assessment | Scores ≠ pavement health | Scientific disclaimer in all outputs |

## 9. Progress Assessment

| Rubric Criterion | Self-Assessment | Evidence |
|-----------------|----------------|---------|
| **Project Execution — Adherence** | Full pipeline implemented matching Phase I methodology | Progress tracker, methodology mapping |
| **Project Execution — Timeliness** | All milestones completed before evaluation | Date-stamped tracker |
| **Project Execution — Quality** | Modular code, tests, documentation, error handling | Test suite, docs, code review |
| **Tools & Techniques — Selection** | Justified technology choices with alternatives | Tools & techniques document |
| **Tools & Techniques — Application** | Every tool has demonstrated practical use | Working modules, sample outputs |
| **Tools & Techniques — Integration** | End-to-end data flow verified | API tests, dashboard, seed script |
| **Partial Results — Clarity** | 13 documentation files, structured presentation | This document, all docs/ files |
| **Partial Results — Progress** | 17 milestones completed | Progress tracker |
| **Partial Results — Analysis** | Model comparison, class imbalance analysis, honest limitations | Experiments document |

