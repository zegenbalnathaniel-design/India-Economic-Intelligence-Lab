"""Unit tests for analysis.states (State Economy Lab — the state explorer tabs)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from analysis import states as S
from data_sources import loaders


# ---------------------------------------------------------------------------
# State-name normalisation against every real state-level file
# ---------------------------------------------------------------------------

def _state_level_files() -> dict[str, pd.Series]:
    raw = loaders.RAW_DIR
    return {
        "spliced constant NSDP": loaders.load_nsdp_spliced()["state"],
        "as-published constant NSDP": loaders.load_nsdp_constant_as_published()["state"],
        "current NSDP (RBI)": loaders.load_nsdp_current()["state"],
        "current NSDP Delhi/Puducherry unaligned": pd.read_csv(
            raw / "rbi_handbook" / "nsdp_current_prices_delhi_puducherry_UNALIGNED.csv")["state"],
        "splice link factors": pd.read_csv(raw / "rbi_handbook" / "nsdp_splice_link_factors.csv")["state"],
        "state GSDP/NSDP (older vintage)": loaders.load_state_gsdp_nsdp_percapita()["state"],
        "PLFS unemployment": loaders.load_unemployment_by_state()["state"],
        "HCES urban MPCE": loaders.load_hces_urban_mpce()["state_ut"],
    }


@pytest.mark.parametrize("label", list(_state_level_files().keys()))
def test_every_file_state_maps_onto_canonical_set(label):
    names = _state_level_files()[label].unique()
    unmatched = S.unmatched_names(names)
    assert unmatched == [], f"{label}: unrecognised state names {unmatched}"
    for n in names:
        c = S.normalise_state(n)
        assert c is None or c == S.NATIONAL or c in S.CANONICAL_STATES


def test_observed_variants_resolve_to_one_canonical_name():
    assert S.normalise_state("Andaman and Nicobar Islands") == "Andaman & Nicobar Islands"
    assert S.normalise_state("Andaman & Nicobar Islands") == "Andaman & Nicobar Islands"
    assert S.normalise_state("Jammu and Kashmir") == "Jammu & Kashmir"
    assert S.normalise_state("Jammu & Kashmir*") == "Jammu & Kashmir"
    assert S.normalise_state("Jammu & Kashmir-U.T.") == "Jammu & Kashmir"
    assert S.normalise_state("Dadra & Nagar Haveli and Daman & Diu") == "Dadra & Nagar Haveli and Daman & Diu"
    assert S.normalise_state("  Kerala ") == "Kerala"
    assert S.normalise_state("India") == S.NATIONAL
    assert S.normalise_state("All-India") == S.NATIONAL


def test_footnotes_and_unknown_names_are_not_guessed():
    for footnote in S.NON_STATE_ROWS:
        assert S.normalise_state(footnote) is None
    assert S.normalise_state("Atlantis") is None
    assert S.unmatched_names(["Kerala", "Atlantis"]) == ["Atlantis"]
    assert S.normalise_state("") is None
    assert S.normalise_state(float("nan")) is None


def test_every_canonical_state_appears_in_some_file():
    seen = set()
    for names in _state_level_files().values():
        seen |= {S.normalise_state(n) for n in names.unique()}
    assert set(S.CANONICAL_STATES) <= seen


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def panel():
    return S.build_panel()


@pytest.fixture(scope="module")
def benchmarks():
    return S.national_benchmarks()


def test_panel_has_required_long_format_columns(panel):
    for col in ["state", "indicator", "period", "value", "unit", "source", "status"]:
        assert col in panel.columns
    assert set(panel["indicator"]) == set(S.INDICATORS)
    assert set(panel["state"]) <= set(S.CANONICAL_STATES)
    assert not panel.duplicated(["state", "indicator", "period"]).any()


def test_panel_values_match_raw_files(panel):
    def v(state, ind, period):
        hit = panel[(panel.state == state) & (panel.indicator == ind) & (panel.period == period)]
        return hit["value"].iloc[0]
    assert v("Kerala", "plfs_unemployment", "2023-24") == 7.2
    assert v("Kerala", "hces_urban_mpce", "2023-24") == 7783
    assert v("Kerala", "nsdp_pc_current_old", "2024-25") == 308338
    assert v("Andaman & Nicobar Islands", "gsdp_pc_constant_old", "2023-24") == 201631
    sp = loaders.load_nsdp_spliced()
    raw = sp[(sp.state == "Bihar") & (sp.financial_year == "2004-05")].iloc[0, 2]
    assert math.isclose(v("Bihar", "nsdp_pc_constant_spliced", "2004-05"), raw)


def test_blank_cells_stay_nan_never_zero(panel):
    # Kerala 2024-25 is blank in the RBI current-price table.
    cell = panel[(panel.state == "Kerala") & (panel.indicator == "nsdp_pc_current_rbi")
                 & (panel.period == "2024-25")]
    assert len(cell) == 1 and pd.isna(cell["value"].iloc[0])
    assert (panel["value"] == 0).sum() == 0


def test_known_data_issues_are_carried_not_repaired(panel):
    # Delhi and Puducherry: absent from the current-price NSDP table.
    cur = panel[panel.indicator == "nsdp_pc_current_rbi"]
    assert "Delhi" not in set(cur.state) and "Puducherry" not in set(cur.state)
    assert "13 of 14" in S.missing_reason(panel, "Delhi", "nsdp_pc_current_rbi")
    # Ladakh's short row in the older-vintage file is excluded, not realigned.
    lad = panel[(panel.state == "Ladakh") & (panel.indicator == "nsdp_pc_current_old")]
    assert lad["value"].isna().all()
    assert "Ladakh" in S.malformed_rows(loaders.RAW_DIR / "state_gsdp_nsdp_percapita.csv")
    # Delhi's blanked row in the same file.
    dg = panel[(panel.state == "Delhi") & (panel.indicator == "gsdp_pc_current_old")]
    assert dg["value"].isna().all() and "blanked" in dg["note"].iloc[0]
    # Bihar's CHECK flag survives.
    bihar = panel[(panel.state == "Bihar") & (panel.indicator == "nsdp_pc_current_rbi")]
    assert bihar["note"].str.startswith("CHECK").all()


def test_unparseable_cells_raise_instead_of_becoming_nan():
    assert math.isnan(S._to_number(" "))
    assert math.isnan(S._to_number(""))
    assert S._to_number("1,234") == 1234
    with pytest.raises(ValueError):
        S._to_number("abc")


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

def test_benchmarks_only_from_source_national_rows(benchmarks):
    assert S.benchmark_for(benchmarks, "hces_urban_mpce", "2023-24") == 6996
    assert S.benchmark_for(benchmarks, "plfs_unemployment", "2023-24") == 3.2
    assert S.benchmark_for(benchmarks, "nsdp_pc_constant_old", "2024-25") == 114710
    # No all-India row in these sources -> no benchmark, not a computed one.
    assert S.benchmark_for(benchmarks, "nsdp_pc_constant_spliced", "2022-23") is None
    assert S.benchmark_for(benchmarks, "nsdp_pc_current_rbi", "2023-24") is None


def test_inventory_states_no_benchmark_explicitly(panel, benchmarks):
    inv = S.inventory(panel, benchmarks).set_index("indicator")
    assert inv.at["nsdp_pc_constant_spliced", "national_benchmark"] == S.NO_BENCHMARK
    assert inv.at["nsdp_pc_constant_spliced", "first_period"] == "2004-05"
    assert inv.at["nsdp_pc_constant_spliced", "last_period"] == "2022-23"
    assert inv.at["nsdp_pc_current_rbi", "last_period"] == "2024-25"
    assert inv.at["hces_urban_mpce", "n_states"] == 36


# ---------------------------------------------------------------------------
# Ranking / profile / comparison
# ---------------------------------------------------------------------------

def _toy_panel() -> pd.DataFrame:
    rows = []
    vals = {"A": [100, 121], "B": [50, 50], "C": [np.nan, 80]}
    for s, (v0, v1) in vals.items():
        for p, v in (("2020-21", v0), ("2022-23", v1)):
            rows.append({"state": s, "indicator": "plfs_unemployment", "period": p, "value": v,
                         "unit": "%", "source": "x", "status": "PARTIAL",
                         "note": "blank in source" if pd.isna(v) else ""})
    return pd.DataFrame(rows)


def test_rank_states_keeps_missing_states_unranked():
    r = S.rank_states(_toy_panel(), "plfs_unemployment", "2020-21", states=["A", "B", "C", "D"])
    assert list(r["state"]) == ["A", "B", "C", "D"]
    assert list(r["rank"][:2]) == [1, 2]
    assert r["rank"][2:].isna().all()
    assert r.loc[r.state == "C", "note"].iloc[0] == "blank in source"
    assert r.loc[r.state == "D", "note"].iloc[0] == "state not in source table"
    assert (r["n_reporting"] == 2).all()
    asc = S.rank_states(_toy_panel(), "plfs_unemployment", "2020-21", ascending=True, states=["A", "B"])
    assert list(asc["state"]) == ["B", "A"]


def test_state_profile_has_every_indicator(panel, benchmarks):
    prof = S.state_profile(panel, "Kerala", benchmarks).set_index("indicator")
    assert set(prof.index) == set(S.INDICATORS)
    assert prof.at["hces_urban_mpce", "benchmark"] == 6996
    assert prof.at["nsdp_pc_constant_spliced", "benchmark_note"] == S.NO_BENCHMARK
    # Kerala's 2022-23 spliced value is blank, so latest is 2021-22.
    assert prof.at["nsdp_pc_constant_spliced", "period"] == "2021-22"
    lad = S.state_profile(panel, "Ladakh", benchmarks).set_index("indicator")
    assert pd.isna(lad.at["plfs_unemployment", "value"])
    assert lad.at["plfs_unemployment", "missing_reason"] == "state not in source table"


def test_compare_states_never_drops_a_state(panel):
    states = ["Kerala", "Delhi", "Ladakh"]
    c = S.compare_states(panel, states, ["nsdp_pc_current_rbi"], basis="common")
    assert list(c["state"]) == states
    # Kerala is blank for 2024-25, so the latest period any of the three
    # reports is 2023-24; Delhi and Ladakh are absent from this source.
    assert (c["period"] == "2023-24").all()
    assert c["value"].tolist()[0] == 279751
    assert c["value"][1:].isna().all()
    assert c["note"][1:].str.startswith("no data").all()
    c2 = S.compare_states(panel, ["Kerala", "Karnataka"], ["nsdp_pc_current_rbi"], basis="common")
    assert (c2["period"] == "2024-25").all()  # Karnataka reports 2024-25
    assert pd.isna(c2["value"].iloc[0]) and "blank in source" in c2["note"].iloc[0]
    own = S.compare_states(panel, states, ["nsdp_pc_current_rbi"], basis="own_latest").set_index("state")
    assert own.at["Kerala", "period"] == "2023-24"
    assert pd.isna(own.at["Delhi", "value"])
    with pytest.raises(ValueError):
        S.compare_states(panel, states, ["plfs_unemployment"], basis="nope")


# ---------------------------------------------------------------------------
# Historical change and CAGR
# ---------------------------------------------------------------------------

def test_cagr_known_value_and_invalid_cases():
    val, reason = S.cagr(100, 121, 2)
    assert math.isclose(val, 10.0) and reason == ""
    assert math.isnan(S.cagr(0, 10, 2)[0])
    assert math.isnan(S.cagr(-5, 10, 2)[0])
    assert math.isnan(S.cagr(10, 10, 0)[0])
    assert math.isnan(S.cagr(np.nan, 10, 2)[0])


def test_historical_change_first_vs_latest():
    h = S.historical_change(_toy_panel(), "plfs_unemployment", ["A", "C", "D"], "2020-21", "2022-23").set_index("state")
    assert math.isclose(h.at["A", "cagr_pct"], 10.0)
    assert h.at["A", "years"] == 2
    # C only has the 2022-23 value: one observation, no change computed.
    assert pd.isna(h.at["C", "cagr_pct"]) and "only one" in h.at["C", "note"]
    assert pd.isna(h.at["D", "first_value"]) and h.at["D", "note"].startswith("no data")


def test_historical_change_strict_requires_both_endpoints(panel):
    h = S.historical_change(panel, "nsdp_pc_constant_spliced", ["Kerala", "Bihar"], "2004-05", "2022-23",
                            strict=True).set_index("state")
    assert pd.isna(h.at["Kerala", "cagr_pct"]) and "2022-23" in h.at["Kerala", "note"]
    assert not pd.isna(h.at["Bihar", "cagr_pct"])
    loose = S.historical_change(panel, "nsdp_pc_constant_spliced", ["Kerala"], "2004-05", "2022-23").set_index("state")
    assert loose.at["Kerala", "last_period"] == "2021-22"
    assert loose.at["Kerala", "years"] == 17


def test_fiscal_year_start():
    assert S.fiscal_year_start("2011-12") == 2011
    with pytest.raises(ValueError):
        S.fiscal_year_start("FY12")


def test_format_value_never_shows_zero_for_missing():
    assert S.format_value(np.nan, "₹") == "no data"
    assert S.format_value(125261, "₹") == "₹1,25,261"
    assert S.format_value(7783, "₹/month") == "₹7,783/month"
    assert S.format_value(7.2, "%") == "7.2%"
