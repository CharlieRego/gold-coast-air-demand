"""Read the real raw files when they are present (the 16 MB international file is not in git)."""

import pytest

from src.config import RAW_DIR
from src.ingest.fetch import load_manifest
from src.ingest.tidy import read_airport_traffic, read_domestic_routes, read_international_seats

manifest = load_manifest()


def raw(key):
    entry = manifest.get(key)
    path = RAW_DIR / entry["file_name"] if entry else None
    if not path or not path.exists():
        pytest.skip(f"raw file for {key} not available")
    return path, entry


def test_airport_traffic_reads_gold_coast():
    path, entry = raw("airport_traffic")
    df, report_end = read_airport_traffic(path)
    assert report_end == entry["label_month"]
    assert list(df.columns) == ["month", "domestic", "international", "total"]
    assert df["month"].min().strftime("%Y-%m") == "2009-01"


def test_domestic_routes_status_values():
    path, _ = raw("domestic_routes")
    df = read_domestic_routes(path)
    assert set(df["status"]) <= {"reported", "suppressed", "no_flights"}
    assert df.loc[df["status"] == "reported", "passengers"].notna().all()
    assert df.loc[df["status"] != "reported", "passengers"].isna().all()
    assert {"OOL-SYD", "OOL-MEL"} <= set(df["route"])


def test_international_seats_reads_gold_coast():
    path, _ = raw("international_seats")
    df = read_international_seats(path)
    assert (df["seats"].dropna() > 0).all()
