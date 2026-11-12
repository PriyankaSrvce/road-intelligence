# Demo Guide

## Prerequisites

- Python 3.11+
- Git
- ~500 MB disk space

## Step-by-Step Demo

### 1. Set Up Environment

```bash
cd road-intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Convert Custom Dataset (Optional)

If `data/sample_dataset/` contains the 69 annotated Bengaluru road images:

```bash
python -m src.vision.convert_sample_dataset
```

**Expected output:**
```
✓ Converted 69 images, 93 annotations
  Mapped:  90
  Dropped: 3 (Repair class)

  Class counts (frozen IDs):
    2 (alligator_crack): 41
    3 (pothole): 49

  YOLO labels:  data/sample_dataset_yolo/labels
  Metadata CSV: data/sample_dataset_yolo/frame_metadata.csv
  Dataset YAML: data/sample_dataset_yolo/dataset.yaml
```

### 3. Seed the Demo Database

```bash
python -m src.db.seed_demo
```

**Expected output:**
```
✓ Demo database seeded at data/roads_demo.db
  Corridor: SRV College Morning Route
  Segments: 5
  Surveys:  2
  Images:   10
```

### 4. Verify the Database

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/roads_demo.db')
for table in ['corridors','road_segments','surveys','images','damage_detections','condition_history','predictions']:
    n = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'  {table}: {n} rows')
conn.close()
"
```

### 5. Run Tests

```bash
python -m pytest tests/ -v
```

### 6. Start the API

```bash
uvicorn src.api.main:app --reload --port 8000
```

**Test endpoints:**
- Health: http://localhost:8000/health
- Segments: http://localhost:8000/segments
- Stats: http://localhost:8000/stats
- Risk: http://localhost:8000/risk
- Swagger UI: http://localhost:8000/docs

### 7. Start the Dashboard

In a **new terminal**:

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

**Opens at:** http://localhost:8501

### 8. Dashboard Walkthrough

1. **Overview** — See total segments, surveys, images, detections. Condition band pie chart. Top risk segments.
2. **Map View** — Interactive map with colour-coded segments (green=good, red=very poor).
3. **Segment Detail** — Select a segment to see condition history chart, defect breakdown, risk prediction.
4. **Defect Analysis** — Class distribution, confidence histogram, severity and area ratio charts.
5. **Survey Comparison** — Compare two surveys side-by-side. See which segments improved or worsened.
6. **Maintenance Priority** — Ranked table of segments by risk probability.

### 9. YOLO Inference (Requires Model Weights)

If model weights are available at `models/yolov8s_rdd_india_baseline.pt`:

```bash
# Via API
curl -X POST http://localhost:8000/detect \
  -F "image=@data/sample_dataset/images/sample_road_frame_000000.jpg"

# Via command line
python src/vision/inference.py --source data/sample_dataset/images/ --limit 5
```

If weights are not available, the `/detect` endpoint returns a 503 with instructions.

### 10. Docker + PostgreSQL (Optional)

```bash
# Start PostGIS container
docker compose up -d

# Set connection string
export DATABASE_URL="postgresql://roads_user:roads_pass@localhost:5432/roads_db"

# Restart API (will use PostgreSQL)
uvicorn src.api.main:app --reload --port 8000
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Database not found` | Run `python -m src.db.seed_demo` |
| `Model weights not found` | Run `dvc pull models/yolov8s_rdd_india_baseline.pt.dvc` |
| Dashboard shows no data | Ensure `data/roads_demo.db` exists |
| Port 8000 in use | Use `--port 8001` |

