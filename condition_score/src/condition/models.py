"""Baseline and tree-based prediction models for road condition."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from condition.config import RANDOM_SEED, WEATHER_COLUMNS


def _features() -> list[str]:
    return ["score", "prev_score", "prev_rate", "days_since_prev", *WEATHER_COLUMNS]


def baseline_persistence(test: pd.DataFrame) -> np.ndarray:
    """Predict that the next score equals the current score."""
    return test["score"].to_numpy(dtype=float)


def _average_days_to_next_survey(test: pd.DataFrame) -> float:
    dates = pd.Series(pd.to_datetime(test["survey_date"].dropna().unique())).sort_values()
    intervals = dates.diff().dt.total_seconds().div(86400).dropna()
    if not intervals.empty:
        return float(intervals.mean())
    if "days_since_prev" in test.columns:
        observed_intervals = test["days_since_prev"].dropna()
        if not observed_intervals.empty:
            return float(observed_intervals.mean())
    return 0.0


def baseline_linear_trend(test: pd.DataFrame) -> np.ndarray:
    """Extrapolate the last available deterioration rate to the next survey."""
    scores = test["score"].to_numpy(dtype=float, copy=True)
    if "prev_rate" not in test.columns:
        return scores
    rates = test["prev_rate"].to_numpy(dtype=float)
    predicted = scores.copy()
    valid_rates = ~np.isnan(rates)
    predicted[valid_rates] = (
        scores[valid_rates] - rates[valid_rates] * _average_days_to_next_survey(test)
    )
    return predicted


def fit_tree_model(
    train: pd.DataFrame, kind: str = "rf"
):
    """Fit a seeded random forest or XGBoost regressor on complete rows."""
    if kind not in {"rf", "xgb"}:
        raise ValueError("kind must be 'rf' or 'xgb'")
    features = _features()
    required = [*features, "next_score"]
    missing = [column for column in required if column not in train.columns]
    if missing:
        raise ValueError(f"Training table is missing columns: {', '.join(missing)}")

    usable = train.dropna(subset=required)
    if usable.empty:
        raise ValueError("No complete training rows are available")
    x_train = usable[features]
    y_train = usable["next_score"]

    if kind == "rf":
        model = RandomForestRegressor(
            n_estimators=100, random_state=RANDOM_SEED, n_jobs=1
        )
    else:
        from xgboost import XGBRegressor

        model = XGBRegressor(
            n_estimators=100,
            random_state=RANDOM_SEED,
            n_jobs=1,
            objective="reg:squarederror",
        )
    model.fit(x_train, y_train)
    return model


def predict(model, test: pd.DataFrame) -> np.ndarray:
    """Predict next scores, using persistence for rows with missing features."""
    features = _features()
    missing = [column for column in features if column not in test.columns]
    if missing:
        raise ValueError(f"Test table is missing columns: {', '.join(missing)}")

    result = baseline_persistence(test).copy()
    complete = test[features].notna().all(axis=1).to_numpy()
    if complete.any():
        result[complete] = model.predict(test.loc[complete, features])
    return result


def evaluate(y_true, y_pred) -> dict:
    """Return MAE and RMSE over rows with a known target."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    valid = ~np.isnan(actual)
    if not valid.any():
        return {"mae": float("nan"), "rmse": float("nan")}
    mae = mean_absolute_error(actual[valid], predicted[valid])
    rmse = np.sqrt(mean_squared_error(actual[valid], predicted[valid]))
    return {"mae": float(mae), "rmse": float(rmse)}


def compare_models(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Compare persistence, linear trend, random forest, and XGBoost."""
    y_true = test["next_score"].to_numpy(dtype=float)
    predictions = {
        "persistence": baseline_persistence(test),
        "linear_trend": baseline_linear_trend(test),
        "random_forest": predict(fit_tree_model(train, "rf"), test),
        "xgboost": predict(fit_tree_model(train, "xgb"), test),
    }
    results = []
    for model_name, y_pred in predictions.items():
        metrics = evaluate(y_true, y_pred)
        results.append({"model": model_name, **metrics})

    result_frame = pd.DataFrame(results)
    persistence_mae = result_frame.loc[
        result_frame["model"] == "persistence", "mae"
    ].iloc[0]
    result_frame["beats_persistence"] = result_frame["mae"] < persistence_mae
    return result_frame
