# Geospatial Methodology

## Overview

UrbanRoadAI uses geospatial data to link detected road defects to specific road segments, enabling segment-level condition assessment and spatial visualisation.

## Coordinate System

- **CRS:** EPSG:4326 (WGS 84)
- **Storage:** Latitude/longitude as FLOAT8 (PostgreSQL) or REAL (SQLite)
- **Geometry:** LINESTRING for road segments

## GPS Data Sources

### 1. Custom Dataset (Pascal VOC XML Annotations)

Each annotated image includes embedded GPS metadata:

```xml
<source>
    <timestamp_ist>2026-11-05 09:00:03</timestamp_ist>
    <latitude>12.912345</latitude>
    <longitude>77.525678</longitude>
    <speed_mps>2.5</speed_mps>
    <gps_accuracy_m>3.0</gps_accuracy_m>
</source>
```

**Coverage:** Bengaluru (12.911°–12.914° N, 77.523°–77.528° E)

### 2. GPX Track Files

Field survey GPS tracks in standard GPX 1.1 format. Parsed by `src/gis/matcher.py`:

```python
from src.gis.matcher import parse_gpx
points = parse_gpx("data/gps_tracks/survey_track.gpx")
# Returns: [GpsPoint(lat, lon, timestamp, elevation), ...]
```

## Haversine Distance

Used for all distance calculations (no projection needed for short distances):

```
a = sin²(Δφ/2) + cos(φ₁) · cos(φ₂) · sin²(Δλ/2)
d = 2R · atan2(√a, √(1−a))
```

Where R = 6,371,000 m (mean Earth radius).

Implementation: `src/gis/matcher.py → haversine(lat1, lon1, lat2, lon2)`

## GPS-to-Segment Matching Algorithm

### Process

1. For each GPS point (from image metadata or GPX track):
2. Compute the minimum haversine distance to each road segment polyline.
3. Select the nearest segment within `max_distance_m` (default: 50 m).
4. Assign a confidence level based on distance.

### Confidence Levels

| Distance | Confidence | Meaning |
|----------|-----------|---------|
| ≤ 15 m | `high` | GPS point clearly on the road segment |
| 15–30 m | `medium` | Likely correct but GPS drift possible |
| 30–50 m | `low` | Uncertain — could be adjacent road |
| > 50 m | `unmatched` | Not assignable to any segment |

### Implementation

```python
from src.gis.matcher import match_to_segment

result = match_to_segment(
    lat=12.9717,
    lon=77.5948,
    segments=[{"segment_id": "RS_001", "geom_wkt": "LINESTRING(...)"}],
    max_distance_m=50.0,
)
# Returns: MatchResult(segment_id="RS_001", distance_m=15.3, confidence="medium")
```

### WKT Parsing

Road segment geometries are stored as WKT LINESTRING in SQLite mode:

```
LINESTRING(77.5946 12.9716, 77.5960 12.9720)
```

The `_parse_linestring_wkt()` function extracts `(lon, lat)` coordinate tuples for distance computation.

## OpenStreetMap Integration

Road segments are derived from OpenStreetMap (OSM) data:
- Each segment stores an `osm_way_id` for traceability.
- `road_type` follows OSM highway classification: `primary`, `secondary`, `tertiary`, `residential`.
- Segment lengths are approximate (~200–400 m).

## PostGIS Mode

In production mode (PostgreSQL), geometries use native PostGIS types:

```sql
CREATE TABLE road_segments (
    ...
    geom GEOMETRY(LineString, 4326)
);

-- Spatial queries
SELECT ST_AsGeoJSON(geom) FROM road_segments;
SELECT * FROM road_segments WHERE ST_DWithin(geom, ST_MakePoint(lon, lat)::geography, 50);
```

## Limitations

1. **GPS accuracy varies:** Consumer phone GPS typically has 3–10 m accuracy. This is accounted for in the confidence thresholds.
2. **Point-to-vertex matching:** Current implementation checks distance to polyline vertices only, not interpolated segments. Sufficient for segments with endpoints.
3. **No snap-to-road:** We do not use map-matching algorithms (e.g., Valhalla, OSRM) for GPS trace correction. This could improve accuracy for production use.

