"""Evidence ledger and data validation."""
from __future__ import annotations

import pandas as pd
import pytest

from data_sources import registry, validation


def test_every_data_file_is_registered_and_consistent():
    assert registry.registry_problems() == []


def test_get_and_frame():
    d = registry.get("wil_india")
    assert d.status == "VERIFIED" and d.url.startswith("https://wid.world")
    with pytest.raises(KeyError):
        registry.get("nope")
    f = registry.as_frame()
    assert {"id", "publisher", "status", "limitations", "files"} <= set(f.columns)
    assert f["id"].is_unique


def test_illustrative_and_live_are_labelled():
    assert registry.get("bank_panel_illustrative").status == "ILLUSTRATIVE"
    assert registry.get("worldbank_wdi").status == "LIVE"


def test_check_frame_finds_planted_problems():
    df = pd.DataFrame({
        "state": ["Kerala", "Kerala ", "kerala", "Goa", "Goa"],
        "financial_year": ["2020-21", "2021-22", "2022-23", "2020-21", "2020-22"],
        "income_share": [10, 20, 130, 5, 5],
        "price_level": [100, 110, None, -5, 7],
    })
    found = {(r["check"], r["severity"]) for r in validation.check_frame(df, "t.csv")}
    assert ("name whitespace", "WARN") in found
    assert ("inconsistent names", "WARN") in found
    assert ("period labels", "WARN") in found          # 2020-22 is not a financial year
    assert ("impossible values", "WARN") in found      # share > 100 and negative price
    assert ("missing values", "INFO") in found


def test_clean_frame_reports_ok_and_periods_parse():
    df = pd.DataFrame({"year": [2001, 2002], "value": [1.0, 2.0]})
    assert validation.check_frame(df, "ok.csv")[0]["severity"] == "OK"
    for good in ("2004-05", "1999-00", "2026-08", "Jun-2013", "DEC 2018", "2018-Q2", "1960-2022"):
        assert validation._valid_period(good), good
    assert not validation._valid_period("2004-13")  # neither a financial year nor a month


def test_validate_all_runs_without_errors():
    r = validation.validate_all()
    assert not r.empty and (r["severity"] != "ERROR").all()
