"""The README's generated blocks must match the published forecast.json."""

import json

import pytest

from src.config import OUTPUT_DIR
from src.export.readme import README, render

PATH = OUTPUT_DIR / "forecast.json"


@pytest.fixture(scope="module")
def doc():
    if not PATH.exists():
        pytest.skip("output/forecast.json not generated yet")
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_readme_numbers_match_forecast_json(doc):
    text = README.read_text(encoding="utf-8")
    assert text == render(text, doc), "README is out of date: run python -m src.export.readme"


def test_results_block_states_the_headline(doc):
    block = render(README.read_text(encoding="utf-8"), doc)
    total = doc["headline"]["total"]
    assert f"{total['forecast'] / 1e6:.1f} million" in block
    assert f"{doc['accuracy']['series']['total']['model_error_1_6']}% average error" in block


def test_missing_markers_fail_loudly(doc):
    with pytest.raises(ValueError, match="marker"):
        render("# README without markers\n", doc)
