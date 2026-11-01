#!/usr/bin/env bash
# Fortnightly refresh, run by cron on an Australian server (BITRE's website refuses
# connections from overseas cloud servers such as GitHub Actions runners).
#
#   scripts/refresh.sh            run only in even ISO weeks (cron calls it weekly)
#   scripts/refresh.sh --force    run now
#   scripts/refresh.sh --no-push  run, but don't commit or push (for testing)
#
# Downloads the latest BITRE files, runs the data checks, backtest, forecast and tests.
# Commits and pushes only if the forecast actually changed. Any failure stops the run
# before anything is committed.
set -euo pipefail
cd "$(dirname "$0")/.."

FORCE=0; PUSH=1
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --no-push) PUSH=0; FORCE=1 ;;
  esac
done

log() { echo "$(TZ=Australia/Brisbane date '+%F %T') $*"; }

week=$(TZ=Australia/Brisbane date +%V)
if [[ $FORCE -eq 0 && $((10#$week % 2)) -ne 0 ]]; then
  log "ISO week $week is odd: skipping"
  exit 0
fi

log "refresh start (week $week)"
git pull -q --ff-only

.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m src.pipeline
.venv/bin/python -m pytest -q

if .venv/bin/python scripts/changed.py; then
  latest=$(.venv/bin/python -c "import json; print(json.load(open('output/forecast.json'))['latest_data_month'])")
  if [[ $PUSH -eq 1 ]]; then
    git add output/ data/processed/ data/raw/ README.md
    git commit -q -m "data: refresh forecast (BITRE data to $latest)"
    git push -q
    log "pushed new forecast (data to $latest)"
  else
    log "forecast changed (data to $latest); --no-push, so not committed"
  fi
else
  log "nothing new"
fi

# Discard the run's own timestamp-only edits so the next pull is clean
git checkout -q -- .
log "refresh done"
