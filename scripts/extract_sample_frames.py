"""Extract frames from road survey videos with quality assessment.

Extracts one frame every N seconds from MP4 videos.  Optionally computes
a Laplacian variance blur score so blurry frames can be filtered.

Run from repo root:
    python scripts/extract_sample_frames.py \\
        --input data/raw_videos/ \\
        --output data/sample_frames/ \\
        --interval 1.0 \\
        --blur-threshold 50
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    sys.exit("opencv-python is required.  pip install opencv-python")


def blur_score(frame) -> float:
    """Laplacian variance — higher = sharper."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def extract_frames(
    video_path: Path,
    output_dir: Path,
    interval_sec: float = 1.0,
    blur_threshold: float = 0.0,
    prefix: str = "",
) -> list[dict]:
    """Extract frames from *video_path* every *interval_sec* seconds.

    Returns a list of metadata dicts (frame_index, timestamp_sec,
    blur_score, file_path, accepted).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, int(fps * interval_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    idx = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if idx % frame_interval == 0:
            score = blur_score(frame)
            ts = idx / fps
            accepted = score >= blur_threshold

            fname = f"{prefix}{video_path.stem}_{idx:06d}.jpg"
            fpath = output_dir / fname

            if accepted:
                cv2.imwrite(str(fpath), frame)
                saved += 1

            results.append({
                "video": video_path.name,
                "frame_index": idx,
                "timestamp_sec": round(ts, 2),
                "blur_score": round(score, 2),
                "accepted": accepted,
                "file_path": str(fpath) if accepted else "",
            })

        idx += 1

    cap.release()
    print(f"  {video_path.name}: {idx} frames, {len(results)} sampled, "
          f"{saved} accepted (blur ≥ {blur_threshold})")
    return results


def main():
    parser = argparse.ArgumentParser(description="Extract frames from road survey videos")
    parser.add_argument("--input", required=True, help="Video file or directory of videos")
    parser.add_argument("--output", default="data/sample_frames", help="Output directory")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between frames")
    parser.add_argument("--blur-threshold", type=float, default=0.0,
                        help="Minimum blur score to accept (0 = accept all)")
    parser.add_argument("--csv", default="", help="Output CSV path for metadata")
    args = parser.parse_args()

    src = Path(args.input)
    out = Path(args.output)

    if src.is_dir():
        videos = sorted(src.glob("*.mp4")) + sorted(src.glob("*.MP4"))
    elif src.is_file():
        videos = [src]
    else:
        sys.exit(f"Input not found: {src}")

    if not videos:
        sys.exit(f"No MP4 files found in {src}")

    print(f"Processing {len(videos)} video(s) → {out}/")
    all_meta = []
    for v in videos:
        meta = extract_frames(v, out, args.interval, args.blur_threshold)
        all_meta.extend(meta)

    # Write metadata CSV
    csv_path = Path(args.csv) if args.csv else out / "frame_extraction_log.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_meta[0].keys())
        writer.writeheader()
        writer.writerows(all_meta)
    print(f"\n✓ Metadata saved to {csv_path}")
    print(f"  Total frames sampled: {len(all_meta)}")
    print(f"  Accepted: {sum(1 for r in all_meta if r['accepted'])}")


if __name__ == "__main__":
    main()

