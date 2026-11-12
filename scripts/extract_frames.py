#!/usr/bin/env python3
"""Stages 2-4: extract frames (1 per second) from the road clips, sync them to the
real GPX track, mask the GPS-Map-Camera overlay and the bike fairing, and reject
unusable frames with a recorded reason.

Run from the repo root:  python scripts/extract_frames.py
Reads:   data/clips_manifest.csv, data/gps/*.gpx, data/videos/*.mp4
Writes:  data/extracted_frames/<clip>/<clip>_<sec>.jpg  (masked, kept frames only)
         data/frames_geotagged.csv  (every sampled frame, kept or rejected, with reason)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FMT = "%Y-%m-%dT%H:%M:%SZ"
EPOCH = dt.datetime(1970, 1, 1)

# Regions as fractions of the frame: (x0, y0, x1, y1). Tune by looking at the output.
MASKS = [(0.18, 0.64, 0.80, 0.96),   # GPS Map Camera overlay box (address, lat/long)
         (0.00, 0.55, 0.25, 1.00)]   # bike fairing, bottom-left
PROBE = (0.22, 0.70, 0.78, 0.93)     # inside the overlay: should be dark if the frame is upright


def epoch(s: str) -> float:
    return (dt.datetime.strptime(s, FMT) - EPOCH).total_seconds()


def load_gpx(path: Path):
    t, lat, lon, spd = [], [], [], []
    for el in ET.parse(path).getroot().iter():
        if el.tag.endswith("trkpt"):
            tm, s = None, 0.0
            for ch in el:
                if ch.tag.endswith("time"):
                    tm = epoch(ch.text.strip())
                elif ch.tag.endswith("speed"):
                    s = float(ch.text)
            if tm is not None:
                t.append(tm)
                lat.append(float(el.get("lat")))
                lon.append(float(el.get("lon")))
                spd.append(s * 3.6)  # m/s -> km/h
    return np.array(t), np.array(lat), np.array(lon), np.array(spd)


def region(img, box):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    return int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "data" / "clips_manifest.csv"))
    ap.add_argument("--gpx", default=str(next((ROOT / "data" / "gps").glob("*.gpx"))))
    ap.add_argument("--videos", default=str(ROOT / "data" / "videos"))
    ap.add_argument("--out", default=str(ROOT / "data" / "extracted_frames"))
    ap.add_argument("--min-speed", type=float, default=2.0, help="km/h; slower frames are rejected")
    ap.add_argument("--min-blur", type=float, default=25.0, help="Laplacian variance of the road area")
    ap.add_argument("--max-overlay-brightness", type=float, default=115.0)
    a = ap.parse_args()

    gt, glat, glon, gspd = load_gpx(Path(a.gpx))
    print(f"GPX: {len(gt)} points, {dt.datetime.utcfromtimestamp(gt[0])} to {dt.datetime.utcfromtimestamp(gt[-1])} UTC")

    rows, totals = [], Counter()
    with open(a.manifest) as f:
        clips = list(csv.DictReader(f))

    for c in clips:
        vid = Path(a.videos) / c["clip_file"]
        clip_id = vid.stem[:15]
        start = epoch(c["gpx_start_utc"])
        outdir = Path(a.out) / clip_id
        outdir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(vid))
        next_sec, stats = 0.0, Counter()

        while cap.grab():
            pos = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if pos < next_sec:
                continue
            ok, frame = cap.retrieve()
            next_sec = int(pos) + 1
            if not ok:
                continue
            ts = start + pos
            h, w = frame.shape[:2]
            row = {"clip_file": c["clip_file"], "t_s": round(pos, 2),
                   "utc_time": dt.datetime.utcfromtimestamp(ts).strftime(FMT),
                   "lat": "", "lon": "", "speed_kmh": "", "overlay_brightness": "", "blur_var": "",
                   "status": "", "reason": "", "path": "",
                   "gps_quality": "logged", "sync_method": c["sync_method"]}

            if not (gt[0] <= ts <= gt[-1]):
                row.update(status="rejected", reason="no_gps_coverage")
            else:
                row["lat"] = round(float(np.interp(ts, gt, glat)), 7)
                row["lon"] = round(float(np.interp(ts, gt, glon)), 7)
                row["speed_kmh"] = round(float(np.interp(ts, gt, gspd)), 1)
                x0, y0, x1, y1 = region(frame, PROBE)
                bright = float(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).mean())
                road = cv2.cvtColor(frame[: int(0.6 * h)], cv2.COLOR_BGR2GRAY)
                blur = float(cv2.Laplacian(road, cv2.CV_64F).var())
                row["overlay_brightness"], row["blur_var"] = round(bright, 1), round(blur, 1)
                if row["speed_kmh"] < a.min_speed:
                    row.update(status="rejected", reason="stationary")
                elif bright > a.max_overlay_brightness:
                    row.update(status="rejected", reason="not_upright_or_no_overlay")
                elif blur < a.min_blur:
                    row.update(status="rejected", reason="blurred_or_covered")
                else:
                    for m in MASKS:
                        x0, y0, x1, y1 = region(frame, m)
                        frame[y0:y1, x0:x1] = 114  # YOLO letterbox grey
                    p = outdir / f"{clip_id}_{int(pos):04d}.jpg"
                    cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    row.update(status="kept", path=str(p.relative_to(ROOT)))

            stats[row["reason"] or "kept"] += 1
            rows.append(row)

        totals.update(stats)
        print(f"{c['clip_file']}: sampled={sum(stats.values())}  {dict(stats)}")

    out_csv = ROOT / "data" / "frames_geotagged.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nTOTAL sampled={sum(totals.values())}  {dict(totals)}")
    print(f"Wrote {out_csv.relative_to(ROOT)}")
    print("Check the rejected reasons by eye; tune --min-blur and --max-overlay-brightness if needed.")


if __name__ == "__main__":
    main()
