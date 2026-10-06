"""Shared pytest fixtures for the india_econ test suite."""

from __future__ import annotations

import pytest

from india_econ._worldbank import fetch_indicator_series


@pytest.fixture(autouse=True)
def _clear_worldbank_cache():
    """Every test starts with a clean lru_cache so tests don't bleed into each other."""
    fetch_indicator_series.cache_clear()
    yield
    fetch_indicator_series.cache_clear()
