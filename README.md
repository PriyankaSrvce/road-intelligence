# 🛣️ UrbanRoadAI

**AI-Powered Urban Road Condition Monitoring, Geospatial Mapping & Predictive Maintenance Prioritization**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![YOLO](https://img.shields.io/badge/model-YOLOv8s-green.svg)](https://docs.ultralytics.com/)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![PostGIS](https://img.shields.io/badge/database-PostGIS-336791.svg)](https://postgis.net/)
[![SDG 11](https://img.shields.io/badge/SDG-11%20Sustainable%20Cities-orange.svg)](https://sdgs.un.org/goals/goal11)

---

## Problem Statement

Urban roads deteriorate due to traffic loading, environmental conditions, water ingress and ageing. Conventional inspection is time-consuming, inconsistent and difficult to scale.

UrbanRoadAI uses **street-level imagery**, **computer vision (YOLO)**, **geospatial mapping (OSM/PostGIS)** and **repeated road surveys** to identify visible road defects, assess road-condition trends and support maintenance prioritization.

> ⚠️ **Scientific Limitation:** This image-based system identifies **visible surface defects** only. Ordinary road images cannot independently determine pavement layer thickness, subgrade strength, material composition or complete structural pavement health.

## Architecture

```
Road Video/Image Collection
        │
        ▼
Frame Extraction & Quality Assessment (OpenCV)
        │
        ▼
GPS + Timestamp Association (XML metadata)
        │
        ▼
YOLO-Based Road Defect Detection (YOLOv8s)
        │
        ▼
Bounding-Box & Confidence Extraction
        │
        ▼
GPS-to-Road-Segment Matching (Haversine + OSM)
        │
        ▼
PostgreSQL + PostGIS Database (or SQLite demo)
        │
        ▼
Condition Scoring & Band Classification
        │
        ▼
Repeated-Survey Comparison
        │
        ▼
Experimental Risk Prediction (rule-based)
        │
        ▼
Maintenance Prioritization
        │
        ▼
FastAPI Backend + Streamlit Dashboard
```

## Quick Start

```bash
# 1. Clone & set up environment
git clone https://github.com/PriyankaSrvce/road-intelligence.git
cd road-intelligence
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Convert custom dataset (if sample_dataset exists)
python -m src.vision.convert_sample_dataset

# 4. Seed the demo database (SQLite)
python -m src.db.seed_demo

# 5. Start the API
uvicorn src.api.main:app --reload --port 8000

# 6. Start the dashboard (new terminal)
streamlit run dashboard/app.py

# 7. Run tests
python -m pytest tests/ -v
```

## Project Structure

```
road-intelligence/
├── configs/
│   └── classes.yaml              # Frozen class IDs (0-3)
├── dashboard/
│   └── app.py                    # Streamlit dashboard
├── data/
│   ├── sample_dataset/           # 69 annotated Bengaluru road images
│   ├── sample_dataset_yolo/      # Converted YOLO-format labels
│   └── roads_demo.db             # SQLite demo database (generated)
├── docs/
│   ├── architecture.md           # System architecture
│   ├── api.md                    # API documentation
│   ├── database.md               # Database schema design
│   ├── vision.md                 # Computer vision methodology
│   ├── gis.md                    # Geospatial methodology
│   ├── condition-assessment.md   # Scoring formula & risk prediction
│   ├── experiments.md            # Experimental results
│   ├── demo-guide.md             # Step-by-step demo instructions
│   ├── shared_decisions.md       # Team data contracts
│   └── phase2/                   # Phase II evaluation evidence
├── models/                       # DVC-tracked model weights
├── scripts/
│   └── extract_sample_frames.py  # Video frame extraction
├── src/
│   ├── api/main.py               # FastAPI backend
│   ├── db/
│   │   ├── schema.sql            # PostgreSQL + PostGIS schema
│   │   ├── schema_sqlite.sql     # SQLite mirror schema
│   │   ├── db.py                 # Dual-backend database helper
│   │   └── seed_demo.py          # Demo data seeder
│   ├── gis/matcher.py            # GPS-to-segment matching
│   ├── prediction/scoring.py     # Condition scoring & risk
│   └── vision/
│       ├── inference.py          # YOLO inference (schema 1.0)
│       ├── train.py              # YOLO training with MLflow
│       ├── build_yolo_dataset.py # RDD2022 dataset builder
│       └── convert_sample_dataset.py  # Custom dataset converter
├── tests/                        # Pytest test suite
├── docker-compose.yml            # PostgreSQL + PostGIS container
└── requirements.txt
```

## Datasets

| Dataset | Images | Classes | Source |
|---------|--------|---------|--------|
| RDD2022 India | ~15,000 | 4 (D00, D10, D20, D40) | Kaggle / RDD2022 |
| Custom Bengaluru | 69 | 3 (D40, D20, Block crack) | Field survey (Nov 2026) |

## Model Results

| Model | Dataset | mAP@50 | mAP@50-95 | Inference (ms/img) |
|-------|---------|--------|-----------|-------------------|
| YOLOv8s | RDD2022 India | **0.334** | 0.177 | ~15 (CPU) |
| YOLO11s | RDD2022 India | 0.320 | 0.162 | ~18 (CPU) |

**Selected baseline:** YOLOv8s (higher mAP@50, better generalisation).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check + DB status |
| GET | `/segments` | List all road segments |
| GET | `/segments/{id}` | Single segment detail |
| GET | `/segments/{id}/history` | Condition history over surveys |
| GET | `/risk` | Highest-risk segments |
| GET | `/stats` | Summary statistics |
| POST | `/detect` | Upload image for YOLO inference |

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11 | Core development |
| Detection | YOLOv8s (Ultralytics) | Road damage detection |
| Image Processing | OpenCV | Frame extraction, blur assessment |
| Database | PostgreSQL + PostGIS | Spatial data storage (production) |
| Database | SQLite | Offline demonstration |
| API | FastAPI + Uvicorn | RESTful backend |
| Dashboard | Streamlit + Plotly | Interactive visualisation |
| Experiment Tracking | MLflow | Training run comparison |
| Dataset Versioning | DVC | Model weights & dataset tracking |
| Containerisation | Docker Compose | PostgreSQL deployment |
| Version Control | Git / GitHub | Collaborative development |

## SDG Alignment

**SDG 11 — Sustainable Cities and Communities:** UrbanRoadAI supports evidence-based road maintenance decision-making, contributing to safer, more resilient urban infrastructure.

## Team

RVCE Engineering — Team 11

## License

This project is developed as part of the RVCE Experiential Learning programme.

---

> ⚠️ **Disclaimer:** Condition scores reflect visible surface defects only. This is not a structural pavement assessment. Risk predictions are experimental and rule-based.
