"""Tests for the live World Bank fetch path, the fallback trigger, and caching.

These never touch the real network -- ``requests.get`` is monkeypatched
with a counting stand-in so the tests work the same whether or not the
sandbox they run in has outbound internet access.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

import india_econ as ie
from india_econ import _worldbank
from india_econ.exceptions import DataFetchError


def _fake_response(points):
    """Build a Mock that looks like requests.Response for a WB API call."""
    records = [{"value": str(v), "date": str(y)} for y, v in points]
    payload = [{"page": 1, "pages": 1}, records]
    response = Mock()
    response.raise_for_status = Mock()
    response.json = Mock(return_value=payload)
    return response


def test_live_fetch_success_sets_status_live(monkeypatch):
    points = [(2018, 6.0), (2019, 6.2), (2020, 5.9)]
    mock_get = Mock(return_value=_fake_response(points))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    result = ie.inflation(allow_live=True)

    assert result.source == "live"
    assert mock_get.call_count == 1
    assert list(result.data.index) == [2018, 2019, 2020]
    assert result.data.loc[2019] == 6.2


def test_live_fetch_failure_falls_back_to_synthetic(monkeypatch):
    mock_get = Mock(side_effect=ConnectionError("blocked by sandbox proxy"))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    result = ie.inflation(allow_live=True)

    assert result.source == "synthetic"
    assert "fallback" in result.metadata["note"].lower()


def test_allow_live_false_never_calls_requests(monkeypatch):
    mock_get = Mock(return_value=_fake_response([(2020, 1.0)]))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    result = ie.inflation(allow_live=False)

    assert result.source == "synthetic"
    mock_get.assert_not_called()


def test_fetch_indicator_series_is_cached(monkeypatch):
    mock_get = Mock(return_value=_fake_response([(2020, 1.0), (2021, 2.0)]))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    first = _worldbank.fetch_indicator_series("FP.CPI.TOTL.ZG")
    second = _worldbank.fetch_indicator_series("FP.CPI.TOTL.ZG")

    assert first == second
    assert mock_get.call_count == 1  # second call served from lru_cache


def test_cache_is_keyed_per_indicator_code(monkeypatch):
    mock_get = Mock(return_value=_fake_response([(2020, 1.0)]))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    _worldbank.fetch_indicator_series("FP.CPI.TOTL.ZG")
    _worldbank.fetch_indicator_series("SL.UEM.TOTL.ZS")

    assert mock_get.call_count == 2  # different codes are not shared in the cache


def test_two_public_calls_for_same_indicator_only_fetch_once(monkeypatch):
    mock_get = Mock(return_value=_fake_response([(2020, 1.0), (2021, 2.0)]))
    monkeypatch.setattr(_worldbank.requests, "get", mock_get)

    ie.inflation(start=2020, end=2021, allow_live=True)
    ie.inflation(start=2020, end=2020, allow_live=True)  # different window, same code

    assert mock_get.call_count == 1


def test_malformed_response_raises_data_fetch_error(monkeypatch):
    bad_response = Mock()
    bad_response.raise_for_status = Mock()
    bad_response.json = Mock(return_value={"not": "the expected list shape"})
    monkeypatch.setattr(_worldbank.requests, "get", Mock(return_value=bad_response))

    with pytest.raises(DataFetchError):
        _worldbank.fetch_indicator_series("FP.CPI.TOTL.ZG")


def test_empty_data_raises_data_fetch_error(monkeypatch):
    monkeypatch.setattr(_worldbank.requests, "get", Mock(return_value=_fake_response([])))

    with pytest.raises(DataFetchError):
        _worldbank.fetch_indicator_series("FP.CPI.TOTL.ZG")
