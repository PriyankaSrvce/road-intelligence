# API Documentation

## Overview

The UrbanRoadAI API is built with **FastAPI** and serves road condition data to the dashboard and external clients. It supports both PostgreSQL and SQLite backends.

**Base URL:** `http://localhost:8000`

## Starting the API

```bash
# Using uvicorn
uvicorn src.api.main:app --reload --port 8000

# Using Python module
python -m src.api.main

# Auto-generated docs
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

## Endpoints

### GET /health

Health check — verifies database connectivity.

**Response (200):**
```json
{
  "status": "ok",
  "database": "sqlite"
}
```

**Response (503):** Database unavailable.

---

### GET /segments

List all road segments.

**Response (200):**
```json
[
  {
    "segment_id": "RS_001",
    "corridor_id": "C01",
    "road_name": "College Road (Demo Seg 1)",
    "road_type": "tertiary",
    "length_m": 320.0,
    "geometry": "LINESTRING(77.5946 12.9716, 77.5960 12.9720)"
  }
]
```

---

### GET /segments/{segment_id}

Get a single road segment by ID.

**Parameters:**
- `segment_id` (path, string): Segment identifier (e.g., `RS_001`)

**Response (200):** Single segment object.
**Response (404):** `"segment not found"`

---

### GET /segments/{segment_id}/history

Condition history for a road segment across surveys.

**Response (200):**
```json
[
  {
    "survey_date": "2026-10-15",
    "score": 45.0,
    "band": "fair",
    "n_defects": 3,
    "defect_density": 1.0
  },
  {
    "survey_date": "2026-11-01",
    "score": 52.3,
    "band": "poor",
    "n_defects": 5,
    "defect_density": 1.67
  }
]
```

---

### GET /risk

Highest-risk segments ranked by risk probability.

**Query Parameters:**
- `top` (int, default=20, min=1, max=200): Number of segments to return.

**Response (200):**
```json
[
  {
    "segment_id": "RS_004",
    "risk_prob": 0.72,
    "horizon_days": 180,
    "model_version": "rule_v1",
    "made_at": "2026-11-11T15:30:00",
    "road_name": "Ring Road Section (Demo Seg 4)"
  }
]
```

---

### GET /stats

Summary statistics for the dashboard.

**Response (200):**
```json
{
  "total_segments": 5,
  "total_images": 10,
  "total_detections": 25,
  "total_surveys": 2,
  "defect_class_distribution": [
    {"class_name": "pothole", "count": 15},
    {"class_name": "alligator_crack", "count": 8}
  ],
  "condition_band_distribution": [
    {"band": "fair", "count": 3},
    {"band": "good", "count": 2}
  ]
}
```

---

### POST /detect

Upload an image for YOLO inference.

**Request:** Multipart file upload (`image` field).

**Constraints:**
- Content-Type must start with `image/`
- Maximum file size: 20 MB
- Supported formats: JPEG, PNG

**Response (200):** Vision schema 1.0 result:
```json
{
  "schema_version": "1.0",
  "image_id": "frame_001",
  "image_width": 640,
  "image_height": 640,
  "model_version": "yolov8s_rdd-india_seed42_img640",
  "conf_threshold": 0.25,
  "inference_ms": 15.2,
  "num_detections": 2,
  "detections": [
    {
      "class_id": 3,
      "class_code": "D40",
      "class_name": "pothole",
      "confidence": 0.87,
      "x_min": 120.5, "y_min": 200.3,
      "x_max": 280.1, "y_max": 350.7,
      "area_ratio": 0.058,
      "model_version": "yolov8s_rdd-india_seed42_img640"
    }
  ]
}
```

**Error Responses:**
- **400:** Invalid file type or empty file.
- **413:** Image too large.
- **503:** Model weights not found or vision dependencies not installed.
- **500:** Inference failure.

## CORS

All origins allowed (`*`) for development. Should be restricted in production.

## Error Format

```json
{
  "detail": "Error message here"
}
```

