"""Build the final YOLO dataset from the Kaggle RDD_SPLIT India data.

Raw IDs (checked by eye):  0=longitudinal 1=transverse 2=alligator 3=other 4=pothole
Frozen IDs (classes.yaml): 0=longitudinal 1=transverse 2=alligator 3=pothole
Raw 3 ("other corruption") is dropped.

Run from repo root:
    python src/vision/build_yolo_dataset.py
"""
import argparse
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

REMAP = {0: 0, 1: 1, 2: 2, 4: 3}   # raw id -> frozen id
DROP = {3}                          # raw ids to discard
IMG_EXTS = (".jpg", ".jpeg", ".png")


def find_image(img_dir, stem):
    for ext in IMG_EXTS:
        p = img_dir / (stem + ext)
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/RDD_India/RDD_SPLIT")
    ap.add_argument("--out", default="data/processed/rdd2022_india")
    ap.add_argument("--force", action="store_true", help="delete --out first if it exists")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    if out.exists():
        if not args.force:
            raise SystemExit(f"{out} already exists. Re-run with --force to rebuild it.")
        shutil.rmtree(out)

    names = {int(k): v["name"] for k, v in
             yaml.safe_load(open("configs/classes.yaml"))["classes"].items()}

    stats = Counter()
    rows = []
    for split in ("train", "val", "test"):
        img_dir, lbl_dir = src / split / "images", src / split / "labels"
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

        for lp in sorted(lbl_dir.glob("*.txt")):
            ip = find_image(img_dir, lp.stem)
            if ip is None:
                stats["missing_image"] += 1
                continue

            kept, dropped_here, raw_boxes = [], 0, 0
            for line in lp.read_text().splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                raw_boxes += 1
                raw_id = int(float(parts[0]))
                if raw_id in DROP:
                    dropped_here += 1
                elif raw_id in REMAP:
                    kept.append(f"{REMAP[raw_id]} " + " ".join(parts[1:]))
                    rows.append({"split": split, "class_id": REMAP[raw_id]})
                else:
                    stats[f"unknown_raw_id_{raw_id}"] += 1

            stats["dropped_boxes"] += dropped_here
            if raw_boxes == 0:
                stats["originally_empty_images"] += 1
            elif not kept:
                stats["images_emptied_by_drop"] += 1
            if dropped_here and kept:
                stats["images_with_dropped_and_kept_boxes"] += 1

            shutil.copy2(ip, out / "images" / split / ip.name)
            (out / "labels" / split / f"{lp.stem}.txt").write_text(
                "\n".join(kept) + ("\n" if kept else ""))
            stats[f"images_{split}"] += 1
            if not kept:
                stats[f"empty_{split}"] += 1

    df = pd.DataFrame(rows)
    table = df.pivot_table(index="class_id", columns="split", aggfunc="size", fill_value=0)
    table = table.reindex(columns=["train", "val", "test"], fill_value=0)
    table["total"] = table.sum(axis=1)
    table.insert(0, "class_name", [names[i] for i in table.index])
    table.to_csv(out / "class_counts.csv")

    ds = {"train": "images/train", "val": "images/val",
          "test": "images/test", "names": names}
    with open(out / "dataset.yaml", "w") as f:
        yaml.safe_dump(ds, f, sort_keys=False)

    print("\nBoxes per class (frozen IDs):\n", table.to_string())
    print("\nReport:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"\nDone. Output in {out}")


if __name__ == "__main__":
    main()

