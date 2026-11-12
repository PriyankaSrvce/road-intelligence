"""UrbanRoadAI FastAPI backend.

Supports two database backends:
  - PostgreSQL + PostGIS  (set DATABASE_URL env var)
  - SQLite               (default, for offline demonstration)

Run:
    uvicorn src.api.main:app --reload --port 8000
Or:
    python -m src.api.main
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the project root is on sys.path so imports work.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.db import get_db, is_postgres  # noqa: E402

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UrbanRoadAI API",
    version="0.2",
    description="AI-powered urban road condition monitoring and maintenance prioritization.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db():
    """Return a database wrapper (created per request for SQLite thread safety)."""
    return get_db()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Health check — verifies the database connection."""
    db = _db()
    try:
        db.fetch_one("SELECT 1")
        backend = "postgresql" if is_postgres() else "sqlite"
        return {"status": "ok", "database": backend}
    except Exception as exc:
        raise HTTPException(503, f"Database unavailable: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------

@app.get("/segments")
def list_segments():
    """List all road segments with their basic info."""
    db = _db()
    try:
        if is_postgres():
            return db.fetch_all(
                """SELECT segment_id, corridor_id, road_name, road_type,
                          length_m, ST_AsGeoJSON(geom)::json AS geometry
                   FROM road_segments ORDER BY segment_id""")
        else:
            return db.fetch_all(
                """SELECT segment_id, corridor_id, road_name, road_type,
                          length_m, geom_wkt AS geometry
                   FROM road_segments ORDER BY segment_id""")
    finally:
        db.close()


@app.get("/segments/{segment_id}")
def segment(segment_id: str):
    """Get a single road segment by ID."""
    db = _db()
    try:
        if is_postgres():
            row = db.fetch_one(
                """SELECT segment_id, corridor_id, road_name, road_type,
                          length_m, ST_AsGeoJSON(geom)::json AS geometry
                   FROM road_segments WHERE segment_id = %s""",
                (segment_id,))
        else:
            row = db.fetch_one(
                """SELECT segment_id, corridor_id, road_name, road_type,
                          length_m, geom_wkt AS geometry
                   FROM road_segments WHERE segment_id = ?""",
                (segment_id,))
        if not row:
            raise HTTPException(404, "segment not found")
        return row
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Condition history
# ---------------------------------------------------------------------------

@app.get("/segments/{segment_id}/history")
def history(segment_id: str):
    """Get the condition history for a road segment."""
    db = _db()
    try:
        placeholder = "%s" if is_postgres() else "?"
        return db.fetch_all(
            f"""SELECT survey_date, score, band, n_defects, defect_density
                FROM condition_history WHERE segment_id = {placeholder}
                ORDER BY survey_date""",
            (segment_id,))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Risk / maintenance prioritization
# ---------------------------------------------------------------------------

@app.get("/risk")
def risk(top: int = Query(20, ge=1, le=200)):
    """Highest-risk segments, using each segment's latest prediction."""
    db = _db()
    try:
        if is_postgres():
            return db.fetch_all(
                """SELECT * FROM (
                     SELECT DISTINCT ON (p.segment_id)
                            p.segment_id, p.risk_prob, p.horizon_days,
                            p.model_version, p.made_at, r.road_name
                     FROM predictions p JOIN road_segments r USING (segment_id)
                     ORDER BY p.segment_id, p.made_at DESC) latest
                   ORDER BY risk_prob DESC LIMIT %s""",
                (top,))
        else:
            # SQLite: no DISTINCT ON, use a subquery.
            return db.fetch_all(
                """SELECT p.segment_id, p.risk_prob, p.horizon_days,
                          p.model_version, p.made_at, r.road_name
                   FROM predictions p
                   JOIN road_segments r ON p.segment_id = r.segment_id
                   WHERE p.id = (
                       SELECT p2.id FROM predictions p2
                       WHERE p2.segment_id = p.segment_id
                       ORDER BY p2.made_at DESC LIMIT 1)
                   ORDER BY p.risk_prob DESC LIMIT ?""",
                (top,))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Defect detection (image upload)
# ---------------------------------------------------------------------------

@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    """Run YOLO inference on an uploaded road image.

    If model weights are available, runs actual inference via
    src.vision.inference.run_inference().  Otherwise returns a clear
    error message explaining the dependency.
    """
    # Validate the upload.
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "Upload must be an image file (JPEG/PNG).")

    contents = await image.read()
    if len(contents) == 0:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 20 MB).")

    # Save to a temp file for inference.
    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from src.vision.inference import run_inference, to_db_rows
        result = run_inference(tmp_path, image_id=Path(image.filename).stem)

        # Persist detections to database.
        db = _db()
        try:
            rows = to_db_rows(result)
            # Note: in a production system we would also insert an images row.
            # For now, return the inference result.
            return result
        finally:
            db.close()

    except FileNotFoundError:
        raise HTTPException(
            503,
            "Model weights not found.  Download the .pt file via "
            "'dvc pull models/yolov8s_rdd_india_baseline.pt.dvc' or place "
            "it manually in models/.",
        )
    except ImportError as exc:
        raise HTTPException(
            503,
            f"Vision dependencies not installed: {exc}.  "
            "Run 'pip install ultralytics' to enable inference.",
        )
    except Exception as exc:
        raise HTTPException(500, f"Inference failed: {exc}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Statistics summary
# ---------------------------------------------------------------------------

@app.get("/stats")
def stats():
    """Return summary statistics for the dashboard."""
    db = _db()
    try:
        total_segments = db.fetch_one(
            "SELECT COUNT(*) as n FROM road_segments")["n"]
        total_images = db.fetch_one(
            "SELECT COUNT(*) as n FROM images")["n"]
        total_detections = db.fetch_one(
            "SELECT COUNT(*) as n FROM damage_detections")["n"]
        total_surveys = db.fetch_one(
            "SELECT COUNT(*) as n FROM surveys")["n"]

        class_dist = db.fetch_all(
            """SELECT dc.class_name, COUNT(*) as count
               FROM damage_detections dd
               JOIN damage_classes dc ON dd.class_id = dc.class_id
               GROUP BY dc.class_name ORDER BY count DESC""")

        band_dist = db.fetch_all(
            """SELECT band, COUNT(*) as count
               FROM condition_history GROUP BY band""")

        return {
            "total_segments": total_segments,
            "total_images": total_images,
            "total_detections": total_detections,
            "total_surveys": total_surveys,
            "defect_class_distribution": class_dist,
            "condition_band_distribution": band_dist,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

