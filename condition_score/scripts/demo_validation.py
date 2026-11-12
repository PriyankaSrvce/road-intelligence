"""Demonstrate score and human-rating validation on synthetic segments."""

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from condition.ratings import mean_rating, ratings_wide
from condition.score import score_segments
from condition.validation import (
    interpret_agreement,
    plot_score_vs_rating,
    rater_agreement,
    score_vs_rating,
)


def main() -> None:
    """Generate reproducible synthetic validation data and print statistics."""
    rng = random.Random(2026)
    segment_ids = [f"S{number:02d}" for number in range(1, 41)]
    images_per_segment = pd.DataFrame(
        {"road_segment_id": segment_ids, "n_images": [4] * len(segment_ids)}
    )

    detections = []
    damage_types = ["D00", "D10", "D20", "D40"]
    for segment_id in segment_ids:
        for _ in range(rng.randint(0, 5)):
            damage_type = rng.choice(damage_types)
            area_ratio = rng.uniform(0.003, 0.12)
            detections.append(
                {
                    "road_segment_id": segment_id,
                    "damage_type": damage_type,
                    "area_ratio": area_ratio,
                    "confidence": rng.uniform(0.45, 0.98),
                }
            )
    detection_frame = pd.DataFrame(
        detections,
        columns=["road_segment_id", "damage_type", "area_ratio", "confidence"],
    )
    scores = score_segments(detection_frame, images_per_segment)

    rating_rows = []
    for score_row in scores.itertuples(index=False):
        expected_rating = 1 + score_row.score / 25
        for rater in ("Asha", "Ravi", "Meena"):
            noisy_rating = expected_rating + rng.gauss(0, 0.45)
            rating_rows.append(
                {
                    "road_segment_id": score_row.road_segment_id,
                    "rater": rater,
                    "rating": max(1, min(5, round(noisy_rating))),
                }
            )
    long_ratings = pd.DataFrame(rating_rows)
    wide_ratings = ratings_wide(long_ratings)
    average_ratings = mean_rating(long_ratings)

    agreement = rater_agreement(wide_ratings)
    score_correlation = score_vs_rating(scores, average_ratings)
    output_path = Path(__file__).resolve().parents[1] / "data" / "score_vs_rating.png"
    plot_score_vs_rating(scores, average_ratings, str(output_path))

    print(f"Rater agreement: {agreement}")
    print(f"Agreement interpretation: {interpret_agreement(agreement['value'])}")
    print(f"Score vs. rating: {score_correlation}")
    print(f"Plot saved to: {output_path.relative_to(Path(__file__).resolve().parents[1])}")


if __name__ == "__main__":
    main()
