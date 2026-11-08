"""Small, auditable demand forecasts. No external data or future-derived features."""
from __future__ import annotations

import numpy as np
import pandas as pd

MODEL_LABELS = {
    "mean": "Constant training mean",
    "weekday": "Weekday averages",
    "weekday_trend": "Weekday + linear trend",
}


def design(dates, origin):
    dates = pd.DatetimeIndex(dates)
    # Intercept, six weekday indicators, and a trend in weeks.
    return np.column_stack([
        np.ones(len(dates)),
        *[(dates.day_of_week == day).astype(float) for day in range(1, 7)],
        (dates - pd.Timestamp(origin)).days.to_numpy() / 7.0,
    ])


def predict(train: pd.DataFrame, dates, model: str) -> np.ndarray:
    """Forecast all requested dates from a fixed origin; never use holdout lags."""
    dates = pd.DatetimeIndex(dates)
    y = train["coin_in_usd"].to_numpy(dtype=float)
    if model == "mean":
        result = np.full(len(dates), y.mean())
    elif model == "weekday":
        means = train.groupby(train.gaming_date.dt.day_of_week).coin_in_usd.mean()
        result = np.array([means.get(day, y.mean()) for day in dates.day_of_week])
    elif model == "weekday_trend":
        origin = train.gaming_date.min()
        coef = np.linalg.lstsq(design(train.gaming_date, origin), y, rcond=None)[0]
        result = design(dates, origin) @ coef
    else:
        raise ValueError(f"Unknown model: {model}")
    return np.maximum(result, 0)


def absolute_error_radius(errors, coverage=0.9):
    """Finite-sample absolute-error quantile; temporal dependence limits coverage."""
    values = np.sort(np.abs(np.asarray(errors, dtype=float)))
    if not len(values):
        raise ValueError("Calibration errors are required")
    rank = min(len(values), int(np.ceil((len(values) + 1) * coverage)))
    return float(values[rank - 1])


def run_forecast(property_daily: pd.DataFrame):
    df = property_daily.copy().sort_values("gaming_date")
    df["gaming_date"] = pd.to_datetime(df.gaming_date)
    for column in ["coin_in_usd", "theo_usd", "pos_cash_usd", "pos_cogs_usd", "machine_supplied_costs_usd", "tech_labor_cost_usd"]:
        df[column] = df[column].astype(float)
    train = df[df.gaming_date < "2025-05-01"]
    test = df[df.gaming_date >= "2025-05-01"]
    cv_rows, errors_by_model = [], {name: [] for name in MODEL_LABELS}
    # Both tuning folds end before May; neither can inspect final test outcomes.
    for origin in ["2025-03-01", "2025-04-01"]:
        start = pd.Timestamp(origin)
        earlier = train[train.gaming_date < start]
        validation = train[(train.gaming_date >= start) & (train.gaming_date < start + pd.Timedelta(days=30))]
        for model, label in MODEL_LABELS.items():
            errors = validation.coin_in_usd.to_numpy() - predict(earlier, validation.gaming_date, model)
            errors_by_model[model].extend(errors.tolist())
            cv_rows.append({"origin": origin, "model": model, "label": label,
                            "mae_usd": float(np.abs(errors).mean()), "days": len(errors)})
    scores = {model: float(np.abs(errors).mean()) for model, errors in errors_by_model.items()}
    chosen = min(scores, key=scores.get)
    radius = absolute_error_radius(errors_by_model[chosen])
    rows, metrics = [], []
    for model, label in MODEL_LABELS.items():
        forecasts = predict(train, test.gaming_date, model)
        errors = test.coin_in_usd.to_numpy() - forecasts
        metrics.append({"model": model, "label": label, "selected": model == chosen,
                        "cv_mae_usd": scores[model], "test_mae_usd": float(np.abs(errors).mean()),
                        "test_rmse_usd": float(np.sqrt(np.mean(errors ** 2))),
                        "test_bias_usd": float((-errors).mean())})
        for date, actual, estimate in zip(test.gaming_date, test.coin_in_usd, forecasts):
            rows.append({"gaming_date": date, "model": model, "label": label,
                         "actual_usd": actual, "forecast_usd": float(estimate),
                         "lower_90_usd": max(0, float(estimate) - radius) if model == chosen else np.nan,
                         "upper_90_usd": float(estimate) + radius if model == chosen else np.nan})
    history = pd.DataFrame(rows)
    selected_test = history[history.model == chosen]
    coverage = float(((selected_test.actual_usd >= selected_test.lower_90_usd) &
                      (selected_test.actual_usd <= selected_test.upper_90_usd)).mean())
    future_dates = pd.date_range("2025-07-01", periods=30)
    estimates = predict(df, future_dates, chosen)
    # Preserve the training-only calibration rule for the operational refit.
    future = pd.DataFrame({"gaming_date": future_dates, "forecast_coin_in_usd": estimates,
                           "lower_90_usd": np.maximum(0, estimates - radius),
                           "upper_90_usd": estimates + radius})
    june = df[df.gaming_date >= "2025-06-01"]
    hold = float(june.theo_usd.sum() / june.coin_in_usd.sum())
    fnb_per_day = float((june.pos_cash_usd - june.pos_cogs_usd).mean())
    costs_per_day = float((june.machine_supplied_costs_usd + june.tech_labor_cost_usd).mean())
    future["expected_theo_usd"] = future.forecast_coin_in_usd * hold
    future["assumed_fnb_margin_usd"] = fnb_per_day
    future["assumed_supplied_costs_usd"] = costs_per_day
    future["expected_contribution_usd"] = future.expected_theo_usd + fnb_per_day - costs_per_day
    # These endpoints reflect only wagering-demand uncertainty, not payout/cost uncertainty.
    future["demand_only_contribution_lower_usd"] = future.lower_90_usd * hold + fnb_per_day - costs_per_day
    future["demand_only_contribution_upper_usd"] = future.upper_90_usd * hold + fnb_per_day - costs_per_day
    summary = {"selected_model": chosen, "selected_label": MODEL_LABELS[chosen],
               "selection_rule": "Lowest pooled MAE over March and April fixed-origin 30-day folds; selected before May.",
               "train_start": "2025-01-01", "train_end": "2025-04-30",
               "test_start": "2025-05-01", "test_end": "2025-06-30", "test_days": len(test),
               "future_start": "2025-07-01", "future_end": "2025-07-30",
               "radius_90_usd": radius, "test_coverage_90": coverage,
               "assumed_theo_hold": hold, "assumed_fnb_margin_per_day_usd": fnb_per_day,
               "assumed_supplied_costs_per_day_usd": costs_per_day,
               "metrics": metrics, "cv_folds": cv_rows,
               "interval_note": "Nominal 90% daily demand error bands from pre-May validation errors. Serial dependence, changing demand and only two folds limit coverage. They are not a 90% interval for the 30-day total or realized profit.",
               "limitations": "Only six months; no annual seasonality. No later-published tourism, observed future payouts, or holdout lags are used. July is an as-of-June-30 scenario in the fictional challenge."}
    return summary, history, future
