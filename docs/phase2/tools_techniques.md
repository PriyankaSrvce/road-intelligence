# Tools & Techniques — Selection, Application and Integration

## Technology Selection Table

| Tool | Category | Why Selected | Alternatives Considered | Practical Role in Project |
|------|----------|-------------|------------------------|--------------------------|
| **Python 3.11** | Language | Team expertise; rich ML/CV/GIS ecosystem | C++ (too low-level), Java (less ML support) | All source code |
| **YOLOv8s** | Detection | Best mAP@50 (0.334) on our dataset; fast CPU inference; Ultralytics framework | YOLO11s (lower mAP), Faster R-CNN (too slow on CPU), SSD (less accurate) | Detects 4 road damage classes from images |
| **OpenCV** | Image Processing | Industry standard; VideoCapture, blur detection, I/O | Pillow (fewer features), scikit-image (slower video) | Frame extraction, Laplacian blur scoring |
| **RDD2022** | Benchmark Dataset | Standard road damage dataset; India subset with relevant damage types | Custom only (too small for training), ROADS (different classes) | Training and validation of YOLOv8s |
| **Custom Bengaluru Dataset** | Local Dataset | Real local road conditions; GPS-annotated | Synthetic data (not representative), Google Street View (no control) | 69 annotated images for local validation |
| **PostgreSQL + PostGIS** | Spatial DB | Mature spatial database; ST_* functions; scalable | MongoDB (weaker spatial), SpatiaLite (limited), MySQL (no native spatial) | Production spatial data storage |
| **SQLite** | Demo DB | Zero-config; Python stdlib; portable | In-memory only, H2 | Offline demonstration without Docker |
| **FastAPI** | Backend | Async; auto-docs (OpenAPI); type validation; Pythonic | Flask (no validation), Django (heavy), Express.js (different language) | 7 REST endpoints serving road data |
| **Streamlit** | Dashboard | Rapid prototyping; Python-native; interactive widgets | Dash (more boilerplate), Grafana (separate stack), React (long dev time) | 6-page interactive dashboard |
| **Plotly** | Charting | Interactive charts; mapbox integration; consistent style | Matplotlib (static), Altair (less map support) | Bar, pie, line, histogram, scatter map |
| **MLflow** | Experiment Tracking | Structured logging; model comparison; artifact storage | W&B (paid tier needed), TensorBoard (less structured) | Training run metrics and comparison |
| **DVC** | Dataset Versioning | Git-like workflow; GDrive remote; reproducible pipelines | Git LFS (no pipeline), manual (error-prone) | Track model weights and large datasets |
| **Docker Compose** | Containerisation | Reproducible PostGIS deployment; one-command setup | Manual PostgreSQL install (not portable), Kubernetes (overkill) | PostGIS container for production mode |
| **Git / GitHub** | Version Control | Industry standard; branch-based collaboration; PR workflow | SVN (outdated), Mercurial (less ecosystem) | 6 feature branches, collaborative development |
| **pytest** | Testing | Fixtures; parameterisation; wide adoption | unittest (verbose), nose (deprecated) | 30+ test cases across 5 modules |

## Application Evidence

Every tool has a demonstrable, practical role:

| Tool | Claim | Evidence |
|------|-------|---------|
| OpenCV | Frame extraction + blur detection | `scripts/extract_sample_frames.py` — processes MP4 → JPEG with blur scores |
| YOLOv8s | Road damage detection | `docs/sample_inference_output.json` — 10 real inference results |
| PostGIS | Spatial data storage | `src/db/schema.sql` — 9 tables with GEOMETRY columns |
| SQLite | Offline demo database | `data/roads_demo.db` — seeded by `src/db/seed_demo.py` |
| FastAPI | REST API | 7 working endpoints; auto-generated Swagger at `/docs` |
| Streamlit | Dashboard | 6 pages: Overview, Map, Segment Detail, Defect Analysis, Survey Comparison, Maintenance Priority |
| MLflow | Experiment tracking | `src/vision/train.py` logs metrics, params, and artifacts to MLflow |
| DVC | Dataset versioning | `data/processed/rdd2022_india.dvc`, `models/*.pt.dvc` |
| Docker | PostGIS deployment | `docker-compose.yml` — one-command `docker compose up` |
| pytest | Testing | `tests/` — 5 test files, 30+ tests covering scoring, API, GIS, conversion |

## Integration Evidence

The components exchange structured data through well-defined contracts:

| Integration | From → To | Contract | Working? |
|------------|-----------|----------|----------|
| Image → Detection | JPEG → `inference.py` | File path → Schema 1.0 JSON | ✅ |
| Detection → Database | Schema 1.0 → `to_db_rows()` → SQL INSERT | Dict list → `damage_detections` rows | ✅ |
| GPS → Segment | Lat/lon → `match_to_segment()` | Coordinates → MatchResult | ✅ |
| Database → Scoring | SQL SELECT → `score_segment()` | Detection dicts → score/band | ✅ |
| Scoring → Database | Score dict → SQL INSERT | Score → `condition_history` row | ✅ |
| Database → API | SQL queries → JSON responses | Dict rows → HTTP JSON | ✅ |
| API → Dashboard | HTTP GET → Streamlit display | JSON → DataFrames → Plotly charts | ✅ |
| Database → Dashboard | SQLite direct read → display | SQL → pandas → Plotly | ✅ |

