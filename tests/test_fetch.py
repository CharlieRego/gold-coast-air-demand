import pytest

from src.errors import SourceChangedError
from src.ingest.fetch import find_file_link, page_links

AIRPORT_PAGE = """
<a href="https://www.bitre.gov.au/sites/default/files/documents/Aviation-Airport%20Traffic%20Data-June%202026.xlsx">
  Monthly airport traffic data for top 20 airports: January 2009 to current – June 2026</a>
<a href="https://www.bitre.gov.au/sites/default/files/documents/WebMonthlyAirportData1985-Jul2013_Top20.xls">
  Monthly airport traffic data for top 20 airports: January 1985 to July 2013</a>
"""

INTL_PAGE = """
<a href="/sites/default/files/documents/International_airline_activity_OpFltsSeats_1225_Tables.xlsx">old</a>
<a href="/sites/default/files/documents/International_airline_activity_OpFltsSeats_0726_Tables.xlsx">new</a>
<a href="/sites/default/files/documents/International_airline_activity_CityPairs_2009toCurrent_0726.xlsx">other</a>
"""


def test_airport_link_found_from_link_text():
    url, label = find_file_link("airport_traffic", page_links(AIRPORT_PAGE, "https://www.bitre.gov.au/x"))
    assert url.endswith("June%202026.xlsx")
    assert label == "2026-06"


def test_newest_international_edition_wins_and_relative_links_resolve():
    url, label = find_file_link("international_seats", page_links(INTL_PAGE, "https://www.bitre.gov.au/resource/x"))
    assert url == "https://www.bitre.gov.au/sites/default/files/documents/International_airline_activity_OpFltsSeats_0726_Tables.xlsx"
    assert label == "2026-07"


def test_domestic_routes_label_from_file_name():
    html = '<a href="/sites/default/files/documents/toproutesjuly2014july2026.xlsx">Top routes</a>'
    _, label = find_file_link("domestic_routes", page_links(html, "https://www.bitre.gov.au/"))
    assert label == "2026-07"


def test_missing_link_raises():
    with pytest.raises(SourceChangedError):
        find_file_link("domestic_routes", page_links("<a href='/nothing.xlsx'>x</a>", "https://www.bitre.gov.au/"))
