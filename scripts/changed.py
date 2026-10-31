"""Exit 0 if output/forecast.json changed in a meaningful way since the last commit, else 1.

Run timestamps (generated_at, run_date) don't count: only new data or a new forecast does.
"""

import json
import subprocess
import sys
from pathlib import Path

IGNORE = {"generated_at", "run_date"}

new = json.loads(Path("output/forecast.json").read_text(encoding="utf-8"))
try:
    old = json.loads(subprocess.check_output(["git", "show", "HEAD:output/forecast.json"]))
except subprocess.CalledProcessError:
    old = {}

strip = lambda d: {k: v for k, v in d.items() if k not in IGNORE}
changed = strip(new) != strip(old)
print("forecast changed" if changed else "no meaningful change")
sys.exit(0 if changed else 1)
