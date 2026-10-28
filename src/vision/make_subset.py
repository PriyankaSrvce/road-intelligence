"""Make a tiny copy of the dataset for laptop smoke tests.
Run from repo root:  python src/vision/make_subset.py
"""
import argparse
import random
import shutil
from pathlib import Path

IMG_EXTS = (".jpg", ".jpeg", ".png")


def find_image(img_dir, stem):
    for ext in IMG_EXTS:
        p = img_dir / (stem + ext)
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/processed/rdd2022_india")
    ap.add_argument("--out", default="data/processed/rdd2022_tiny")
    ap.add_argument("--train", type=int, default=120)
    ap.add_argument("--val", type=int, default=40)
    ap.add_argument("--test", type=int, default=40)
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    rnd = random.Random(42)

    for split, n in (("train", args.train), ("val", args.val), ("test", args.test)):
        lbls = sorted((src / "labels" / split).glob("*.txt"))
        full = [p for p in lbls if p.stat().st_size > 0]
        empty = [p for p in lbls if p.stat().st_size == 0]
        rnd.shuffle(full)
        rnd.shuffle(empty)
        n_empty = n // 5
        chosen = full[: n - n_empty] + empty[:n_empty]
        (out / "images" / split).mkdir(parents=True)
        (out / "labels" / split).mkdir(parents=True)
        for lp in chosen:
            ip = find_image(src / "images" / split, lp.stem)
            shutil.copy2(ip, out / "images" / split / ip.name)
            shutil.copy2(lp, out / "labels" / split / lp.name)
        print(f"{split}: {len(chosen)} images")

    shutil.copy2(src / "dataset.yaml", out / "dataset.yaml")
    print(f"Done. Tiny dataset in {out}")


if __name__ == "__main__":
    main()
