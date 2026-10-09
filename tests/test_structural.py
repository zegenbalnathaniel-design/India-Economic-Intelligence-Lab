"""Tests for analysis/structural.py and the Structural Transformation Lab page.

All frames here are SYNTHETIC test fixtures (round numbers chosen so the
arithmetic is checkable by hand) -- they are never used by the app. The
page tests patch `worldbank._http_get_json`, so no network call is made.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd
import pytest

from analysis import structural as S
from data_sources import registry
from data_sources import worldbank as WB

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "app" / "pages" / "13_Structural_Transformation_Lab.py"


def frame(rows):
    """rows: (iso3, country, code, year, value)."""
    return pd.DataFrame(
        [{"country": c, "iso3": i, "indicator": k, "indicator_name": k, "year": y, "value": v,
          "lastupdated": "2026-07-01", "retrieved_at": "2026-10-09T00:00:00Z"} for i, c, k, y, v in rows],
        columns=WB.TIDY_COLUMNS,
    )


SHARES_2020 = {  # agr 20/50, ind 25/20, srv 45/30 -> VA sum 90, employment sum 100
    "NV.AGR.TOTL.ZS": 20.0, "NV.IND.TOTL.ZS": 25.0, "NV.SRV.TOTL.ZS": 45.0,
    "SL.AGR.EMPL.ZS": 50.0, "SL.IND.EMPL.ZS": 20.0, "SL.SRV.EMPL.ZS": 30.0,
}
SHARES_2010 = {
    "NV.AGR.TOTL.ZS": 25.0, "NV.IND.TOTL.ZS": 26.0, "NV.SRV.TOTL.ZS": 40.0,
    "SL.AGR.EMPL.ZS": 60.0, "SL.IND.EMPL.ZS": 15.0, "SL.SRV.EMPL.ZS": 25.0,
}


def india_frame(extra=()):
    rows = [("IND", "India", k, 2020, v) for k, v in SHARES_2020.items()]
    rows += [("IND", "India", k, 2010, v) for k, v in SHARES_2010.items()]
    rows += list(extra)
    return frame(rows)


# --- Derived productivity ---------------------------------------------------
def test_relative_productivity_published_basis():
    t = S.sector_table(india_frame())
    snap = S.snapshot(t, "IND", 2020).set_index("sector")
    assert snap.loc["Agriculture", "rlp"] == pytest.approx(20 / 50)
    assert snap.loc["Industry", "rlp"] == pytest.approx(25 / 20)
    assert snap.loc["Services", "rlp"] == pytest.approx(45 / 30)
    assert snap.loc["Agriculture", "gap_pp"] == pytest.approx(-30.0)
    # employment-weighted mean equals va_sum / 100 on the published basis
    assert S.weighted_rlp(snap.reset_index()) == pytest.approx(0.90)


def test_share_sums_are_reported_not_rescaled():
    t = S.sector_table(india_frame())
    snap = S.snapshot(t, "IND", 2020)
    assert snap["va_sum"].tolist() == pytest.approx([90.0] * 3)
    assert snap["va_residual"].tolist() == pytest.approx([10.0] * 3)
    assert snap["emp_sum"].tolist() == pytest.approx([100.0] * 3)
    # published shares are untouched
    assert snap.set_index("sector").loc["Agriculture", "va_share"] == 20.0


def test_rescaled_version_is_separate_and_consistent():
    t = S.sector_table(india_frame())
    snap = S.snapshot(t, "IND", 2020).set_index("sector")
    assert snap["va_share_rescaled"].sum() == pytest.approx(100.0)
    assert snap.loc["Agriculture", "va_share_rescaled"] == pytest.approx(100 * 20 / 90)
    assert snap.loc["Agriculture", "rlp_rescaled"] == pytest.approx((100 * 20 / 90) / 50)
    assert S.weighted_rlp(snap.reset_index(), rescaled=True) == pytest.approx(1.0)
    # ratios between sectors do not depend on the basis
    pub = snap.loc["Services", "rlp"] / snap.loc["Agriculture", "rlp"]
    res = snap.loc["Services", "rlp_rescaled"] / snap.loc["Agriculture", "rlp_rescaled"]
    assert pub == pytest.approx(res)


def test_partial_year_gives_no_sum_and_is_not_complete():
    rows = [("IND", "India", k, 2021, v) for k, v in SHARES_2020.items() if k != "NV.IND.TOTL.ZS"]
    t = S.sector_table(india_frame(rows))
    snap = S.snapshot(t, "IND", 2021).set_index("sector")
    assert snap["va_sum"].isna().all() and snap["va_share_rescaled"].isna().all()
    assert math.isnan(snap.loc["Industry", "rlp"])
    assert snap.loc["Agriculture", "rlp"] == pytest.approx(0.4)   # still computable
    assert snap.loc["Agriculture", "emp_sum"] == pytest.approx(100.0)
    assert S.complete_years(t, "IND") == [2010, 2020]


def test_zero_or_missing_employment_gives_nan_not_infinity():
    rows = [("BGD", "Bangladesh", "NV.AGR.TOTL.ZS", 2020, 10.0), ("BGD", "Bangladesh", "SL.AGR.EMPL.ZS", 2020, 0.0),
            ("BGD", "Bangladesh", "NV.IND.TOTL.ZS", 2020, 10.0), ("BGD", "Bangladesh", "SL.IND.EMPL.ZS", 2020, math.nan)]
    snap = S.snapshot(S.sector_table(frame(rows)), "BGD", 2020).set_index("sector")
    assert math.isnan(snap.loc["Agriculture", "rlp"]) and math.isnan(snap.loc["Industry", "rlp"])
    assert math.isnan(snap.loc["Industry", "gap_pp"])


def test_no_interpolation_of_missing_years():
    t = S.sector_table(india_frame())
    assert sorted(t["year"].unique().tolist()) == [2010, 2020]   # 2011-2019 not invented


def test_duplicate_observations_are_rejected():
    df = india_frame([("IND", "India", "NV.AGR.TOTL.ZS", 2020, 21.0)])
    with pytest.raises(ValueError):
        S.sector_table(df)


def test_composition_change_and_missing_endpoint():
    t = S.sector_table(india_frame())
    ch = S.composition_change(t, "IND", 2010, 2020).set_index("sector")
    assert ch.loc["Agriculture", "va_change_pp"] == pytest.approx(-5.0)
    assert ch.loc["Agriculture", "emp_change_pp"] == pytest.approx(-10.0)
    ch2 = S.composition_change(t, "IND", 2010, 2015).set_index("sector")
    assert ch2["va_change_pp"].isna().all()


def test_peak_latest_lfp_and_same_year_pairs():
    df = frame([
        ("IND", "India", S.MANUF, 2000, 15.0), ("IND", "India", S.MANUF, 2005, 17.0),
        ("IND", "India", S.MANUF, 2010, 13.0),
        ("IND", "India", S.LFP_FEMALE, 2010, 25.0), ("IND", "India", S.LFP_MALE, 2010, 75.0),
        ("IND", "India", S.LFP_FEMALE, 2011, 26.0),
        ("IND", "India", S.GDP_PER_WORKER, 2010, 10000.0), ("IND", "India", "SL.AGR.EMPL.ZS", 2010, 50.0),
        ("IND", "India", S.GDP_PER_WORKER, 2011, 11000.0),   # no agri value in 2011 -> not paired
    ])
    p = S.peak_and_latest(df, S.MANUF, "IND")
    assert (p["peak_year"], p["latest_year"], p["change_from_peak_pp"]) == (2005, 2010, pytest.approx(-4.0))
    assert S.peak_and_latest(df, S.MANUF, "CHN") is None
    lfp = S.lfp_table(df).set_index("year")
    assert lfp.loc[2010, "gap_pp"] == pytest.approx(50.0) and math.isnan(lfp.loc[2011, "gap_pp"])
    pair = S.latest_pair(df, S.GDP_PER_WORKER, "SL.AGR.EMPL.ZS").iloc[0]
    assert pair["year"] == 2010 and pair["x"] == 10000.0 and pair["y"] == 50.0


# --- Findings ---------------------------------------------------------------
def test_findings_text_from_synthetic_frame():
    extra = [
        ("IND", "India", S.MANUF, 2010, 17.0), ("IND", "India", S.MANUF, 2020, 14.0),
        ("IND", "India", S.LFP_FEMALE, 2020, 25.0), ("IND", "India", S.LFP_MALE, 2020, 75.0),
        ("IND", "India", S.VULNERABLE, 2020, 70.0),
    ]
    fs = S.findings(india_frame(extra), "IND")
    assert fs[0] == ("In 2020, agriculture employed 50.0% of workers in India but produced 20.0% of GDP as "
                     "value added — a gap of -30.0 percentage points.")
    assert fs[1].startswith("In 2020, value added per worker in services was 3.8× that in agriculture, "
                            "and in industry 3.1×")
    assert "sum to 90.0% of GDP; the remaining 10.0%" in fs[2]
    assert fs[3] == ("Agriculture's share of employment went from 60.0% in 2010 to 50.0% in 2020 (-10.0 pp), "
                     "while its value-added share went from 25.0% to 20.0% (-5.0 pp).")
    assert fs[4] == ("Manufacturing value added was 14.0% of GDP in 2020, -3.0 pp from its highest level in the "
                     "selected years (17.0% in 2010).")
    assert "25.0% of women aged 15+ in India were in the labour force against 75.0% of men — a gap of 50.0 pp" in fs[5]
    assert fs[6].startswith("In 2020, 70.0% of India's workers were in vulnerable employment")
    assert len(fs) == 7


def test_findings_only_from_available_data():
    assert S.findings(frame([]), "IND") == []
    only_vuln = frame([("IND", "India", S.VULNERABLE, 2019, 72.5)])
    fs = S.findings(only_vuln, "IND")
    assert len(fs) == 1 and "72.5%" in fs[0] and "2019" in fs[0]


# --- Downloads, catalogue, registry -----------------------------------------
def test_csv_header_round_trip():
    t = S.sector_table(india_frame())
    text = S.csv_with_header(t, {"years": (2010, 2020), "countries": ("IND", "CHN")}, "test")
    assert text.startswith("# test\n# years: [2010, 2020]\n# countries: [\"IND\", \"CHN\"]\n# indicators:")
    back = pd.read_csv(io.StringIO(text), comment="#")
    assert list(back.columns) == S.SHARE_COLUMNS and len(back) == len(t)
    rec = S.settings_record({"years": (2010, 2020)})
    assert json.loads(json.dumps(rec))["indicators"] == list(S.CODES)


def test_catalogue_and_registry():
    assert len(S.CODES) == 11
    for code, m in S.INDICATORS.items():
        assert m.code == code and m.change_kind in WB.CHANGE_KINDS and m.definition and m.source_note
    for code in ("SL.AGR.EMPL.ZS", "SL.TLF.CACT.FE.ZS", "SL.EMP.VULN.ZS"):
        assert "ILO modelled" in S.INDICATORS[code].label
    assert registry.get("wdi_structural").status == "LIVE"
    assert registry.get("state_sectoral_gva").status == "DATA REQUIRED"
    assert registry.get("plfs_state_industry").status == "DATA REQUIRED"
    assert registry.registry_problems() == []


# --- Page smoke tests (AppTest, mocked API) ---------------------------------
def _synthetic_value(code: str, iso3: str, year: int) -> float | None:
    k = {"IND": 0, "CHN": 1, "IDN": 2, "BGD": 3, "VNM": 4}.get(iso3, 5)
    t = year - 2000
    vals = {
        "NV.AGR.TOTL.ZS": 25 - 0.5 * t - k, "NV.IND.TOTL.ZS": 28 + 0.2 * t + k,
        "NV.IND.MANF.ZS": 16 + (0.3 * t if t < 4 else 1.2 - 0.2 * (t - 4)) + k,
        "NV.SRV.TOTL.ZS": 38 + 0.3 * t, "SL.AGR.EMPL.ZS": 58 - t - k, "SL.IND.EMPL.ZS": 18 + 0.4 * t,
        "SL.SRV.EMPL.ZS": 24 + 0.6 * t + k, "SL.TLF.CACT.FE.ZS": 30 - 0.2 * t + 3 * k,
        "SL.TLF.CACT.MA.ZS": 78 - 0.1 * t, "SL.GDP.PCAP.EM.KD": 8000 * (1.05 ** t) * (1 + k),
        "SL.EMP.VULN.ZS": 75 - 0.5 * t - k,
    }
    if code == "SL.EMP.VULN.ZS" and year == 2003:
        return None  # an API null: must stay a gap
    return round(vals[code], 3)


def _fake_api(url, timeout):
    p = urlparse(url)
    parts = unquote(p.path).split("/")
    countries = parts[parts.index("country") + 1].split(";")
    code = parts[parts.index("indicator") + 1]
    lo, hi = (int(x) for x in parse_qs(p.query)["date"][0].split(":"))
    rows = []
    for iso in countries:
        for y in range(max(lo, 2000), min(hi, 2008) + 1):
            rows.append({"indicator": {"id": code, "value": f"{code} (synthetic test)"},
                         "country": {"id": iso[:2], "value": iso.title()}, "countryiso3code": iso,
                         "date": str(y), "value": _synthetic_value(code, iso, y),
                         "unit": "", "obs_status": "", "decimal": 1})
    return [{"page": 1, "pages": 1, "per_page": 20000, "total": len(rows),
             "sourceid": "2", "lastupdated": "2026-07-01"}, rows]


def _offline_api(url, timeout):
    raise WB.WorldBankConnectionError(f"Could not reach {url}: blocked in test")


def _app(monkeypatch, fake):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from app.components import freshness

    freshness.reload_stale_modules()  # mark modules current so the page does not reload away the patch
    monkeypatch.setattr(WB, "_http_get_json", fake)
    st.cache_data.clear()
    return AppTest.from_file(str(PAGE), default_timeout=200)


def _all_text(at) -> str:
    parts = []
    for kind in ("markdown", "error", "warning", "info", "caption", "header", "title"):
        parts += [str(e.value) for e in getattr(at, kind)]
    return "\n".join(parts)


def test_page_renders_with_mocked_data_and_widgets(monkeypatch):
    at = _app(monkeypatch, _fake_api).run()
    assert not at.exception, at.exception
    text = _all_text(at)
    assert "DATA UNAVAILABLE — the World Bank API" not in text
    assert "In 2008, agriculture employed 50.0% of workers in Ind but produced 21.0% of GDP" in text
    assert "DATA REQUIRED" in text
    assert len(at.get("plotly_chart")) >= 9
    assert len(at.get("download_button")) == 3

    at.toggle(key="st_rescaled").set_value(True).run()
    assert not at.exception, at.exception
    assert any("DERIVED" in str(c) for d in at.dataframe for c in d.value.columns)
    at.selectbox(key="st_focus").set_value("CHN").run()
    assert not at.exception, at.exception
    at.select_slider(key="st_year_CHN").set_value(2004).run()
    assert not at.exception, at.exception
    at.select_slider(key="st_comp_years_CHN").set_value((2002, 2006)).run()
    assert not at.exception, at.exception
    at.toggle(key="st_paths").set_value(False).run()
    assert not at.exception, at.exception
    at.multiselect(key="st_peers").set_value([]).run()
    assert not at.exception, at.exception
    assert "Choose at least one peer economy" in _all_text(at)


def test_page_renders_offline_without_numbers(monkeypatch):
    at = _app(monkeypatch, _offline_api).run()
    assert not at.exception, at.exception
    errors = " ".join(str(e.value) for e in at.error)
    assert "DATA UNAVAILABLE — the World Bank API could not be reached" in errors
    assert "DATA REQUIRED" in errors
    text = _all_text(at)
    assert "What is structural transformation?" in text and "Relative labour productivity" in text
    assert "state_gsva_by_sector.csv" in text
    assert "In 20" not in text                      # no generated findings
    assert len(at.get("plotly_chart")) == 0          # no charts without data
    assert len(at.get("download_button")) == 0
    at.toggle(key="st_rescaled").set_value(True).run()
    assert not at.exception, at.exception
