"""Turn the raw BITRE workbooks into small, tidy Gold Coast tables.

Each reader finds its header row by content and checks the header cells it relies
on, so a layout change raises SourceChangedError instead of silently misreading.
"""

from __future__ import annotations

import re

import pandas as pd

from src.config import AIRPORT_CODE, AIRPORT_NAME, AIRPORT_NAME_INTL
from src.errors import SourceChangedError
from src.ingest.fetch import MONTHS


def _find_row(raw: pd.DataFrame, col: int, value: str, max_rows: int = 40) -> int:
    for i in range(min(max_rows, len(raw))):
        cell = raw.iat[i, col]
        if isinstance(cell, str) and cell.strip() == value:
            return i
    raise SourceChangedError(f"Header '{value}' not found in column {col}")


def _expect(raw: pd.DataFrame, row: int, expected: dict[int, str], what: str) -> None:
    for col, text in expected.items():
        cell = raw.iat[row, col]
        if not (isinstance(cell, str) and cell.strip() == text):
            raise SourceChangedError(f"{what}: expected '{text}' in row {row + 1}, column {col + 1}, found {cell!r}")


def _month(year, month) -> pd.Series:
    return pd.to_datetime(pd.DataFrame({"year": year, "month": month, "day": 1}))


# ── Airport traffic ─────────────────────────────────────────────────────


def read_airport_traffic(path) -> tuple[pd.DataFrame, str]:
    """Gold Coast monthly passenger movements. Returns (table, report_period_end 'YYYY-MM')."""
    raw = pd.read_excel(path, sheet_name="Airport Passengers", header=None, dtype=object)

    period = str(raw.iat[0, 0])
    m = re.search(r"REPORT PERIOD:.*\bto\s+([A-Za-z]+)\s+(\d{4})", period)
    if not m or m[1].lower() not in MONTHS:
        raise SourceChangedError(f"Airport traffic: unexpected report period line {period!r}")
    report_end = f"{int(m[2]):04d}-{MONTHS[m[1].lower()]:02d}"

    h = _find_row(raw, 0, "AIRPORT")
    _expect(raw, h, {1: "Year", 2: "Month", 3: "INBOUND", 4: "OUTBOUND", 5: "TOTAL", 8: "TOTAL", 11: "TOTAL"}, "Airport traffic")
    _expect(raw, h - 2, {3: "DOMESTIC and REGIONAL AIRLINES", 6: "INTERNATIONAL AIRLINES", 9: "TOTAL PASSENGERS"}, "Airport traffic")

    data = raw.iloc[h + 1 :, :12].copy()
    data.columns = ["airport", "year", "month", "dom_in", "dom_out", "domestic", "int_in", "int_out", "international", "tot_in", "tot_out", "total"]
    gc = data[data["airport"].astype(str).str.strip().str.upper() == AIRPORT_NAME].copy()
    if gc.empty:
        raise SourceChangedError(f"Airport traffic: no rows for {AIRPORT_NAME}")

    out = pd.DataFrame({"month": _month(gc["year"].astype(int), gc["month"].astype(int))})
    for col in ["domestic", "international", "total"]:
        out[col] = pd.to_numeric(gc[col], errors="raise").astype("int64")
    return out.sort_values("month").reset_index(drop=True), report_end


# ── Domestic routes ─────────────────────────────────────────────────────


def read_domestic_routes(path) -> pd.DataFrame:
    """Gold Coast city pairs: monthly passengers, flights, seats and published load factor.

    Where BITRE shows text instead of numbers the values stay empty and `status` says
    why: "suppressed" ("Data not available for release") or "no_flights" ("COVID19 No flights").
    """
    raw = pd.read_excel(path, sheet_name="Top Routes", header=None, dtype=object)
    h = _find_row(raw, 0, "City Pair Route")
    _expect(raw, h, {2: "Year", 3: "Month", 4: "Revenue", 5: "Aircraft", 6: "Rev Pax", 10: "Seats"}, "Domestic routes")
    _expect(raw, h + 1, {4: "Passengers", 5: "Trips (a)", 6: "LF %"}, "Domestic routes")

    data = raw.iloc[h + 2 :, [0, 1, 2, 3, 4, 5, 6, 10]].copy()
    data.columns = ["port_a", "port_b", "year", "month", "passengers", "flights", "load_factor_pct", "seats"]
    gc = data[(data["port_a"] == AIRPORT_CODE) | (data["port_b"] == AIRPORT_CODE)].copy()
    if gc.empty:
        raise SourceChangedError(f"Domestic routes: no rows for {AIRPORT_CODE}")

    other = gc["port_a"].where(gc["port_b"] == AIRPORT_CODE, gc["port_b"])
    out = pd.DataFrame({"month": _month(gc["year"].astype(int), gc["month"].astype(int)), "route": AIRPORT_CODE + "-" + other})
    for col in ["passengers", "flights", "seats"]:
        out[col] = pd.to_numeric(gc[col], errors="coerce").astype("Int64")
    out["load_factor_pct"] = pd.to_numeric(gc["load_factor_pct"], errors="coerce").round(2)
    # Text in place of numbers is kept as a status, never converted to a value
    text = gc["passengers"].astype(str)
    out["status"] = "reported"
    out.loc[text.str.contains("not available for release", case=False).values, "status"] = "suppressed"
    out.loc[text.str.contains("no flights", case=False).values, "status"] = "no_flights"
    bad = out["passengers"].isna() & (out["status"] == "reported")
    if bad.any():
        raise SourceChangedError(f"Domestic routes: unexpected non-numeric values {sorted(set(text[bad.values]))}")
    return out.sort_values(["route", "month"]).reset_index(drop=True)


# ── International seats ─────────────────────────────────────────────────


def read_international_seats(path) -> pd.DataFrame:
    """Gold Coast international scheduled flights and seats operated, by month.

    Uses the "(b) All / Maximum" columns: all flights and seats available at the airport.
    Months with no international flights are absent from the source.
    """
    raw = pd.read_excel(path, sheet_name="AUS", header=None, dtype=object)
    h = _find_row(raw, 0, "Month")
    _expect(raw, h, {1: "Airport", 3: "(b) InFlightsAll", 5: "(b) OutFlightsAll", 7: "(b) InSeatsMax", 9: "(b) OutSeatsMax"}, "International seats")

    data = raw.iloc[h + 1 :, [0, 1, 3, 5, 7, 9]].copy()
    data.columns = ["month", "airport", "flights_in", "flights_out", "seats_in", "seats_out"]
    gc = data[data["airport"] == AIRPORT_NAME_INTL].copy()
    if gc.empty:
        raise SourceChangedError(f"International seats: no rows for {AIRPORT_NAME_INTL}")

    out = pd.DataFrame({"month": pd.to_datetime(gc["month"]).dt.to_period("M").dt.to_timestamp()})
    # Blank cells stay blank (one COVID-era month has only outbound figures)
    for col in ["flights_in", "flights_out", "seats_in", "seats_out"]:
        vals = gc[col].where(gc[col].notna() & (gc[col].astype(str).str.strip() != ""))
        out[col] = pd.to_numeric(vals, errors="raise").astype("Int64")
    out["seats"] = out["seats_in"] + out["seats_out"]
    return out.sort_values("month").reset_index(drop=True)
