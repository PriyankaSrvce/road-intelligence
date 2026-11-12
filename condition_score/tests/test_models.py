import numpy as np
import pandas as pd
import pytest

from condition.config import RANDOM_SEED, WEATHER_COLUMNS
from condition.models import (
    baseline_linear_trend,
    baseline_persistence,
    compare_models,
    evaluate,
    fit_tree_model,
    predict,
)


def model_table(n=30):
    dates = pd.date_range("2025-01-01", periods=n, freq="7D")
    scores = np.linspace(95, 40, n)
    return pd.DataFrame(
        {
            "survey_date": dates,
            "score": scores,
            "prev_score": scores + 2,
            "prev_rate": np.full(n, 2 / 7),
            "days_since_prev": np.full(n, 7.0),
            "rainfall_mm": np.linspace(0, 20, n),
            "temp_c": np.linspace(15, 25, n),
            "next_score": np.r_[scores[1:], np.nan],
        }
    )


def test_persistence_returns_current_score():
    test = pd.DataFrame({"score": [90.0, 75.0]})

    np.testing.assert_array_equal(baseline_persistence(test), [90.0, 75.0])


def test_linear_trend_uses_rate_and_falls_back_to_persistence():
    test = pd.DataFrame(
        {
            "score": [90.0, 75.0],
            "prev_rate": [1.0, np.nan],
            "days_since_prev": [7.0, 7.0],
            "survey_date": pd.to_datetime(["2025-01-01", "2025-01-08"]),
        }
    )

    np.testing.assert_allclose(baseline_linear_trend(test), [83.0, 75.0])


@pytest.mark.parametrize("kind", ["rf", "xgb"])
def test_tree_models_fit_predict_shape_and_reproducibility(kind):
    table = model_table()
    train = table.iloc[:20]
    test = table.iloc[20:25].copy()

    model1 = fit_tree_model(train, kind=kind)
    model2 = fit_tree_model(train, kind=kind)
    predictions1 = predict(model1, test)
    predictions2 = predict(model2, test)

    assert predictions1.shape == (5,)
    np.testing.assert_allclose(predictions1, predictions2)
    assert model1.get_params()["random_state"] == RANDOM_SEED


def test_prediction_falls_back_to_persistence_on_missing_features():
    train = model_table()
    model = fit_tree_model(train.iloc[:20], "rf")
    test = model_table().iloc[20:22].copy()
    test.loc[test.index[0], "prev_rate"] = np.nan

    predicted = predict(model, test)

    assert predicted[0] == test.iloc[0]["score"]
    assert predicted.shape == (2,)


def test_linear_trend_beats_persistence_on_steady_decline():
    table = model_table(20)
    test = table.iloc[5:15].copy()
    test["next_score"] = test["score"] - 2
    test["prev_rate"] = 2 / 7

    persistence_metrics = evaluate(
        test["next_score"], baseline_persistence(test)
    )
    trend_metrics = evaluate(test["next_score"], baseline_linear_trend(test))

    assert trend_metrics["mae"] < persistence_metrics["mae"]


def test_evaluate_ignores_missing_targets():
    metrics = evaluate([10.0, np.nan, 20.0], [8.0, 1000.0, 18.0])

    assert metrics["mae"] == pytest.approx(2.0)
    assert metrics["rmse"] == pytest.approx(2.0)


def test_compare_models_returns_requested_models_and_flag():
    table = model_table()
    results = compare_models(table.iloc[:20], table.iloc[20:25])

    assert results["model"].tolist() == [
        "persistence",
        "linear_trend",
        "random_forest",
        "xgboost",
    ]
    assert {"mae", "rmse", "beats_persistence"}.issubset(results.columns)
