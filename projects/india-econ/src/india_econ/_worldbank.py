"""Thin client for the World Bank's open, unauthenticated data API.

Only one function here ever touches the network: :func:`_http_get_json`.
Everything else is parsing and caching built on top of it, which keeps the
caching layer easy to test with a mock (patch ``requests.get``, call the
cached function twice, assert the mock fired once) and easy to reason
about (one World Bank "indicator code" -> one cached network call,
independent of what date range a caller eventually asks for).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import requests

from .exceptions import DataFetchError

REQUEST_TIMEOUT_SECONDS = 10
_BASE_URL = "https://api.worldbank.org/v2/country/IND/indicator"


def _http_get_json(url: str) -> object:
    """Perform the actual HTTP GET. Isolated so tests can patch ``requests.get``."""
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=64)
def fetch_indicator_series(indicator_code: str) -> Tuple[Tuple[int, float], ...]:
    """Fetch one World Bank indicator code's full available history for India.

    Returns a tuple of ``(year, value)`` pairs sorted ascending by year.
    The result is cached (by ``indicator_code`` alone) for the lifetime of
    the process, so asking for the same indicator with a different
    ``start``/``end`` window later does not trigger a second HTTP request
    -- callers filter the cached full series locally instead.

    Raises :class:`~india_econ.exceptions.DataFetchError` if the request
    fails, times out, or the response can't be parsed as expected. This
    lets callers catch one specific exception type and fall back to
    synthetic data, rather than guessing which of several network/parsing
    exceptions might occur.
    """
    url = f"{_BASE_URL}/{indicator_code}?format=json&per_page=2000"
    try:
        payload = _http_get_json(url)
    except Exception as exc:  # requests.* exceptions, json decode errors, etc.
        raise DataFetchError(
            f"Live fetch of World Bank indicator '{indicator_code}' failed: {exc}"
        ) from exc

    try:
        records = payload[1]
        if records is None:
            raise DataFetchError(
                f"World Bank API returned no data for indicator '{indicator_code}'."
            )
        points = []
        for row in records:
            value = row.get("value")
            year_str = row.get("date")
            if value is None or year_str is None:
                continue
            points.append((int(year_str), float(value)))
    except DataFetchError:
        raise
    except Exception as exc:
        raise DataFetchError(
            f"Could not parse World Bank response for indicator '{indicator_code}': {exc}"
        ) from exc

    if not points:
        raise DataFetchError(
            f"World Bank API returned zero usable data points for indicator '{indicator_code}'."
        )

    return tuple(sorted(points))


def clear_cache() -> None:
    """Clear the live-fetch cache. Mainly useful for tests."""
    fetch_indicator_series.cache_clear()
