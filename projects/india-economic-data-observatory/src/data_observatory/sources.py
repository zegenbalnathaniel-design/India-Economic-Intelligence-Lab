"""Live-fetch functions against real official endpoints.

Every function here makes (or attempts to make) a real HTTP request to a
real, documented, official endpoint for Indian economic data. None of them
require an API key. All of them are expected to be able to fail in any
given runtime environment — including this one, see `docs/DATA_SOURCES.md`
for the actual probe result — and every function here returns `None` on any
failure rather than raising, so the caller in `loaders.py` can cleanly fall
back to a synthetic series.

Design note on why World Bank is the primary target: it is the only one of
the four official sources this project documents (RBI DBIE, MoSPI, World
Bank, IMF IFS) that exposes a plain, unauthenticated, versioned JSON REST
API intended for machine consumption. RBI's Database on Indian Economy
(dbie.rbi.org.in) and MoSPI (mospi.gov.in) are primarily interactive
BI-portal / report-download sites without a stable public JSON API; this
module still attempts a real HTTP GET against a documented endpoint/page for
those two (so the "attempt live first" architecture is real and not just
theater for World Bank), but failure there is the expected, normal outcome
even with working internet access.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

try:
    import requests
except ImportError:  # pragma: no cover - requests is a declared dependency
    requests = None  # type: ignore

WORLD_BANK_API_BASE = "https://api.worldbank.org/v2/country/{country}/indicator/{code}"
RBI_DBIE_URL = "https://dbie.rbi.org.in/"
MOSPI_URL = "https://www.mospi.gov.in/"
IMF_IFS_URL = "https://www.imf.org/en/Data"

REQUEST_TIMEOUT_SECONDS = 10


def fetch_world_bank_indicator(
    indicator_code: str,
    start: str,
    end: str,
    country: str = "IND",
) -> Optional[pd.Series]:
    """Fetch one World Bank indicator series for `country` between `start`
    and `end` (year strings or full dates; only the year is used, since
    World Bank's indicator API is annual).

    Returns a `pd.Series` indexed by calendar-year timestamps (January 1st
    of each year), or `None` if the request failed, returned no data, or
    the response could not be parsed. Never raises.
    """
    if requests is None:
        return None
    start_year = str(start)[:4]
    end_year = str(end)[:4]
    url = WORLD_BANK_API_BASE.format(country=country, code=indicator_code)
    params = {
        "format": "json",
        "per_page": "20000",
        "date": f"{start_year}:{end_year}",
    }
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            return None
        payload = resp.json()
    except Exception:
        return None

    # World Bank's API returns [metadata_dict, list_of_observations] on
    # success, or a single dict (sometimes with a "message" error key) on
    # failure / malformed requests.
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return None
    records = payload[1]
    if not isinstance(records, list) or len(records) == 0:
        return None

    dates, values = [], []
    for rec in records:
        try:
            val = rec.get("value")
            year = rec.get("date")
            if val is None or year is None:
                continue
            dates.append(pd.Timestamp(f"{year}-01-01"))
            values.append(float(val))
        except (TypeError, ValueError, AttributeError):
            continue

    if not dates:
        return None
    series = pd.Series(values, index=pd.DatetimeIndex(dates), name=indicator_code).sort_index()
    return series


def probe_rbi_dbie() -> Optional[bytes]:
    """Best-effort real HTTP GET against RBI's Database on Indian Economy
    portal. DBIE is an interactive BI-tool front end, not a stable JSON API,
    so this cannot parse a usable time series out of the response — it
    exists so the architecture genuinely *attempts* a live RBI touch before
    falling back, rather than skipping straight to synthetic. A real
    programmatic integration against DBIE would need its documented
    data-extraction endpoints and, in practice, manual export/scripted
    download rather than a single stateless GET.
    """
    if requests is None:
        return None
    try:
        resp = requests.get(RBI_DBIE_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception:
        return None


def probe_mospi() -> Optional[bytes]:
    """Best-effort real HTTP GET against MoSPI's homepage, for the same
    reason as `probe_rbi_dbie`: MoSPI publishes CPI/WPI/GDP releases as
    downloadable PDF/Excel bulletins rather than a queryable REST API."""
    if requests is None:
        return None
    try:
        resp = requests.get(MOSPI_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception:
        return None
