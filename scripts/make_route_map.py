#!/usr/bin/env python3
"""Build (1) an interactive route map and (2) a manual-review sheet from real data.

Run from the repo root:  python scripts/make_route_map.py
Needs:   pip install folium
Reads:   data/gps/*.gpx, data/frames_geotagged.csv, data/detections.csv
Writes:  docs/route_map.html                      open in a browser (needs internet for map tiles)
         docs/figures/diag/review_top24.jpg       numbered boxes to judge by eye
         docs/manual_review.csv                   fill the 'verdict' column with tp / fp

The route is coloured by the share of sampled frames that had at least one detection.
These are RAW model outputs (unvalidated, include false positives), not condition scores.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import cv2
import folium
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FMT = "%Y-%m-%dT%H:%M:%SZ"
EPOCH = dt.datetime(1970, 1, 1)
CLASS_COL = {"pothole": "#ef4444", "alligator_crack": "#f97316",
             "longitudinal_crack": "#eab308", "transverse_crack": "#38bdf8"}


def epoch(s):
    return (dt.datetime.strptime(s, FMT) - EPOCH).total_seconds()


def load_gpx(path):
    t, lat, lon = [], [], []
    for el in ET.parse(path).getroot().iter():
        if el.tag.endswith("trkpt"):
            tm = None
            for ch in el:
                if ch.tag.endswith("time"):
                    tm = epoch(ch.text.strip())
            if tm is not None:
                t.append(tm)
                lat.append(float(el.get("lat")))
                lon.append(float(el.get("lon")))
    return np.array(t), np.array(lat), np.array(lon)


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


def crop_b64(path, box, pad=40, max_w=260):
    im = cv2.imread(str(ROOT / path))
    if im is None:
        return ""
    h, w = im.shape[:2]
    x1, y1, x2, y2 = box
    c = im[max(0, y1 - pad):min(h, y2 + pad), max(0, x1 - pad):min(w, x2 + pad)]
    s = max_w / c.shape[1]
    c = cv2.resize(c, (max_w, max(1, int(c.shape[0] * s))))
    ok, buf = cv2.imencode(".jpg", c, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode() if ok else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpx", default=str(next((ROOT / "data" / "gps").glob("*.gpx"))))
    ap.add_argument("--chunk-m", type=float, default=100.0)
    ap.add_argument("--min-conf", type=float, default=0.30)
    ap.add_argument("--max-markers", type=int, default=250)
    a = ap.parse_args()

    gt, glat, glon = load_gpx(Path(a.gpx))
    cum = np.concatenate([[0], np.cumsum([hav(glat[i], glon[i], glat[i + 1], glon[i + 1]) for i in range(len(gt) - 1)])])
    chunk_of_pt = (cum // a.chunk_m).astype(int)
    n_chunks = chunk_of_pt.max() + 1
    print(f"track {cum[-1] / 1000:.2f} km -> {n_chunks} chunks of {a.chunk_m:.0f} m")

    frames = [r for r in csv.DictReader(open(ROOT / "data" / "frames_geotagged.csv")) if r["status"] == "kept"]
    dets = [d for d in csv.DictReader(open(ROOT / "data" / "detections.csv")) if float(d["conf"]) >= a.min_conf]

    def chunk_at(utc):
        return int(np.interp(epoch(utc), gt, cum) // a.chunk_m)

    kept_n, flagged = defaultdict(int), defaultdict(set)
    for r in frames:
        kept_n[chunk_at(r["utc_time"])] += 1
    for d in dets:
        flagged[chunk_at(d["utc_time"])].add(d["path"])

    def colour(share):
        return "#22c55e" if share == 0 else "#eab308" if share <= 0.15 else "#f97316" if share <= 0.35 else "#ef4444"

    m = folium.Map(location=[glat.mean(), glon.mean()], zoom_start=14, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", attr="Esri, HERE, Garmin, OpenStreetMap contributors")
    for ci in range(n_chunks):
        idx = np.where(chunk_of_pt == ci)[0]
        if len(idx) < 2:
            continue
        pts = list(zip(glat[idx].tolist(), glon[idx].tolist()))
        k = kept_n.get(ci, 0)
        share = len(flagged.get(ci, ())) / k if k else 0
        folium.PolyLine(pts, color=colour(share) if k else "#64748b", weight=6, opacity=0.9,
                        tooltip=f"chunk {ci}: {k} frames, {len(flagged.get(ci, ()))} flagged ({share:.0%})").add_to(m)

    top = sorted(dets, key=lambda d: -float(d["conf"]))[:a.max_markers]
    for d in top:
        img = crop_b64(d["path"], (int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"])))
        html = (f"<b>{d['class_name']}</b> conf {d['conf']}<br>{d['utc_time']} UTC<br>"
                f"{float(d['lat']):.5f}, {float(d['lon']):.5f}<br><i>unvalidated model output</i><br>"
                f"<img src='data:image/jpeg;base64,{img}' width='240'>")
        folium.CircleMarker([float(d["lat"]), float(d["lon"])], radius=5, color=CLASS_COL.get(d["class_name"], "#fff"),
                            fill=True, fill_opacity=0.9, popup=folium.Popup(html, max_width=280)).add_to(m)
    folium.Marker([glat[0], glon[0]], tooltip="Start").add_to(m)
    folium.Marker([glat[-1], glon[-1]], tooltip="End").add_to(m)
    m.get_root().html.add_child(folium.Element(
        "<div style='position:fixed;bottom:20px;left:20px;z-index:9999;background:#1e293bcc;color:#fff;"
        "padding:10px 14px;border-radius:8px;font:12px sans-serif;max-width:320px'>"
        "<b>REAL DATA</b> (logged GPS, clips synced by filename time)<br>"
        f"Route colour = share of frames with a detection per {a.chunk_m:.0f} m "
        "(green 0, yellow &le;15%, orange &le;35%, red &gt;35%, grey = no usable frames).<br>"
        f"Dots = detections with conf &ge; {a.min_conf}. RAW and UNVALIDATED: includes false positives. "
        "Not a condition score.</div>"))
    out = ROOT / "docs" / "route_map.html"
    m.save(str(out))
    print("wrote", out.relative_to(ROOT), f"({len(top)} markers of {len(dets)} detections >= {a.min_conf})")

    # manual-review sheet: top 24 distinct frames by confidence
    seen, pick = set(), []
    for d in sorted(dets, key=lambda d: -float(d["conf"])):
        if d["path"] not in seen:
            seen.add(d["path"])
            pick.append(d)
        if len(pick) == 24:
            break
    thumbs = []
    for i, d in enumerate(pick, 1):
        im = cv2.imread(str(ROOT / d["path"]))
        cv2.rectangle(im, (int(d["x1"]), int(d["y1"])), (int(d["x2"]), int(d["y2"])), (0, 0, 255), 5)
        t = cv2.resize(im, (320, 180))
        cv2.putText(t, f"#{i} {d['class_name'][:5]} {d['conf']}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        thumbs.append(t)
    while thumbs and len(thumbs) % 6:
        thumbs.append(np.zeros((180, 320, 3), np.uint8))
    if thumbs:
        sheet = ROOT / "docs" / "figures" / "diag" / "review_top24.jpg"
        sheet.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(sheet), np.vstack([np.hstack(thumbs[i:i + 6]) for i in range(0, len(thumbs), 6)]))
        with open(ROOT / "docs" / "manual_review.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rank", "path", "class_name", "conf", "verdict"])
            for i, d in enumerate(pick, 1):
                w.writerow([i, d["path"], d["class_name"], d["conf"], ""])
        print("wrote review sheet and docs/manual_review.csv (fill 'verdict' with tp or fp)")


if __name__ == "__main__":
    main()
