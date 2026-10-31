"""Rolling-origin backtest over the last 12 months of data.

For every month in the test window and every horizon h = 1..12, each method is
trained only on data up to h months before that month, then asked to forecast it.
The baseline is "same month last year", which needs no training.

Error = |forecast - actual| / actual, in %.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.model.models import BASELINE, CANDIDATES, forecast

TEST_MONTHS = 12
MAX_H = 12
PARTS = ("domestic", "international")


def months_between(a: pd.Timestamp, b: pd.Timestamp) -> int:
    return (a.year - b.year) * 12 + a.month - b.month


def test_window(data: pd.DataFrame) -> pd.DatetimeIndex:
    return data.index[-TEST_MONTHS:]


def run_backtest(data: pd.DataFrame) -> pd.DataFrame:
    """One row per (series, candidate, origin, target): forecast and actual."""
    test = test_window(data)
    origins = data.index[(data.index >= test[0] - pd.DateOffset(months=MAX_H)) & (data.index < test[-1])]
    rows = []
    for name in PARTS:
        for origin in origins:
            targets = [t for t in test if 0 < months_between(t, origin) <= MAX_H]
            h = max(months_between(t, origin) for t in targets)
            for cand in [BASELINE, *CANDIDATES]:
                fc = forecast(cand, data[name], name, origin, h)
                for t in targets:
                    k = months_between(t, origin)
                    rows.append({"series": name, "candidate": cand, "origin": origin, "target": t, "h": k,
                                 "forecast": float(fc[k - 1]), "actual": float(data.at[t, name])})
        print(f"[backtest] {name}: {len(origins)} forecast origins")
    return pd.DataFrame(rows)


def add_total(bt: pd.DataFrame, choice: dict[str, str]) -> pd.DataFrame:
    """Add total = domestic + international rows, for the chosen methods and for the baseline."""
    out = [bt]
    for label, picks in {"chosen": choice, BASELINE: {p: BASELINE for p in PARTS}}.items():
        parts = [bt[(bt.series == p) & (bt.candidate == picks[p])].set_index(["origin", "target", "h"])[["forecast", "actual"]]
                 for p in PARTS]
        tot = (parts[0] + parts[1]).reset_index()
        tot["series"], tot["candidate"] = "total", label
        out.append(tot)
    return pd.concat(out, ignore_index=True)


def with_errors(bt: pd.DataFrame) -> pd.DataFrame:
    bt = bt.copy()
    bt["pct_error"] = (bt["forecast"] - bt["actual"]) / bt["actual"] * 100
    bt["abs_pct_error"] = bt["pct_error"].abs()
    bt["bucket"] = np.where(bt["h"] <= 6, "1-6", "7-12")
    return bt


def choose(bt: pd.DataFrame) -> dict[str, str]:
    """Per series, the candidate with the lowest average error over all horizons 1–12."""
    err = with_errors(bt[bt.candidate != BASELINE])
    means = err.groupby(["series", "candidate"])["abs_pct_error"].mean()
    return {p: means.loc[p].idxmin() for p in PARTS}


def summary(bt: pd.DataFrame) -> pd.DataFrame:
    err = with_errors(bt)
    by_bucket = err.groupby(["series", "candidate", "bucket"])["abs_pct_error"].agg(["mean", "size"]).unstack("bucket")
    overall = err.groupby(["series", "candidate"])["abs_pct_error"].mean().rename(("mean", "all"))
    return by_bucket.join(overall).round(2)
