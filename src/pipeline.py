"""Run the pipeline: fetch → tidy → check → (model → export, added later).

    python -m src.pipeline            download the latest BITRE files, then process
    python -m src.pipeline --offline  reuse the files already in data/raw
"""

from __future__ import annotations

import argparse
import json

from src.checks.checks import check_airport, check_intl_seats, check_routes, enforce
from src.config import PROCESSED_DIR, RAW_DIR
from src.ingest.fetch import fetch_all, load_manifest, verify_local
from src.ingest.tidy import read_airport_traffic, read_domestic_routes, read_international_seats

INTL_CONTINUOUS_FROM = "2023-01-01"


def run(offline: bool = False) -> dict:
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
    return {"airport": airport, "routes": routes, "intl": intl, "manifest": manifest}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use files already in data/raw")
    run(offline=ap.parse_args().offline)
