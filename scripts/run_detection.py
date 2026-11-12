#!/usr/bin/env python3
"""Stage 5: run the RDD2022-trained YOLOv8s weights on the kept, geotagged frames.

Run from the repo root:  python scripts/run_detection.py
Reads:   data/frames_geotagged.csv (rows with status == kept)
Writes:  data/detections.csv                        every detection with the frame's GPS
         docs/figures/diag/detections/*.jpg         annotated frames with the most confident hits
Nothing is invented: counts below are what the model actually returned.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(ROOT / "models" / "yolov8s_rdd_india_baseline.pt"))
    ap.add_argument("--frames-csv", default=str(ROOT / "data" / "frames_geotagged.csv"))
    ap.add_argument("--conf", type=float, default=0.15, help="low on purpose: model is weak on this domain")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--examples", type=int, default=24)
    a = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(a.weights)
    names = model.names
    print("classes:", names, "| conf >=", a.conf, "| imgsz", a.imgsz)

    frames = [r for r in csv.DictReader(open(a.frames_csv)) if r["status"] == "kept"]
    print("kept frames to process:", len(frames))

    dets, per_frame = [], Counter()
    for i in range(0, len(frames), 16):
        batch = frames[i:i + 16]
        results = model.predict([str(ROOT / r["path"]) for r in batch], conf=a.conf,
                                imgsz=a.imgsz, device=a.device, verbose=False)
        for r, res in zip(batch, results):
            h, w = res.orig_shape
            for b in res.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cid = int(b.cls[0])
                dets.append({"path": r["path"], "clip_file": r["clip_file"], "t_s": r["t_s"],
                             "utc_time": r["utc_time"], "lat": r["lat"], "lon": r["lon"],
                             "speed_kmh": r["speed_kmh"], "class_id": cid, "class_name": names[cid],
                             "conf": round(float(b.conf[0]), 3),
                             "x1": round(x1), "y1": round(y1), "x2": round(x2), "y2": round(y2),
                             "area_ratio": round((x2 - x1) * (y2 - y1) / (w * h), 4),
                             "gps_quality": r["gps_quality"], "data_source": "real"})
                per_frame[r["path"]] += 1
        print(f"  processed {min(i + 16, len(frames))}/{len(frames)}", end="\r")

    out = ROOT / "data" / "detections.csv"
    fields = list(dets[0].keys()) if dets else ["path"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dets)

    print("\n=== SUMMARY (real model output) ===")
    print("frames processed:", len(frames))
    print("frames with >=1 detection:", len(per_frame))
    print("total detections:", len(dets))
    print("per class:", dict(Counter(d["class_name"] for d in dets)))
    if dets:
        confs = sorted(d["conf"] for d in dets)
        print(f"confidence: min {confs[0]}  median {confs[len(confs)//2]}  max {confs[-1]}")
    print("wrote", out.relative_to(ROOT))

    # annotated examples: most confident detections, one per frame
    exdir = ROOT / "docs" / "figures" / "diag" / "detections"
    exdir.mkdir(parents=True, exist_ok=True)
    best = {}
    for d in dets:
        if d["path"] not in best or d["conf"] > best[d["path"]]["conf"]:
            best[d["path"]] = d
    for d in sorted(best.values(), key=lambda d: -d["conf"])[:a.examples]:
        im = cv2.imread(str(ROOT / d["path"]))
        for e in dets:
            if e["path"] == d["path"]:
                cv2.rectangle(im, (e["x1"], e["y1"]), (e["x2"], e["y2"]), (0, 0, 255), 3)
                cv2.putText(im, f"{e['class_name']} {e['conf']}", (e["x1"], max(e["y1"] - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imwrite(str(exdir / f"{d['conf']:.2f}_{Path(d['path']).name}"), im)
    print("annotated examples in", exdir.relative_to(ROOT))


if __name__ == "__main__":
    main()
