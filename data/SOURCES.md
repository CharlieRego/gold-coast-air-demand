# Data sources

All files in `data/raw/` are stored exactly as downloaded. Retrieval date for every file below: **27 October 2026**. `data/raw/manifest.json` records the URL, retrieval time and SHA-256 of the files currently in use and is updated by every pipeline run.

BITRE's web firewall silently drops requests whose user agent contains a URL, so the pipeline identifies itself as `gold-coast-air-demand/1.0`.

## BITRE (Bureau of Infrastructure and Transport Research Economics)

**Licence and attribution.** BITRE publishes on the Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts website. Its copyright page (https://www.infrastructure.gov.au/copyright) says material is licensed under Creative Commons Attribution 4.0 International where identified, and is to be attributed as "© Commonwealth of Australia". The spreadsheets themselves carry a disclaimer that data comes from third parties and the Commonwealth gives no warranty as to its accuracy.

Attribution used on the page: *Source: Bureau of Infrastructure and Transport Research Economics (BITRE), © Commonwealth of Australia, CC BY 4.0.*

> Open question: the spreadsheets don't show a CC logo themselves. The wording above follows the department's site-wide copyright page.

### 1. Airport traffic data (main series)
| | |
|---|---|
| Page | https://www.bitre.gov.au/resource/aviation/airport-traffic-data (release date 2 Oct 2026) |
| File | `Aviation-Airport Traffic Data-June 2026.xlsx` — https://www.bitre.gov.au/sites/default/files/documents/Aviation-Airport%20Traffic%20Data-June%202026.xlsx |
| SHA-256 | `9a5ec82c1685e0f434dcbdec66047b1c0049de014984ff2d54091384d6d92632` |
| Sheet used | `Airport Passengers` (header on row 7) |
| Columns | Airport, Year, Month; Domestic & Regional inbound/outbound/total; International inbound/outbound/total; Total inbound/outbound/total (revenue passengers, RPT only) |
| Coverage | Jan 2009 – **Jun 2026**, 20 airports + "All Australian Airports". Gold Coast: 210 months |
| Checks run | No missing months, no duplicate months, no negatives, domestic + international = total in all 210 rows |
| Note | The URL contains the month name, so it changes each release. The ingest step must discover the link from the page, not hard-code it |

### 2. Domestic aviation activity – top routes
| | |
|---|---|
| Page | https://www.bitre.gov.au/resource/aviation/australian-domestic-aviation-activity-time-series (linked from https://www.bitre.gov.au/resource/aviation/domestic-aviation-activity, release date 1 Oct 2026) |
| File | `toproutesjuly2014july2026.xlsx` — https://www.bitre.gov.au/sites/default/files/documents/toproutesjuly2014july2026.xlsx |
| SHA-256 | `2bb013e3a1d8b427a54193bcb86025440c4cbae9ea90bc102b0f52974a9a0f66` |
| Sheet used | `Top Routes` |
| Columns | City-pair codes, Year, Month, revenue passengers, aircraft trips, load factor %, distance, RPKs, ASKs, seats (monthly and moving annual) |
| Coverage | Jul 2014 – **Jul 2026** |
| Gold Coast routes | OOL–SYD, OOL–MEL, OOL–ADL (from 2014), OOL–CBR (from 2020), OOL–CNS (from 2021, mostly "Data not available for release") |
| Year to Jul 2026 | 89.8% of seats filled across the four reported routes (SYD 88.8%, MEL 90.6%, ADL 91.7%, CBR 90.5%); about 176–194 seats per flight |
| Note | Traffic is both directions combined, counted on board by flight stage |
| Text values | Some months show text instead of numbers: "Data not available for release." (suppressed) and "COVID19 No flights". These are kept as empty values with a `status` column, never turned into numbers |

### 3. International airlines – operated flights and seats
| | |
|---|---|
| Page in brief | https://www.bitre.gov.au/publications/ongoing/international_airlines-operated_flights_seats — only has the **Dec 2025** edition (release date 4 May 2026) |
| Page used | https://www.bitre.gov.au/resource/aviation/international-airline-activity-time-series-data (release date 14 Oct 2026) |
| File | `International_airline_activity_OpFltsSeats_0726_Tables.xlsx` — https://www.bitre.gov.au/sites/default/files/documents/International_airline_activity_OpFltsSeats_0726_Tables.xlsx |
| SHA-256 | `9e8d6e73e42ebcf4e7b06d29eebac6505d5aa02a9e52e247ccb55755294abd7f` |
| Size | 16.2 MB |
| Sheet used | `AUS` (flights and seats by Australian airport, inbound/outbound) |
| Coverage | Sep 2003 – **Jul 2026** |
| Gaps | Gold Coast rows are missing for months with no international flights (2020–22), for several months in 2003–05, and for Sep–Oct 2022, although the airport file shows international passengers in those two months. Sep 2020 has outbound figures only. From Jan 2023 the series is complete, so only those months are used |
| FY26 check | Gold Coast international seats Jul 2025 – Jun 2026 (in + out) = 911,830; international passengers from file 1 = 778,891, so about 85.4% of seats filled (derived, not a published figure) |

## DETSI (Department of the Environment, Tourism, Science and Innovation) — stretch goal C

**Licence:** Creative Commons Attribution 4.0 (CC-BY-4.0), confirmed in the Queensland open data portal metadata for all three datasets. Publisher: Environment, Tourism, Science and Innovation. Data are near real time, **preliminary and not quality checked**.

| Dataset | Page | Feed | Gold Coast site |
|---|---|---|---|
| Near real time wave data | https://www.data.qld.gov.au/dataset/coastal-data-system-near-real-time-wave-data | https://apps.des.qld.gov.au/data-sets/waves/wave-7dayopdata.csv (7 days, all sites, ~1.1 MB). Filtered API: `datastore_search` on resource `2bbef99e-9974-49b9-a316-57402b00609c` (~1.5 KB) | `Gold Coast Mk4` (also Palm Beach Mk4, Tweed Heads Mk4, Tweed Offshore) |
| Near real time tide data | https://www.data.qld.gov.au/dataset/coastal-data-system-tide-data | https://apps.des.qld.gov.au/data-sets/storm-tides/stdtide-7dayopdata.csv | `goldcoast` not listed in this one (only `tweedsbj` nearby) |
| Near real time storm tide data | https://www.data.qld.gov.au/dataset/coastal-data-system-near-real-time-storm-tide-data | https://apps.des.qld.gov.au/data-sets/storm-tides/tide-7dayopdata.csv (~4.9 MB). Datastore resource `7afe7233-fae0-4024-bc98-3a72f05675bd` | `goldcoast` (lat -27.9386, lon 153.4326) |
| Gold Coast wave site | https://www.qld.gov.au/environment/coasts-waterways/beach/waves-sites/gold-coast | — | Jointly operated with City of Gold Coast |

Wave columns: Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hs (significant wave height, m), Hmax, Tp (peak period, s), Tz, SST (sea temperature, °C), Direction (degrees), Current Speed, Current Direction. Half-hourly readings.
Tide columns: Site, Seconds, DateTime, Water Level, Prediction, Residual, Latitude, Longitude. 10-minute readings.
Observed 27 Oct 2026 ~17:20 AEST: latest Gold Coast wave reading was 15:30 (about 2 hours old); latest Gold Coast water level reading was 16:30, with the 16:40 row showing `-99.000` (missing value).

### How the page reads DETSI data
The page uses the open data portal's filtered `datastore_search` API (sorted by `Seconds`, filtered to `Gold Coast Mk4` and `goldcoast`), about 2 KB a request, fetched on the server at most every 30 minutes. It carries the same readings as the CSV feeds. Missing values are `-99` or `-99.9` and are skipped. The storm tide metadata doesn't state the datum for `Water Level`, so the page shows the reading against DETSI's own predicted tide and doesn't name a datum.

Observed 1 Nov 2026 about 04:00 AEST: the latest Gold Coast wave reading was 30 Oct 19:00, and DETSI's CSV said "Wave Data provided @ 20:30hrs on 30-10-2026", so the source itself was about 31 hours behind. The tide gauge had shown `-99` since 30 Oct 15:10. The page showed "Buoy data delayed – last reading at …", as designed.

## Not used
- `International_airline_activity_OpFltsSeats_1225_Tables.xlsx` (Dec 2025 edition) — superseded by the Jul 2026 edition.
- `International_airline_activity_CityPairs_2009toCurrent_0726.xlsx` — passengers by city pair to Jul 2026. Not needed for the forecast; may be useful later for route-level international load factors.
