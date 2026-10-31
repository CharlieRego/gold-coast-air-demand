"""Forecasting models and training windows.

Models work on log passenger numbers, so seasonal swings scale with the level and
forecasts can't go negative. Each returns point forecasts only; likely ranges come
from the backtest errors (see src/model/ranges.py).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.statespace.sarimax import SARIMAX

SEASON = 12

# COVID handling. "recent": train only on months after recovery.
# "long": keep the pre-COVID history and cut out the COVID months. The cut is a whole
# number of years so the months still line up for the seasonal pattern.
WINDOWS = {
    "recent": {"domestic": [("2022-07", None)], "international": [("2022-07", None)]},
    "long": {
        "domestic": [("2009-01", "2020-02"), ("2022-03", None)],       # drops Mar 2020 – Feb 2022 (24 months)
        "international": [("2009-01", "2020-02"), ("2023-03", None)],  # drops Mar 2020 – Feb 2023 (36 months)
    },
}

MODELS = ("ets", "sarima")
CANDIDATES = [f"{m}_{w}" for m in MODELS for w in WINDOWS]
BASELINE = "same_month_last_year"

DESCRIPTIONS = {
    "ets": "exponential smoothing (ETS) with a damped trend and a monthly seasonal pattern, on log passengers",
    "sarima": "seasonal ARIMA (0,1,1)(0,1,1)12, the 'airline model', on log passengers",
    "recent": "trained on July 2022 onward (after COVID recovery)",
    "long": "trained on 2009 onward with the COVID months removed",
}


def training_values(series: pd.Series, window: str, name: str, until: pd.Timestamp) -> np.ndarray:
    """Values used for training, in time order, with the COVID gap removed. Ends at `until`."""
    segments = WINDOWS[window][name]
    for (_, end), (next_start, _) in zip(segments, segments[1:]):
        gap = (pd.Period(next_start, "M") - pd.Period(end, "M")).n - 1
        assert gap % SEASON == 0, f"{window}/{name}: a {gap}-month cut would shift the seasons"
    parts = [(series.loc[s:e] if e else series.loc[s:]).loc[:until] for s, e in segments]
    return pd.concat(parts).to_numpy(dtype=float)


def forecast(candidate: str, series: pd.Series, name: str, until: pd.Timestamp, h: int) -> np.ndarray:
    """Point forecasts for the h months after `until`."""
    if candidate == BASELINE:
        return seasonal_naive(series.loc[:until].to_numpy(dtype=float), h)
    model, window = candidate.split("_")
    logy = np.log(training_values(series, window, name, until))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # convergence chatter from statsmodels
        if model == "ets":
            res = ETSModel(logy, error="add", trend="add", damped_trend=True,
                           seasonal="add", seasonal_periods=SEASON).fit(disp=False)
        else:
            res = SARIMAX(logy, order=(0, 1, 1), seasonal_order=(0, 1, 1, SEASON)).fit(disp=False)
        return np.exp(np.asarray(res.forecast(h)))


def seasonal_naive(y: np.ndarray, h: int) -> np.ndarray:
    """Same month last year (valid for h <= 12)."""
    assert h <= SEASON
    return y[-SEASON:][:h].astype(float)


def describe(candidate: str) -> str:
    if candidate == BASELINE:
        return "same month last year"
    model, window = candidate.split("_")
    return f"{DESCRIPTIONS[model]}, {DESCRIPTIONS[window]}"
