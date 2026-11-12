"""Tests for src.prediction.scoring — condition scoring and risk prediction."""
import pytest
from src.prediction.scoring import score_segment, predict_risk, _band


class TestScoreSegment:
    """Tests for the segment condition scoring function."""

    def test_score_no_defects(self):
        result = score_segment([], segment_length_m=300.0)
        assert result["score"] == 0.0
        assert result["band"] == "good"
        assert result["n_defects"] == 0
        assert result["defect_density"] == 0.0

    def test_score_zero_length(self):
        det = [{"class_id": 3, "confidence": 0.8, "area_ratio": 0.03, "severity": "moderate"}]
        result = score_segment(det, segment_length_m=0)
        assert result["score"] == 0.0
        assert result["band"] == "good"

    def test_score_single_pothole(self):
        det = [{"class_id": 3, "confidence": 0.85, "area_ratio": 0.03, "severity": "moderate"}]
        result = score_segment(det, segment_length_m=300.0)
        assert result["score"] > 0
        assert result["band"] != "good" or result["score"] > 0
        assert result["n_defects"] == 1
        assert result["class_counts"] == {3: 1}

    def test_score_multiple_classes(self):
        dets_single = [{"class_id": 3, "confidence": 0.85, "area_ratio": 0.03, "severity": "moderate"}]
        dets_multi = [
            {"class_id": 3, "confidence": 0.85, "area_ratio": 0.03, "severity": "moderate"},
            {"class_id": 2, "confidence": 0.70, "area_ratio": 0.02, "severity": "moderate"},
            {"class_id": 0, "confidence": 0.60, "area_ratio": 0.01, "severity": "low"},
        ]
        r1 = score_segment(dets_single, segment_length_m=300.0)
        r2 = score_segment(dets_multi, segment_length_m=300.0)
        assert r2["score"] > r1["score"]
        assert r2["n_defects"] == 3

    def test_score_below_threshold_filtered(self):
        det = [{"class_id": 3, "confidence": 0.10, "area_ratio": 0.05, "severity": "high"}]
        result = score_segment(det, segment_length_m=300.0, conf_threshold=0.30)
        assert result["n_defects"] == 0
        assert result["score"] == 0.0

    def test_score_high_severity_higher(self):
        det_mod = [{"class_id": 3, "confidence": 0.8, "area_ratio": 0.03, "severity": "moderate"}]
        det_high = [{"class_id": 3, "confidence": 0.8, "area_ratio": 0.03, "severity": "high"}]
        r1 = score_segment(det_mod, segment_length_m=300.0)
        r2 = score_segment(det_high, segment_length_m=300.0)
        assert r2["score"] >= r1["score"]

    def test_formula_explanation_present(self):
        det = [{"class_id": 3, "confidence": 0.85, "area_ratio": 0.03, "severity": "moderate"}]
        result = score_segment(det, segment_length_m=300.0)
        assert "weighted_sum" in result["formula_explanation"]


class TestBand:
    """Tests for the condition band function."""

    def test_band_good(self):
        assert _band(0) == "good"
        assert _band(25) == "good"

    def test_band_fair(self):
        assert _band(26) == "fair"
        assert _band(50) == "fair"

    def test_band_poor(self):
        assert _band(51) == "poor"
        assert _band(75) == "poor"

    def test_band_very_poor(self):
        assert _band(76) == "very_poor"
        assert _band(100) == "very_poor"


class TestPredictRisk:
    """Tests for the experimental risk prediction function."""

    def test_no_history(self):
        result = predict_risk([])
        assert result["risk_prob"] == 0.5
        assert result["model_version"] == "rule_v1"
        assert result["horizon_days"] == 180

    def test_good_segment_low_risk(self):
        history = [{"survey_date": "2026-10-01", "score": 10}]
        result = predict_risk(history, road_type="residential")
        assert result["risk_prob"] < 0.5

    def test_poor_segment_high_risk(self):
        history = [{"survey_date": "2026-10-01", "score": 85}]
        result = predict_risk(history, road_type="primary")
        assert result["risk_prob"] > 0.5

    def test_worsening_trend_increases_risk(self):
        stable = [
            {"survey_date": "2026-09-01", "score": 50},
            {"survey_date": "2026-10-01", "score": 50},
        ]
        worsening = [
            {"survey_date": "2026-09-01", "score": 30},
            {"survey_date": "2026-10-01", "score": 70},
        ]
        r_stable = predict_risk(stable, road_type="tertiary")
        r_worse = predict_risk(worsening, road_type="tertiary")
        assert r_worse["risk_prob"] > r_stable["risk_prob"]

    def test_road_type_primary_higher(self):
        history = [{"survey_date": "2026-10-01", "score": 50}]
        r_primary = predict_risk(history, road_type="primary")
        r_residential = predict_risk(history, road_type="residential")
        assert r_primary["risk_prob"] > r_residential["risk_prob"]

    def test_risk_bounded_0_1(self):
        history = [{"survey_date": "2026-10-01", "score": 100}]
        result = predict_risk(history)
        assert 0.0 <= result["risk_prob"] <= 1.0

    def test_custom_horizon(self):
        result = predict_risk([], horizon_days=365)
        assert result["horizon_days"] == 365

