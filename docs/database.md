# Database Design

## Overview

UrbanRoadAI uses a **dual-backend database architecture**:
- **PostgreSQL + PostGIS** for production spatial queries
- **SQLite** for offline demonstration and testing

Both backends share the same logical schema. The `src/db/db.py` helper auto-detects which backend to use based on the `DATABASE_URL` environment variable.

## Entity-Relationship Diagram

```
corridors ──────────┐
  corridor_id (PK)  │
  name              │
  notes             │
                    │
road_segments ◄─────┘      surveys ◄────── corridors
  segment_id (PK)            survey_id (PK)
  corridor_id (FK)           corridor_id (FK)
  osm_way_id                 survey_date
  road_name                  video_file
  road_type                  notes
  length_m
  geom (PostGIS) /
  geom_wkt (SQLite)
        │                        │
        │    ┌───────────────────┘
        │    │
        ▼    ▼
      images
        image_id (PK)
        survey_id (FK)
        segment_id (FK)
        captured_at
        lat, lon
        blur_score
        file_path
            │
            ▼
      damage_detections           damage_classes
        detection_id (PK)           class_id (PK)
        image_id (FK)    ────────►  class_name
        class_id (FK)
        confidence
        x_min, y_min, x_max, y_max
        area_ratio
        severity
        model_version

      condition_history           predictions
        segment_id (FK)             segment_id (FK)
        survey_id (FK)              horizon_days
        survey_date                 risk_prob
        score                       model_version
        band                        made_at
        n_defects
        defect_density

      weather_data                maintenance_records
        corridor_id (FK)            segment_id (FK)
        obs_date                    done_on
        rainfall_mm                 work_type
        temp_c, humidity_pct        source
```

## Table Descriptions

### Core Tables

| Table | Purpose | Row Count (typical) |
|-------|---------|-------------------|
| `corridors` | Survey routes/corridors | 1-5 |
| `road_segments` | Individual road segments (~200-400 m each) | 5-50 |
| `surveys` | Dated survey events | 2-10 |
| `images` | Individual analysed frames with GPS | 10-1000 |
| `damage_detections` | One row per detected defect | 10-5000 |
| `damage_classes` | Lookup table (4 rows, frozen) | 4 |

### Derived Tables

| Table | Purpose | Computed By |
|-------|---------|-------------|
| `condition_history` | Score per segment per survey | `score_segment()` |
| `predictions` | Risk probability per segment | `predict_risk()` |

### Supporting Tables

| Table | Purpose | Source |
|-------|---------|--------|
| `weather_data` | Environmental context | External API (future) |
| `maintenance_records` | Known repair history | Manual entry (future) |

## Dual-Backend Design

```python
# Auto-detection in src/db/db.py
def get_db(url=None):
    url = url or os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql"):
        return _PostgresDB(url)      # psycopg + connection pool
    return _SQLiteDB(str(SQLITE_PATH))  # sqlite3 stdlib
```

### PostgreSQL + PostGIS (Production)

- Geometry column: `geom GEOMETRY(LineString, 4326)`
- Spatial queries: `ST_AsGeoJSON()`, `ST_DWithin()`, `ST_Distance()`
- Connection pooling via `psycopg_pool`
- Schema: `src/db/schema.sql`
- Deployment: `docker-compose.yml` (PostGIS 16-3.4)

### SQLite (Demonstration)

- Geometry stored as WKT text: `geom_wkt TEXT`
- Spatial calculations done in Python (haversine)
- Auto-creates tables on first connection
- Schema: `src/db/schema_sqlite.sql`
- No external dependencies

## Key Design Decisions

1. **`segment_id` is TEXT, not SERIAL** — Format `RS_001`, human-readable, consistent across backends.
2. **`image_id` is TEXT** — Derived from the frame filename, not auto-generated.
3. **`area_ratio` stored, not computed** — Avoids re-reading image dimensions at query time.
4. **`severity` is derived from `area_ratio`** — Low (<1%), Moderate (1-5%), High (>5%). Documented limitation: bounding-box area ≠ actual damage area.
5. **Timestamps stored with timezone** — Convention: Asia/Kolkata (IST).
6. **CRS: EPSG:4326** — Standard WGS 84 for all coordinates.

