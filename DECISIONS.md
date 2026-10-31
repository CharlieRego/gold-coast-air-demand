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

## 2026-10-27 · Refresh schedule
- **Options:** monthly (as first planned), weekly, or every 14 days.
- **Choice:** every 14 days, Wednesday 03:00 Brisbane time, plus a manual trigger. GitHub Actions cron can't express "every 14 days", so the workflow runs weekly and skips odd ISO weeks.
- **Why:** BITRE release dates move around, so a monthly run could sit up to a month behind a new file. Fortnightly is frequent enough, and a run with no new file commits nothing. Wednesday keeps it clear of another scheduled job I run on Mondays.

## 2026-10-27 · Text where numbers should be
- **Problem:** The domestic routes file has "Data not available for release." and "COVID19 No flights" in some number cells. The international seats file has one blank cell (Sep 2020) and some missing months.
- **Options:** (a) treat them as zero; (b) keep them empty, with a `status` column saying why; (c) drop the rows.
- **Choice:** (b). Any other text in a number cell stops the pipeline.
- **Why:** "Suppressed" isn't zero, and turning text into numbers would mean inventing data. Keeping the rows shows the gaps honestly. The model doesn't use these files; they only supply load factors and seat counts from recent, complete months.

## 2026-11-01 · How to handle COVID, and which model
- **What the data showed:** Gold Coast domestic passengers were back to 2019 levels by about March 2022. International took until about April 2023, then fell 20% in 2024 and grew 14% in 2025.
- **Options tested:** two models (ETS exponential smoothing with a damped trend, and the seasonal ARIMA "airline model"), both on log passenger numbers, each trained two ways: (1) *recent*: July 2022 onward only; (2) *long*: 2009 onward with the COVID months cut out. The cut is exactly 24 months for domestic (Mar 2020 – Feb 2022) and 36 months for international (Mar 2020 – Feb 2023), so the months still line up for the seasonal pattern. Domestic and international are forecast separately and added up for the total.
- **Test:** rolling origin over the last 12 months (Jul 2025 – Jun 2026). Every month was forecast 1 to 12 months ahead using only data available at the time. Baseline: same month last year.
- **Results (average % error, 1–6 / 7–12 months ahead):**

  | | ETS recent | ETS long | SARIMA recent | SARIMA long | Same month last year |
  |---|---|---|---|---|---|
  | Domestic | **3.9 / 3.5** | 4.4 / 5.4 | 6.4 / 8.9 | 4.9 / 6.2 | 5.3 / 5.3 |
  | International | **14.3 / 19.0** | 14.5 / 19.9 | 15.0 / 21.0 | 12.8 / 25.7 | 19.8 / 19.8 |
  | Total (domestic + international) | **4.7 / 4.9** | | | | 7.1 / 7.1 |

- **Rule and choice:** for each series, the method with the lowest average error over horizons 1–12. ETS on recent data won for both. Forecasting domestic and international separately and adding them beat a direct model of the total (5.5 / 7.2 for ETS long on the total).
- **Caveat:** the method was chosen on the same 12 months it is scored on, so real accuracy may be a little worse. The page says so. With only four years of post-COVID data there wasn't room for a separate test year.
- **Not used:** statsforecast. statsmodels covered both models.

## 2026-11-01 · Likely ranges
- **Options:** (a) the model's own simulated 80% ranges; (b) the 10th–90th percentile of the backtest's signed errors; (c) forecast ± the absolute % error that 8 in 10 backtest forecasts at a similar distance ahead (1–3, 4–6, 7–9, 10–12 months) stayed within.
- **Choice:** (c).
- **Why:** (a) was too narrow: in the backtest, ETS's 80% ranges caught the actual figure only 32–75% of the time, depending on the series and distance ahead. (b) failed a sanity check: domestic forecasts 4–6 months ahead ran low in every test case, so the whole range sat above the forecast. (c) is easy to explain ("this is how far off the method has recently been, this far ahead") and always contains the forecast. The six-month headline range adds up the monthly ranges, which is cautious because it assumes a month that runs high is followed by others that also run high.

## 2026-11-01 · The forecast runs low, and I'm saying so instead of correcting it
- **Finding:** over the test year the chosen method came in below the actual figure in 80% of forecasts, by 3.8% on average for the total (domestic 3.2%, international 7.6%). Early numbers for July 2026, the month after the latest airport data, back this up for international: seats on international flights were up 13.6% on July 2025, while the model forecast international passengers up 3%. Domestic route passengers were up 0.4%, in line with the model's flat forecast.
- **Options:** (a) shift the forecast up by the backtest bias; (b) leave it and say so.
- **Choice:** (b). The page shows a "treat this as a cautious estimate" line, generated from the backtest, and the July early numbers next to the forecast.
- **Why:** correcting with the same 12 months used to score the model would make the accuracy figures look better than they are. The bias is reported as measured.

## 2026-11-01 · Chart library for the web page
- **Options:** Recharts (as first planned) or a small hand-drawn SVG chart.
- **Choice:** hand-drawn SVG in one React component.
- **Why:** the page is opened from a QR code on phones over mobile data. The chart only needs one line, a dashed forecast, a shaded range, a highlighted six-month window and a hover/touch readout, which is about 250 lines of SVG. That adds no dependency and keeps the JavaScript small. It also has keyboard arrow-key reading and a table view, so it doesn't rely on hover alone.
