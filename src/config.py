"""Paths and source definitions shared by the pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"
MANIFEST_PATH = RAW_DIR / "manifest.json"

# BITRE's firewall drops requests whose user agent contains a URL, so keep it plain.
USER_AGENT = "gold-coast-air-demand/1.0"

BITRE_ATTRIBUTION = (
    "Source: Bureau of Infrastructure and Transport Research Economics (BITRE), "
    "© Commonwealth of Australia, CC BY 4.0."
)

# Each source is found by reading its BITRE page and picking the matching link,
# because the file names change with every release.
SOURCES = {
    "airport_traffic": {
        "title": "Airport traffic data: monthly, top 20 airports",
        "page_url": "https://www.bitre.gov.au/resource/aviation/airport-traffic-data",
        # Link text reads e.g. "Monthly airport traffic data for top 20 airports: January 2009 to current – June 2026"
        "link_text_pattern": r"top 20 airports:\s*January 2009 to current\W+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})",
        "keep_raw_in_git": True,
    },
    "domestic_routes": {
        "title": "Australian domestic aviation activity: top routes",
        "page_url": "https://www.bitre.gov.au/resource/aviation/australian-domestic-aviation-activity-time-series",
        # e.g. toproutesjuly2014july2026.xlsx
        "href_pattern": r"toproutesjuly2014(?P<month>[a-z]+)(?P<year>\d{4})\.xlsx$",
        "keep_raw_in_git": True,
    },
    "international_seats": {
        "title": "International airline activity: operated flights and seats",
        "page_url": "https://www.bitre.gov.au/resource/aviation/international-airline-activity-time-series-data",
        # e.g. International_airline_activity_OpFltsSeats_0726_Tables.xlsx (MMYY)
        "href_pattern": r"International_airline_activity_OpFltsSeats_(?P<mm>\d{2})(?P<yy>\d{2})_Tables\.xlsx$",
        "keep_raw_in_git": False,  # 16 MB; manifest keeps its SHA-256 instead
    },
}

AIRPORT_NAME = "GOLD COAST"  # airport traffic file
AIRPORT_CODE = "OOL"  # domestic routes file
AIRPORT_NAME_INTL = "Gold Coast"  # international seats file
