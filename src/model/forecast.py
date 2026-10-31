"""Final forecast with likely ranges built from backtest errors.

The likely range for a month h months ahead is the forecast ± X%, where X% is the
error that 8 in 10 of the same method's backtest forecasts at a similar distance
ahead (1–3, 4–6, 7–9, 10–12 months) stayed within. In plain words: "how far off
this method has recently been, this far ahead". The range is symmetric because
the backtest errors can all lean one way (e.g. domestic ran above forecast in
2025–26), and a range that doesn't contain the forecast would confuse readers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.model.backtest import PARTS, months_between, with_errors
from src.model.models import forecast

RANGE_COVER = 80  # % of backtest errors the range half-width covers
BUCKETS = [(1, 3), (4, 6), (7, 9), (10, 12)]
HEADLINE_MONTHS = 6


def bucket_of(h: int) -> tuple[int, int]:
    return next(b for b in BUCKETS if b[0] <= h <= b[1])


def range_widths(bt: pd.DataFrame, series: str, candidate: str) -> dict[tuple[int, int], float]:
    """Half-width of the likely range (as a fraction) for each horizon bucket."""
    err = with_errors(bt[(bt.series == series) & (bt.candidate == candidate)])
    return {(lo_h, hi_h): float(np.percentile(err.loc[err.h.between(lo_h, hi_h), "abs_pct_error"], RANGE_COVER)) / 100
            for lo_h, hi_h in BUCKETS}


def horizon(latest: pd.Timestamp, today: pd.Timestamp) -> tuple[int, pd.Timestamp]:
    """Forecast up to 5 months past the current month, so the next six months are covered. Max 12."""
    end = (today.to_period("M") + HEADLINE_MONTHS - 1).to_timestamp()
    h = months_between(end, latest)
    return max(HEADLINE_MONTHS, min(h, 12)), end


def build(data: pd.DataFrame, choice: dict[str, str], bt: pd.DataFrame, today: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    latest = data.index[-1]
    h, _ = horizon(latest, today)
    months = pd.date_range(latest + pd.DateOffset(months=1), periods=h, freq="MS")
    fc = pd.DataFrame({"month": months, "h": range(1, h + 1)})
    for name in PARTS:
        point = forecast(choice[name], data[name], name, latest, h)
        fc[name] = point
    fc["total"] = fc["domestic"] + fc["international"]
    widths = {}
    for name in ["domestic", "international", "total"]:
        w = range_widths(bt, name, "chosen" if name == "total" else choice[name])
        widths[name] = {f"{a}-{b}": round(v * 100, 1) for (a, b), v in w.items()}
        fc[f"{name}_low"] = [p * (1 - w[bucket_of(k)]) for p, k in zip(fc[name], fc.h)]
        fc[f"{name}_high"] = [p * (1 + w[bucket_of(k)]) for p, k in zip(fc[name], fc.h)]
    return fc, {"horizon": h, "range_pct": widths}


def headline(data: pd.DataFrame, fc: pd.DataFrame, today: pd.Timestamp) -> dict:
    """Totals for the next six calendar months from today (or the last six forecast months)."""
    start = today.to_period("M").to_timestamp()
    period = fc[fc.month >= start].head(HEADLINE_MONTHS)
    if len(period) < HEADLINE_MONTHS:
        period = fc.tail(HEADLINE_MONTHS)
    prev = [m - pd.DateOffset(years=1) for m in period.month]
    prev_actual = data.loc[prev]
    out = {
        "period_start": period.month.iloc[0].strftime("%Y-%m"),
        "period_end": period.month.iloc[-1].strftime("%Y-%m"),
        "months_ahead_of_data": [int(period.h.iloc[0]), int(period.h.iloc[-1])],
        "previous_period_start": prev[0].strftime("%Y-%m"),
        "previous_period_end": prev[-1].strftime("%Y-%m"),
    }
    for name in ["total", "domestic", "international"]:
        f, a = period[name].sum(), prev_actual[name].sum()
        out[name] = {
            "forecast": int(round(f)),
            # Monthly ranges added together: assumes a month that runs high is
            # followed by others that also run high, so this is a wide, cautious range
            "low": int(round(period[f"{name}_low"].sum())),
            "high": int(round(period[f"{name}_high"].sum())),
            "previous_actual": int(a),
            "change_pct": round((f / a - 1) * 100, 1),
        }
    return out
