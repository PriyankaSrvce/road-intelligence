# System Architecture

## Overview

UrbanRoadAI follows a modular, pipeline-based architecture where each component has a well-defined input/output contract. The system supports two deployment modes: **production** (PostgreSQL + PostGIS) and **demonstration** (SQLite).

## Pipeline Flowchart

```
┌──────────────────┐
│  Road Survey     │  Raw MP4 videos from dashcam/phone
│  Video/Images    │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Frame           │  scripts/extract_sample_frames.py
│  Extraction      │  OpenCV VideoCapture, configurable interval
│  + Quality       │  Laplacian variance blur score
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  GPS + Timestamp │  Embedded in Pascal VOC XML annotations
│  Association     │  or GPX track file matching
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  YOLO Detection  │  src/vision/inference.py
│  (YOLOv8s)       │  4 classes: longitudinal, transverse,
│                  │  alligator, pothole
└───────┬──────────┘
        │  Vision output schema 1.0
        ▼
┌──────────────────┐
│  GPS-to-Segment  │  src/gis/matcher.py
│  Matching        │  Haversine distance, confidence levels
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  PostgreSQL +    │  src/db/schema.sql (PostGIS)
│  PostGIS / SQLite│  src/db/schema_sqlite.sql (demo)
│  Database        │  src/db/db.py (dual-backend helper)
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Condition       │  src/prediction/scoring.py
│  Scoring         │  Weighted formula → 0-100 score
│  + Band          │  Good / Fair / Poor / Very Poor
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Repeated Survey │  Compare condition_history rows
│  Comparison      │  per segment across survey_dates
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Risk Prediction │  src/prediction/scoring.py
│  (Experimental)  │  Rule-based, model_version="rule_v1"
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Maintenance     │  Ranked by risk_prob DESC
│  Prioritization  │  Considers road_type, trend, score
└───────┬──────────┘
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│  FastAPI Backend │────▶│  Streamlit        │
│  src/api/main.py │     │  Dashboard        │
│  REST endpoints  │     │  dashboard/app.py │
└──────────────────┘     └──────────────────┘
```

## Component Responsibilities

| Component | Module | Input | Output |
|-----------|--------|-------|--------|
| Frame Extraction | `scripts/extract_sample_frames.py` | MP4 video | JPEG frames + metadata CSV |
| Dataset Conversion | `src/vision/convert_sample_dataset.py` | Pascal VOC XML + JPEG | YOLO labels + metadata CSV |
| Detection | `src/vision/inference.py` | JPEG image | Schema 1.0 JSON (detections) |
| Training | `src/vision/train.py` | YOLO dataset | Trained .pt weights + MLflow logs |
| GIS Matching | `src/gis/matcher.py` | GPS lat/lon + segments | MatchResult (segment_id, distance, confidence) |
| Database | `src/db/db.py` | SQL queries | Query results (dict rows) |
| Scoring | `src/prediction/scoring.py` | Detection list + segment length | Score, band, density, explanation |
| Risk Prediction | `src/prediction/scoring.py` | Condition history + road type | Risk probability + explanation |
| API | `src/api/main.py` | HTTP requests | JSON responses |
| Dashboard | `dashboard/app.py` | SQLite DB or API | Interactive visualisations |

## Technology Selection Justification

| Technology | Why Selected | Alternatives Considered |
|-----------|-------------|----------------------|
| YOLOv8s | Best mAP@50 (0.334) on RDD2022 India; single-stage, fast CPU inference | YOLO11s (0.320 mAP), Faster R-CNN (too slow for CPU) |
| FastAPI | Async, auto-docs (OpenAPI), type validation, Python-native | Flask (no auto-validation), Django (too heavy) |
| PostgreSQL + PostGIS | Mature spatial database, ST_* functions, industry standard | MongoDB (less spatial), SpatiaLite (limited) |
| SQLite | Zero-config demo mode, stdlib, portable | In-memory only (not persistent) |
| Streamlit | Rapid dashboard, Python-native, interactive widgets | Dash (more boilerplate), Grafana (separate stack) |
| MLflow | Experiment tracking, artifact logging, model registry | W&B (paid), TensorBoard (less structured) |
| DVC | Dataset versioning, Git-like workflow, GDrive remote | Git LFS (no pipelines), manual (error-prone) |
| OpenCV | Frame extraction, blur detection, image I/O | Pillow (fewer features), ffmpeg CLI (harder to integrate) |

## Data Contracts

All inter-module communication uses structured data:

- **Vision → Database:** Schema 1.0 (see `docs/shared_decisions.md §3`)
- **Database → API:** SQL queries return dict rows
- **API → Dashboard:** JSON over HTTP
- **GIS → Database:** `MatchResult` dataclass → `segment_id` foreign key
- **Scoring → Database:** `score_segment()` returns dict → `condition_history` row

