"""Shared test fixtures for UrbanRoadAI test suite."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = ROOT / "src" / "db" / "schema_sqlite.sql"


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SQLite database with schema and seed data."""
    db_path = tmp_path / "test_roads.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Apply schema
    conn.executescript(SCHEMA_SQL.read_text())
    conn.commit()

    # Seed minimal data
    conn.execute(
        "INSERT INTO corridors (corridor_id, name, notes) VALUES (?, ?, ?)",
        ("C01", "Test Corridor", "Unit test data"),
    )

    for seg in [
        ("RS_001", "C01", 100, "Test Road A", "tertiary", 300.0,
         "LINESTRING(77.5946 12.9716, 77.5960 12.9720)"),
        ("RS_002", "C01", 101, "Test Road B", "secondary", 250.0,
         "LINESTRING(77.5960 12.9720, 77.5975 12.9728)"),
    ]:
        conn.execute(
            """INSERT INTO road_segments
               (segment_id, corridor_id, osm_way_id, road_name, road_type,
                length_m, geom_wkt) VALUES (?,?,?,?,?,?,?)""",
            seg,
        )

    conn.execute(
        """INSERT INTO surveys (corridor_id, survey_date, video_file, notes)
           VALUES (?, ?, ?, ?)""",
        ("C01", "2026-10-15", "test.mp4", "Test survey"),
    )
    survey_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    for img in [
        ("IMG_001", survey_id, "RS_001", "2026-10-15T09:00:00+05:30",
         12.9716, 77.5946, 85.0, "data/test/img001.jpg"),
        ("IMG_002", survey_id, "RS_001", "2026-10-15T09:00:05+05:30",
         12.9718, 77.5950, 90.0, "data/test/img002.jpg"),
    ]:
        conn.execute(
            """INSERT INTO images
               (image_id, survey_id, segment_id, captured_at, lat, lon,
                blur_score, file_path) VALUES (?,?,?,?,?,?,?,?)""",
            img,
        )

    for det in [
        ("IMG_001", 3, 0.85, 100, 200, 300, 400, 0.03, "moderate", "yolov8s_test"),
        ("IMG_001", 2, 0.72, 50, 100, 200, 250, 0.015, "moderate", "yolov8s_test"),
        ("IMG_002", 3, 0.91, 150, 250, 350, 450, 0.05, "high", "yolov8s_test"),
    ]:
        conn.execute(
            """INSERT INTO damage_detections
               (image_id, class_id, confidence, x_min, y_min, x_max, y_max,
                area_ratio, severity, model_version) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            det,
        )

    conn.execute(
        """INSERT INTO condition_history
           (segment_id, survey_id, survey_date, score, band, n_defects, defect_density)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("RS_001", survey_id, "2026-10-15", 45.0, "fair", 3, 1.0),
    )

    conn.execute(
        """INSERT INTO predictions
           (segment_id, horizon_days, risk_prob, model_version)
           VALUES (?, ?, ?, ?)""",
        ("RS_001", 180, 0.65, "rule_v1"),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture()
def api_client(tmp_db, monkeypatch):
    """Return a Starlette TestClient wired to the tmp SQLite DB."""
    # Force SQLite mode with our tmp database
    monkeypatch.setenv("DATABASE_URL", "")
    # Patch the SQLite path in db module
    import src.db.db as db_mod
    monkeypatch.setattr(db_mod, "SQLITE_PATH", tmp_db)

    from starlette.testclient import TestClient
    from src.api.main import app
    return TestClient(app)

