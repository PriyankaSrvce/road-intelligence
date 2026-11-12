"""Tests for src.gis.matcher — haversine and GPS-to-segment matching."""
import pytest
from src.gis.matcher import haversine, match_to_segment, _parse_linestring_wkt, GpsPoint


class TestHaversine:
    def test_same_point_zero(self):
        assert haversine(12.9716, 77.5946, 12.9716, 77.5946) == 0.0

    def test_known_distance_bengaluru(self):
        # Two points ~300 m apart in Bengaluru
        d = haversine(12.9716, 77.5946, 12.9740, 77.5975)
        assert 300 < d < 500  # approximate

    def test_symmetry(self):
        d1 = haversine(12.9716, 77.5946, 13.0, 77.6)
        d2 = haversine(13.0, 77.6, 12.9716, 77.5946)
        assert abs(d1 - d2) < 0.01  # should be identical

    def test_large_distance(self):
        # Bengaluru to Mumbai ~840 km
        d = haversine(12.9716, 77.5946, 19.0760, 72.8777)
        assert 800_000 < d < 900_000


class TestParseLinestringWkt:
    def test_valid_linestring(self):
        wkt = "LINESTRING(77.5946 12.9716, 77.5960 12.9720)"
        coords = _parse_linestring_wkt(wkt)
        assert len(coords) == 2
        assert coords[0] == (77.5946, 12.9716)
        assert coords[1] == (77.5960, 12.9720)

    def test_multiple_points(self):
        wkt = "LINESTRING(77.1 12.1, 77.2 12.2, 77.3 12.3)"
        coords = _parse_linestring_wkt(wkt)
        assert len(coords) == 3


class TestMatchToSegment:
    @pytest.fixture()
    def segments(self):
        return [
            {
                "segment_id": "RS_001",
                "geom_wkt": "LINESTRING(77.5946 12.9716, 77.5960 12.9720)",
            },
            {
                "segment_id": "RS_002",
                "geom_wkt": "LINESTRING(77.5960 12.9720, 77.5975 12.9728)",
            },
        ]

    def test_match_near_segment(self, segments):
        # Point very close to RS_001's first vertex (12.9716, 77.5946)
        result = match_to_segment(12.97165, 77.59465, segments)
        assert result.segment_id == "RS_001"
        assert result.confidence == "high"
        assert result.distance_m < 15

    def test_match_near_second_segment(self, segments):
        # Point close to RS_002's second vertex (12.9728, 77.5975)
        result = match_to_segment(12.97285, 77.59755, segments)
        assert result.segment_id == "RS_002"

    def test_unmatched_far_point(self, segments):
        # Point far away (100+ m from both segments)
        result = match_to_segment(13.0, 77.7, segments, max_distance_m=50.0)
        assert result.segment_id == "UNMATCHED"
        assert result.confidence == "unmatched"

    def test_empty_segments(self):
        result = match_to_segment(12.9716, 77.5946, [])
        assert result.segment_id == "UNMATCHED"

