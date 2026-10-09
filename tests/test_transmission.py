"""Tests for analysis/transmission.py, its parameters file and the simulator page."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import pytest

from analysis import transmission as T
from data_sources import registry

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "app" / "pages" / "15_Macro_Transmission_Simulator.py"


@pytest.fixture(scope="module")
def table():
    return T.load_parameters()


@pytest.fixture(scope="module")
def full_a(table):
    """Set A with every DATA REQUIRED input filled with arbitrary test numbers
    (test fixtures only -- never shipped as defaults)."""
    p = T.defaults(table, "A")
    filler = {"baseline_crude_usd": 80.0, "oil_import_share_gdp": 4.0, "exports_gdp": 20.0, "imports_gdp": 24.0,
              "export_price_elasticity_sr": 0.2, "import_price_elasticity_sr": 0.1,
              "export_price_elasticity_lr": 0.8, "import_price_elasticity_lr": 0.6, "revenue_gdp_ratio": 20.0}
    return {**p, **filler}


# ---------------------------------------------------------------------------
# Parameters file: schema and provenance
# ---------------------------------------------------------------------------
def test_parameters_schema_and_provenance(table):
    assert set(T.REQUIRED_COLUMNS) <= set(table.columns)
    assert T.parameter_problems(table) == []


def test_every_value_has_citation_url_and_quote(table):
    vals = table[table["value"].notna()]
    assert len(vals) > 0
    for _, r in vals.iterrows():
        assert r["source_citation"].strip(), r["parameter"]
        assert r["url"].startswith("http"), r["parameter"]
        assert r["quote_or_context"].strip(), r["parameter"]
        assert "web search summary" in r["verified_via"], r["parameter"]
        assert r["status"] == "CITED"


def test_blank_values_are_data_required(table):
    blank = table[table["value"].isna()]
    assert len(blank) > 0
    assert (blank["status"] == "DATA REQUIRED").all()


def test_problem_checker_catches_uncited_value(table):
    bad = table.copy()
    i = bad.index[bad["value"].notna()][0]
    bad.loc[i, "source_citation"] = ""
    bad.loc[i, "url"] = ""
    probs = T.parameter_problems(bad)
    assert any("value without source_citation" in p for p in probs)
    assert any("url is not a web address" in p for p in probs)
    bad2 = table.copy()
    j = bad2.index[bad2["value"].isna()][0]
    bad2.loc[j, "status"] = "CITED"
    assert any("must have status DATA REQUIRED" in p for p in T.parameter_problems(bad2))


def test_known_cited_values(table):
    a = T.defaults(table, "A")
    assert a["capex_multiplier"] == pytest.approx(2.45)
    assert a["repo_to_walr_fresh"] == pytest.approx(187 / 250, abs=1e-3)
    assert a["repo_to_walr_outstanding"] == pytest.approx(111 / 250, abs=1e-3)
    assert a["policy_to_cpi_cumulative"] == pytest.approx(-160 / 250)
    assert a["oil_cpi_bps_per_10pct"] == 30
    assert a["export_price_elasticity_sr"] is None  # never invented


def test_set_b_falls_back_to_a(table):
    a, b = T.defaults(table, "A"), T.defaults(table, "B")
    assert b["oil_cpi_bps_per_10pct"] == 20 and a["oil_cpi_bps_per_10pct"] == 30
    assert b["repo_to_walr_fresh"] == a["repo_to_walr_fresh"]  # no alternative -> same as A


def test_parameters_file_registered():
    assert registry.registry_problems() == []
    d = registry.get("transmission_parameters")
    assert "data/raw/transmission/parameters.csv" in d.files


# ---------------------------------------------------------------------------
# Equations: zero shock, linearity, identities, hand-checked values
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", T.SCENARIO_KEYS)
def test_zero_shock_gives_zero(scenario, full_a):
    for regime in T.OIL_REGIMES:
        for r in T.run(scenario, 0.0, full_a, regime):
            if r.status == T.QUANTIFIED:
                assert r.value == 0.0, r.link.id


@pytest.mark.parametrize("scenario", T.SCENARIO_KEYS)
def test_linearity(scenario, full_a):
    lo, hi, default, _ = T.SCENARIOS[scenario].slider
    for regime in T.OIL_REGIMES:
        one = T.run(scenario, default, full_a, regime)
        two = T.run(scenario, 2 * default, full_a, regime)
        neg = T.run(scenario, -default, full_a, regime)
        for a, b, c in zip(one, two, neg):
            if a.status == T.QUANTIFIED:
                assert b.value == pytest.approx(2 * a.value), a.link.id
                assert c.value == pytest.approx(-a.value), a.link.id


def test_all_links_quantified_when_all_parameters_present(full_a):
    for s in T.SCENARIO_KEYS:
        for r in T.run(s, 1.0, full_a):
            assert r.status in (T.QUANTIFIED, T.NOT_APPLICABLE)


def _val(results, link_id):
    return next(r for r in results if r.link.id == link_id)


def test_policy_hand_calculation(full_a):
    res = T.run("policy", 50.0, full_a)
    assert _val(res, "walr_fresh").value == pytest.approx(0.748 * 0.5)
    assert _val(res, "credit_growth").value == pytest.approx(-2.78 * 0.5)
    assert _val(res, "investment_rate").value == pytest.approx(-0.50 * 0.748 * 0.5)
    assert _val(res, "cpi").value == pytest.approx(-0.64 * 0.5)


def test_oil_hand_calculation_and_regimes(full_a):
    res = T.run("oil", 20.0, full_a, T.FULL_PASS_THROUGH)
    assert _val(res, "cpi").value == pytest.approx(0.30 * 2)
    assert _val(res, "gdp_growth").value == pytest.approx(-0.15 * 2)
    assert _val(res, "cad").value == pytest.approx(0.43 * (80 * 0.2) / 10)
    assert _val(res, "import_bill_mech").value == pytest.approx(4.0 * 0.2)
    assert _val(res, "fiscal").status == T.NOT_APPLICABLE
    res2 = T.run("oil", 20.0, full_a, T.GOVT_ABSORBS)
    assert _val(res2, "fiscal").value == pytest.approx(0.43 * 1.6)
    assert _val(res2, "cpi").status == T.NOT_APPLICABLE


def test_rupee_import_price_identity_and_trade_balance(full_a):
    res = T.run("rupee", 5.0, full_a)
    assert _val(res, "import_prices").value == 5.0
    assert _val(res, "cpi").value == pytest.approx(0.35)
    # 0.05 * (20*0.2 - 24*(1-0.1)) = 0.05 * (4 - 21.6) = -0.88
    assert _val(res, "trade_balance_sr").value == pytest.approx(-0.88)
    # 0.05 * (20*0.8 - 24*0.4) = 0.05 * 6.4 = 0.32 -> J-curve: worse then better
    assert _val(res, "trade_balance_lr").value == pytest.approx(0.32)


def test_marshall_lerner_condition():
    # balanced trade: TB improves iff eps_x + eps_m > 1
    assert T.trade_balance_change(10, 20, 20, 0.6, 0.6) > 0 and T.marshall_lerner(0.6, 0.6)
    assert T.trade_balance_change(10, 20, 20, 0.3, 0.3) < 0 and not T.marshall_lerner(0.3, 0.3)
    assert T.trade_balance_change(10, 20, 20, 0.5, 0.5) == pytest.approx(0.0)
    assert T.marshall_lerner(None, 0.5) is None


def test_capex_deficit_identity(full_a):
    for shock in (0.1, 0.5, -0.3, 1.7):
        res = T.run("capex", shock, full_a)
        assert _val(res, "deficit_gross").value == pytest.approx(shock)          # ΔFD = ΔG exactly
        assert _val(res, "demand").value == pytest.approx(2.45 * shock)
        assert _val(res, "deficit_net").value == pytest.approx(shock - 0.20 * 2.45 * shock)


# ---------------------------------------------------------------------------
# Missing parameter -> "needs parameter", never a number
# ---------------------------------------------------------------------------
def test_missing_parameter_gives_needs_parameter(table):
    a = T.defaults(table, "A")  # shipped defaults: trade elasticities etc. blank
    res = T.run("rupee", 5.0, a)
    tb = _val(res, "trade_balance_sr")
    assert tb.status == T.NEEDS_PARAMETER and tb.value is None
    assert "export_price_elasticity_sr" in tb.missing
    assert _val(res, "cpi").status == T.QUANTIFIED


def test_missing_upstream_parameter_propagates(full_a):
    p = {**full_a, "repo_to_walr_fresh": None}
    res = T.run("policy", 50.0, p)
    for link_id in ("walr_fresh", "investment_rate", "gdp_growth"):
        r = _val(res, link_id)
        assert r.status == T.NEEDS_PARAMETER and r.value is None
    assert _val(res, "cpi").status == T.QUANTIFIED


def test_nan_and_garbage_count_as_missing(full_a):
    p = {**full_a, "capex_multiplier": float("nan")}
    assert _val(T.run("capex", 0.5, p), "demand").status == T.NEEDS_PARAMETER
    assert T.format_value(None, T.NEEDS_PARAMETER, "pp") == "needs parameter"


def test_comparison_table_baseline_and_sets(table):
    a, b = T.defaults(table, "A"), T.defaults(table, "B")
    t = T.comparison_table("oil", 10.0, a, b)
    cpi = t[t["link"] == "cpi"].iloc[0]
    assert cpi["baseline (no shock)"] == 0.0
    assert cpi["scenario · set A"] == pytest.approx(0.30)
    assert cpi["scenario · set B"] == pytest.approx(0.20)
    cad = t[t["link"] == "cad"].iloc[0]
    assert cad["status A"] == T.NEEDS_PARAMETER and pd.isna(cad["scenario · set A"])


def test_diagram_edges_cover_links_and_qualitative(table):
    a = T.defaults(table, "A")
    for s in T.SCENARIO_KEYS:
        res = T.run(s, 1.0, a)
        edges = T.diagram_edges(s, res)
        statuses = {e["status"] for e in edges}
        assert T.QUALITATIVE in statuses
        nodes = set(T.SCENARIOS[s].nodes)
        assert all(e["source"] in nodes and e["target"] in nodes for e in edges)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def test_export_payload_and_files(table):
    a, b = T.defaults(table, "A"), T.defaults(table, "B")
    b["capex_multiplier"] = 1.5  # a user edit
    t = T.comparison_table("capex", 0.5, a, b)
    payload = T.export_payload("capex", 0.5, a, b, t)
    assert payload["label"] == T.HYPOTHETICAL_LABEL
    assert payload["scenario"]["shock"] == 0.5
    pa = {r["parameter"]: r for r in payload["parameters"]["set_A"]}
    pb = {r["parameter"]: r for r in payload["parameters"]["set_B"]}
    assert pa["capex_multiplier"]["status"] == "CITED" and "Bose" in pa["capex_multiplier"]["source_citation"]
    assert pa["capex_multiplier"]["url"].startswith("http")
    assert pb["capex_multiplier"]["status"] == "USER-SET" and pb["capex_multiplier"]["source_citation"] == ""
    assert pa["revenue_gdp_ratio"]["status"] == "DATA REQUIRED" and pa["revenue_gdp_ratio"]["value"] is None
    outs = {o["effect"]: o for o in payload["outputs"]}
    assert outs["Δ fiscal deficit before revenue feedback"]["scenario · set A"] == pytest.approx(0.5)
    assert outs["Δ fiscal deficit after revenue feedback"]["status A"] == T.NEEDS_PARAMETER
    assert outs["Δ fiscal deficit after revenue feedback"]["scenario · set A"] is None

    js = json.loads(T.export_json(payload))
    assert js["label"].startswith("HYPOTHETICAL")
    csv_text = T.export_csv(payload)
    assert csv_text.startswith("# HYPOTHETICAL")
    body = pd.read_csv(io.StringIO(csv_text), comment="#")
    assert set(body["section"]) == {"output", "parameter"}
    assert body[body["section"] == "parameter"]["source_citation"].fillna("").str.contains("Bose").any()


# ---------------------------------------------------------------------------
# Page smoke test (Streamlit AppTest): every scenario, widgets, reset
# ---------------------------------------------------------------------------
def test_page_smoke_all_scenarios_and_widgets():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(PAGE), default_timeout=60)
    at.run()
    assert not at.exception
    for s in T.SCENARIO_KEYS:
        at.radio(key="tm_scenario").set_value(s).run()
        assert not at.exception, s
        lo, hi, *_ = T.SCENARIOS[s].slider
        at.slider(key=f"tm_shock_{s}").set_value(hi).run()
        assert not at.exception, s
    # oil: switch regime and fill a data input
    at.radio(key="tm_scenario").set_value("oil").run()
    at.radio(key="tm_oil_regime").set_value(T.GOVT_ABSORBS).run()
    at.number_input(key="tm_D_baseline_crude_usd").set_value(80.0).run()
    assert not at.exception
    # rupee: fill elasticities and shares, edit set B
    at.radio(key="tm_scenario").set_value("rupee").run()
    for k, v in {"tm_D_exports_gdp": 20.0, "tm_D_imports_gdp": 24.0, "tm_A_export_price_elasticity_sr": 0.2,
                 "tm_A_import_price_elasticity_sr": 0.1, "tm_A_export_price_elasticity_lr": 0.8,
                 "tm_A_import_price_elasticity_lr": 0.6, "tm_B_inr_cpi_bps_per_5pct_depr": 50.0}.items():
        at.number_input(key=k).set_value(v).run()
    assert not at.exception
    assert any("holds" in m.value for m in at.markdown)
    # reset restores cited defaults
    at.button(key="tm_reset_btn").click().run()
    assert not at.exception
    assert at.number_input(key="tm_B_inr_cpi_bps_per_5pct_depr").value == 20.0
    assert at.number_input(key="tm_A_export_price_elasticity_sr").value is None
    assert at.slider(key="tm_shock_rupee").value == T.SCENARIOS["rupee"].slider[2]
