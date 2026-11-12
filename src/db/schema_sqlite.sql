-- UrbanRoadAI: SQLite schema for offline demonstration.
-- Mirrors src/db/schema.sql but without PostGIS types.
-- Geometry stored as WKT text; spatial queries use lat/lon directly.
--
-- data_source: 'real' | 'simulated'
--   Every row of survey data must declare its provenance.
--   The dashboard shows a "SIMULATED DEMO DATA" badge for simulated rows.

CREATE TABLE IF NOT EXISTS damage_classes (
  class_id   INTEGER PRIMARY KEY,
  class_name TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO damage_classes (class_id, class_name) VALUES
  (0,'longitudinal_crack'),
  (1,'transverse_crack'),
  (2,'alligator_crack'),
  (3,'pothole');

CREATE TABLE IF NOT EXISTS corridors (
  corridor_id TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  notes       TEXT,
  data_source TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated'))
);

CREATE TABLE IF NOT EXISTS road_segments (
  segment_id  TEXT PRIMARY KEY,
  corridor_id TEXT REFERENCES corridors,
  osm_way_id  INTEGER,
  road_name   TEXT,
  road_type   TEXT,
  length_m    REAL CHECK (length_m > 0),
  geom_wkt    TEXT,  -- WKT LineString in EPSG:4326
  data_source TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated'))
);

CREATE TABLE IF NOT EXISTS surveys (
  survey_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  corridor_id TEXT NOT NULL REFERENCES corridors,
  survey_date TEXT NOT NULL,           -- ISO date YYYY-MM-DD
  video_file  TEXT,
  notes       TEXT,
  data_source TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated')),
  UNIQUE (corridor_id, survey_date, video_file)
);

CREATE TABLE IF NOT EXISTS images (
  image_id    TEXT PRIMARY KEY,
  survey_id   INTEGER NOT NULL REFERENCES surveys,
  segment_id  TEXT REFERENCES road_segments,
  captured_at TEXT NOT NULL,            -- ISO timestamp
  lat         REAL NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lon         REAL NOT NULL CHECK (lon BETWEEN -180 AND 180),
  blur_score  REAL,
  file_path   TEXT NOT NULL,
  data_source TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated'))
);

CREATE TABLE IF NOT EXISTS damage_detections (
  detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id     TEXT NOT NULL REFERENCES images ON DELETE CASCADE,
  class_id     INTEGER NOT NULL REFERENCES damage_classes,
  confidence   REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  x_min REAL, y_min REAL, x_max REAL, y_max REAL,
  area_ratio   REAL CHECK (area_ratio BETWEEN 0 AND 1),
  severity     TEXT CHECK (severity IN ('low','moderate','high')),
  model_version TEXT NOT NULL,
  data_source  TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated'))
);

CREATE TABLE IF NOT EXISTS condition_history (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id     TEXT NOT NULL REFERENCES road_segments,
  survey_id      INTEGER NOT NULL REFERENCES surveys,
  survey_date    TEXT NOT NULL,
  score          REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
  band           TEXT CHECK (band IN ('good','fair','poor','very_poor')),
  n_defects      INTEGER,
  defect_density REAL,
  data_source    TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated')),
  UNIQUE (segment_id, survey_id)
);

CREATE TABLE IF NOT EXISTS weather_data (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  corridor_id TEXT NOT NULL REFERENCES corridors,
  obs_date    TEXT NOT NULL,
  rainfall_mm REAL, temp_c REAL, humidity_pct REAL,
  source      TEXT,
  UNIQUE (corridor_id, obs_date)
);

CREATE TABLE IF NOT EXISTS maintenance_records (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id TEXT NOT NULL REFERENCES road_segments,
  done_on    TEXT,
  work_type  TEXT,
  source     TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id    TEXT NOT NULL REFERENCES road_segments,
  made_at       TEXT NOT NULL DEFAULT (datetime('now')),
  horizon_days  INTEGER NOT NULL,
  risk_prob     REAL NOT NULL CHECK (risk_prob BETWEEN 0 AND 1),
  model_version TEXT NOT NULL,
  data_source   TEXT NOT NULL DEFAULT 'simulated' CHECK (data_source IN ('real','simulated'))
);
