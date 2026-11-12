"""Tests for FastAPI endpoints (src.api.main)."""
import pytest


class TestHealth:
    def test_health(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "sqlite"


class TestSegments:
    def test_list_segments(self, api_client):
        resp = api_client.get("/segments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # seeded 2 segments

    def test_segment_detail(self, api_client):
        resp = api_client.get("/segments/RS_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["segment_id"] == "RS_001"
        assert "road_name" in data

    def test_segment_not_found(self, api_client):
        resp = api_client.get("/segments/NONEXISTENT")
        assert resp.status_code == 404


class TestHistory:
    def test_history(self, api_client):
        resp = api_client.get("/segments/RS_001/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # seeded 1 condition_history row

    def test_history_empty_segment(self, api_client):
        resp = api_client.get("/segments/RS_002/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestRisk:
    def test_risk(self, api_client):
        resp = api_client.get("/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_risk_with_top(self, api_client):
        resp = api_client.get("/risk?top=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 1


class TestStats:
    def test_stats(self, api_client):
        resp = api_client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_segments" in data
        assert "total_images" in data
        assert "total_detections" in data
        assert "total_surveys" in data
        assert data["total_segments"] >= 2
        assert data["total_detections"] >= 3


class TestDetect:
    def test_detect_no_file(self, api_client):
        resp = api_client.post("/detect")
        assert resp.status_code == 422  # validation error

