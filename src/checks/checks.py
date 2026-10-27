"""Data checks. Every check runs; if any fail, DataCheckError lists them all."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.errors import DataCheckError


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _ym(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m")


def continuous_months(df: pd.DataFrame, label: str, col: str = "month") -> CheckResult:
    months = pd.DatetimeIndex(df[col])
    full = pd.date_range(months.min(), months.max(), freq="MS")
    missing = full.difference(months)
    return CheckResult(f"{label}: continuous months", missing.empty,
                       f"{len(months)} months {_ym(months.min())} to {_ym(months.max())}" if missing.empty
                       else f"missing {[_ym(m) for m in missing[:12]]}")


def no_duplicates(df: pd.DataFrame, label: str, keys: list[str]) -> CheckResult:
    dupes = df[df.duplicated(keys, keep=False)]
    return CheckResult(f"{label}: no duplicate {'/'.join(keys)}", dupes.empty,
                       "none" if dupes.empty else f"{len(dupes)} duplicate rows, e.g. {dupes.head(3).to_dict('records')}")


def no_negatives(df: pd.DataFrame, label: str, cols: list[str]) -> CheckResult:
    neg = (df[cols] < 0).sum()
    return CheckResult(f"{label}: no negative values", int(neg.sum()) == 0,
                       "none" if neg.sum() == 0 else neg[neg > 0].to_dict().__repr__())


def no_missing(df: pd.DataFrame, label: str, cols: list[str]) -> CheckResult:
    na = df[cols].isna().sum()
    return CheckResult(f"{label}: no missing values", int(na.sum()) == 0,
                       "none" if na.sum() == 0 else na[na > 0].to_dict().__repr__())


def parts_sum_to_total(df: pd.DataFrame, label: str) -> CheckResult:
    diff = df["domestic"] + df["international"] - df["total"]
    bad = df[diff != 0]
    return CheckResult(f"{label}: domestic + international = total", bad.empty,
                       f"all {len(df)} months" if bad.empty else f"{len(bad)} months differ, e.g. {[_ym(m) for m in bad['month'][:5]]}")


def latest_month_matches(df: pd.DataFrame, label: str, expected: str, source: str) -> CheckResult:
    latest = _ym(df["month"].max())
    return CheckResult(f"{label}: latest month matches {source}", latest == expected,
                       f"data {latest}, {source} {expected}")


def in_range(df: pd.DataFrame, label: str, col: str, lo: float, hi: float) -> CheckResult:
    vals = df[col].dropna()
    bad = vals[(vals < lo) | (vals > hi)]
    return CheckResult(f"{label}: {col} between {lo} and {hi}", bad.empty,
                       "ok" if bad.empty else f"{len(bad)} out of range, e.g. {bad.head(3).tolist()}")


def check_airport(df: pd.DataFrame, report_end: str, page_label: str) -> list[CheckResult]:
    label = "Airport traffic"
    cols = ["domestic", "international", "total"]
    return [
        continuous_months(df, label),
        no_duplicates(df, label, ["month"]),
        no_missing(df, label, cols),
        no_negatives(df, label, cols),
        parts_sum_to_total(df, label),
        latest_month_matches(df, label, report_end, "the file's report period"),
        latest_month_matches(df, label, page_label, "the BITRE page link"),
    ]


def check_routes(df: pd.DataFrame, label_month: str) -> list[CheckResult]:
    label = "Domestic routes"
    cols = ["passengers", "flights", "seats", "load_factor_pct"]
    return [
        no_duplicates(df, label, ["route", "month"]),
        no_negatives(df, label, cols),
        in_range(df, label, "load_factor_pct", 0, 100),
        latest_month_matches(df, label, label_month, "the file name"),
    ]


def check_intl_seats(df: pd.DataFrame, label_month: str, recent_from: str) -> list[CheckResult]:
    """Older months have gaps in the source (no flights during COVID, and some
    early and 2022 months missing), so continuity is only required for recent months."""
    label = "International seats"
    cols = ["flights_in", "flights_out", "seats_in", "seats_out"]
    recent = df[df["month"] >= recent_from]
    return [
        continuous_months(recent, f"{label} (from {recent_from[:7]})"),
        no_missing(recent, f"{label} (from {recent_from[:7]})", cols),
        no_duplicates(df, label, ["month"]),
        no_negatives(df, label, cols),
        latest_month_matches(df, label, label_month, "the file name"),
    ]


def enforce(results: list[CheckResult]) -> None:
    for r in results:
        print(f"[check] {'PASS' if r.passed else 'FAIL'}  {r.name}: {r.detail}")
    failed = [r for r in results if not r.passed]
    if failed:
        raise DataCheckError("Data checks failed:\n" + "\n".join(f"- {r.name}: {r.detail}" for r in failed))
