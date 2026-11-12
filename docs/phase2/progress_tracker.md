# Phase II Progress Tracker

**Project:** UrbanRoadAI — AI-Powered Urban Road Condition Monitoring
**Evaluation Date:** 12 November 2026
**Branch:** `feature/phase2-integration`

## Milestone Status

| # | Milestone | Status | Date | Rubric Criteria |
|---|-----------|--------|------|-----------------|
| 1 | Repository audit & recovery | ✅ Complete | 11-Nov | Project Execution — Adherence |
| 2 | Custom dataset integration | ✅ Complete | 11-Nov | Tools & Techniques — Application |
| 3 | Dataset conversion (VOC → YOLO) | ✅ Complete | 11-Nov | Tools & Techniques — Application |
| 4 | Database schema (PostgreSQL + SQLite) | ✅ Complete | 11-Nov | Tools & Techniques — Selection |
| 5 | Database helper (dual-backend) | ✅ Complete | 11-Nov | Tools & Techniques — Integration |
| 6 | Demo database seeder | ✅ Complete | 11-Nov | Project Execution — Quality |
| 7 | Condition scoring module | ✅ Complete | 11-Nov | Project Execution — Adherence |
| 8 | Risk prediction module | ✅ Complete | 11-Nov | Project Execution — Adherence |
| 9 | GIS matching module | ✅ Complete | 11-Nov | Tools & Techniques — Application |
| 10 | FastAPI backend (7 endpoints) | ✅ Complete | 11-Nov | Tools & Techniques — Integration |
| 11 | Streamlit dashboard (6 pages) | ✅ Complete | 11-Nov | Tools & Techniques — Integration |
| 12 | Test suite (5 files, 30+ tests) | ✅ Complete | 11-Nov | Project Execution — Quality |
| 13 | Frame extraction script | ✅ Complete | 11-Nov | Tools & Techniques — Application |
| 14 | Documentation (13 docs) | ✅ Complete | 11-Nov | Partial Results — Clarity |
| 15 | Requirements & config updates | ✅ Complete | 11-Nov | Project Execution — Quality |
| 16 | Model training (YOLOv8s) | ✅ Complete | Pre-Phase2 | Tools & Techniques — Application |
| 17 | Model comparison (v8s vs 11s) | ✅ Complete | Pre-Phase2 | Partial Results — Analysis |

## Dependency Tracker

| Dependency | Status | Impact |
|-----------|--------|--------|
| Python packages (pip install) | ⏳ User action needed | Tests, API, dashboard won't run |
| Model weights (.pt file) | ⏳ Needs DVC pull | Live inference unavailable; demo uses sample output |
| Docker (PostGIS) | ⏳ Optional | SQLite demo works without Docker |
| RDD2022 dataset | ⏳ Needs DVC pull | Not needed for demo (sample output available) |

## Completed Deliverables

### Code Modules (src/)
- `src/vision/inference.py` — YOLO inference (schema 1.0)
- `src/vision/train.py` — YOLO training with MLflow
- `src/vision/convert_sample_dataset.py` — Custom dataset converter
- `src/vision/build_yolo_dataset.py` — RDD2022 dataset builder
- `src/db/schema.sql` — PostgreSQL + PostGIS schema (9 tables)
- `src/db/schema_sqlite.sql` — SQLite mirror schema
- `src/db/db.py` — Dual-backend database helper
- `src/db/seed_demo.py` — Demo data seeder
- `src/gis/matcher.py` — GPX parsing + GPS-to-segment matching
- `src/prediction/scoring.py` — Condition scoring + risk prediction
- `src/api/main.py` — FastAPI backend (7 endpoints)

### Dashboard
- `dashboard/app.py` — 6-page Streamlit dashboard

### Tests
- `tests/conftest.py` — Shared fixtures (tmp_db, api_client)
- `tests/test_scoring.py` — Scoring & risk tests
- `tests/test_api.py` — API endpoint tests
- `tests/test_gis.py` — Haversine & matching tests
- `tests/test_convert.py` — Dataset conversion tests

### Documentation
- `README.md` — Project overview
- `docs/architecture.md` — System architecture
- `docs/database.md` — Database design
- `docs/api.md` — API documentation
- `docs/vision.md` — CV methodology
- `docs/gis.md` — Geospatial methodology
- `docs/condition-assessment.md` — Scoring formula
- `docs/experiments.md` — Experimental results
- `docs/demo-guide.md` — Demo instructions
- `docs/phase2/progress_tracker.md` — This file
- `docs/phase2/methodology_mapping.md` — Phase I → II mapping
- `docs/phase2/tools_techniques.md` — Technology justification
- `docs/phase2/partial_results.md` — Partial results summary

