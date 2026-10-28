"""Draw YOLO boxes on N images (with boxes only) so a human can eyeball them.
Guarantees a few examples of every class.

Run from repo root:
    python src/vision/check_labels.py
"""
import argparse
import random
from pathlib import Path

import cv2
import yaml

COLORS = {0: (255, 100, 0), 1: (0, 200, 0), 2: (0, 200, 255), 3: (0, 0, 255)}  # BGR
IMG_EXTS = (".jpg", ".jpeg", ".png")


def classes_in(lp):
    return {int(l.split()[0]) for l in lp.read_text().splitlines() if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed/rdd2022_india")
    ap.add_argument("--split", default="train")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--per-class", type=int, default=5)
    args = ap.parse_args()

    data = Path(args.data)
    names = yaml.safe_load(open(data / "dataset.yaml"))["names"]
    lbls = [p for p in sorted((data / "labels" / args.split).glob("*.txt")) if p.stat().st_size > 0]
    random.Random(42).shuffle(lbls)
    cls = {p: classes_in(p) for p in lbls}

    chosen = []
    for cid in names:                                   # a few of every class first
        for p in [p for p in lbls if cid in cls[p] and p not in chosen][: args.per_class]:
            chosen.append(p)
    for p in lbls:                                      # then fill with random ones
        if len(chosen) >= args.n:
            break
        if p not in chosen:
            chosen.append(p)

    out = data / "label_check"
    out.mkdir(exist_ok=True)
    saved = 0
    for lp in chosen:
        ip = next((data / "images" / args.split / (lp.stem + e)
                   for e in IMG_EXTS if (data / "images" / args.split / (lp.stem + e)).exists()), None)
        img = cv2.imread(str(ip)) if ip else None
        if img is None:
            continue
        H, W = img.shape[:2]
        for line in lp.read_text().splitlines():
            cid, cx, cy, w, h = line.split()
            cid = int(cid)
            cx, cy, w, h = float(cx) * W, float(cy) * H, float(w) * W, float(h) * H
            p1, p2 = (int(cx - w / 2), int(cy - h / 2)), (int(cx + w / 2), int(cy + h / 2))
            color = COLORS.get(cid, (255, 255, 255))
            cv2.rectangle(img, p1, p2, color, 3)
            cv2.putText(img, names[cid], (p1[0], max(20, p1[1] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imwrite(str(out / f"{args.split}_{ip.name}"), img)
        saved += 1
    print(f"Saved {saved} images to {out}")


if __name__ == "__main__":
    main()
