"""Regression tests for the RS_001/history score-drops-to-zero bug.

Bug fixed: seed_demo v1 assigned images round-robin regardless of which
survey they belonged to, leaving some segment×survey pairs with zero images
and therefore a forced score of 0.0 — even for segments with real detections.

These tests verify:
  1. No segment has a score of 0 when it has detections in that survey.
  2. All 4 condition bands appear across the seeded segments.
  3. Condition scores are within [0, 100].
  4. Each segment has ≥ 3 survey entries.
  5. data_source column is present and set to 'simulated'.
  6. No duplicate detections for the same image.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def demo_db():
    """Return a connection to the seeded demo database.

    Requires `python -m src.db.seed_demo` to have been run.
    """
    db_path = Path(__file__).resolve().parents[1] / "data" / "roads_demo.db"
    if not db_path.exists():
        pytest.skip(
            f"Demo database not found at {db_path}. "
            "Run `python -m src.db.seed_demo` first."
        )
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestScoreIntegrity:
    """Core regression suite for the 60→0 score-drop bug."""

    def test_no_zero_score_when_detections_exist(self, demo_db):
        """A segment×survey with ≥1 detection must NOT have score = 0."""
        rows = demo_db.execute(
            """SELECT ch.segment_id, ch.survey_id, ch.score,
                      COUNT(dd.detection_id) as n_dets
               FROM condition_history ch
               JOIN images i
                 ON i.segment_id = ch.segment_id AND i.survey_id = ch.survey_id
               LEFT JOIN damage_detections dd ON dd.image_id = i.image_id
               GROUP BY ch.segment_id, ch.survey_id, ch.score"""
        ).fetchall()

        violations = [
            dict(r) for r in rows
            if r["n_dets"] > 0 and r["score"] == 0.0
        ]
        assert violations == [], (
            f"Segments with detections but score=0.0: {violations}\n"
            "This is the regression for the seed_demo v1 bug."
        )

    def test_scores_in_valid_range(self, demo_db):
        """All condition scores must be in [0, 100]."""
        rows = demo_db.execute(
            "SELECT segment_id, survey_date, score FROM condition_history"
        ).fetchall()
        for r in rows:
            assert 0.0 <= r["score"] <= 100.0, (
                f"Score out of range: {r['segment_id']} {r['survey_date']} → {r['score']}"
            )

    def test_all_four_bands_present(self, demo_db):
        """All four bands (good/fair/poor/very_poor) must appear in condition_history."""
        bands = {
            r[0] for r in demo_db.execute(
                "SELECT DISTINCT band FROM condition_history"
            ).fetchall()
        }
        required = {"good", "fair", "poor", "very_poor"}
        missing = required - bands
        assert not missing, (
            f"Missing condition bands: {missing}. "
            f"Found: {bands}. Seed data must cover all four bands."
        )

    def test_each_segment_has_three_surveys(self, demo_db):
        """Each segment must have exactly 3 survey entries in condition_history."""
        rows = demo_db.execute(
            """SELECT segment_id, COUNT(*) as n
               FROM condition_history GROUP BY segment_id"""
        ).fetchall()
        assert rows, "No condition_history rows found."
        for r in rows:
            assert r["n"] >= 3, (
                f"Segment {r['segment_id']} has only {r['n']} survey entries. "
                "Expected ≥ 3."
            )

    def test_rs001_deteriorates(self, demo_db):
        """RS_001 should worsen over surveys (fastest deterioration segment)."""
        rows = demo_db.execute(
            """SELECT score FROM condition_history
               WHERE segment_id='RS_001' ORDER BY survey_date"""
        ).fetchall()
        scores = [r["score"] for r in rows]
        assert len(scores) >= 2, "RS_001 needs at least 2 survey entries."
        assert scores[-1] > scores[0], (
            f"RS_001 should worsen over time but scores are: {scores}"
        )

    def test_rs001_last_survey_not_zero(self, demo_db):
        """RS_001's latest survey must not be 0.0 (regression for the original bug)."""
        row = demo_db.execute(
            """SELECT score FROM condition_history
               WHERE segment_id='RS_001' ORDER BY survey_date DESC LIMIT 1"""
        ).fetchone()
        assert row is not None
        assert row["score"] > 0.0, (
            f"RS_001 latest score is {row['score']} — must be > 0 (regression test)."
        )


class TestDataSource:
    """Verify data_source column is present and correct on all tables."""

    def test_condition_history_all_simulated(self, demo_db):
        rows = demo_db.execute(
            "SELECT COUNT(*) as n FROM condition_history WHERE data_source='simulated'"
        ).fetchone()
        total = demo_db.execute(
            "SELECT COUNT(*) as n FROM condition_history"
        ).fetchone()
        assert rows["n"] == total["n"], (
            f"Only {rows['n']} / {total['n']} condition_history rows marked 'simulated'."
        )

    def test_road_segments_have_data_source(self, demo_db):
        rows = demo_db.execute(
            "SELECT COUNT(*) as n FROM road_segments WHERE data_source IS NOT NULL"
        ).fetchone()
        total = demo_db.execute(
            "SELECT COUNT(*) as n FROM road_segments"
        ).fetchone()
        assert rows["n"] == total["n"], "Some road_segment rows missing data_source."

    def test_predictions_all_simulated(self, demo_db):
        rows = demo_db.execute(
            "SELECT COUNT(*) as n FROM predictions WHERE data_source='simulated'"
        ).fetchone()
        total = demo_db.execute(
            "SELECT COUNT(*) as n FROM predictions"
        ).fetchone()
        assert rows["n"] == total["n"]

    def test_no_invalid_data_source_values(self, demo_db):
        """data_source must only be 'real' or 'simulated'."""
        for table in ["road_segments", "surveys", "images",
                      "damage_detections", "condition_history", "predictions"]:
            try:
                rows = demo_db.execute(
                    f"SELECT COUNT(*) as n FROM {table} "
                    "WHERE data_source NOT IN ('real','simulated')"
                ).fetchone()
                assert rows["n"] == 0, (
                    f"Table {table} has {rows['n']} rows with invalid data_source."
                )
            except sqlite3.OperationalError:
                pytest.skip(f"Table {table} has no data_source column (schema not updated).")


class TestNoduplicateDetections:
    """Verify the duplicate-detection bug (v1 seed inserted detections per survey loop)."""

    def test_no_duplicate_detection_rows(self, demo_db):
        """Each (image_id, class_id, x_min, y_min) combination should appear once."""
        rows = demo_db.execute(
            """SELECT image_id, class_id, x_min, y_min, COUNT(*) as n
               FROM damage_detections
               GROUP BY image_id, class_id, x_min, y_min
               HAVING n > 1"""
        ).fetchall()
        assert not rows, (
            f"Duplicate detections found: {[dict(r) for r in rows[:5]]}\n"
            "This is the regression for the seed_demo v1 duplication bug."
        )

    def test_total_detections_reasonable(self, demo_db):
        """Total detections should be > 0 and < 1000 (not pathologically large)."""
        n = demo_db.execute(
            "SELECT COUNT(*) FROM damage_detections"
        ).fetchone()[0]
        assert n > 0, "No detections in database."
        assert n < 1000, f"Unusually high detection count {n} — possible duplication."
