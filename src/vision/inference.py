"""Road-damage inference: run the detector and return records in the agreed Vision output format.

Python use (run from repo root, e.g. from FastAPI):
    from src.vision.inference import run_inference
    result = run_inference("frame.jpg", image_id="SURVEY01_000123")

Command line:
    python src/vision/inference.py --source <image or folder> --limit 10 --out docs/sample_inference_output.json
"""
import argparse
import json
from functools import lru_cache
from pathlib import Path

import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = str(ROOT / "models" / "yolov8s_rdd_india_baseline.pt")
DEFAULT_MODEL_VERSION = "yolov8s_rdd-india_seed42_img640"
SCHEMA_VERSION = "1.0"
IMG_EXTS = {".jpg", ".jpeg", ".png"}


def load_classes():
    cfg = yaml.safe_load(open(ROOT / "configs" / "classes.yaml"))["classes"]
    return {int(k): {"code": v["code"], "name": v["name"]} for k, v in cfg.items()}


class RoadDamageDetector:
    def __init__(self, weights=DEFAULT_WEIGHTS, model_version=DEFAULT_MODEL_VERSION,
                 device="cpu", imgsz=640):
        self.classes = load_classes()
        self.model = YOLO(str(weights))
        self.model_version = model_version
        self.device = device
        self.imgsz = imgsz
        names = {int(k): v for k, v in self.model.names.items()}
        expected = {k: v["name"] for k, v in self.classes.items()}
        if names != expected:
            raise ValueError(f"Weights class names {names} do not match configs/classes.yaml {expected}")

    def predict(self, image, image_id=None, conf_threshold=0.25):
        if isinstance(image, Path):
            image = str(image)
        if image_id is None:
            if isinstance(image, str):
                image_id = Path(image).stem
            else:
                raise ValueError("image_id is required when image is a numpy array")
        res = self.model.predict(source=image, conf=conf_threshold, imgsz=self.imgsz,
                                 device=self.device, verbose=False)[0]
        h, w = res.orig_shape
        dets = []
        b = res.boxes
        for (x1, y1, x2, y2), conf, cls in zip(b.xyxy.tolist(), b.conf.tolist(), b.cls.tolist()):
            x1, x2 = min(max(x1, 0.0), w), min(max(x2, 0.0), w)
            y1, y2 = min(max(y1, 0.0), h), min(max(y2, 0.0), h)
            cid = int(cls)
            dets.append({
                "class_id": cid,
                "class_code": self.classes[cid]["code"],
                "class_name": self.classes[cid]["name"],
                "confidence": round(conf, 4),
                "x_min": round(x1, 1), "y_min": round(y1, 1),
                "x_max": round(x2, 1), "y_max": round(y2, 1),
                "area_ratio": round((x2 - x1) * (y2 - y1) / (w * h), 6),
                "model_version": self.model_version,
            })
        dets.sort(key=lambda d: d["confidence"], reverse=True)
        return {
            "schema_version": SCHEMA_VERSION,
            "image_id": image_id,
            "image_width": int(w),
            "image_height": int(h),
            "model_version": self.model_version,
            "conf_threshold": conf_threshold,
            "inference_ms": round(res.speed["inference"], 1),
            "num_detections": len(dets),
            "detections": dets,
        }


@lru_cache(maxsize=2)
def get_detector(weights=DEFAULT_WEIGHTS, model_version=DEFAULT_MODEL_VERSION, device="cpu"):
    """Load the model once and reuse it (important for an API)."""
    return RoadDamageDetector(weights, model_version, device)


def run_inference(image, image_id=None, conf_threshold=0.25, weights=DEFAULT_WEIGHTS,
                  model_version=DEFAULT_MODEL_VERSION, device="cpu"):
    """image: file path (str/Path) or BGR numpy array. Returns one dict per image."""
    return get_detector(weights, model_version, device).predict(image, image_id, conf_threshold)


def to_db_rows(result):
    """One flat row per detection, ready for the damage_detections table."""
    keys = ("class_id", "confidence", "x_min", "y_min", "x_max", "y_max",
            "area_ratio", "model_version")
    return [{"image_id": result["image_id"], **{k: d[k] for k in keys}}
            for d in result["detections"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="image file or folder of images")
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--weights", default=DEFAULT_WEIGHTS)
    ap.add_argument("--model-version", default=DEFAULT_MODEL_VERSION)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    src = Path(args.source)
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXTS) if src.is_dir() else [src]
    if args.limit:
        files = files[: args.limit]
    results = [run_inference(f, conf_threshold=args.conf, weights=args.weights,
                             model_version=args.model_version, device=args.device)
               for f in files]

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"Saved {len(results)} results to {args.out}")

    with_dets = next((r for r in results if r["num_detections"]), None)
    without = next((r for r in results if not r["num_detections"]), None)
    for label, r in (("WITH DETECTIONS", with_dets), ("NO DETECTIONS", without)):
        if r:
            print(f"\n--- example: {label} ---")
            print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
