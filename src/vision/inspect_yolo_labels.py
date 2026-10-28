"""Inspect a YOLO-format dataset: validate labels, count boxes per class,
and save sample images per class ID so a human can confirm what each ID means.

Run from repo root:
    python src/vision/inspect_yolo_labels.py
"""
import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import pandas as pd

COLORS = [(255, 100, 0), (0, 200, 0), (0, 200, 255), (0, 0, 255), (255, 0, 255), (200, 200, 0)]
IMG_EXTS = (".jpg", ".jpeg", ".png")


def find_image(img_dir, stem):
    for ext in IMG_EXTS:
        p = img_dir / (stem + ext)
        if p.exists():
            return p
    return None


def read_label(lp, problems):
    boxes = []
    for line in lp.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            problems["bad_line_length"] += 1
            continue
        try:
            cid = int(float(parts[0]))
            cx, cy, w, h = (float(v) for v in parts[1:])
        except ValueError:
            problems["non_numeric"] += 1
            continue
        if w <= 0 or h <= 0 or not all(0 <= v <= 1 for v in (cx, cy, w, h)):
            problems["out_of_range_box"] += 1
            continue
        boxes.append((cid, cx, cy, w, h))
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/raw/RDD_India/RDD_SPLIT")
    ap.add_argument("--samples", type=int, default=12)
    args = ap.parse_args()

    root = Path(args.root)
    problems = Counter()
    rows = []
    empty = Counter()
    n_files = Counter()
    by_class = defaultdict(list)

    for split in ("train", "val", "test"):
        img_dir, lbl_dir = root / split / "images", root / split / "labels"
        for lp in sorted(lbl_dir.glob("*.txt")):
            n_files[split] += 1
            boxes = read_label(lp, problems)
            if not boxes:
                empty[split] += 1
                continue
            for cid in {b[0] for b in boxes}:
                by_class[cid].append((img_dir, lp))
            for b in boxes:
                rows.append({"split": split, "class_id": b[0]})

    print("\nLabel files per split:", dict(n_files))
    print("Empty (background) label files:", dict(empty))
    if rows:
        df = pd.DataFrame(rows)
        table = df.pivot_table(index="class_id", columns="split", aggfunc="size", fill_value=0)
        table["total"] = table.sum(axis=1)
        print("\nBoxes per class ID:\n", table)
        table.to_csv(root / "class_counts_raw.csv")
    print("\nProblems found:", dict(problems) or "none")

    out_root = root.parent / "class_samples"
    rnd = random.Random(42)
    for cid, items in sorted(by_class.items()):
        out = out_root / f"class_{cid}"
        out.mkdir(parents=True, exist_ok=True)
        for img_dir, lp in rnd.sample(items, min(args.samples, len(items))):
            ip = find_image(img_dir, lp.stem)
            img = cv2.imread(str(ip)) if ip else None
            if img is None:
                continue
            H, W = img.shape[:2]
            for bcid, cx, cy, w, h in read_label(lp, Counter()):
                p1 = (int((cx - w / 2) * W), int((cy - h / 2) * H))
                p2 = (int((cx + w / 2) * W), int((cy + h / 2) * H))
                color = COLORS[bcid % len(COLORS)]
                thick = 4 if bcid == cid else 1
                cv2.rectangle(img, p1, p2, color, thick)
                cv2.putText(img, str(bcid), (p1[0], max(20, p1[1] - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            cv2.imwrite(str(out / ip.name), img)
    print(f"\nSample images saved in {out_root}")


if __name__ == "__main__":
    main()
