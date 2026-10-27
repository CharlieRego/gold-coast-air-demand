# Decision log

Each entry: date, the options, the choice, and why.

---

## 2026-10-27 · Which international seats file to use
- **Options:** (a) the Dec 2025 edition on the "International airlines operated flights and seats" page; (b) the Jul 2026 edition of the same tables on BITRE's international time-series page; (c) leave international seats out.
- **Choice:** (b).
- **Why:** Same tables, same publisher, but (b) runs to July 2026, one month past the airport traffic file (June 2026). (a) would be six months stale. The ingest step will look for the newest `OpFltsSeats_MMYY_Tables.xlsx` link on the time-series page.

## 2026-10-27 · Keeping a 16 MB spreadsheet in git
- **Options:** (a) commit every raw download; (b) commit the small files (airport traffic 0.9 MB, top routes 1.7 MB) and, for the 16 MB international file, commit only its SHA-256 and the extracted Gold Coast rows; (c) commit nothing raw.
- **Choice:** (b). The file is gitignored; `data/raw/manifest.json` records its URL, retrieval date and SHA-256.
- **Why:** A monthly 16 MB binary adds roughly 200 MB a year to the repo history for about 280 rows of Gold Coast data. The hash plus the source URL still lets anyone check the file they download is the one used.

## 2026-10-27 · Forecast horizon, given the data lag
- **Problem:** On 27 Oct 2026 the latest BITRE airport month is June 2026. "The next 6 months" from the data is July–December 2026, and four of those months have already happened by the event on 3 November.
- **Options:** (a) forecast six months past the latest data month (Jul–Dec 2026) and say so; (b) forecast up to six months past *today* (Jul 2026 – Apr 2027, 10 steps) and write the headline about the coming six months (Nov 2026 – Apr 2027); (c) shorten the history gap with July 2026 route-level data.
- **Choice:** (b), with the chart clearly separating "data to June 2026" from "forecast", and the likely range widening with each month further out. The horizon is recalculated on each refresh. (c) is out: route data covers only some of the airport's traffic.
- **Why:** A headline about months that are already over is not useful to people planning for summer. The longer horizon costs accuracy, so the backtest will report errors at 1–6 and 7–10 months ahead separately.

## 2026-10-27 · What the scenario slider calculates
- **Problem:** The airport figures are *passenger movements*. Each passenger on a flight arriving at or leaving Gold Coast is one movement. So a weekly return service adds two legs a week, not one.
- **Formula:** extra monthly movements = weekly return flights × 2 legs × seats per flight × load factor × (365.25 ÷ 12 ÷ 7 ≈ 4.35 weeks per month).
- **Default load factor:** 89.8%, the share of seats filled on Gold Coast's four reported domestic routes in the year to July 2026 (BITRE top routes file). For international, the equivalent figure is 85.4% (FY26 international passengers ÷ operated seats, derived from two BITRE files). A domestic/international toggle that switches the default.
- **Default seats per flight:** 180, close to the 176–194 average seats per flight on those routes (BITRE top routes, year to July 2026).

## 2026-10-27 · Python libraries
- **Options:** statsforecast (fast, but pulls in numba) or statsmodels (ETS and SARIMA, lighter, widely known).
- **Choice:** statsmodels, plus pandas and openpyxl. Add statsforecast only if the backtest shows a model it has that statsmodels lacks.

## 2026-10-27 · How to handle COVID (2020–22) — to decide on 29 Oct with evidence
- Gold Coast passengers fell to almost zero in April 2020. Domestic traffic dipped with each lockdown until about January 2022. International stayed near zero until early 2022 and had largely recovered by mid-2022.
- **Options to test in the backtest:** (1) train from Jul 2022 only (48 months; the earliest backtest fold has 36); (2) use 2009–Feb 2020 plus Jul 2022 onward, with a level shift for the post-COVID period; (3) model domestic and international separately with different start dates.
- The choice will be based on rolling-origin backtest error against the "same month last year" baseline.

## 2026-10-27 · Refresh schedule
- **Options:** monthly (as first planned), weekly, or every 14 days.
- **Choice:** every 14 days, Wednesday 03:00 Brisbane time, plus a manual trigger. GitHub Actions cron can't express "every 14 days", so the workflow runs weekly and skips odd ISO weeks.
- **Why:** BITRE release dates move around, so a monthly run could sit up to a month behind a new file. Fortnightly is frequent enough, and a run with no new file commits nothing. Wednesday keeps it clear of another scheduled job I run on Mondays.

## 2026-10-27 · Text where numbers should be
- **Problem:** The domestic routes file has "Data not available for release." and "COVID19 No flights" in some number cells. The international seats file has one blank cell (Sep 2020) and some missing months.
- **Options:** (a) treat them as zero; (b) keep them empty, with a `status` column saying why; (c) drop the rows.
- **Choice:** (b). Any other text in a number cell stops the pipeline.
- **Why:** "Suppressed" isn't zero, and turning text into numbers would mean inventing data. Keeping the rows shows the gaps honestly. The model doesn't use these files; they only supply load factors and seat counts from recent, complete months.
