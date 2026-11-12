"""Convert sample_dataset (Pascal VOC XML + JPEG) into the UrbanRoadAI pipeline.

This script does three things:
  1. Parses all XML annotations (Pascal VOC format with embedded GPS/timestamp).
  2. Converts annotations to YOLO format with our frozen class IDs.
  3. Produces a metadata CSV for database ingestion.

Class mapping (sample_dataset → frozen classes):
  D40         → 3 (pothole)
  D20         → 2 (alligator_crack)
  Block crack → 2 (alligator_crack)   [block/alligator are visually similar]
  Repair      → DROPPED               [not a defect class]

Run from repo root:
    python -m src.vision.convert_sample_dataset
"""
from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "data" / "sample_dataset"
OUT_DIR = ROOT / "data" / "sample_dataset_yolo"
CLASSES_YAML = ROOT / "configs" / "classes.yaml"

# Mapping from annotation class names → frozen class IDs.
# "Repair" is intentionally omitted (not a damage class).
CLASS_MAP = {
    "D40": 3,            # pothole
    "D20": 2,            # alligator_crack
    "Block crack": 2,    # alligator_crack (block/alligator are visually similar)
    # "Repair" is dropped — it indicates previous maintenance, not a defect.
}


def parse_xml(xml_path: Path) -> dict:
    """Parse one Pascal VOC XML annotation with GPS metadata."""
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    filename = root.findtext("filename", "")
    size = root.find("size")
    w = int(size.findtext("width", "0"))
    h = int(size.findtext("height", "0"))

    source = root.find("source")
    meta = {}
    if source is not None:
        meta["database"] = source.findtext("database", "")
        meta["timestamp_ist"] = source.findtext("timestamp_ist", "")
        meta["latitude"] = source.findtext("latitude", "")
        meta["longitude"] = source.findtext("longitude", "")
        meta["speed_mps"] = source.findtext("speed_mps", "")
        meta["gps_accuracy_m"] = source.findtext("gps_accuracy_m", "")

    objects = []
    for obj in root.findall("object"):
        name = obj.findtext("name", "").strip()
        bb = obj.find("bndbox")
        xmin = int(bb.findtext("xmin", "0"))
        ymin = int(bb.findtext("ymin", "0"))
        xmax = int(bb.findtext("xmax", "0"))
        ymax = int(bb.findtext("ymax", "0"))
        objects.append({
            "class_name": name,
            "xmin": xmin, "ymin": ymin,
            "xmax": xmax, "ymax": ymax,
        })

    return {
        "filename": filename,
        "width": w,
        "height": h,
        "meta": meta,
        "objects": objects,
    }


def voc_to_yolo(xmin, ymin, xmax, ymax, img_w, img_h):
    """Convert Pascal VOC bbox (pixel) to YOLO format (normalised center)."""
    cx = (xmin + xmax) / 2.0 / img_w
    cy = (ymin + ymax) / 2.0 / img_h
    bw = (xmax - xmin) / img_w
    bh = (ymax - ymin) / img_h
    return cx, cy, bw, bh


def main():
    # Load frozen class names for reference.
    class_cfg = yaml.safe_load(CLASSES_YAML.read_text())["classes"]
    frozen_names = {int(k): v["name"] for k, v in class_cfg.items()}

    xml_dir = SAMPLE_DIR / "xml"
    img_dir = SAMPLE_DIR / "images"
    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        raise SystemExit(f"No XML files found in {xml_dir}")

    # Prepare output.
    (OUT_DIR / "images").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "labels").mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    stats = {"total_images": 0, "total_annotations": 0,
             "mapped": 0, "dropped": 0}
    class_counts = {}

    for xml_path in xml_files:
        parsed = parse_xml(xml_path)
        stem = Path(parsed["filename"]).stem
        w, h = parsed["width"], parsed["height"]
        stats["total_images"] += 1

        # Symlink image (avoid copying ~100 MB).
        src_img = img_dir / parsed["filename"]
        dst_img = OUT_DIR / "images" / parsed["filename"]
        if src_img.exists() and not dst_img.exists():
            dst_img.symlink_to(src_img.resolve())

        # Convert annotations.
        yolo_lines = []
        for obj in parsed["objects"]:
            stats["total_annotations"] += 1
            class_name = obj["class_name"]
            if class_name not in CLASS_MAP:
                stats["dropped"] += 1
                continue
            cid = CLASS_MAP[class_name]
            cx, cy, bw, bh = voc_to_yolo(
                obj["xmin"], obj["ymin"], obj["xmax"], obj["ymax"], w, h)
            yolo_lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            class_counts[cid] = class_counts.get(cid, 0) + 1
            stats["mapped"] += 1

        # Write YOLO label file (even if empty — background image).
        (OUT_DIR / "labels" / f"{stem}.txt").write_text(
            "\n".join(yolo_lines) + ("\n" if yolo_lines else ""))

        # Metadata row for DB ingestion.
        m = parsed["meta"]
        metadata_rows.append({
            "image_id": stem,
            "filename": parsed["filename"],
            "width": w,
            "height": h,
            "timestamp_ist": m.get("timestamp_ist", ""),
            "latitude": m.get("latitude", ""),
            "longitude": m.get("longitude", ""),
            "speed_mps": m.get("speed_mps", ""),
            "gps_accuracy_m": m.get("gps_accuracy_m", ""),
            "n_annotations": len(yolo_lines),
        })

    # Write metadata CSV.
    csv_path = OUT_DIR / "frame_metadata.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metadata_rows[0].keys())
        writer.writeheader()
        writer.writerows(metadata_rows)

    # Write YOLO dataset.yaml.
    ds = {
        "path": str(OUT_DIR.resolve()),
        "train": "images",
        "val": "images",
        "test": "images",
        "names": frozen_names,
    }
    (OUT_DIR / "dataset.yaml").write_text(yaml.dump(ds, sort_keys=False))

    # Report.
    print(f"✓ Converted {stats['total_images']} images, "
          f"{stats['total_annotations']} annotations")
    print(f"  Mapped:  {stats['mapped']}")
    print(f"  Dropped: {stats['dropped']} (Repair class)")
    print(f"\n  Class counts (frozen IDs):")
    for cid in sorted(class_counts):
        print(f"    {cid} ({frozen_names[cid]}): {class_counts[cid]}")
    print(f"\n  YOLO labels:  {OUT_DIR / 'labels'}")
    print(f"  Metadata CSV: {csv_path}")
    print(f"  Dataset YAML: {OUT_DIR / 'dataset.yaml'}")


if __name__ == "__main__":
    main()

