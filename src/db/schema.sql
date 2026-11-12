-- UrbanRoadAI: PostGIS schema. Coordinates stored in EPSG:4326.
-- Matches docs/shared_decisions.md and configs/classes.yaml.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE damage_classes (
  class_id   SMALLINT PRIMARY KEY,
  class_name TEXT NOT NULL UNIQUE
);
-- Keep in sync with the frozen class IDs agreed by the team.
INSERT INTO damage_classes (class_id, class_name) VALUES
  (0,'longitudinal_crack'),
  (1,'transverse_crack'),
  (2,'alligator_crack'),
  (3,'pothole');

CREATE TABLE corridors (
  corridor_id TEXT PRIMARY KEY,           -- e.g. C01
  name        TEXT NOT NULL,
  notes       TEXT
);

CREATE TABLE road_segments (
  segment_id  TEXT PRIMARY KEY,           -- e.g. RS_0001
  corridor_id TEXT REFERENCES corridors,
  osm_way_id  BIGINT,
  road_name   TEXT,
  road_type   TEXT,                       -- OSM highway tag
  length_m    REAL CHECK (length_m > 0),
  geom        geometry(LineString,4326) NOT NULL
);
CREATE INDEX road_segments_geom_gix ON road_segments USING GIST (geom);
CREATE INDEX road_segments_corridor_ix ON road_segments (corridor_id);

CREATE TABLE surveys (                    -- one drive of one corridor
  survey_id   SERIAL PRIMARY KEY,
  corridor_id TEXT NOT NULL REFERENCES corridors,
  survey_date DATE NOT NULL,
  video_file  TEXT,
  notes       TEXT,
  UNIQUE (corridor_id, survey_date, video_file)
);

CREATE TABLE images (
  image_id    TEXT PRIMARY KEY,           -- frame_id from the metadata CSV
  survey_id   INT  NOT NULL REFERENCES surveys,
  segment_id  TEXT REFERENCES road_segments,
  captured_at TIMESTAMPTZ NOT NULL,
  lat         DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lon         DOUBLE PRECISION NOT NULL CHECK (lon BETWEEN -180 AND 180),
  geom        geometry(Point,4326) NOT NULL,
  blur_score  REAL,
  file_path   TEXT NOT NULL
);
CREATE INDEX images_geom_gix ON images USING GIST (geom);
CREATE INDEX images_segment_ix ON images (segment_id);
CREATE INDEX images_survey_ix ON images (survey_id);

CREATE TABLE damage_detections (
  detection_id  BIGSERIAL PRIMARY KEY,
  image_id      TEXT NOT NULL REFERENCES images ON DELETE CASCADE,
  class_id      SMALLINT NOT NULL REFERENCES damage_classes,
  confidence    REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  x_min REAL, y_min REAL, x_max REAL, y_max REAL,   -- pixel coords
  area_ratio    REAL CHECK (area_ratio BETWEEN 0 AND 1),
  severity      TEXT CHECK (severity IN ('low','moderate','high')),
  model_version TEXT NOT NULL
);
CREATE INDEX detections_image_ix ON damage_detections (image_id);
CREATE INDEX detections_class_ix ON damage_detections (class_id);

CREATE TABLE condition_history (          -- one row per segment per survey
  id             BIGSERIAL PRIMARY KEY,
  segment_id     TEXT NOT NULL REFERENCES road_segments,
  survey_id      INT  NOT NULL REFERENCES surveys,
  survey_date    DATE NOT NULL,
  score          REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
  band           TEXT CHECK (band IN ('good','fair','poor','very_poor')),
  n_defects      INT,
  defect_density REAL,                    -- defects per 100 m
  UNIQUE (segment_id, survey_id)
);
CREATE INDEX condition_seg_date_ix ON condition_history (segment_id, survey_date);

CREATE TABLE weather_data (
  id          BIGSERIAL PRIMARY KEY,
  corridor_id TEXT NOT NULL REFERENCES corridors,
  obs_date    DATE NOT NULL,
  rainfall_mm REAL, temp_c REAL, humidity_pct REAL,
  source      TEXT,
  UNIQUE (corridor_id, obs_date)
);

CREATE TABLE maintenance_records (
  id         BIGSERIAL PRIMARY KEY,
  segment_id TEXT NOT NULL REFERENCES road_segments,
  done_on    DATE,
  work_type  TEXT,
  source     TEXT
);

CREATE TABLE predictions (
  id            BIGSERIAL PRIMARY KEY,
  segment_id    TEXT NOT NULL REFERENCES road_segments,
  made_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  horizon_days  INT NOT NULL,
  risk_prob     REAL NOT NULL CHECK (risk_prob BETWEEN 0 AND 1),
  model_version TEXT NOT NULL
);
CREATE INDEX predictions_seg_ix ON predictions (segment_id, made_at DESC);

