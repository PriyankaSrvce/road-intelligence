# Shared Decisions (Team 11)
Owner: Role E. Any change needs team agreement and a dated entry in the changelog.

## 1. Class IDs
| ID | RDD2022 code | Name |
|----|--------------|------|
| 0 | D00 | longitudinal_crack |
| 1 | D10 | transverse_crack |
| 2 | D20 | alligator_crack |
| 3 | D40 | pothole |

## 2. Segment IDs
Format: RS_<3+ digit number>, e.g. RS_001. Generated once by the GIS role from
OSM and never renumbered. Table road_segments is the master list.

## 3. Vision output (src/vision/inference.py, schema 1.0)
Per image: schema_version, image_id, image_width, image_height, model_version,
conf_threshold, inference_ms, num_detections, detections[].
Per detection: class_id, class_code, class_name, confidence (0-1), x_min, y_min,
x_max, y_max (pixels, original image, origin top-left), area_ratio (box area /
image area, 0-1), model_version.
An image with no detections returns num_detections = 0 and an empty list.
Vision does NOT return lat, lon, timestamp or road_segment_id: ingestion stores
lat/lon/timestamp on the images row, GIS fills road_segment_id, and the API joins
on image_id. Database rows come from to_db_rows(): image_id, class_id, confidence,
x_min, y_min, x_max, y_max, area_ratio, model_version.
Sample output: docs/sample_inference_output.json

## 4. Database tables (PostgreSQL + PostGIS)
road_segments, images, damage_detections, condition_history, weather_data,
maintenance_records, predictions

## 5. Condition score bands
| score | label |
|-------|-------|
| 0-25 | Good |
| 26-50 | Fair |
| 51-75 | Poor |
| 76-100 | Very Poor |

## 6. Conventions
- Timezone: Asia/Kolkata (IST). Store timestamps with timezone.
- CRS: EPSG:4326 for storage.
- Image size for training: 640. Random seed: 42.
- MLflow run names: <model>_<dataset>_seed<seed>_img<size>

## Changelog
- initial version
- 2026-10-28: Dataset source = Kaggle re-upload of RDD2022 India (aliabdelmenam/rdd-2022), 70/15/15 split. Raw class 3 (other corruption) dropped; raw 4 (pothole) mapped to frozen ID 3. Counts in docs/rdd2022_india_class_counts.csv
- 2026-11-02: Section 3 now describes the Vision output (schema 1.0); GPS, timestamp and road_segment_id come from ingestion/GIS, not Vision.
