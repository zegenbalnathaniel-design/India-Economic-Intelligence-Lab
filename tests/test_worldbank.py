"""Tests for data_sources/worldbank.py.

The live API is never called: `_http_get_json` / `urlopen` are patched
with payloads shaped like the documented v2 JSON schema, so these tests
check parsing, error mapping and the change arithmetic only.
"""
from __future__ import annotations

import io
import math
import socket
import urllib.error
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from data_sources import worldbank as WB


def obs(iso3, year, value, code="NY.GDP.MKTP.KD.ZG", name="India"):
    return {
        "indicator": {"id": code, "value": "GDP growth (annual %)"},
        "country": {"id": iso3[:2], "value": name},
        "countryiso3code": iso3,
        "date": str(year),
        "value": value,
        "unit": "", "obs_status": "", "decimal": 1,
    }


def page(rows, page_no=1, pages=1, total=None):
    return [
        {"page": page_no, "pages": pages, "per_page": 20000,
         "total": len(rows) if total is None else total,
         "sourceid": "2", "lastupdated": "2026-07-01"},
        rows,
    ]


# --- URL ------------------------------------------------------------------
def test_build_url_shape():
    url = WB.build_url("FP.CPI.TOTL.ZG", ["ind", "chn"], 2000, 2024, page=2)
    p = urlparse(url)
    assert p.path == "/v2/country/IND%3BCHN/indicator/FP.CPI.TOTL.ZG" or p.path == "/v2/country/IND;CHN/indicator/FP.CPI.TOTL.ZG"
    q = parse_qs(p.query)
    assert q["format"] == ["json"] and q["date"] == ["2000:2024"] and q["page"] == ["2"]


def test_build_url_rejects_bad_input():
    with pytest.raises(ValueError):
        WB.build_url("X", [], 2000, 2001)
    with pytest.raises(ValueError):
        WB.build_url("X", ["IND"], 2010, 2000)


# --- Parsing ---------------------------------------------------------------
def test_parse_valid_page_keeps_null_as_nan():
    meta, rows = WB.parse_response(page([obs("IND", 2023, 8.2), obs("IND", 2024, None)]))
    assert meta["total"] == 2 and meta["lastupdated"] == "2026-07-01"
    assert rows[0]["value"] == 8.2 and rows[0]["year"] == 2023 and rows[0]["iso3"] == "IND"
    assert math.isnan(rows[1]["value"])  # missing is never zero


def test_parse_api_error_message():
    payload = [{"message": [{"id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid"}]}]
    with pytest.raises(WB.WorldBankAPIError, match="120"):
        WB.parse_response(payload)


def test_parse_null_data_with_zero_total_is_empty():
    meta, rows = WB.parse_response([{"page": 1, "pages": 0, "total": 0}, None])
    assert rows == [] and meta["total"] == 0


@pytest.mark.parametrize("payload", [
    {},                                                    # not a list
    [],                                                    # empty
    [{"page": 1, "pages": 1, "total": 1}],                 # missing data element
    [{"page": 1, "pages": 1}, []],                         # metadata missing total
    [{"page": 1, "pages": 1, "total": 3}, None],           # null data but total > 0
    page([{**obs("IND", 2023, 1.0), "date": "2023Q1"}]),   # non-annual date
    page([{**obs("IND", 2023, 1.0), "value": "abc"}]),     # non-numeric value
    page([{**obs("IND", 2023, 1.0), "value": True}]),      # boolean value
])
def test_parse_schema_errors(payload):
    with pytest.raises(WB.WorldBankSchemaError):
        WB.parse_response(payload)


# --- Fetch -----------------------------------------------------------------
def test_fetch_follows_pagination_and_returns_tidy_frame(monkeypatch):
    calls = []

    def fake(url, timeout):
        calls.append(url)
        n = int(parse_qs(urlparse(url).query)["page"][0])
        rows = [obs("IND", 2020 + n, float(n))]
        return page(rows, page_no=n, pages=2, total=2)

    monkeypatch.setattr(WB, "_http_get_json", fake)
    df = WB.fetch("NY.GDP.MKTP.KD.ZG", "ind", 2020, 2024)
    assert len(calls) == 2
    assert list(df.columns) == WB.TIDY_COLUMNS
    assert df["year"].tolist() == [2021, 2022] and df["value"].tolist() == [1.0, 2.0]
    assert df["lastupdated"].eq("2026-07-01").all() and df["retrieved_at"].notna().all()


def test_fetch_is_all_or_nothing(monkeypatch):
    def fake(url, timeout):
        if "FP.CPI" in url:
            raise WB.WorldBankTimeoutError("timed out")
        return page([obs("IND", 2023, 7.0)])

    monkeypatch.setattr(WB, "_http_get_json", fake)
    with pytest.raises(WB.WorldBankTimeoutError):
        WB.fetch(["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG"], ["IND"], 2020, 2024)


def test_fetch_requires_codes_and_countries():
    with pytest.raises(ValueError):
        WB.fetch([], ["IND"], 2000, 2001)
    with pytest.raises(ValueError):
        WB.fetch(["X"], [" "], 2000, 2001)


# --- HTTP error mapping ----------------------------------------------------
def _patch_urlopen(monkeypatch, exc=None, body=b""):
    class Resp(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout):
        if exc is not None:
            raise exc
        return Resp(body)

    monkeypatch.setattr(WB.urllib.request, "urlopen", fake)


def test_timeout_maps_to_timeout_error(monkeypatch):
    _patch_urlopen(monkeypatch, urllib.error.URLError(socket.timeout("timed out")))
    with pytest.raises(WB.WorldBankTimeoutError):
        WB._http_get_json("https://example.invalid")


def test_unreachable_maps_to_connection_error(monkeypatch):
    _patch_urlopen(monkeypatch, urllib.error.URLError("Name or service not known"))
    with pytest.raises(WB.WorldBankConnectionError):
        WB._http_get_json("https://example.invalid")
    assert WB.WorldBankConnectionError in WB.NETWORK_ERRORS


def test_http_status_maps_to_http_error(monkeypatch):
    _patch_urlopen(monkeypatch, urllib.error.HTTPError("u", 503, "Service Unavailable", None, None))
    with pytest.raises(WB.WorldBankHTTPError) as ei:
        WB._http_get_json("https://example.invalid")
    assert ei.value.status == 503


def test_non_json_body_is_schema_error_and_bom_is_tolerated(monkeypatch):
    _patch_urlopen(monkeypatch, body=b"<html>maintenance</html>")
    with pytest.raises(WB.WorldBankSchemaError):
        WB._http_get_json("https://example.invalid")
    _patch_urlopen(monkeypatch, body="﻿[1]".encode("utf-8"))
    assert WB._http_get_json("https://example.invalid") == [1]


# --- latest_vs_previous ----------------------------------------------------
def _frame(rows):
    return pd.DataFrame(
        [{"country": c, "iso3": i, "indicator": k, "indicator_name": "", "year": y, "value": v,
          "lastupdated": None, "retrieved_at": None} for c, i, k, y, v in rows],
        columns=WB.TIDY_COLUMNS,
    )


def test_lvp_rate_series_reports_pp_not_percent():
    df = _frame([("India", "IND", "FP.CPI.TOTL.ZG", 2022, 6.7), ("India", "IND", "FP.CPI.TOTL.ZG", 2023, 5.4)])
    r = WB.latest_vs_previous(df).iloc[0]
    assert r["change_kind"] == "pp" and r["pp_change"] == pytest.approx(-1.3)
    assert math.isnan(r["pct_change"])


def test_lvp_level_series_reports_percent():
    df = _frame([("India", "IND", "FI.RES.TOTL.CD", 2022, 200.0), ("India", "IND", "FI.RES.TOTL.CD", 2023, 250.0)])
    r = WB.latest_vs_previous(df).iloc[0]
    assert r["pct_change"] == pytest.approx(25.0) and math.isnan(r["pp_change"])


def test_lvp_skips_missing_years_and_handles_single_obs():
    df = _frame([
        ("India", "IND", "SI.POV.GINI", 2011, 35.7), ("India", "IND", "SI.POV.GINI", 2015, float("nan")),
        ("India", "IND", "SI.POV.GINI", 2021, 32.8),
        ("China", "CHN", "SI.POV.GINI", 2020, 37.1),
        ("Brazil", "BRA", "SI.POV.GINI", 2020, float("nan")),
    ])
    out = WB.latest_vs_previous(df).set_index("iso3")
    assert int(out.loc["IND", "previous_year"]) == 2011  # null 2015 skipped
    assert out.loc["IND", "abs_change"] == pytest.approx(-2.9)
    assert math.isnan(out.loc["IND", "pct_change"])        # points: no % change
    assert pd.isna(out.loc["CHN", "previous_year"]) and math.isnan(out.loc["CHN", "abs_change"])
    assert "BRA" not in out.index                          # all-null group omitted


def test_lvp_no_percent_from_non_positive_base():
    df = _frame([("India", "IND", "FI.RES.TOTL.CD", 2022, 0.0), ("India", "IND", "FI.RES.TOTL.CD", 2023, 5.0)])
    assert math.isnan(WB.latest_vs_previous(df).iloc[0]["pct_change"])


def test_unknown_indicator_defaults_to_points():
    assert WB.change_kind_for("SOME.UNKNOWN") == "points"
    with pytest.raises(ValueError):
        WB.change_kind_for("X", {"X": "bogus"})


def test_catalogue_is_consistent():
    assert WB.INDIA not in WB.PEER_COUNTRIES
    assert set(WB.DEFAULT_PEERS) <= set(WB.PEER_COUNTRIES)
    for code, m in WB.INDICATORS.items():
        assert m.code == code and m.change_kind in WB.CHANGE_KINDS and m.definition and m.source_note
