"""Train a YOLO detector and log everything to MLflow (SQLite backend).

Run from the repo root, e.g.
    python src/vision/train.py --model yolov8s.pt --epochs 50 --device 0
"""
import argparse
import sys
import time
from pathlib import Path

import mlflow
import pandas as pd
from ultralytics import YOLO, settings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from naming import run_name  # noqa: E402

PROJECT = str(Path("runs/vision").resolve())


def log_eval(model, split, data, args, name):
    m = model.val(data=data, split=split, imgsz=args.imgsz, batch=args.batch,
                  device=args.device, workers=args.workers, plots=False,
                  project=PROJECT, name=f"{name}_{split}", exist_ok=True, verbose=False)
    box = m.box
    metrics = {
        f"{split}_precision": float(box.mp),
        f"{split}_recall": float(box.mr),
        f"{split}_f1": float(box.f1.mean()) if len(box.f1) else 0.0,
        f"{split}_mAP50": float(box.map50),
        f"{split}_mAP50_95": float(box.map),
        f"{split}_inference_ms": float(m.speed["inference"]),
    }
    print(f"\n=== {split.upper()} (inference {m.speed['inference']:.1f} ms/img) ===")
    print(f"{'class':<20}{'P':>8}{'R':>8}{'F1':>8}{'mAP50':>8}{'mAP50-95':>10}")
    seen = set()
    for k, ci in enumerate(box.ap_class_index):
        ci = int(ci)
        seen.add(ci)
        cname = m.names[ci]
        p, r, ap50, ap = (float(v) for v in box.class_result(k))
        f1 = float(box.f1[k])
        metrics.update({
            f"{split}_{cname}_precision": p, f"{split}_{cname}_recall": r,
            f"{split}_{cname}_f1": f1, f"{split}_{cname}_mAP50": ap50,
            f"{split}_{cname}_mAP50_95": ap,
        })
        print(f"{cname:<20}{p:>8.3f}{r:>8.3f}{f1:>8.3f}{ap50:>8.3f}{ap:>10.3f}")
    for ci, cname in m.names.items():
        if ci not in seen:
            print(f"{cname:<20} no instances in this split")
    print(f"{'ALL':<20}{box.mp:>8.3f}{box.mr:>8.3f}{metrics[f'{split}_f1']:>8.3f}"
          f"{box.map50:>8.3f}{box.map:>10.3f}")
    mlflow.log_metrics(metrics)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolov8s.pt")
    ap.add_argument("--data", default="data/processed/rdd2022_india/dataset.yaml")
    ap.add_argument("--dataset-tag", default="rdd-india")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--tag", default="")
    ap.add_argument("--plots", action="store_true")
    args = ap.parse_args()

    try:
        settings.update({"mlflow": False})  # we log to MLflow ourselves
    except Exception:
        pass
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("road-intelligence-vision")

    data = str(Path(args.data).resolve())
    name = run_name(Path(args.model).stem, args.dataset_tag, args.seed, args.imgsz, args.tag)

    with mlflow.start_run(run_name=name):
        mlflow.log_params({
            "model": args.model, "dataset": args.dataset_tag, "data_yaml": args.data,
            "epochs": args.epochs, "imgsz": args.imgsz, "batch": args.batch,
            "seed": args.seed, "device": args.device,
        })
        model = YOLO(args.model)
        t0 = time.time()
        model.train(data=data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                    seed=args.seed, device=args.device, workers=args.workers,
                    project=PROJECT, name=name, exist_ok=True, plots=args.plots)
        mlflow.log_metric("train_minutes", (time.time() - t0) / 60)

        save_dir = Path(model.trainer.save_dir)
        results_csv = save_dir / "results.csv"
        if results_csv.exists():
            res = pd.read_csv(results_csv)
            res.columns = [c.strip() for c in res.columns]
            for _, row in res.iterrows():
                step = int(row["epoch"])
                mlflow.log_metrics(
                    {k.replace("(B)", "").replace("/", "_"): float(v)
                     for k, v in row.items() if k != "epoch" and pd.notna(v)},
                    step=step)
            mlflow.log_artifact(str(results_csv))

        best = save_dir / "weights" / "best.pt"
        if not best.exists():
            best = save_dir / "weights" / "last.pt"
        mlflow.log_artifact(str(best))

        final = YOLO(str(best))
        for split in ("val", "test"):
            log_eval(final, split, data, args, name)

        print(f"\nRun name : {name}")
        print(f"Weights  : {best}")


if __name__ == "__main__":
    main()
