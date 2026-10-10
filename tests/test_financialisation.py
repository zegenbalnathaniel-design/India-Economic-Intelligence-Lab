"""Tests for analysis/financialisation.py, data_sources/wdi_financial.py,
data_sources/financialisation_uploads.py and the Lab page.

The World Bank API is never called: fetchers are stubbed, and the page
smoke test patches `urllib.request.urlopen`. Numbers in stubs are test
fixtures exercising code paths -- they are not data and never ship.
"""
from __future__ import annotations

import math
import subprocess
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from analysis import financialisation as F, inequality
from data_sources import financialisation_uploads as UP, loaders, registry, wdi_financial as WF, worldbank as WB

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inc():
    return loaders.load_wil_income_shares()


@pytest.fixture(scope="module")
def wlth():
    return loaders.load_wil_wealth_shares()


@pytest.fixture(scope="module")
def paper():
    return loaders.load_paper_a_returns()


# --- A. Lorenz / concentration ----------------------------------------------
def test_lorenz_table_points_match_published_shares(inc):
    lz = F.lorenz_table(inc, [2022])
    assert list(lz["pop_share"]) == list(F.LORENZ_BREAKS)
    r = inc.set_index("year").loc[2022]
    pts = dict(zip(lz["pop_share"], lz["cum_share"]))
    assert pts[0.5] == pytest.approx(r["bottom_50"] / 100)
    assert pts[0.9] == pytest.approx((r["bottom_50"] + r["middle_40"]) / 100)
    assert pts[0.99] == pytest.approx(1 - r["top_1"] / 100)
    assert pts[0.999] == pytest.approx(1 - r["top_0_1"] / 100)
    assert lz["cum_share"].is_monotonic_increasing


def test_lorenz_table_unknown_year_is_not_filled(wlth):
    with pytest.raises(KeyError):
        F.lorenz_table(wlth, [1965])  # between survey years -- never interpolated


def test_lorenz_table_flags_tentative(wlth):
    lz = F.lorenz_table(wlth, [2022, 2023])
    assert not lz.loc[lz["year"] == 2022, "tentative"].any()
    assert lz.loc[lz["year"] == 2023, "tentative"].all()


def test_lorenz_area_matches_gini_lower_bound(inc):
    lz = F.lorenz_table(inc, [1990])
    x, y = lz["pop_share"].to_numpy(), lz["cum_share"].to_numpy()
    area = sum((x[i + 1] - x[i]) * (y[i] + y[i + 1]) / 2 for i in range(len(x) - 1))
    g = inequality.gini_series(inc).set_index("year").loc[1990, "gini_lower_bound"]
    assert 1 - 2 * area == pytest.approx(g)


def test_partition_gap_is_rounding_only(inc, wlth):
    assert F.partition_gap(inc)["sum_minus_100_pp"].abs().max() <= 0.2
    assert F.partition_gap(wlth)["sum_minus_100_pp"].abs().max() <= 0.2


def test_concentration_compare_uses_common_years_only(inc, wlth):
    firm = wlth[~wlth["tentative"]]
    cc = F.concentration_compare(inc, firm)
    assert set(cc["year"]) == set(inc["year"]) & set(firm["year"])
    assert 2023 not in set(cc["year"]) and 1951 not in set(cc["year"])
    r = cc.set_index("year").loc[2022]
    assert r["income_top_10"] == 57.7 and r["wealth_top_10"] == 65.0
    assert r["top_10_gap_pp"] == pytest.approx(7.3)
    assert r["gini_gap"] == pytest.approx(r["wealth_gini_lb"] - r["income_gini_lb"])


# --- B. Composition ------------------------------------------------------------
def test_composition_table_from_paper_a(paper):
    c = F.composition_table(paper).set_index("asset")
    assert list(c.index) == F.COMPOSITION_ORDER
    assert c["share_pct"].to_dict() == {"Residential property": 77, "Gold": 11, "Durable goods": 7,
                                        "Financial assets": 5}
    assert F.composition_sum(c.reset_index()) == 100
    assert math.isnan(c.loc["Durable goods", "return_pct"])  # negative, no figure -- never 0
    assert "negative" in c.loc["Durable goods", "return_text"]
    assert c.loc["Residential property", "return_pct"] == 9.3


def test_portfolio_return_bounds_bracket_stated(paper):
    b = F.portfolio_return_bounds(paper)
    assert b["weight_base_pct"] == 93
    assert b["lower_all_deposits"] == pytest.approx((77 * 9.3 + 11 * 9.2 + 5 * 6.5) / 93)
    assert b["upper_all_equity"] == pytest.approx((77 * 9.3 + 11 * 9.2 + 5 * 13.5) / 93)
    assert b["lower_all_deposits"] <= b["stated"] <= b["upper_all_equity"]


# --- C/D. WDI helpers ----------------------------------------------------------
def _tidy(code, values, iso3="IND"):
    return pd.DataFrame([{"country": "X", "iso3": iso3, "indicator": code, "indicator_name": code, "year": y,
                          "value": v, "lastupdated": "t", "retrieved_at": "t"} for y, v in values.items()])


def test_wdi_series_drops_missing_and_filters():
    df = pd.concat([_tidy("A", {2011: 1.0, 2012: float("nan"), 2014: 3.0}), _tidy("A", {2011: 9.0}, iso3="CHN")])
    s = F.wdi_series(df, "A")
    assert s.to_dict() == {2011: 1.0, 2014: 3.0}
    assert F.wdi_series(None, "A").empty and F.wdi_series(df, "B").empty


def test_change_summary_and_gap():
    assert F.change_summary(pd.Series({2011: 10.0})) is None
    ch = F.change_summary(pd.Series({2014: 20.0, 2011: 10.0, 2017: 25.0}))
    assert ch == {"first_year": 2011, "first": 10.0, "last_year": 2017, "last": 25.0, "change": 15.0, "n_obs": 3}
    gap = F.participation_gap(pd.Series({2011: 40.0, 2014: 60.0, 2017: 80.0}), pd.Series({2011: 20.0, 2017: 70.0}))
    assert gap["year"].tolist() == [2011, 2017]  # 2014 has no poorest-40% value: not filled
    assert gap["gap_pp"].tolist() == [20.0, 10.0]


# --- E. Alignment & statistics -------------------------------------------------
def test_align_two_outer_join_without_interpolation():
    a = pd.Series({2000: 1.0, 2001: 2.0, 2003: 4.0})
    b = pd.Series({2001: 10.0, 2002: 20.0, 2003: 30.0, 2010: 99.0})
    al = F.align_two(a, b, 2000, 2005, names=("a", "b"))
    assert al["year"].tolist() == [2000, 2001, 2002, 2003]
    assert math.isnan(al.set_index("year").loc[2002, "a"])
    assert al["both_observed"].tolist() == [False, True, False, True]
    same = F.align_two(a, a, 2000, 2005, names=("x", "x"))
    assert list(same.columns) == ["year", "x", "x (2)", "both_observed"]


def test_pearson_requires_min_n_and_variation():
    al = F.align_two(pd.Series({y: float(y) for y in range(2000, 2004)}),
                     pd.Series({y: float(y) ** 2 for y in range(2000, 2004)}), 2000, 2010)
    assert F.pearson(al) is None  # n = 4 < 5
    al = F.align_two(pd.Series({y: float(y) for y in range(2000, 2010)}),
                     pd.Series({y: -2.0 * y for y in range(2000, 2010)}), 2000, 2010)
    r = F.pearson(al)
    assert r["r"] == pytest.approx(-1.0) and r["n"] == 10
    flat = F.align_two(pd.Series({y: 1.0 for y in range(2000, 2010)}),
                       pd.Series({y: float(y) for y in range(2000, 2010)}), 2000, 2010)
    assert F.pearson(flat) is None


def test_first_differences_skip_gaps():
    a = pd.Series({2000: 1.0, 2001: 3.0, 2002: 6.0, 2005: 7.0, 2006: 9.0})
    b = pd.Series({2000: 10.0, 2001: 11.0, 2002: 13.0, 2005: 20.0, 2006: 18.0})
    d = F.first_differences(F.align_two(a, b, 2000, 2010, names=("a", "b")))
    assert d["year"].tolist() == [2001, 2002, 2006]  # 2002 -> 2005 crosses a gap
    assert d["a"].tolist() == [2.0, 3.0, 2.0] and d["b"].tolist() == [1.0, 2.0, -2.0]


def test_overlap_change():
    al = F.align_two(pd.Series({2000: 1.0, 2005: 3.0, 2010: 7.0}), pd.Series({2005: 10.0, 2010: 12.0, 2011: 1.0}),
                     1990, 2020, names=("a", "b"))
    ch = F.overlap_change(al)
    assert (ch["first_year"], ch["last_year"], ch["n_common"]) == (2005, 2010, 2)
    assert ch["a_change"] == 4.0 and ch["b_change"] == 2.0
    assert F.overlap_change(F.align_two(pd.Series({2000: 1.0}), pd.Series({2001: 1.0}), 1990, 2020)) is None


def test_wil_catalogue_excludes_tentative(inc, wlth):
    cat = F.wil_catalogue(inc, wlth, loaders.load_wil_vhnwi())
    assert 2023 not in cat["WIL wealth share · Top 1%"]["series"].index
    assert 2023 in F.wil_catalogue(inc, wlth, include_tentative=True)["WIL wealth share · Top 1%"]["series"].index
    assert cat["WIL income share · Top 10%"]["series"].loc[2022] == 57.7
    assert cat["Forbes billionaires' wealth, % of NNI"]["series"].notna().all()


# --- F. Findings -------------------------------------------------------------------
def test_findings_offline_state_says_unavailable(inc, wlth, paper):
    f = F.build_findings(inc, wlth, F.composition_table(paper), wdi_status="DATA UNAVAILABLE")
    assert tuple(f) == F.FINDING_SECTIONS
    text = " ".join(sum(f.values(), []))
    assert "DATA UNAVAILABLE" in text
    assert "57.7%" in text and "40.1%" in text   # WIL values flow through
    assert "Account ownership" in text and "r =" not in text


def test_findings_with_series_are_built_from_inputs(inc, wlth, paper):
    acct = {"total": pd.Series({2011: 30.0, 2021: 70.0}), "poorest_40": pd.Series({2011: 20.0, 2021: 65.0}),
            "richest_60": pd.Series({2011: 40.0, 2021: 75.0})}
    mcap = pd.Series({y: 50.0 + (y - 2002) * (1 + (y % 3)) for y in range(2002, 2023)})
    al = F.align_two(mcap, wlth[~wlth["tentative"]].set_index("year")["top_1"], 2002, 2022)
    mv = {"change": F.overlap_change(al), "corr": F.pearson(al), "corr_diff": F.pearson(F.first_differences(al))}
    f = F.build_findings(inc, wlth, F.composition_table(paper), account=acct, market_vs_top1=mv)
    stat = " ".join(f["Statistical results"])
    assert "20.0 pp in 2011 → 10.0 pp in 2021 (-10.0 pp)" in stat
    assert f"r = {mv['corr']['r']:.2f} (n = {mv['corr']['n']})" in stat
    assert any("broadened" in s for s in f["Interpretation"])
    assert any("not evidence of a causal" in s for s in f["Interpretation"])
    assert len(f["Hypotheses requiring further testing"]) >= 2


# --- WDI per-series fetch ------------------------------------------------------------
def test_fetch_each_reports_status_per_series():
    def fake(code, countries, start, end):
        if code == "BAD":
            raise WB.WorldBankAPIError([{"id": "120", "key": "Invalid value", "value": "x"}])
        if code == "EMPTY":
            return _tidy(code, {2011: float("nan")})
        return _tidy(code, {2011: 1.0, 2014: 2.0})

    r = WF.fetch_each(["GOOD", "BAD", "EMPTY"], fetch=fake)
    assert [r[c].status for c in r] == [WF.OK, WF.API_ERROR, WF.NO_DATA]
    t = WF.status_table(r)
    assert t.loc[0, "observations"] == 2 and t.loc[0, "first_year"] == 2011 and t.loc[0, "latest_year"] == 2014
    assert pd.isna(t.loc[1, "latest_year"]) and "WorldBankAPIError" in t.loc[1, "detail"]
    assert not WF.all_unreachable(r)
    assert set(WF.combined_frame(r)["indicator"]) == {"GOOD"}


def test_fetch_each_stops_after_unreachable():
    calls = []

    def down(code, *a):
        calls.append(code)
        raise WB.WorldBankConnectionError("no route")

    r = WF.fetch_each(["A", "B", "C"], fetch=down)
    assert calls == ["A"]
    assert [x.status for x in r.values()] == [WF.UNREACHABLE, WF.NOT_ATTEMPTED, WF.NOT_ATTEMPTED]
    assert WF.all_unreachable(r) and WF.combined_frame(r).empty


def test_wdi_catalogue_codes():
    assert set(WF.ACCOUNT_CODES) | set(WF.DEPTH_CODES) == set(WF.INDICATORS)
    assert all(m.change_kind == "pp" for m in WF.INDICATORS.values())


# --- Upload contracts & registry --------------------------------------------------------
def test_upload_contracts_absent_means_data_required():
    for name, c in UP.CONTRACTS.items():
        assert not c.path.exists()  # nothing ships: DATA REQUIRED
        assert UP.load(name) == (None, [])
        assert list(UP.template(name).columns) == list(c.columns) and UP.template(name).empty
        assert c.safeguard


def test_upload_contract_validation():
    c = UP.CONTRACTS["demat_accounts"]
    assert UP.validate(pd.DataFrame({"month": ["2024-01"]}), c)[0].startswith("missing column")
    bad = pd.DataFrame({"month": ["2024-13", "2024-01", "2024-01"], "depository": ["NSDL", "Both", "NSDL"],
                        "demat_accounts": [1, -1, "x"], "source_file": ["f", "f", "f"]})
    problems = " | ".join(UP.validate(bad, c))
    for frag in ("non-numeric", "negative", "YYYY-MM", "NSDL or CDSL"):
        assert frag in problems
    good = pd.DataFrame({"month": ["2024-01", "2024-01"], "depository": ["NSDL", "CDSL"],
                         "demat_accounts": [1, 2], "source_file": ["f", "f"]})
    assert UP.validate(good, c) == []
    dup = pd.concat([good, good])
    assert any("duplicate" in p for p in UP.validate(dup, c))
    sip = UP.CONTRACTS["amfi_sip"]
    ok_sip = pd.DataFrame({"month": ["2024-01"], "sip_contribution_inr_cr": [1.0], "sip_accounts": [None],
                           "source_file": ["f"]})
    assert UP.validate(ok_sip, sip) == []  # sip_accounts optional


def test_registry_records_for_page():
    assert registry.registry_problems() == []
    for i in ("wdi_financial_inclusion", "wdi_financial_depth"):
        assert registry.get(i).status == "LIVE" and registry.get(i).files == ()
    urls = {"amfi_mf_folios_sip": "https://www.amfiindia.com/", "nsdl_demat_accounts": "https://nsdl.co.in/",
            "cdsl_demat_accounts": "https://www.cdslindia.com/"}
    for i, url in urls.items():
        d = registry.get(i)
        assert d.status == "DATA REQUIRED" and d.files == () and d.url == url
        assert "Inequality & Financialisation Lab" in d.used_on
    assert registry.get("aidis77_asset_composition").status == "DATA REQUIRED"


# --- Page smoke (AppTest in a subprocess, so the page's module reloads cannot
#     affect other tests) ----------------------------------------------------------------
_SMOKE = textwrap.dedent('''
    import io, json, sys, urllib.error, urllib.request
    from unittest import mock
    from urllib.parse import parse_qs, urlparse
    sys.path.insert(0, ROOT)
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    PAGE = ROOT + "/app/views/14_Inequality_Financialisation_Lab.py"

    def offline(*a, **k):
        raise urllib.error.URLError("no network in tests")

    class Resp(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def online(req, timeout=None):  # stub payloads: test fixtures, not data
        p = urlparse(req.full_url)
        code = p.path.split("/indicator/")[1]
        s, e = map(int, parse_qs(p.query)["date"][0].split(":"))
        if code == "FD.AST.PRVT.GD.ZS":
            body = [{"message": [{"id": "120", "key": "Invalid value", "value": "stub"}]}]
        else:
            yrs = [2011, 2014, 2017, 2021] if code.startswith("FX.") else list(range(e, s - 1, -1))
            rows = [{"indicator": {"id": code, "value": code}, "country": {"id": "IN", "value": "India"},
                     "countryiso3code": "IND", "date": str(y), "value": float(y % 7 + 10)} for y in yrs]
            body = [{"page": 1, "pages": 1, "per_page": 20000, "total": len(rows), "lastupdated": "x"}, rows]
        return Resp(json.dumps(body).encode())

    for mode, fn in (("offline", offline), ("online", online)):
        st.cache_data.clear()
        with mock.patch.object(urllib.request, "urlopen", fn):
            at = AppTest.from_file(PAGE, default_timeout=120).run()
            steps = [lambda: at.radio(key="fin_lz_measure").set_value("Wealth (Table C.1)"),
                     lambda: at.multiselect(key="fin_lz_years_w").set_value([1961, 2023]),
                     lambda: at.select_slider(key="fin_cc_year").set_value(1991),
                     lambda: at.radio(key="fin_q2_top").set_value("Top 10% wealth share"),
                     lambda: at.selectbox(key="fin_cmp_b").set_value(at.selectbox(key="fin_cmp_b").options[-1]),
                     lambda: at.slider(key="fin_cmp_years").set_value((2000, 2020)),
                     lambda: at.slider(key="fin_years").set_value((2005, 2022)),
                     lambda: at.button(key="fin_refresh").click()]
            assert not at.exception, [x.value for x in at.exception]
            for step in steps:
                step(); at.run()
                assert not at.exception, [x.value for x in at.exception]
            errs = " ".join(e.value for e in at.error)
            assert ("DATA UNAVAILABLE" in errs) == (mode == "offline"), (mode, errs)
            assert [h.value[0] for h in at.header] == list("ABCDEF")
            print(mode, "ok")
''')


def test_page_smoke_offline_and_stubbed_online():
    proc = subprocess.run([sys.executable, "-c", f"ROOT = {str(ROOT)!r}\n" + _SMOKE],
                          capture_output=True, text=True, timeout=500, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "offline ok" in proc.stdout and "online ok" in proc.stdout
