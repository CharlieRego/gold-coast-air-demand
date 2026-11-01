"""Keep the numbers in README.md in step with output/forecast.json.

The README has two generated blocks, each between marker comments. Every pipeline run
rewrites them from the forecast it just built, so the README never shows stale figures.

    python -m src.export.readme     rewrite the blocks from the current output/forecast.json
"""

from __future__ import annotations

import json
import re

import pandas as pd

from src.config import OUTPUT_DIR, ROOT

README = ROOT / "README.md"
BLOCKS = ("results", "accuracy")


def _month(ym: str) -> str:
    return pd.Timestamp(ym + "-01").strftime("%b %Y")


def _millions(n: float) -> str:
    return f"{n / 1e6:.1f} million"


def results_block(doc: dict) -> str:
    h, t = doc["headline"], doc["headline"]["total"]
    acc = doc["accuracy"]["series"]["total"]
    run = _day(doc["run_date"])
    direction = "below" if t["change_pct"] < 0 else "above"
    lines = [
        f"**Latest forecast**, built {run} from BITRE data to {_month(doc['latest_data_month'])}:",
        "",
        f"- **About {_millions(t['forecast'])} passengers** through Gold Coast Airport, "
        f"{_month(h['period_start'])} – {_month(h['period_end'])} "
        f"(likely range {t['low'] / 1e6:.1f}–{t['high'] / 1e6:.1f} million), "
        f"{abs(t['change_pct']):.0f}% {direction} the same months a year earlier.",
        f"- **{acc['model_error_1_6']}% average error** 1–6 months ahead in a 12-month backtest, "
        f"against {acc['baseline_error_1_6']}% for \"same month last year\".",
    ]
    if doc["headline"].get("caution"):
        lines.append(f"- {doc['headline']['caution']}")
    return "\n".join(lines)


def accuracy_block(doc: dict) -> str:
    a = doc["accuracy"]
    rows = [
        f"Test year {_month(a['test_start'])} – {_month(a['test_end'])}, "
        f"{a['forecasts_per_series']} forecasts per series. Average % difference between forecast and actual passengers:",
        "",
        "| | 1–6 months ahead: model | same month last year | 7–12 months ahead: model | same month last year |",
        "|---|---|---|---|---|",
    ]
    for key, label in (("total", "Total"), ("domestic", "Domestic"), ("international", "International")):
        s = a["series"][key]
        b = "**" if key == "total" else ""
        rows.append(
            f"| {b}{label}{b} | {b}{s['model_error_1_6']}%{b} | {s['baseline_error_1_6']}% "
            f"| {b}{s['model_error_7_12']}%{b} | {s['baseline_error_7_12']}% |"
        )
    return "\n".join(rows)


def _day(ymd: str) -> str:
    ts = pd.Timestamp(ymd)
    return f"{ts.day} {ts.strftime('%b %Y')}"


def render(text: str, doc: dict) -> str:
    """Return the README text with both generated blocks rewritten from doc."""
    builders = {"results": results_block, "accuracy": accuracy_block}
    for name in BLOCKS:
        pattern = re.compile(rf"(<!-- {name}:start[^>]*-->\n).*?(<!-- {name}:end -->)", re.DOTALL)
        if not pattern.search(text):
            raise ValueError(f"README.md is missing the '{name}' marker comments")
        text = pattern.sub(lambda m: m.group(1) + builders[name](doc) + "\n" + m.group(2), text)
    return text


def update(doc: dict) -> None:
    text = README.read_text(encoding="utf-8")
    README.write_text(render(text, doc), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    update(json.loads((OUTPUT_DIR / "forecast.json").read_text(encoding="utf-8")))
    print(f"[done] {README} updated from output/forecast.json")
