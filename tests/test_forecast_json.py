"""The published forecast.json must match its schema and its own internal logic."""

import json

import pandas as pd
import pytest

from src.config import OUTPUT_DIR
from src.export.export import validate
from src.ingest.fetch import load_manifest

PATH = OUTPUT_DIR / "forecast.json"


@pytest.fixture(scope="module")
def doc():
    if not PATH.exists():
        pytest.skip("output/forecast.json not generated yet")
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_matches_schema_and_invariants(doc):
    validate(doc)  # JSON schema + ranges in order + continuous months


def test_forecast_starts_the_month_after_the_latest_data(doc):
    latest = pd.Period(doc["latest_data_month"], "M")
    assert doc["history"][-1]["month"] == doc["latest_data_month"]
    assert doc["forecast"][0]["month"] == str(latest + 1)
    assert [r["months_ahead"] for r in doc["forecast"]] == list(range(1, len(doc["forecast"]) + 1))


def test_total_is_domestic_plus_international(doc):
    for r in doc["history"]:
        assert r["domestic"] + r["international"] == r["total"]
    for r in doc["forecast"]:
        assert abs(r["domestic"]["forecast"] + r["international"]["forecast"] - r["total"]["forecast"]) <= 1


def test_headline_adds_up(doc):
    h = doc["headline"]
    months = [r for r in doc["forecast"] if h["period_start"] <= r["month"] <= h["period_end"]]
    assert len(months) == 6
    assert abs(sum(r["total"]["forecast"] for r in months) - h["total"]["forecast"]) <= 6
    prev = [r for r in doc["history"] if h["previous_period_start"] <= r["month"] <= h["previous_period_end"]]
    assert sum(r["total"] for r in prev) == h["total"]["previous_actual"]


def test_sources_match_the_manifest(doc):
    manifest = load_manifest()
    for s in doc["sources"]:
        assert s["sha256"] == manifest[s["key"]]["sha256"]
        assert s["covers_to"] == manifest[s["key"]]["label_month"]
    assert doc["latest_data_month"] == manifest["airport_traffic"]["label_month"]


def test_scenario_defaults_are_plausible(doc):
    for side in ["domestic", "international"]:
        sc = doc["scenario"][side]
        assert 0.5 < sc["load_factor"] <= 1
        assert 50 <= sc["seats_per_flight"] <= 500
