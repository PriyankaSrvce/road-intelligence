"""UrbanRoadAI – GIS utilities: GPX parsing and GPS-to-segment matching.

Provides:
  parse_gpx()       – extract timestamped GPS points from a .gpx file
  match_to_segment() – assign a GPS point to the nearest road segment
  haversine()       – distance between two lat/lon points

Coordinate system: EPSG:4326 (WGS 84).
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GpsPoint:
    lat: float
    lon: float
    timestamp: datetime | None = None
    elevation: float | None = None


@dataclass
class MatchResult:
    segment_id: str
    distance_m: float
    confidence: str       # 'high', 'medium', 'low', 'unmatched'


# ---------------------------------------------------------------------------
# GPX parsing
# ---------------------------------------------------------------------------

_GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}


def parse_gpx(gpx_path: str | Path) -> list[GpsPoint]:
    """Parse a GPX file and return a list of GpsPoint objects.

    Supports GPX 1.1 <trkpt> elements.  Falls back to namespace-less
    parsing if the default namespace doesn't match.
    """
    tree = ET.parse(str(gpx_path))
    root = tree.getroot()

    # Try with namespace first, then without.
    points: list[GpsPoint] = []
    trkpts = root.findall(".//gpx:trkpt", _GPX_NS)
    if not trkpts:
        trkpts = root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")
    if not trkpts:
        # Namespace-less fallback.
        trkpts = root.findall(".//trkpt")

    for pt in trkpts:
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])

        ts = None
        time_el = (pt.find("gpx:time", _GPX_NS)
                   or pt.find("{http://www.topografix.com/GPX/1/1}time")
                   or pt.find("time"))
        if time_el is not None and time_el.text:
            try:
                ts = datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
            except ValueError:
                pass

        ele = None
        ele_el = (pt.find("gpx:ele", _GPX_NS)
                  or pt.find("{http://www.topografix.com/GPX/1/1}ele")
                  or pt.find("ele"))
        if ele_el is not None and ele_el.text:
            try:
                ele = float(ele_el.text)
            except ValueError:
                pass

        points.append(GpsPoint(lat=lat, lon=lon, timestamp=ts, elevation=ele))

    return points


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

_R_EARTH_M = 6_371_000  # mean Earth radius in metres


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance in metres between two points (WGS 84)."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return _R_EARTH_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Segment matching
# ---------------------------------------------------------------------------

def _parse_linestring_wkt(wkt: str) -> list[tuple[float, float]]:
    """Extract [(lon, lat), ...] from a WKT LINESTRING."""
    wkt = wkt.strip()
    if wkt.upper().startswith("LINESTRING"):
        wkt = wkt[wkt.index("(") + 1 : wkt.rindex(")")]
    coords = []
    for pair in wkt.split(","):
        parts = pair.strip().split()
        coords.append((float(parts[0]), float(parts[1])))   # lon, lat
    return coords


def _point_to_line_distance(lat: float, lon: float,
                            line: list[tuple[float, float]]) -> float:
    """Minimum haversine distance from a point to a polyline (metres)."""
    best = float("inf")
    for llon, llat in line:
        d = haversine(lat, lon, llat, llon)
        if d < best:
            best = d
    return best


def match_to_segment(
    lat: float,
    lon: float,
    segments: list[dict],
    max_distance_m: float = 50.0,
) -> MatchResult:
    """Find the nearest road segment for a GPS point.

    Parameters
    ----------
    lat, lon : float
        WGS 84 coordinates of the GPS point.
    segments : list[dict]
        Each dict must have 'segment_id' and either 'geom_wkt' (SQLite mode)
        or 'geom' (PostGIS GeoJSON mode).
    max_distance_m : float
        Maximum acceptable distance for a match.

    Returns
    -------
    MatchResult with the nearest segment_id, distance, and confidence.
    """
    best_id = None
    best_dist = float("inf")

    for seg in segments:
        wkt = seg.get("geom_wkt") or seg.get("geom", "")
        if not wkt or not isinstance(wkt, str):
            continue
        try:
            line = _parse_linestring_wkt(wkt)
        except (ValueError, IndexError):
            continue
        d = _point_to_line_distance(lat, lon, line)
        if d < best_dist:
            best_dist = d
            best_id = seg["segment_id"]

    if best_id is None or best_dist > max_distance_m:
        return MatchResult(
            segment_id="UNMATCHED",
            distance_m=best_dist if best_id else -1,
            confidence="unmatched",
        )

    if best_dist <= 15:
        conf = "high"
    elif best_dist <= 30:
        conf = "medium"
    else:
        conf = "low"

    return MatchResult(segment_id=best_id, distance_m=round(best_dist, 1), confidence=conf)

