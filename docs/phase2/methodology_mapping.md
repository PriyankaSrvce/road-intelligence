# Methodology Mapping: Phase I → Phase II

## Overview

This document maps the methodology proposed in Phase I to the actual implementation in Phase II, documenting what was planned, what was built, and any justified deviations.

## Pipeline Mapping

| Phase I Methodology Step | Phase II Implementation | Status | Notes |
|--------------------------|------------------------|--------|-------|
| **Data Collection** — Road survey videos | `scripts/extract_sample_frames.py` | ✅ Implemented | 5 MP4 videos collected (Oct 2026), 69 custom images annotated (Nov 2026) |
| **Frame Extraction** — Extract frames from video | `scripts/extract_sample_frames.py` | ✅ Implemented | OpenCV VideoCapture, configurable interval, blur filtering |
| **Image Quality Assessment** — Filter blurry frames | `scripts/extract_sample_frames.py` (blur_score) | ✅ Implemented | Laplacian variance method |
| **GPS Association** — Link frames to coordinates | Pascal VOC XML metadata + `src/gis/matcher.py` | ✅ Implemented | GPS embedded in annotation XML; GPX track parsing also supported |
| **Damage Detection** — YOLO-based detection | `src/vision/inference.py` + `src/vision/train.py` | ✅ Implemented | YOLOv8s trained on RDD2022 India; inference produces schema 1.0 output |
| **Benchmark Dataset** — RDD2022 | `src/vision/build_yolo_dataset.py` | ✅ Implemented | 15,400 images, 4 classes, DVC-tracked |
| **Custom Dataset** — Bengaluru road imagery | `data/sample_dataset/` + `src/vision/convert_sample_dataset.py` | ✅ Implemented | 69 annotated images, VOC → YOLO conversion |
| **GPS-to-Segment Matching** — OSM integration | `src/gis/matcher.py` | ✅ Implemented | Haversine distance, confidence levels, OSM way IDs |
| **Spatial Database** — PostgreSQL + PostGIS | `src/db/schema.sql` + `src/db/db.py` | ✅ Implemented | 9 tables; dual-backend (PostGIS + SQLite) |
| **Condition Assessment** — Segment scoring | `src/prediction/scoring.py` | ✅ Implemented | Weighted formula, 4 bands (Good/Fair/Poor/Very Poor) |
| **Repeated Survey Comparison** — Trend analysis | Dashboard survey comparison page | ✅ Implemented | Side-by-side comparison, trend indicators |
| **Deterioration Prediction** — Experimental | `src/prediction/scoring.py` (predict_risk) | ✅ Implemented | Rule-based (not ML); clearly labelled as experimental |
| **Maintenance Prioritization** — Ranking | API `/risk` endpoint + dashboard priority page | ✅ Implemented | Ranked by risk probability |
| **API Backend** — FastAPI | `src/api/main.py` | ✅ Implemented | 7 REST endpoints, auto-documentation |
| **Dashboard** — Streamlit | `dashboard/app.py` | ✅ Implemented | 6 pages with interactive charts and maps |
| **Experiment Tracking** — MLflow | `src/vision/train.py` (MLflow integration) | ✅ Implemented | Training runs logged with metrics and artifacts |
| **Dataset Versioning** — DVC | `.dvc` files for models and datasets | ✅ Configured | DVC pointers present; remote needs setup for pull |
| **Containerisation** — Docker | `docker-compose.yml` | ✅ Implemented | PostGIS container for production mode |

## Deviations from Phase I Methodology

| Deviation | Justification |
|-----------|---------------|
| **Added SQLite backend** alongside PostgreSQL | Enables demonstration without Docker; no loss of functionality for evaluation |
| **Rule-based risk prediction** instead of ML model | Insufficient repeated-survey data for ML training; rule-based is honest and transparent |
| **Custom dataset has 3 classes** (not 4) | Field survey area had no longitudinal or transverse cracks; this is a data reality, not a methodology failure |
| **"Repair" class dropped** from custom dataset | Repair patches are not defects; keeping them would contaminate the defect detector |
| **Portrait image orientation** (2160×3840) | Phone was mounted vertically during survey; YOLO handles aspect ratio internally |

## Alignment with Project Objectives

| Phase I Objective | Phase II Evidence |
|-------------------|-------------------|
| Identify visible road defects | YOLOv8s detects 4 defect classes; mAP@50 = 0.334 on RDD2022 |
| Assess road condition trends | Condition scoring + repeated survey comparison |
| Support maintenance prioritisation | Risk prediction + ranked priority table |
| Use geospatial mapping | GPS association + segment matching + map visualisation |
| Align with SDG 11 | Evidence-based infrastructure monitoring |

