"""Generate and summarize a reproducible example rating sheet."""

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from condition.ratings import make_rating_template, mean_rating, ratings_wide, validate_ratings


def main() -> None:
    """Write demo data and print validated rating summaries."""
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    segment_ids = [f"S{number}" for number in range(1, 7)]
    raters = ["Asha", "Ravi", "Meena"]
    segments_path = data_dir / "demo_segments.txt"
    ratings_path = data_dir / "demo_ratings.csv"
    segments_path.write_text("\n".join(segment_ids) + "\n", encoding="utf-8")

    template = make_rating_template(segment_ids, raters)
    rng = random.Random(42)
    typical_ratings = [5, 5, 4, 3, 2, 1]
    for row_index, (segment_id, rater) in enumerate(
        template[["road_segment_id", "rater"]].itertuples(index=False, name=None)
    ):
        base_rating = typical_ratings[segment_ids.index(segment_id)]
        variation = rng.choice([-1, 0, 0, 1])
        template.loc[row_index, "rating"] = max(1, min(5, base_rating + variation))
    template.to_csv(ratings_path, index=False)

    loaded_ratings = pd.read_csv(ratings_path)
    validated = validate_ratings(loaded_ratings)

    print(f"Saved segment IDs to {segments_path.relative_to(project_root)}")
    print(f"Saved demo ratings to {ratings_path.relative_to(project_root)}")
    print("\nValidated ratings:")
    print(validated.to_string(index=False))
    print("\nMean rating by segment:")
    print(mean_rating(validated).to_string(index=False))
    print("\nRatings by rater:")
    print(ratings_wide(validated).to_string(index=False))


if __name__ == "__main__":
    main()
