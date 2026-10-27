import pandas as pd
import pytest

from src.checks.checks import check_airport, enforce
from src.errors import DataCheckError


def airport(months=("2026-01", "2026-02", "2026-03"), dom=(100, 110, 120), intl=(10, 11, 12), total=None):
    total = total or tuple(d + i for d, i in zip(dom, intl))
    return pd.DataFrame({
        "month": pd.to_datetime([m + "-01" for m in months]),
        "domestic": dom, "international": intl, "total": total,
    })


def failures(df, report_end="2026-03", page_label="2026-03"):
    return [r.name for r in check_airport(df, report_end, page_label) if not r.passed]


def test_clean_series_passes():
    assert failures(airport()) == []


def test_gap_in_months_fails():
    assert any("continuous" in f for f in failures(airport(months=("2026-01", "2026-03", "2026-04")), "2026-04", "2026-04"))


def test_duplicate_month_fails():
    assert any("duplicate" in f for f in failures(airport(months=("2026-01", "2026-02", "2026-02")), "2026-02", "2026-02"))


def test_negative_value_fails():
    assert any("negative" in f for f in failures(airport(dom=(100, -5, 120))))


def test_parts_not_summing_to_total_fails():
    assert any("= total" in f for f in failures(airport(total=(110, 121, 999))))


def test_latest_month_mismatch_fails():
    fails = failures(airport(), report_end="2026-04", page_label="2026-05")
    assert sum("latest month" in f for f in fails) == 2


def test_enforce_raises_with_every_failure_listed():
    results = check_airport(airport(dom=(100, -5, 120), total=(110, 121, 999)), "2026-03", "2026-03")
    with pytest.raises(DataCheckError) as e:
        enforce(results)
    assert "negative" in str(e.value) and "= total" in str(e.value)
