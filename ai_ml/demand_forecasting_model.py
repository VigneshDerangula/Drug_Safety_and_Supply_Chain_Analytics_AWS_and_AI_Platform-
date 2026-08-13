"""
demand_forecasting_model.py

Supply chain use case: forecast monthly unit demand per drug/region so
manufacturing and logistics can plan shipments ahead of need.

Uses Holt-Winters exponential smoothing (statsmodels) per (drug_code, region)
series — a solid, explainable baseline for monthly business time series with
trend and seasonality, before reaching for anything heavier. Includes a
backtest harness (last N months held out) reporting MAPE/RMSE per series so
forecast quality is visible, not just asserted.

Usage:
    python demand_forecasting_model.py --mode train
    python demand_forecasting_model.py --mode score --horizon 3
"""
import argparse
import os

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "drug_sales.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "demand_forecast.csv")

MIN_MONTHS_REQUIRED = 12
HOLDOUT_MONTHS = 3


def _load_series() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["sales_month"])
    # Normalize to true calendar-month starts and aggregate in case the source
    # feed has more than one record landing in the same month (common with
    # daily ERP extracts) so each (drug_code, region, month) is unique.
    df["sales_month"] = df["sales_month"].dt.to_period("M").dt.to_timestamp()
    df = df.groupby(["drug_code", "region", "sales_month"], as_index=False)["units_sold"].sum()
    return df.sort_values("sales_month")


def _mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _rmse(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def backtest_and_forecast(series: pd.Series, horizon: int):
    """Holds out the last HOLDOUT_MONTHS to score, then refits on full history to forecast `horizon` months ahead."""
    if len(series) < MIN_MONTHS_REQUIRED:
        return None  # not enough history for a seasonal model

    train, holdout = series.iloc[: -HOLDOUT_MONTHS], series.iloc[-HOLDOUT_MONTHS:]

    model = ExponentialSmoothing(
        train, trend="add", seasonal="add", seasonal_periods=12, initialization_method="estimated"
    ).fit()
    holdout_pred = model.forecast(HOLDOUT_MONTHS)

    mape = _mape(holdout.values, holdout_pred.values)
    rmse = _rmse(holdout.values, holdout_pred.values)

    final_model = ExponentialSmoothing(
        series, trend="add", seasonal="add", seasonal_periods=12, initialization_method="estimated"
    ).fit()
    forecast = final_model.forecast(horizon)

    return {"mape": mape, "rmse": rmse, "forecast": forecast}


def run(mode: str, horizon: int = 3):
    df = _load_series()
    results = []

    for (drug_code, region), group in df.groupby(["drug_code", "region"]):
        series = group.set_index("sales_month")["units_sold"].asfreq("MS")
        series = series.interpolate()  # fill any gaps in the monthly index

        outcome = backtest_and_forecast(series, horizon)
        if outcome is None:
            print(f"[skip] {drug_code}/{region}: fewer than {MIN_MONTHS_REQUIRED} months of history")
            continue

        for month, value in outcome["forecast"].items():
            results.append(
                {
                    "drug_code": drug_code,
                    "region": region,
                    "forecast_month": month.date().isoformat(),
                    "forecast_units": max(0, round(value)),
                    "backtest_mape": round(outcome["mape"], 2),
                    "backtest_rmse": round(outcome["rmse"], 2),
                }
            )

    result_df = pd.DataFrame(results)
    print(result_df.groupby(["drug_code", "region"])[["backtest_mape", "backtest_rmse"]].first().describe())

    if mode == "score":
        result_df.to_csv(OUT_PATH, index=False)
        print(f"Forecast written to {OUT_PATH} ({len(result_df)} rows)")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "score"], default="train")
    parser.add_argument("--horizon", type=int, default=3, help="Months ahead to forecast")
    args = parser.parse_args()

    run(mode=args.mode, horizon=args.horizon)
