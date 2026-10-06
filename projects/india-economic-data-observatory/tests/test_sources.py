import pandas as pd
import pytest

from data_observatory import sources


class _FakeResponse:
    def __init__(self, status_code=200, json_payload=None, content=b""):
        self.status_code = status_code
        self._json_payload = json_payload
        self.content = content

    def json(self):
        return self._json_payload


def test_fetch_world_bank_indicator_parses_valid_payload(monkeypatch):
    payload = [
        {"page": 1, "pages": 1, "per_page": 50, "total": 2},
        [
            {"date": "2001", "value": 5.0},
            {"date": "2000", "value": 4.0},
        ],
    ]

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(200, payload)

    monkeypatch.setattr(sources.requests, "get", fake_get)
    series = sources.fetch_world_bank_indicator("NY.GDP.MKTP.CD", "2000", "2001")
    assert series is not None
    assert series.index.is_monotonic_increasing
    assert list(series.values) == [4.0, 5.0]


def test_fetch_world_bank_indicator_handles_non_200(monkeypatch):
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(500, None))
    assert sources.fetch_world_bank_indicator("NY.GDP.MKTP.CD", "2000", "2001") is None


def test_fetch_world_bank_indicator_handles_malformed_payload(monkeypatch):
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(200, {"message": "bad request"}))
    assert sources.fetch_world_bank_indicator("BAD.CODE", "2000", "2001") is None


def test_fetch_world_bank_indicator_handles_empty_observations(monkeypatch):
    payload = [{"page": 1}, []]
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(200, payload))
    assert sources.fetch_world_bank_indicator("NY.GDP.MKTP.CD", "2000", "2001") is None


def test_fetch_world_bank_indicator_handles_exception(monkeypatch):
    def _raise(*a, **k):
        raise ConnectionError("no network")

    monkeypatch.setattr(sources.requests, "get", _raise)
    assert sources.fetch_world_bank_indicator("NY.GDP.MKTP.CD", "2000", "2001") is None


def test_fetch_world_bank_indicator_skips_null_values(monkeypatch):
    payload = [
        {"page": 1},
        [
            {"date": "2000", "value": None},
            {"date": "2001", "value": 3.0},
        ],
    ]
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(200, payload))
    series = sources.fetch_world_bank_indicator("NY.GDP.MKTP.CD", "2000", "2001")
    assert list(series.values) == [3.0]


def test_probe_rbi_dbie_returns_none_on_exception(monkeypatch):
    def _raise(*a, **k):
        raise ConnectionError("blocked")

    monkeypatch.setattr(sources.requests, "get", _raise)
    assert sources.probe_rbi_dbie() is None


def test_probe_mospi_returns_none_on_non_200(monkeypatch):
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(403, None))
    assert sources.probe_mospi() is None


def test_probe_mospi_returns_content_on_success(monkeypatch):
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResponse(200, None, content=b"<html></html>"))
    assert sources.probe_mospi() == b"<html></html>"
