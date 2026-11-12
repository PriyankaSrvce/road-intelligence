"""Generate a blank human rating sheet as CSV."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from condition.ratings import make_rating_template, read_segment_ids


def main() -> None:
    """Read segment and rater inputs and write a rating template."""
    parser = argparse.ArgumentParser(description="Create a blank road rating sheet.")
    parser.add_argument("--segments", required=True, help="Text file with one segment ID per line")
    parser.add_argument("--raters", required=True, help="Comma-separated rater names")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args()

    segment_ids = read_segment_ids(args.segments)
    raters = [rater.strip() for rater in args.raters.split(",") if rater.strip()]
    template = make_rating_template(segment_ids, raters)
    template.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
