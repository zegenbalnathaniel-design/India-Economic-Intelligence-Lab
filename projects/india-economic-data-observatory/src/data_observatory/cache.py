"""On-disk CSV caching for fetched (or synthetically generated) series.

**Design choice: on-disk CSV under `data/cache/`, not `functools.lru_cache`.**
Reasoning:

- The Streamlit app (`app/Home.py`) reruns its script top-to-bottom on
  every widget interaction, in a fresh-ish process per deployment restart.
  An in-memory `lru_cache` would be invisible to anyone who wants to
  inspect what was actually fetched, and gets silently wiped on every
  process restart — exactly the two things we don't want for data whose
  live/synthetic provenance matters.
- A plain CSV file is human-inspectable (open it, see the dates and
  values), diffable, and survives across runs/sessions, which matters when
  the live World Bank endpoint is flaky: a value fetched live once stays
  cached as "live" even if a later run's live fetch fails, instead of
  silently degrading to synthetic on every re-run.
- It is keyed by indicator key + start + end + live-vs-synthetic status, so
  a cached synthetic result is never served back as if it were live, or
  vice versa, and different date ranges don't collide.

This is deliberately a thin, dependency-free layer (just `pandas` CSV I/O)
rather than a real database, appropriate for this project's scale.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"


def _safe_key(indicator_key: str, start: str, end: str, status: str) -> str:
    raw = f"{indicator_key}__{start}__{end}__{status}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)


def cache_path(indicator_key: str, start: str, end: str, status: str) -> Path:
    return CACHE_DIR / f"{_safe_key(indicator_key, start, end, status)}.csv"


def read_from_cache(indicator_key: str, start: str, end: str, status: str) -> Optional[pd.DataFrame]:
    """Return the cached frame (columns: date index + `value` [+ `imputed`])
    if present on disk, else None. Never raises."""
    path = cache_path(indicator_key, start, end, status)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    except Exception:
        return None


def write_to_cache(indicator_key: str, start: str, end: str, status: str, frame: pd.DataFrame) -> None:
    """Write `frame` to its cache file. Never raises (a cache write failure
    — e.g. a read-only filesystem — should degrade to 'no caching', not
    break the pipeline)."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = cache_path(indicator_key, start, end, status)
        frame.to_csv(path)
    except Exception:
        pass


def clear_cache() -> int:
    """Delete every cached file. Returns the number of files removed.
    Used by tests and available to the app for a manual "refresh" action."""
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for p in CACHE_DIR.glob("*.csv"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n
