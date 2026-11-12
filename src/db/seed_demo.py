"""Seed the demo database with realistic simulated road condition data.

IMPORTANT: ALL DATA IN THIS FILE IS SIMULATED.
Every row written by this script has data_source='simulated'.
The dashboard shows a "SIMULATED DEMO DATA" badge wherever this data appears.

Design goals (fixes for v1 bugs):
  1. 3 survey dates per segment (not 2).
  2. All four condition bands represented across segments.
  3. Mostly-monotonic deterioration with realistic noise.
  4. Each segment × survey has ≥1 image with detections → no zero scores
     except for genuinely good-condition readings.
  5. No duplicate detections: images are unique; each inserted once.
  6. data_source='simulated' on every row.

Bug fixes over v1 seed_demo.py:
  - v1 BUG: images assigned round-robin across all surveys, leaving some
    segment×survey pairs with zero images → score forced to 0.
    FIX: images explicitly defined per segment per survey; each survey
    gets ≥1 image on ≥1 segment.
  - v1 BUG: damage_detections inserted once per survey loop iteration,
    causing the same image's detections to be inserted multiple times.
    FIX: detections inserted only when their parent image row is inserted.
  - v1 BUG: only 1 of 10 sample images had detections (rest had 0 from
    sample_inference_output.json), making 9/10 segments score 0.
    FIX: synthetic detections defined explicitly in this file; not dependent
    on sample_inference_output.json having non-zero detections.

Run from repo root:
    python -m src.db.seed_demo
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from src.db.db import get_db

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "data" / "roads_demo.db"

DATA_SOURCE = "simulated"
MODEL_VERSION = "yolov8s_rdd-india_seed42_img640"

# ---------------------------------------------------------------------------
# Corridor
# ---------------------------------------------------------------------------
CORRIDOR = {
    "corridor_id": "C01",
    "name": "Bengaluru Field Survey Corridor (SIMULATED)",
    "notes": "Approximate route near RVCE campus. All condition data is simulated.",
    "data_source": DATA_SOURCE,
}

# ---------------------------------------------------------------------------
# 7 road segments — spread across different road types and lengths.
# Geometries approximate the GPS track from Oct 2026.
# ---------------------------------------------------------------------------
SEGMENTS = [
    {
        "segment_id": "RS_001",
        "corridor_id": "C01",
        "osm_way_id": 123456781,
        "road_name": "RVCE Main Gate Road",
        "road_type": "tertiary",
        "length_m": 310.0,
        "geom_wkt": "LINESTRING(77.5236 12.9119, 77.5245 12.9124)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_002",
        "corridor_id": "C01",
        "osm_way_id": 123456782,
        "road_name": "Mysore Road Service Road",
        "road_type": "secondary",
        "length_m": 420.0,
        "geom_wkt": "LINESTRING(77.5245 12.9124, 77.5260 12.9131)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_003",
        "corridor_id": "C01",
        "osm_way_id": 123456783,
        "road_name": "Kengeri Ring Road Stretch",
        "road_type": "primary",
        "length_m": 480.0,
        "geom_wkt": "LINESTRING(77.5260 12.9131, 77.5278 12.9138)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_004",
        "corridor_id": "C01",
        "osm_way_id": 123456784,
        "road_name": "College Campus Internal Road",
        "road_type": "residential",
        "length_m": 220.0,
        "geom_wkt": "LINESTRING(77.5278 12.9138, 77.5285 12.9143)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_005",
        "corridor_id": "C01",
        "osm_way_id": 123456785,
        "road_name": "Metro Feeder Road Segment A",
        "road_type": "tertiary",
        "length_m": 350.0,
        "geom_wkt": "LINESTRING(77.5285 12.9143, 77.5296 12.9148)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_006",
        "corridor_id": "C01",
        "osm_way_id": 123456786,
        "road_name": "Industrial Area Connector",
        "road_type": "secondary",
        "length_m": 390.0,
        "geom_wkt": "LINESTRING(77.5296 12.9148, 77.5310 12.9155)",
        "data_source": DATA_SOURCE,
    },
    {
        "segment_id": "RS_007",
        "corridor_id": "C01",
        "osm_way_id": 123456787,
        "road_name": "Bus Depot Access Road",
        "road_type": "tertiary",
        "length_m": 270.0,
        "geom_wkt": "LINESTRING(77.5310 12.9155, 77.5319 12.9160)",
        "data_source": DATA_SOURCE,
    },
]

# ---------------------------------------------------------------------------
# 3 survey dates
# ---------------------------------------------------------------------------
SURVEYS = [
    {
        "corridor_id": "C01",
        "survey_date": "2026-09-05",
        "video_file": "WhatsApp Video 2026-10-28 at 12.40.04.mp4",
        "notes": "Survey 1 — baseline (SIMULATED)",
        "data_source": DATA_SOURCE,
    },
    {
        "corridor_id": "C01",
        "survey_date": "2026-10-15",
        "video_file": "WhatsApp Video 2026-10-28 at 12.41.44.mp4",
        "notes": "Survey 2 — post-monsoon (SIMULATED)",
        "data_source": DATA_SOURCE,
    },
    {
        "corridor_id": "C01",
        "survey_date": "2026-11-05",
        "video_file": "WhatsApp Video 2026-10-28 at 12.41.50.mp4",
        "notes": "Survey 3 — latest (SIMULATED)",
        "data_source": DATA_SOURCE,
    },
]

# ---------------------------------------------------------------------------
# Synthetic images and detections per segment × survey.
#
# Each entry: (image_id, lat, lon, blur_score, detections[])
# Each detection: (class_id, confidence, x_min, y_min, x_max, y_max, area_ratio, severity)
#
# Design: segment RS_001 is "Very Poor" and deteriorating, RS_004 is "Good",
# others span Fair/Poor. Each segment×survey pair has ≥1 image.
# Survey-3 scores are higher than Survey-1 for deteriorating segments.
# ---------------------------------------------------------------------------

# Base GPS coords (lat, lon) per segment centroid (approximate)
_SEG_GPS = {
    "RS_001": (12.9122, 77.5241),
    "RS_002": (12.9128, 77.5253),
    "RS_003": (12.9135, 77.5269),
    "RS_004": (12.9141, 77.5282),
    "RS_005": (12.9146, 77.5291),
    "RS_006": (12.9152, 77.5303),
    "RS_007": (12.9158, 77.5315),
}

# Map survey index (0,1,2) → survey_date (for image captured_at)
_SURVEY_DATES = ["2026-09-05", "2026-10-15", "2026-11-05"]

# Format: { segment_id: { survey_idx: [ (image_id, blur_score, detections[]) ] } }
# detections = list of (class_id, conf, x1, y1, x2, y2, area_ratio, severity)
#
# Condition targets (approximate):
#   RS_001: Survey1=22(Good), Survey2=46(Fair), Survey3=78(VeryPoor)  — fast deterioration
#   RS_002: Survey1=28(Fair), Survey2=55(Poor), Survey3=65(Poor)      — moderate
#   RS_003: Survey1=48(Fair), Survey2=60(Poor), Survey3=74(Poor)      — slow/poor
#   RS_004: Survey1=5(Good),  Survey2=8(Good),  Survey3=12(Good)      — consistently good
#   RS_005: Survey1=35(Fair), Survey2=52(Poor), Survey3=70(Poor)      — moderate deterioration
#   RS_006: Survey1=15(Good), Survey2=30(Fair), Survey3=50(Fair)      — slow deterioration
#   RS_007: Survey1=77(VeryPoor),Survey2=80(VeryPoor),Survey3=82(VeryPoor) — chronically bad

SIMULATED_DATA: dict[str, dict[int, list]] = {
    "RS_001": {
        # Survey 1 — Good (target ~22): 1 small pothole, low confidence
        0: [("SIM_RS001_S1_001", 72.1, [
            (3, 0.42, 310, 480, 410, 560, 0.0068, "low"),
        ])],
        # Survey 2 — Fair (target ~46): 2 potholes + 1 alligator
        1: [("SIM_RS001_S2_001", 68.5, [
            (3, 0.71, 200, 400, 360, 520, 0.021, "moderate"),
            (3, 0.58, 480, 350, 610, 460, 0.019, "moderate"),
            (2, 0.65, 100, 300, 280, 420, 0.028, "moderate"),
        ])],
        # Survey 3 — Very Poor (target ~78): many potholes + alligator
        2: [("SIM_RS001_S3_001", 61.3, [
            (3, 0.88, 150, 350, 350, 520, 0.058, "high"),
            (3, 0.79, 420, 300, 600, 470, 0.052, "high"),
            (2, 0.82, 80,  250, 310, 430, 0.075, "high"),
            (3, 0.67, 580, 400, 710, 510, 0.034, "moderate"),
            (0, 0.55, 200, 500, 640, 540, 0.038, "moderate"),
        ]), ("SIM_RS001_S3_002", 59.8, [
            (3, 0.91, 180, 320, 380, 500, 0.063, "high"),
            (2, 0.74, 350, 280, 580, 450, 0.082, "high"),
        ])],
    },
    "RS_002": {
        # Survey 1 — Fair (target ~28): 1 pothole + 1 long crack
        0: [("SIM_RS002_S1_001", 75.2, [
            (3, 0.52, 250, 420, 390, 530, 0.016, "low"),
            (0, 0.48, 100, 480, 580, 510, 0.014, "low"),
        ])],
        # Survey 2 — Poor (target ~55): 3 defects
        1: [("SIM_RS002_S2_001", 70.1, [
            (3, 0.75, 180, 380, 350, 510, 0.034, "moderate"),
            (2, 0.68, 420, 320, 600, 460, 0.041, "moderate"),
            (0, 0.57, 50, 500, 630, 540, 0.022, "moderate"),
        ])],
        # Survey 3 — Poor (target ~65): deteriorated further
        2: [("SIM_RS002_S3_001", 64.8, [
            (3, 0.84, 160, 360, 360, 510, 0.052, "high"),
            (2, 0.77, 390, 300, 590, 450, 0.063, "high"),
            (0, 0.62, 40, 490, 640, 535, 0.030, "moderate"),
            (3, 0.56, 500, 400, 630, 500, 0.028, "moderate"),
        ])],
    },
    "RS_003": {
        # Survey 1 — Fair (target ~48): mixed damage
        0: [("SIM_RS003_S1_001", 71.5, [
            (2, 0.72, 150, 320, 380, 480, 0.058, "high"),
            (3, 0.61, 440, 390, 580, 500, 0.026, "moderate"),
            (1, 0.49, 50, 510, 620, 545, 0.012, "low"),
        ])],
        # Survey 2 — Poor (target ~60)
        1: [("SIM_RS003_S2_001", 66.3, [
            (2, 0.81, 140, 310, 390, 490, 0.067, "high"),
            (3, 0.74, 420, 380, 580, 490, 0.034, "moderate"),
            (3, 0.59, 580, 350, 700, 460, 0.022, "moderate"),
            (0, 0.52, 60, 500, 630, 540, 0.021, "moderate"),
        ])],
        # Survey 3 — Poor (target ~74)
        2: [("SIM_RS003_S3_001", 60.9, [
            (2, 0.87, 130, 300, 400, 495, 0.079, "high"),
            (3, 0.82, 410, 370, 590, 490, 0.047, "high"),
            (3, 0.75, 570, 340, 700, 455, 0.030, "moderate"),
            (2, 0.68, 200, 420, 420, 540, 0.052, "high"),
            (0, 0.57, 40, 495, 640, 540, 0.024, "moderate"),
        ])],
    },
    "RS_004": {
        # Survey 1 — Good (target ~5): pristine road, one tiny crack
        0: [("SIM_RS004_S1_001", 88.3, [
            (1, 0.35, 300, 500, 400, 525, 0.0028, "low"),
        ])],
        # Survey 2 — Good (target ~8): slight increase
        1: [("SIM_RS004_S2_001", 86.7, [
            (1, 0.38, 290, 498, 420, 526, 0.0034, "low"),
            (0, 0.31, 100, 510, 350, 530, 0.0023, "low"),
        ])],
        # Survey 3 — Good (target ~12): slightly more cracks but still good
        2: [("SIM_RS004_S3_001", 85.1, [
            (0, 0.44, 90, 505, 380, 535, 0.0051, "low"),
            (1, 0.37, 400, 498, 530, 522, 0.0031, "low"),
        ])],
    },
    "RS_005": {
        # Survey 1 — Fair (target ~35)
        0: [("SIM_RS005_S1_001", 69.8, [
            (3, 0.59, 220, 390, 380, 510, 0.025, "moderate"),
            (0, 0.47, 80, 505, 580, 535, 0.016, "low"),
        ])],
        # Survey 2 — Poor (target ~52)
        1: [("SIM_RS005_S2_001", 65.5, [
            (3, 0.73, 200, 375, 400, 515, 0.040, "moderate"),
            (2, 0.65, 430, 330, 610, 470, 0.052, "high"),
            (0, 0.54, 60, 500, 620, 538, 0.023, "moderate"),
        ])],
        # Survey 3 — Poor (target ~70)
        2: [("SIM_RS005_S3_001", 61.2, [
            (3, 0.81, 190, 365, 410, 520, 0.056, "high"),
            (2, 0.76, 420, 320, 615, 475, 0.069, "high"),
            (3, 0.63, 580, 380, 700, 480, 0.028, "moderate"),
            (0, 0.57, 50, 495, 635, 535, 0.027, "moderate"),
        ])],
    },
    "RS_006": {
        # Survey 1 — Good (target ~15)
        0: [("SIM_RS006_S1_001", 80.4, [
            (0, 0.46, 150, 495, 480, 525, 0.0082, "low"),
            (1, 0.38, 200, 505, 460, 525, 0.0053, "low"),
        ])],
        # Survey 2 — Fair (target ~30)
        1: [("SIM_RS006_S2_001", 74.2, [
            (3, 0.55, 310, 410, 440, 510, 0.014, "low"),
            (0, 0.51, 100, 498, 490, 530, 0.015, "low"),
            (0, 0.44, 540, 500, 640, 530, 0.0069, "low"),
        ])],
        # Survey 3 — Fair (target ~50)
        2: [("SIM_RS006_S3_001", 68.9, [
            (3, 0.68, 290, 400, 440, 510, 0.025, "moderate"),
            (2, 0.57, 100, 350, 300, 480, 0.034, "moderate"),
            (0, 0.52, 80, 497, 500, 532, 0.019, "low"),
        ])],
    },
    "RS_007": {
        # Survey 1 — Very Poor (target ~77): chronically bad road
        0: [("SIM_RS007_S1_001", 55.3, [
            (3, 0.89, 100, 300, 320, 490, 0.080, "high"),
            (2, 0.84, 350, 280, 580, 460, 0.090, "high"),
            (3, 0.77, 550, 320, 700, 450, 0.048, "high"),
        ]), ("SIM_RS007_S1_002", 52.1, [
            (3, 0.91, 150, 310, 370, 500, 0.085, "high"),
            (2, 0.79, 400, 290, 630, 470, 0.092, "high"),
        ])],
        # Survey 2 — Very Poor (target ~80)
        1: [("SIM_RS007_S2_001", 51.8, [
            (3, 0.92, 90, 295, 330, 495, 0.088, "high"),
            (2, 0.86, 340, 275, 590, 465, 0.096, "high"),
            (3, 0.81, 540, 315, 700, 450, 0.055, "high"),
            (0, 0.68, 60, 490, 650, 530, 0.040, "moderate"),
        ])],
        # Survey 3 — Very Poor (target ~82): slightly worsened
        2: [("SIM_RS007_S3_001", 50.4, [
            (3, 0.93, 85, 290, 335, 500, 0.092, "high"),
            (2, 0.88, 335, 270, 595, 470, 0.100, "high"),
            (3, 0.83, 535, 310, 705, 455, 0.059, "high"),
            (0, 0.71, 55, 488, 655, 532, 0.044, "moderate"),
            (3, 0.64, 180, 340, 310, 450, 0.030, "moderate"),
        ])],
    },
}


def _severity_from_area(area_ratio: float) -> str:
    """Derive severity label from bounding-box area ratio (documented estimate)."""
    if area_ratio >= 0.05:
        return "high"
    elif area_ratio >= 0.01:
        return "moderate"
    return "low"


def seed() -> None:  # noqa: C901
    """Seed the demo database. Idempotent — safe to call multiple times."""
    # Delete old DB to start fresh (avoids UNIQUE conflicts from schema changes)
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()
        print(f"  Removed old database: {SQLITE_PATH.name}")

    db = get_db()

    # ---- corridor ----------------------------------------------------------
    db.execute(
        "INSERT OR IGNORE INTO corridors (corridor_id, name, notes, data_source)"
        " VALUES (?,?,?,?)",
        (CORRIDOR["corridor_id"], CORRIDOR["name"],
         CORRIDOR["notes"], CORRIDOR["data_source"]),
    )

    # ---- road segments -----------------------------------------------------
    for seg in SEGMENTS:
        db.execute(
            """INSERT OR IGNORE INTO road_segments
               (segment_id, corridor_id, osm_way_id, road_name, road_type,
                length_m, geom_wkt, data_source)
               VALUES (?,?,?,?,?,?,?,?)""",
            (seg["segment_id"], seg["corridor_id"], seg["osm_way_id"],
             seg["road_name"], seg["road_type"], seg["length_m"],
             seg["geom_wkt"], seg["data_source"]),
        )

    # ---- surveys -----------------------------------------------------------
    survey_ids: list[int] = []
    for sv in SURVEYS:
        db.execute(
            """INSERT OR IGNORE INTO surveys
               (corridor_id, survey_date, video_file, notes, data_source)
               VALUES (?,?,?,?,?)""",
            (sv["corridor_id"], sv["survey_date"], sv["video_file"],
             sv["notes"], sv["data_source"]),
        )
        row = db.fetch_one(
            "SELECT survey_id FROM surveys"
            " WHERE corridor_id=? AND survey_date=?",
            (sv["corridor_id"], sv["survey_date"]),
        )
        survey_ids.append(row["survey_id"])

    # ---- images + detections (one pass per segment × survey) ---------------
    total_images = 0
    total_detections = 0

    for seg in SEGMENTS:
        seg_id = seg["segment_id"]
        lat_base, lon_base = _SEG_GPS[seg_id]

        for sv_idx, survey_id in enumerate(survey_ids):
            survey_date = _SURVEY_DATES[sv_idx]
            images_this_survey = SIMULATED_DATA.get(seg_id, {}).get(sv_idx, [])

            for img_tuple in images_this_survey:
                img_id, blur, dets = img_tuple

                # Small GPS jitter per image
                lat = lat_base + (hash(img_id) % 100) * 0.000005
                lon = lon_base + (hash(img_id) % 73) * 0.000005

                db.execute(
                    """INSERT OR IGNORE INTO images
                       (image_id, survey_id, segment_id, captured_at,
                        lat, lon, blur_score, file_path, data_source)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (img_id, survey_id, seg_id,
                     f"{survey_date}T09:00:00+05:30",
                     lat, lon, blur,
                     f"data/simulated/{img_id}.jpg",
                     DATA_SOURCE),
                )
                total_images += 1

                # Insert detections for this image
                for det in dets:
                    cid, conf, x1, y1, x2, y2, area, sev = det
                    db.execute(
                        """INSERT INTO damage_detections
                           (image_id, class_id, confidence,
                            x_min, y_min, x_max, y_max,
                            area_ratio, severity, model_version, data_source)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (img_id, cid, conf, x1, y1, x2, y2,
                         area, sev, MODEL_VERSION, DATA_SOURCE),
                    )
                    total_detections += 1

    # ---- condition history (computed from detections) ----------------------
    from src.prediction.scoring import score_segment

    for seg in SEGMENTS:
        seg_id = seg["segment_id"]
        for sv_idx, survey_id in enumerate(survey_ids):
            dets = db.fetch_all(
                """SELECT d.class_id, d.confidence, d.area_ratio, d.severity
                   FROM damage_detections d
                   JOIN images i ON d.image_id = i.image_id
                   WHERE i.segment_id = ? AND i.survey_id = ?""",
                (seg_id, survey_id),
            )
            result = score_segment(dets, seg["length_m"])
            sv_row = db.fetch_one(
                "SELECT survey_date FROM surveys WHERE survey_id=?",
                (survey_id,),
            )
            db.execute(
                """INSERT OR IGNORE INTO condition_history
                   (segment_id, survey_id, survey_date, score, band,
                    n_defects, defect_density, data_source)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (seg_id, survey_id, sv_row["survey_date"],
                 result["score"], result["band"],
                 result["n_defects"], result["defect_density"],
                 DATA_SOURCE),
            )

    # ---- predictions (rule-based risk) -------------------------------------
    from src.prediction.scoring import predict_risk

    for seg in SEGMENTS:
        seg_id = seg["segment_id"]
        history = db.fetch_all(
            "SELECT * FROM condition_history"
            " WHERE segment_id=? ORDER BY survey_date",
            (seg_id,),
        )
        risk = predict_risk(history, seg["road_type"])
        db.execute(
            """INSERT INTO predictions
               (segment_id, horizon_days, risk_prob, model_version, data_source)
               VALUES (?,?,?,?,?)""",
            (seg_id, risk["horizon_days"], risk["risk_prob"],
             risk["model_version"], DATA_SOURCE),
        )

    db.close()

    # ---- report ------------------------------------------------------------
    print(f"✓ Demo database seeded at {SQLITE_PATH}")
    print(f"  Corridor: {CORRIDOR['name']}")
    print(f"  Segments: {len(SEGMENTS)}")
    print(f"  Surveys:  {len(SURVEYS)} ({', '.join(s['survey_date'] for s in SURVEYS)})")
    print(f"  Images:   {total_images}")
    print(f"  Detections: {total_detections}")
    print(f"  data_source: ALL '{DATA_SOURCE}'")
    print()
    print("  Condition scores per segment (should span all 4 bands):")
    # Re-open to query
    db2 = get_db()
    for seg in SEGMENTS:
        rows = db2.fetch_all(
            "SELECT survey_date, score, band FROM condition_history"
            " WHERE segment_id=? ORDER BY survey_date",
            (seg["segment_id"],),
        )
        scores = " → ".join(f"{r['score']:.1f}({r['band']})" for r in rows)
        print(f"    {seg['segment_id']} [{seg['road_name'][:28]}]: {scores}")
    db2.close()


if __name__ == "__main__":
    seed()
