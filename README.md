# Gold Coast Air Demand Outlook

A monthly forecast of passengers through Gold Coast Airport, built from BITRE open data and published at
[charlierego.com/projects/gold-coast-demand](https://charlierego.com/projects/gold-coast-demand).

It answers one question for people planning around the Gold Coast's visitor season: **how many passengers is the airport likely to handle over the next six months?**

## Pipeline

| Step | Where | What it does |
|---|---|---|
| Ingest | `src/ingest/` | Finds the newest files on BITRE's pages, downloads them to `data/raw/` (with SHA-256 in `data/raw/manifest.json`), and extracts the Gold Coast rows into `data/processed/` |
| Checks | `src/checks/` | Stops the run if months are missing or duplicated, any value is negative, domestic + international doesn't equal the total, or the latest month doesn't match what BITRE says the file covers |
| Model | `src/model/` | Forecasts domestic and international passengers separately and adds them up. Candidates: ETS and seasonal ARIMA, trained on post-COVID data or on 2009 onward with COVID cut out |
| Backtest | `src/model/backtest.py` | Rolling origin over the last 12 months, 1–12 months ahead, against "same month last year" |
| Export | `src/export/` | Writes `output/forecast.json` and checks it against `schema/forecast.schema.json` |

## Accuracy (test year Jul 2025 – Jun 2026)

Average % difference between forecast and actual passengers:

| | 1–6 months ahead | 7–12 months ahead |
|---|---|---|
| This model (domestic + international) | **4.7%** | **4.9%** |
| Same month last year | 7.1% | 7.1% |

The model beat the baseline at both distances. It also ran low: 8 in 10 test forecasts came in below the real number, by about 4% on average, so its forecasts should be read as cautious. Full results and the reasons behind each choice are in [`DECISIONS.md`](DECISIONS.md); every individual test forecast is in `output/backtest.csv`.

## Limitations

- BITRE publishes about three to four months after the month ends, so the forecast starts several months before today.
- Only four years of post-COVID data. The method was chosen on the same 12 months it's scored on.
- International traffic depends on airlines adding or dropping routes, which a model of past passenger numbers can't see coming. Its errors are much larger than domestic.
- Counts are passenger movements on scheduled flights: each arrival and each departure counts once. Charter flights aren't included.

## `forecast.json`

Versioned (`schema_version`), described by [`schema/forecast.schema.json`](schema/forecast.schema.json) and checked by `tests/test_forecast_json.py`. It holds the history from 2019, the monthly forecast with likely ranges, the six-month headline, accuracy results, early indicators from the route and seat files, scenario defaults, and the source of every input.

## Run it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/pip elsewhere
python -m src.pipeline             # download the latest BITRE files, then process and check
python -m src.pipeline --offline   # reuse files already in data/raw
python -m src.pipeline --offline --today 2026-11-01   # fix the run date
python -m pytest
```

## Data

Sources, licences and retrieval dates: [`data/SOURCES.md`](data/SOURCES.md).

Source: Bureau of Infrastructure and Transport Research Economics (BITRE), © Commonwealth of Australia, CC BY 4.0.
