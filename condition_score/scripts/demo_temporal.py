"""Demonstrate temporal road-condition prediction and MLflow tracking."""

import random
import os
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import mlflow
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from condition.models import compare_models
from condition.temporal import build_temporal_table, time_split


def main() -> None:
    """Create synthetic surveys, compare models, and log results locally."""
    rng = random.Random(42)
    survey_dates = pd.date_range("2025-01-01", periods=6, freq="3W")
    weather = pd.DataFrame(
        {
            "survey_date": survey_dates,
            "rainfall_mm": [rng.uniform(0, 40) for _ in survey_dates],
            "temp_c": [rng.uniform(12, 32) for _ in survey_dates],
        }
    )

    scores = []
    for segment_index in range(30):
        current_score = rng.uniform(75, 98)
        decline_per_survey = rng.uniform(1.0, 5.0)
        for date_index, survey_date in enumerate(survey_dates):
            if date_index:
                rainy_drop = (
                    weather.loc[date_index - 1, "rainfall_mm"] / 30
                    if weather.loc[date_index - 1, "rainfall_mm"] > 20
                    else 0
                )
                current_score -= decline_per_survey + rainy_drop + rng.uniform(-1, 1)
            scores.append(
                {
                    "road_segment_id": f"S{segment_index + 1:02d}",
                    "survey_date": survey_date,
                    "score": max(0.0, current_score),
                }
            )
    score_frame = pd.DataFrame(scores)
    table = build_temporal_table(score_frame, weather)
    train, test = time_split(table)
    results = compare_models(train, test)
    print(results.to_string(index=False))

    tracking_uri = (Path.cwd() / "mlruns").resolve().as_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("condition_prediction_demo")
    with mlflow.start_run():
        mlflow.log_params(
            {
                "segments": 30,
                "survey_dates": len(survey_dates),
                "train_fraction": 0.7,
                "random_seed": 42,
            }
        )
        for row in results.itertuples(index=False):
            mlflow.log_metrics(
                {
                    f"{row.model}_mae": row.mae,
                    f"{row.model}_rmse": row.rmse,
                    f"{row.model}_beats_persistence": float(row.beats_persistence),
                }
            )
    print(f"\nMLflow experiment: condition_prediction_demo ({tracking_uri})")


if __name__ == "__main__":
    main()
