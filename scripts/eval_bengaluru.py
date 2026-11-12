#!/usr/bin/env python3
"""Zero-shot evaluation of the RDD2022-trained YOLOv8s weights on the
Bengaluru validation set (data/sample_dataset_yolo).

Every number comes from ultralytics model.val(). Nothing is typed in by hand.
Run from the repo root:  python scripts/eval_bengaluru.py
Outputs: docs/eval_results.json, docs/figures/bengaluru_*.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import cv2
import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT / "models" / "yolov8s_rdd_india_baseline.pt"
DATA_DIR = ROOT / "data" / "sample_dataset_yolo"
FIGS = ROOT / "docs" / "figures"
OUT_JSON = ROOT / "docs" / "eval_results.json"


def label_counts(names: dict) -> tuple[dict, int]:
    """Count GT boxes per class straight from the label files."""
    counts = {i: 0 for i in names}
    n_imgs = 0
    for f in sorted((DATA_DIR / "labels").glob("*.txt")):
        n_imgs += 1
        for line in f.read_text().splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    return counts, n_imgs


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def load_gt(stem, w, h):
    gts = []
    f = DATA_DIR / "labels" / f"{stem}.txt"
    if f.exists():
        for line in f.read_text().splitlines():
            p = line.split()
            if len(p) >= 5:
                c = int(p[0])
                cx, cy, bw, bh = (float(v) for v in p[1:5])
                gts.append((c, (cx - bw / 2) * w, (cy - bh / 2) * h,
                            (cx + bw / 2) * w, (cy + bh / 2) * h))
    return gts


def pick_examples(model, conf, device):
    """Auto-select 4 clean and 4 worst images by matching boxes at IoU 0.5.
    Failure causes are NOT guessed here: review the images and fill them in."""
    rows = []
    for img in sorted((DATA_DIR / "images").glob("*.jpg")):
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        gts = load_gt(img.stem, w, h)
        r = model.predict(str(img), conf=conf, device=device, verbose=False)[0]
        preds = [(int(b.cls[0]), *b.xyxy[0].tolist()) for b in r.boxes]
        used, tp = set(), 0
        for g in gts:
            for i, p in enumerate(preds):
                if i not in used and p[0] == g[0] and iou(g[1:], p[1:]) >= 0.5:
                    used.add(i)
                    tp += 1
                    break
        rows.append({"image": img.stem, "gt": len(gts), "tp": tp,
                     "fn": len(gts) - tp, "fp": len(preds) - tp})
    good = sorted([r for r in rows if r["gt"] > 0 and r["fn"] == 0 and r["fp"] == 0],
                  key=lambda r: -r["gt"])[:4]
    bad = sorted([r for r in rows if r["fn"] + r["fp"] > 0],
                 key=lambda r: -(r["fn"] + r["fp"]))[:4]
    for r in good:
        r["type"] = "correct"
    for r in bad:
        r["type"] = "failure"
        r["cause"] = "TO REVIEW MANUALLY (blur / shadow / small crack / class confusion / domain shift)"
    return good + bad


def draw_examples(examples, model, names, conf, device, out):
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))
    for ax, ex in zip(axes.flat, examples):
        img_p = DATA_DIR / "images" / f"{ex['image']}.jpg"
        im = cv2.cvtColor(cv2.imread(str(img_p)), cv2.COLOR_BGR2RGB)
        h, w = im.shape[:2]
        sc = 480 / h
        disp = cv2.resize(im, (int(w * sc), 480))
        for c, x1, y1, x2, y2 in load_gt(ex["image"], w, h):
            cv2.rectangle(disp, (int(x1 * sc), int(y1 * sc)), (int(x2 * sc), int(y2 * sc)), (0, 255, 0), 2)
        r = model.predict(str(img_p), conf=conf, device=device, verbose=False)[0]
        for b in r.boxes:
            x1, y1, x2, y2 = [int(v * sc) for v in b.xyxy[0].tolist()]
            cv2.rectangle(disp, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(disp, f"{names[int(b.cls[0])]} {float(b.conf[0]):.2f}", (x1, max(y1 - 4, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        ax.imshow(disp)
        ax.axis("off")
        ax.set_title(f"{ex['type']}: {ex['image'][-12:]}\nGT={ex['gt']} TP={ex['tp']} FN={ex['fn']} FP={ex['fp']}",
                     fontsize=9, color="#1b7f3b" if ex["type"] == "correct" else "#c00000")
    fig.suptitle("Green = ground truth, Blue = prediction (conf >= %.2f)" % conf)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def measure_fps(model, device, n=20):
    img = next((DATA_DIR / "images").glob("*.jpg"))
    for _ in range(3):
        model.predict(str(img), device=device, verbose=False)
    t = time.perf_counter()
    for _ in range(n):
        model.predict(str(img), device=device, verbose=False)
    dt = (time.perf_counter() - t) / n
    return round(1 / dt, 2), round(dt * 1000, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(WEIGHTS))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf-vis", type=float, default=0.25, help="threshold for qualitative images only")
    a = ap.parse_args()

    from ultralytics import YOLO

    if not Path(a.weights).exists():
        sys.exit(f"weights not found: {a.weights}")
    model = YOLO(a.weights)
    names = model.names
    print("MODEL CLASS NAMES:", names)

    counts, n_imgs = label_counts(names)
    print(f"IMAGES: {n_imgs}  GT BOXES PER CLASS ID: {counts}")
    present = {i: c for i, c in counts.items() if c > 0}
    print("Classes with ground truth:", {i: names[i] for i in present})
    print("CHECK: confirm these class IDs mean what you think (e.g. 2=alligator/D20, 3=pothole/D40).")

    FIGS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        yml = Path(tmp) / "bengaluru.yaml"
        yml.write_text(yaml.dump({"path": str(DATA_DIR.resolve()), "train": "images", "val": "images",
                                  "names": {int(k): v for k, v in names.items()}}))
        res = model.val(data=str(yml), split="val", imgsz=a.imgsz, conf=0.001, iou=0.6,
                        device=a.device, plots=True, verbose=True,
                        project=str(ROOT / "runs" / "eval"), name="bengaluru_zero_shot", exist_ok=True)

    box = res.box
    per_class = {}
    for k, cid in enumerate(box.ap_class_index.tolist()):
        p, r = float(box.p[k]), float(box.r[k])
        per_class[names[cid]] = {"class_id": cid, "gt_boxes": counts.get(cid, 0),
                                 "precision": round(p, 4), "recall": round(r, 4),
                                 "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                                 "ap50": round(float(box.ap50[k]), 4),
                                 "ap50_95": round(float(box.ap[k]), 4)}
    not_evaluable = [names[i] for i in names if counts.get(i, 0) == 0]

    # copy ultralytics' own plots (confusion matrix, PR curve) at the standard location
    for src, dst in [("confusion_matrix.png", "bengaluru_cm.png"), ("PR_curve.png", "bengaluru_pr.png")]:
        f = Path(res.save_dir) / src
        if f.exists():
            shutil.copy(f, FIGS / dst)

    fps, ms = measure_fps(model, a.device)
    examples = pick_examples(model, a.conf_vis, a.device)
    draw_examples(examples, model, names, a.conf_vis, a.device, FIGS / "bengaluru_qual.png")

    out = {
        "weights": Path(a.weights).name, "eval_type": "zero-shot", "domain": "bengaluru",
        "n_images": n_imgs, "n_boxes": sum(counts.values()),
        "boxes_per_class": {names[i]: c for i, c in counts.items()},
        "not_evaluable_classes": not_evaluable,
        "val_settings": {"imgsz": a.imgsz, "conf": 0.001, "iou": 0.6, "device": a.device},
        "map50": round(float(box.map50), 4), "map50_95": round(float(box.map), 4),
        "per_class": per_class, "inference_fps": fps, "inference_ms": ms,
        "qualitative_examples": examples, "mlflow_run_id": None,
    }

    try:
        import mlflow
        mlflow.set_experiment("bengaluru_domain_eval")
        with mlflow.start_run(run_name="bengaluru_zero_shot") as run:
            mlflow.set_tags({"domain": "bengaluru", "eval": "zero-shot", "data_source": "real"})
            mlflow.log_metrics({"map50": out["map50"], "map50_95": out["map50_95"], "fps": fps})
            for f in FIGS.glob("bengaluru_*.png"):
                mlflow.log_artifact(str(f), "figures")
            out["mlflow_run_id"] = run.info.run_id
    except Exception as e:  # noqa: BLE001
        print("MLflow logging skipped:", e)

    OUT_JSON.write_text(json.dumps(out, indent=2))
    print("\n=== RESULT ===")
    print(json.dumps({k: out[k] for k in ("n_images", "n_boxes", "boxes_per_class", "not_evaluable_classes",
                                          "map50", "map50_95", "per_class", "inference_fps",
                                          "mlflow_run_id")}, indent=2))
    print("Wrote", OUT_JSON, "and figures in", FIGS)


if __name__ == "__main__":
    main()