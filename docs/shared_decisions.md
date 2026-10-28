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

## 3. Detection record (output of Vision to DB / scoring)
| field | type | notes |
|-------|------|-------|
| image_id | text | unique per frame |
| class_id | int | see section 1 |
| confidence | float | 0-1 |
| x_min, y_min, x_max, y_max | float | pixels |
| area_ratio | float | box area / image area, 0-1 |
| timestamp | timestamptz | IST |
| lat, lon | float | WGS84 (EPSG:4326) |
| road_segment_id | text | filled by GIS role |

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
