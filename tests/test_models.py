import numpy as np
import pandas as pd
import pytest

from src.model import models
from src.model.backtest import add_total, choose
from src.model.forecast import horizon


def monthly(start="2009-01", end="2026-06", value=100.0):
    idx = pd.date_range(start, end, freq="MS")
    return pd.Series(value + np.arange(len(idx)), index=idx)


def test_long_window_drops_covid_and_keeps_months_aligned():
    s = monthly()
    y = models.training_values(s, "long", "domestic", s.index[-1])
    kept = pd.concat([s.loc["2009-01":"2020-02"], s.loc["2022-03":]])
    assert np.array_equal(y, kept.to_numpy())
    assert (len(s) - len(y)) % 12 == 0


def test_window_cut_that_breaks_the_seasons_is_rejected(monkeypatch):
    monkeypatch.setitem(models.WINDOWS, "bad", {"domestic": [("2009-01", "2020-02"), ("2022-07", None)]})
    with pytest.raises(AssertionError):
        models.training_values(monthly(), "bad", "domestic", pd.Timestamp("2026-06-01"))


def test_seasonal_naive_repeats_last_year():
    y = np.arange(24, dtype=float)
    assert models.seasonal_naive(y, 3).tolist() == [12.0, 13.0, 14.0]


def test_horizon_covers_the_next_six_months():
    h, end = horizon(pd.Timestamp("2026-06-01"), pd.Timestamp("2026-11-01"))
    assert (h, end) == (10, pd.Timestamp("2027-04-01"))
    assert horizon(pd.Timestamp("2026-06-01"), pd.Timestamp("2026-07-15"))[0] == 6   # at least 6
    assert horizon(pd.Timestamp("2025-01-01"), pd.Timestamp("2026-11-01"))[0] == 12  # at most 12


def test_choose_picks_lowest_error_and_total_is_sum():
    rows = []
    for series in ["domestic", "international"]:
        for cand, err in [("same_month_last_year", 0.2), ("ets_recent", 0.05), ("ets_long", 0.1)]:
            rows.append({"series": series, "candidate": cand, "origin": pd.Timestamp("2025-06-01"),
                         "target": pd.Timestamp("2025-07-01"), "h": 1, "forecast": 100 * (1 + err), "actual": 100.0})
    bt = pd.DataFrame(rows)
    choice = choose(bt)
    assert choice == {"domestic": "ets_recent", "international": "ets_recent"}
    total = add_total(bt, choice)
    chosen = total[(total.series == "total") & (total.candidate == "chosen")].iloc[0]
    assert chosen.forecast == pytest.approx(210) and chosen.actual == 200
