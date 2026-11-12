# Computer Vision Methodology

## Overview

UrbanRoadAI uses **YOLO (You Only Look Once)** single-stage object detection to identify four categories of visible road surface defects from street-level imagery.

## Defect Classes (Frozen)

| Class ID | RDD2022 Code | Name | Description |
|----------|-------------|------|-------------|
| 0 | D00 | `longitudinal_crack` | Cracks parallel to road direction |
| 1 | D10 | `transverse_crack` | Cracks perpendicular to road direction |
| 2 | D20 | `alligator_crack` | Interconnected crack pattern |
| 3 | D40 | `pothole` | Surface hole/depression |

Class IDs are **frozen** in `configs/classes.yaml`. All downstream modules use these IDs.

## Model Selection

### Candidates Evaluated

| Model | Architecture | Parameters | mAP@50 | mAP@50-95 |
|-------|-------------|-----------|--------|-----------|
| **YOLOv8s** | Ultralytics v8 small | ~11M | **0.334** | **0.177** |
| YOLO11s | Ultralytics v11 small | ~9M | 0.320 | 0.162 |

**Selected: YOLOv8s** — Higher mAP@50 (+0.014) and mAP@50-95 (+0.015) on the RDD2022 India test set.

### Selection Rationale

1. **Single-stage detector** — Faster inference, suitable for CPU deployment on laptops.
2. **Ultralytics framework** — Built-in training, validation, export, and MLflow integration.
3. **Transfer learning** — COCO pre-trained weights as starting point.
4. **Community support** — Extensive documentation and active development.

## Training Dataset: RDD2022 India

- **Source:** Kaggle re-upload of RDD2022 (aliabdelmenam/rdd-2022), India subset.
- **Split:** 70% train / 15% validation / 15% test.
- **Image size:** 640 × 640 pixels.
- **Total images:** ~15,400 (519 MB via DVC).

### Class Distribution (RDD2022 India)

| Class | Train Boxes | Val Boxes | Test Boxes | Total |
|-------|-------------|-----------|------------|-------|
| longitudinal_crack | 1,540 | 354 | 317 | 2,211 |
| transverse_crack | 45 | 12 | 11 | 68 |
| alligator_crack | 1,676 | 400 | 370 | 2,446 |
| pothole | 2,233 | 478 | 476 | 3,187 |

> ⚠️ **Class imbalance:** `transverse_crack` has only 68 boxes total — this limits per-class performance.

### Training Configuration

```yaml
model: yolov8s.pt         # COCO pre-trained
data: data/processed/rdd2022_india/dataset.yaml
epochs: 100
imgsz: 640
batch: 16
seed: 42
device: cpu                # No GPU available
optimizer: auto
patience: 50
```

## Model Performance (YOLOv8s Baseline)

### Aggregate Metrics

| Metric | Value |
|--------|-------|
| mAP@50 (test) | 0.334 |
| mAP@50-95 (test) | 0.177 |
| Precision | 0.413 |
| Recall | 0.340 |

### Per-Class Performance

| Class | Precision | Recall | mAP@50 |
|-------|-----------|--------|--------|
| longitudinal_crack | 0.39 | 0.28 | 0.27 |
| transverse_crack | 0.18 | 0.09 | 0.06 |
| alligator_crack | 0.42 | 0.34 | 0.33 |
| pothole | 0.64 | 0.65 | 0.67 |

**Observations:**
- **Pothole** detection is strongest (mAP@50 = 0.67) — largest training set, visually distinctive.
- **Transverse crack** is weakest (mAP@50 = 0.06) — only 68 training boxes.
- Overall mAP is moderate but competitive for a resource-constrained student project.

## Custom Dataset: Bengaluru Road Survey

### Collection

- **Location:** Bengaluru, Karnataka (lat 12.911–12.914, lon 77.523–77.528)
- **Date:** 5 November 2026, 09:00–09:02 IST
- **Method:** Phone-mounted dashcam video, portrait orientation
- **Resolution:** 2160 × 3840 (portrait)
- **Frames:** 69 annotated images

### Annotation Format

Pascal VOC XML with embedded GPS metadata:
```xml
<source>
    <timestamp_ist>2026-11-05 09:00:03</timestamp_ist>
    <latitude>12.912345</latitude>
    <longitude>77.525678</longitude>
    <speed_mps>2.5</speed_mps>
    <gps_accuracy_m>3.0</gps_accuracy_m>
</source>
```

### Class Mapping (Custom → Frozen)

| Custom Label | Frozen ID | Frozen Name | Count | Rationale |
|-------------|-----------|-------------|-------|-----------|
| D40 | 3 | pothole | 49 | Direct mapping |
| D20 | 2 | alligator_crack | 7 | Direct mapping |
| Block crack | 2 | alligator_crack | 34 | Visually similar pattern |
| Repair | — | DROPPED | 3 | Not a defect class |

**Total mapped annotations:** 90 (3 dropped).

### Conversion Pipeline

`src/vision/convert_sample_dataset.py`:
1. Parse Pascal VOC XML annotations.
2. Map class names to frozen IDs.
3. Convert bounding boxes from pixel (VOC) to normalised (YOLO) format.
4. Generate YOLO `.txt` label files.
5. Produce `frame_metadata.csv` with GPS and timestamp.
6. Create `dataset.yaml` for YOLO compatibility.

## Inference Pipeline (Schema 1.0)

```python
from src.vision.inference import run_inference

result = run_inference("frame.jpg", image_id="SURVEY01_000123")
# Returns: schema_version, image_id, image_width, image_height,
#          model_version, conf_threshold, inference_ms,
#          num_detections, detections[]
```

The inference module (`src/vision/inference.py`) validates that model class names match `configs/classes.yaml` at load time, preventing silent class mismatches.

## Scientific Limitations

1. **Bounding-box area ≠ actual damaged area.** The area_ratio is the box area divided by image area — a proxy, not a measurement.
2. **Detection confidence ≠ severity.** A highly confident detection of a small crack is not necessarily more severe than a lower-confidence pothole.
3. **Viewpoint and lighting matter.** Model performance degrades with shadows, wet surfaces, extreme angles, and occlusion.
4. **No depth estimation.** Pothole depth cannot be determined from a single 2D image.

