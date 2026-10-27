# Gold Coast Air Demand Outlook

A monthly forecast of passengers through Gold Coast Airport, built from BITRE open data and published at
[charlierego.com/projects/gold-coast-demand](https://charlierego.com/projects/gold-coast-demand).

> Work in progress (October 2026). Method, accuracy results and limitations will be added here as they are finished.

## What's here so far

| Step | Where | What it does |
|---|---|---|
| Ingest | `src/ingest/` | Finds the newest files on BITRE's pages, downloads them to `data/raw/`, and extracts the Gold Coast rows into `data/processed/` |
| Checks | `src/checks/` | Stops the run if months are missing or duplicated, any value is negative, domestic + international doesn't equal the total, or the latest month doesn't match what BITRE says the file covers |

Sources, licences and retrieval dates: [`data/SOURCES.md`](data/SOURCES.md). Design choices: [`DECISIONS.md`](DECISIONS.md).

## Run it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/pip elsewhere
python -m src.pipeline             # download the latest BITRE files, then process and check
python -m src.pipeline --offline   # reuse files already in data/raw
python -m pytest
```

## Data

Source: Bureau of Infrastructure and Transport Research Economics (BITRE), © Commonwealth of Australia, CC BY 4.0.
