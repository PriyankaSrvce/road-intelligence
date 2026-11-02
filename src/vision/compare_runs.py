"""Compare two MLflow runs (they may live in different SQLite DBs), per class.

Run from repo root:
    python src/vision/compare_runs.py
"""
import argparse

import mlflow
import pandas as pd

CLASSES = ["longitudinal_crack", "transverse_crack", "alligator_crack", "pothole"]
METRICS = ["precision", "recall", "f1", "mAP50", "mAP50_95"]


def load(db, run_name):
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    df = mlflow.search_runs(experiment_names=["road-intelligence-vision"])
    df = df[df["tags.mlflow.runName"] == run_name]
    if df.empty:
        raise SystemExit(f"Run '{run_name}' not found in {db}")
    row = df.iloc[0]
    return {k.replace("metrics.", ""): v for k, v in row.items()
            if k.startswith("metrics.") and v == v}


def build(a, b, split, metrics, la, lb):
    rows = []
    for c in CLASSES + ["ALL"]:
        row = {"class": c}
        for m in metrics:
            key = f"{split}_{m}" if c == "ALL" else f"{split}_{c}_{m}"
            va, vb = a.get(key, float("nan")), b.get(key, float("nan"))
            row[f"{m} {la}"] = va
            row[f"{m} {lb}"] = vb
            row[f"{m} diff"] = vb - va
        rows.append(row)
    return pd.DataFrame(rows).set_index("class").round(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-db", default="mlflow.db")
    ap.add_argument("--a-run", default="yolov8s_rdd-india_seed42_img640")
    ap.add_argument("--a-label", default="v8s")
    ap.add_argument("--b-db", default="mlflow_yolo11s.db")
    ap.add_argument("--b-run", default="yolo11s_rdd-india_seed42_img640")
    ap.add_argument("--b-label", default="11s")
    ap.add_argument("--out", default="docs/model_comparison.csv")
    args = ap.parse_args()

    la, lb = args.a_label, args.b_label
    a, b = load(args.a_db, args.a_run), load(args.b_db, args.b_run)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 50)

    frames = []
    for split in ("test", "val"):
        for group in (["mAP50", "mAP50_95"], ["precision", "recall", "f1"]):
            df = build(a, b, split, group, la, lb)
            print(f"\n=== {split.upper()}: {', '.join(group)}   (diff = {lb} minus {la}) ===")
            print(df.to_string())
        full = build(a, b, split, METRICS, la, lb)
        full.insert(0, "split", split)
        frames.append(full.reset_index())

    print("\n=== Speed and cost ===")
    for key in ("test_inference_ms", "val_inference_ms", "train_minutes"):
        va, vb = a.get(key, float("nan")), b.get(key, float("nan"))
        print(f"{key:<20} {la}: {va:8.2f}   {lb}: {vb:8.2f}")

    pd.concat(frames).to_csv(args.out, index=False)
    print(f"\nSaved full comparison to {args.out}")


if __name__ == "__main__":
    main()
