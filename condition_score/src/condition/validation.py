"""Statistical validation for human ratings and condition scores."""

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pingouin as pg
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score


def _rating_columns(wide: pd.DataFrame) -> list[str]:
    if "road_segment_id" not in wide.columns:
        raise ValueError("wide must include a road_segment_id column")
    return [column for column in wide.columns if column != "road_segment_id"]


def rater_agreement(wide: pd.DataFrame) -> dict:
    """Calculate inter-rater agreement for a wide rating table."""
    raters = _rating_columns(wide)
    if len(raters) < 2:
        raise ValueError("At least 2 raters are required")
    if len(wide) < 5:
        raise ValueError("At least 5 segments are required")
    if wide[raters].isna().any().any():
        raise ValueError("Ratings must not contain missing values")

    if len(raters) == 2:
        value = cohen_kappa_score(
            wide[raters[0]], wide[raters[1]], weights="quadratic"
        )
        return {
            "n_raters": len(raters),
            "n_segments": len(wide),
            "method": "quadratic_weighted_cohen_kappa",
            "value": float(value),
            "details": {"weights": "quadratic"},
        }

    long = wide.melt(
        id_vars="road_segment_id",
        value_vars=raters,
        var_name="rater",
        value_name="rating",
    )
    icc = pg.intraclass_corr(
        data=long,
        targets="road_segment_id",
        raters="rater",
        ratings="rating",
    )
    icc2k = float(icc.loc[icc["Type"] == "ICC(A,k)", "ICC"].iloc[0])
    icc3k = float(icc.loc[icc["Type"] == "ICC(C,k)", "ICC"].iloc[0])
    pairwise_correlations = [
        float(spearmanr(wide[first], wide[second]).statistic)
        for index, first in enumerate(raters)
        for second in raters[index + 1 :]
    ]
    mean_pairwise = float(np.mean(pairwise_correlations))
    return {
        "n_raters": len(raters),
        "n_segments": len(wide),
        "method": "ICC2k",
        "value": icc2k,
        "details": {
            "ICC2k": icc2k,
            "ICC3k": icc3k,
            "mean_pairwise_spearman": mean_pairwise,
        },
    }


def interpret_agreement(value: float) -> str:
    """Describe agreement using the configured interpretation ranges."""
    if value < 0.40:
        return "poor"
    if value < 0.60:
        return "fair"
    if value < 0.75:
        return "good"
    return "excellent"


def _merge_scores_and_ratings(
    scores: pd.DataFrame, mean_ratings: pd.DataFrame
) -> pd.DataFrame:
    score_columns = {"road_segment_id", "score"}
    rating_columns = {"road_segment_id", "mean_rating"}
    missing_scores = score_columns.difference(scores.columns)
    missing_ratings = rating_columns.difference(mean_ratings.columns)
    if missing_scores:
        raise ValueError(f"scores is missing columns: {', '.join(sorted(missing_scores))}")
    if missing_ratings:
        raise ValueError(
            f"mean_ratings is missing columns: {', '.join(sorted(missing_ratings))}"
        )

    merged = scores[["road_segment_id", "score"]].merge(
        mean_ratings[["road_segment_id", "mean_rating"]],
        on="road_segment_id",
        how="inner",
    )
    if len(merged) < 5:
        raise ValueError("At least 5 matching segments are required")
    return merged


def score_vs_rating(scores: pd.DataFrame, mean_ratings: pd.DataFrame) -> dict:
    """Compare segment scores and mean human ratings with Spearman correlation."""
    merged = _merge_scores_and_ratings(scores, mean_ratings)
    rho, p_value = spearmanr(merged["score"], merged["mean_rating"])

    rng = np.random.default_rng(42)
    scores_array = merged["score"].to_numpy()
    ratings_array = merged["mean_rating"].to_numpy()
    bootstrap_rhos = []
    for _ in range(1000):
        indexes = rng.integers(0, len(merged), size=len(merged))
        sample_rho = spearmanr(scores_array[indexes], ratings_array[indexes]).statistic
        if not np.isnan(sample_rho):
            bootstrap_rhos.append(float(sample_rho))
    if bootstrap_rhos:
        lower, upper = np.percentile(bootstrap_rhos, [2.5, 97.5])
        confidence_interval = (float(lower), float(upper))
    else:
        confidence_interval = (float("nan"), float("nan"))

    return {
        "rho": float(rho),
        "p_value": float(p_value),
        "n": len(merged),
        "confidence_interval": confidence_interval,
    }


def plot_score_vs_rating(
    scores: pd.DataFrame, mean_ratings: pd.DataFrame, path: str
) -> None:
    """Save a score-versus-rating scatter plot using a non-interactive backend."""
    merged = _merge_scores_and_ratings(scores, mean_ratings)
    rho = spearmanr(merged["score"], merged["mean_rating"]).statistic

    figure, axis = plt.subplots()
    axis.scatter(merged["score"], merged["mean_rating"])
    axis.set_xlabel("Road condition score (0-100)")
    axis.set_ylabel("Mean human rating (1-5)")
    axis.set_title(f"Score vs. mean rating (Spearman rho = {rho:.3f})")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
