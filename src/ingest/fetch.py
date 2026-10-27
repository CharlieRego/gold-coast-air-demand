"""Find the latest BITRE file links and download them to data/raw.

data/raw/manifest.json records, for each source: page URL, file URL, file name,
the month the source says it covers, SHA-256, size and when it was retrieved.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from src.config import MANIFEST_PATH, RAW_DIR, SOURCES, USER_AGENT
from src.errors import SourceChangedError

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def http_get(url: str, timeout: int = 180, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # network errors, timeouts, HTTP errors
            last_error = e
            time.sleep(5 * (attempt + 1))
    raise SourceChangedError(f"Could not download {url}: {last_error}")


def page_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html)
    return [(urllib.parse.urljoin(base_url, href), text) for href, text in parser.links]


def find_file_link(key: str, links: list[tuple[str, str]]) -> tuple[str, str]:
    """Return (file_url, label_month 'YYYY-MM') for a source, or raise if not found."""
    src = SOURCES[key]
    found: list[tuple[str, str]] = []
    for url, text in links:
        if "link_text_pattern" in src:
            m = re.search(src["link_text_pattern"], text, flags=re.I)
            if m and url.lower().endswith((".xlsx", ".xls")):
                found.append((url, _ym(m["year"], m["month"])))
        else:
            m = re.search(src["href_pattern"], urllib.parse.unquote(url), flags=re.I)
            if m:
                if "mm" in m.groupdict():
                    found.append((url, f"20{m['yy']}-{m['mm']}"))
                else:
                    found.append((url, _ym(m["year"], m["month"])))
    if not found:
        raise SourceChangedError(f"No file link for '{key}' on {src['page_url']}. The page layout may have changed.")
    # The newest edition wins if a page lists more than one
    return max(found, key=lambda x: x[1])


def _ym(year: str, month_name: str) -> str:
    month = MONTHS.get(month_name.lower())
    if month is None:
        raise SourceChangedError(f"Unrecognised month name '{month_name}'")
    return f"{int(year):04d}-{month:02d}"


def sha256(path_or_bytes: Path | bytes) -> str:
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_all() -> dict:
    """Download the latest file for every source. Returns the updated manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key, src in SOURCES.items():
        html = http_get(src["page_url"], timeout=60).decode("utf-8", errors="replace")
        file_url, label_month = find_file_link(key, page_links(html, src["page_url"]))
        file_name = Path(urllib.parse.unquote(urllib.parse.urlparse(file_url).path)).name
        data = http_get(file_url)
        if not data.startswith(b"PK"):  # .xlsx files are zip archives
            raise SourceChangedError(f"{file_url} is not an .xlsx file")
        digest = sha256(data)
        previous = manifest.get(key, {})
        changed = previous.get("sha256") != digest
        if previous.get("file_name") and previous["file_name"] != file_name:
            (RAW_DIR / previous["file_name"]).unlink(missing_ok=True)  # replaced by a newer edition
        (RAW_DIR / file_name).write_bytes(data)
        manifest[key] = {
            "title": src["title"],
            "page_url": src["page_url"],
            "file_url": file_url,
            "file_name": file_name,
            "label_month": label_month,
            "sha256": digest,
            "bytes": len(data),
            "retrieved_at": now if changed else previous.get("retrieved_at", now),
            "last_checked_at": now,
            "raw_file_in_git": src["keep_raw_in_git"],
        }
        print(f"[fetch] {key}: {file_name} (covers to {label_month}) {'NEW' if changed else 'unchanged'}")
    save_manifest(manifest)
    return manifest


def verify_local(manifest: dict) -> None:
    """Offline mode: make sure the raw files on disk are the ones the manifest describes."""
    for key in SOURCES:
        entry = manifest.get(key)
        if not entry:
            raise SourceChangedError(f"Manifest has no entry for '{key}'. Run without --offline first.")
        path = RAW_DIR / entry["file_name"]
        if not path.exists():
            raise SourceChangedError(f"Missing raw file {path}")
        if sha256(path) != entry["sha256"]:
            raise SourceChangedError(f"{path.name} does not match the SHA-256 in the manifest")
