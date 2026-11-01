"""Run the pipeline: fetch → tidy → check → backtest → forecast → export.

    python -m src.pipeline            download the latest BITRE files, then process
    python -m src.pipeline --offline  reuse the files already in data/raw
    --today YYYY-MM-DD                 pretend the run happens on this date (sets the headline period)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.checks.checks import check_airport, check_intl_seats, check_routes, enforce
from src.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from src.export.export import build_json, write
from src.export.readme import update as update_readme
from src.model.backtest import add_total, choose, run_backtest
from src.model.forecast import build, headline
from src.ingest.fetch import fetch_all, load_manifest, verify_local
from src.ingest.tidy import read_airport_traffic, read_domestic_routes, read_international_seats

INTL_CONTINUOUS_FROM = "2023-01-01"


def run(offline: bool = False, today: str | None = None) -> dict:
    today_ts = pd.Timestamp(today) if today else pd.Timestamp(datetime.now(ZoneInfo("Australia/Brisbane")).date())
    manifest = load_manifest() if offline else fetch_all()
    if offline:
        verify_local(manifest)

    airport, report_end = read_airport_traffic(RAW_DIR / manifest["airport_traffic"]["file_name"])
    routes = read_domestic_routes(RAW_DIR / manifest["domestic_routes"]["file_name"])
    intl = read_international_seats(RAW_DIR / manifest["international_seats"]["file_name"])

    results = (
        check_airport(airport, report_end, manifest["airport_traffic"]["label_month"])
        + check_routes(routes, manifest["domestic_routes"]["label_month"])
        + check_intl_seats(intl, manifest["international_seats"]["label_month"], INTL_CONTINUOUS_FROM)
    )
    enforce(results)  # raises before anything is written if a check fails

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fmt = {"date_format": "%Y-%m-%d", "index": False, "lineterminator": "\n"}
    airport.to_csv(PROCESSED_DIR / "gold_coast_passengers.csv", **fmt)
    routes.to_csv(PROCESSED_DIR / "gold_coast_domestic_routes.csv", **fmt)
    intl.to_csv(PROCESSED_DIR / "gold_coast_international_seats.csv", **fmt)
    (PROCESSED_DIR / "checks.json").write_text(
        json.dumps([r.__dict__ for r in results], indent=2) + "\n", encoding="utf-8"
    )
    print(f"[done] processed tables written to {PROCESSED_DIR}")

    data = airport.set_index("month")
    bt = run_backtest(data)
    choice = choose(bt)
    bt = add_total(bt, choice)
    fc, fc_meta = build(data, choice, bt, today_ts)
    head = headline(data, fc, today_ts)
    doc = build_json(data=data, fc=fc, fc_meta=fc_meta, head=head, bt=bt, choice=choice, manifest=manifest,
                     routes=routes, intl_seats=intl, today=today_ts)
    write(doc)  # validates against the schema first
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bt.to_csv(OUTPUT_DIR / "backtest.csv", index=False, date_format="%Y-%m", lineterminator="\n", float_format="%.1f")
    update_readme(doc)  # the README's results and accuracy blocks
    print(f"[done] {OUTPUT_DIR / 'forecast.json'}: {doc['headline']['sentence']}")
    return {"doc": doc, "backtest": bt}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use files already in data/raw")
    ap.add_argument("--today", help="YYYY-MM-DD; defaults to today in Brisbane")
    args = ap.parse_args()
    run(offline=args.offline, today=args.today)
