"""Assemble output/forecast.json and validate it against schema/forecast.schema.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import jsonschema
import pandas as pd

from src.config import BITRE_ATTRIBUTION, OUTPUT_DIR, ROOT
from src.model.backtest import PARTS, test_window, with_errors
from src.model.forecast import RANGE_COVER
from src.model.models import BASELINE, CANDIDATES, describe

SCHEMA_VERSION = "1.0.0"
SCHEMA_PATH = ROOT / "schema" / "forecast.schema.json"
HISTORY_FROM = "2019-01"
WEEKS_PER_MONTH = round(365.25 / 12 / 7, 4)


def _ym(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m")


def _month_name(ym: str) -> str:
    return pd.Timestamp(ym + "-01").strftime("%B %Y")


def scenario_defaults(routes: pd.DataFrame, intl_seats: pd.DataFrame, passengers: pd.DataFrame) -> dict:
    """Load factor and seats per flight over the latest 12 months each source covers."""
    r = routes[routes.status == "reported"]
    r_end = r.month.max()
    r12 = r[r.month > r_end - pd.DateOffset(months=12)]
    # International: passengers (airport file) over seats (seats file), for the months both cover
    i_end = min(intl_seats.month.max(), passengers.index.max())
    months = pd.date_range(end=i_end, periods=12, freq="MS")
    seats = intl_seats.set_index("month").loc[months]
    pax = passengers.loc[months, "international"]
    return {
        "formula": "extra monthly passengers = weekly return flights × 2 × seats per flight × load factor × weeks per month",
        "weeks_per_month": WEEKS_PER_MONTH,
        "domestic": {
            "load_factor": round(r12.passengers.sum() / r12.seats.sum(), 3),
            "seats_per_flight": int(round(r12.seats.sum() / r12.flights.sum())),
            "period_start": _ym(r12.month.min()), "period_end": _ym(r_end),
            "basis": f"Gold Coast domestic routes reported by BITRE ({', '.join(sorted(r12.route.unique()))}): passengers ÷ seats and seats ÷ flights",
            "source": "domestic_routes",
        },
        "international": {
            "load_factor": round(pax.sum() / seats.seats.sum(), 3),
            "seats_per_flight": int(round(seats.seats.sum() / (seats.flights_in + seats.flights_out).sum())),
            "period_start": _ym(months[0]), "period_end": _ym(months[-1]),
            "basis": "Gold Coast international passengers (airport traffic) ÷ international seats operated; seats ÷ flights",
            "source": "international_seats",
        },
    }


def early_indicators(routes: pd.DataFrame, intl_seats: pd.DataFrame, latest: pd.Timestamp) -> list[dict]:
    """Months after the latest airport month that the route and seat files already cover,
    compared with the same month a year earlier (same routes only)."""
    out = []
    r = routes[routes.status == "reported"]
    for m in sorted(r.month[r.month > latest].unique()):
        prev = m - pd.DateOffset(years=1)
        both = r[r.month.isin([m, prev])].pivot_table(index="route", columns="month", values="passengers").dropna()
        if both.empty:
            continue
        out.append({"month": _ym(m), "measure": "passengers on Gold Coast's reported domestic routes",
                    "routes": sorted(both.index), "value": int(both[m].sum()), "previous_year": int(both[prev].sum()),
                    "change_pct": round((both[m].sum() / both[prev].sum() - 1) * 100, 1), "source": "domestic_routes"})
    s = intl_seats.set_index("month")
    for m in s.index[s.index > latest]:
        prev = m - pd.DateOffset(years=1)
        if prev in s.index and pd.notna(s.at[m, "seats"]) and pd.notna(s.at[prev, "seats"]):
            out.append({"month": _ym(m), "measure": "seats on international flights to and from Gold Coast",
                        "routes": [], "value": int(s.at[m, "seats"]), "previous_year": int(s.at[prev, "seats"]),
                        "change_pct": round((s.at[m, "seats"] / s.at[prev, "seats"] - 1) * 100, 1),
                        "source": "international_seats"})
    return out


def caution_sentence(acc: dict) -> str | None:
    t = acc["series"]["total"]
    if t["model_below_actual_pct"] >= 65 and t["model_mean_error"] < 0:
        share = round(t["model_below_actual_pct"] / 10)
        return (f"Over the last 12 months this method came in below the real number in about {share} of every 10 test "
                f"forecasts, by {abs(t['model_mean_error']):.0f}% on average, so treat it as a cautious estimate.")
    if t["model_below_actual_pct"] <= 35 and t["model_mean_error"] > 0:
        share = round((100 - t["model_below_actual_pct"]) / 10)
        return (f"Over the last 12 months this method came in above the real number in about {share} of every 10 test "
                f"forecasts, by {t['model_mean_error']:.0f}% on average, so treat it as an optimistic estimate.")
    return None


def headline_sentence(h: dict) -> str:
    t, i = h["total"], h["international"]
    start, end = _month_name(h["period_start"]), _month_name(h["period_end"])

    def change(pct: float, noun: str) -> str:
        if abs(pct) < 1:
            return f"about the same as {noun}"
        return f"{abs(pct):.0f}% {'more' if pct > 0 else 'fewer'} than {noun}"

    return (
        f"Gold Coast Airport is on track for about {t['forecast'] / 1e6:.1f} million passenger arrivals and departures "
        f"from {start} to {end}, {change(t['change_pct'], 'the same months a year earlier')}, "
        f"with international passengers {'up' if i['change_pct'] >= 0 else 'down'} about {abs(i['change_pct']):.0f}%."
    )


def accuracy(bt: pd.DataFrame, data: pd.DataFrame, choice: dict) -> dict:
    err = with_errors(bt)
    test = test_window(data)

    def mape(series, cand, bucket=None):
        e = err[(err.series == series) & (err.candidate == cand)]
        if bucket:
            e = e[e.bucket == bucket]
        return round(float(e.abs_pct_error.mean()), 1)

    out = {
        "test_start": _ym(test[0]), "test_end": _ym(test[-1]),
        "method": "rolling origin: each of the last 12 months was forecast 1 to 12 months ahead, using only data available at the time",
        "forecasts_per_series": int(len(err[(err.series == "total") & (err.candidate == "chosen")])),
        "error_measure": "average % difference between forecast and actual",
        "series": {},
        "candidates": [],
        "selection_note": "The method for each series was chosen as the one with the lowest average error over these same 12 months, so real-world accuracy may be slightly worse.",
    }
    for s in ["total", *PARTS]:
        model = "chosen" if s == "total" else choice[s]
        out["series"][s] = {
            "model_error_1_6": mape(s, model, "1-6"), "model_error_7_12": mape(s, model, "7-12"),
            "baseline_error_1_6": mape(s, BASELINE, "1-6"), "baseline_error_7_12": mape(s, BASELINE, "7-12"),
        }
        e = err[(err.series == s) & (err.candidate == model)]
        out["series"][s]["model_mean_error"] = round(float(e.pct_error.mean()), 1)
        out["series"][s]["model_below_actual_pct"] = round(float((e.pct_error < 0).mean() * 100), 0)
        out["series"][s]["model_beats_baseline"] = {
            k: out["series"][s][f"model_error_{k}"] < out["series"][s][f"baseline_error_{k}"] for k in ["1_6", "7_12"]
        }
    for s in PARTS:
        for c in [BASELINE, *CANDIDATES]:
            out["candidates"].append({"series": s, "candidate": c, "description": describe(c),
                                      "error_1_6": mape(s, c, "1-6"), "error_7_12": mape(s, c, "7-12"),
                                      "error_all": mape(s, c), "chosen": c == choice[s]})
    return out


def build_json(*, data, fc, fc_meta, head, bt, choice, manifest, routes, intl_seats, today) -> dict:
    hist = data.loc[HISTORY_FROM:]
    acc = accuracy(bt, data, choice)
    point = lambda row, n: {"forecast": int(round(row[n])), "low": int(round(row[f"{n}_low"])), "high": int(round(row[f"{n}_high"]))}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_date": today.strftime("%Y-%m-%d"),
        "unit": "passenger movements (arrivals plus departures), scheduled flights only",
        "latest_data_month": _ym(data.index[-1]),
        "headline": {**head, "sentence": headline_sentence(head), "caution": caution_sentence(acc)},
        "early_indicators": early_indicators(routes, intl_seats, data.index[-1]),
        "model": {
            "name": f"ETS/SARIMA selection by backtest; chosen: {', '.join(f'{k}: {v}' for k, v in choice.items())}",
            "per_series": {s: {"candidate": c, "description": describe(c)} for s, c in choice.items()},
            "total": "domestic forecast + international forecast",
            "likely_range": f"forecast ± the % error that {RANGE_COVER} in 100 backtest forecasts at a similar distance ahead stayed within",
            "likely_range_pct": fc_meta["range_pct"],
            "baseline": "same month last year",
        },
        "history": [{"month": _ym(m), **{n: int(r[n]) for n in ["domestic", "international", "total"]}} for m, r in hist.iterrows()],
        "forecast": [{"month": _ym(r["month"]), "months_ahead": int(r["h"]), **{n: point(r, n) for n in ["domestic", "international", "total"]}}
                     for r in fc.to_dict("records")],
        "accuracy": acc,
        "scenario": scenario_defaults(routes, intl_seats, data),
        "sources": [
            {"key": k, "title": v["title"], "page_url": v["page_url"], "file_url": v["file_url"],
             "covers_to": v["label_month"], "retrieved_at": v["retrieved_at"], "sha256": v["sha256"]}
            for k, v in manifest.items()
        ],
        "attribution": BITRE_ATTRIBUTION,
        "repository": "https://github.com/CharlieRego/gold-coast-air-demand",
    }


def validate(doc: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    for row in doc["forecast"]:
        for n in ["domestic", "international", "total"]:
            v = row[n]
            assert 0 < v["low"] <= v["forecast"] <= v["high"], f"{row['month']} {n}: range out of order {v}"
    months = [r["month"] for r in doc["history"]] + [r["month"] for r in doc["forecast"]]
    expected = [p.strftime("%Y-%m") for p in pd.period_range(months[0], months[-1], freq="M")]
    assert months == expected, "history + forecast months are not continuous"


def write(doc: dict) -> None:
    validate(doc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "forecast.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
