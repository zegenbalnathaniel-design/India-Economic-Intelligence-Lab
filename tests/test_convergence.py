"""Tests for analysis.convergence (State Economy Lab v2) and the balanced-
panel option of analysis.regional.sigma_convergence."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from analysis import convergence as C
from analysis import regional
from analysis import states as S
from data_sources import loaders

COL = C.VALUE_COL


def _long(table: dict[str, dict[str, float]]) -> pd.DataFrame:
    rows = [{"state": s, "financial_year": y, COL: v} for s, d in table.items() for y, v in d.items()]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tile map
# ---------------------------------------------------------------------------

def test_tile_grid_covers_every_canonical_state_once_without_overlap():
    assert set(C.TILE_GRID) == set(S.CANONICAL_STATES)
    assert set(C.TILE_ABBR) == set(C.TILE_GRID)
    assert len(set(C.TILE_GRID.values())) == len(C.TILE_GRID)  # no two tiles share a cell
    assert len(set(C.TILE_ABBR.values())) == len(C.TILE_ABBR)


def test_every_state_name_in_the_data_maps_to_a_tile():
    panel = S.build_panel()
    _, unmatched = C.tile_coverage(panel["state"].unique())
    assert unmatched == []
    raw_names = set(loaders.load_nsdp_spliced()["state"]) | set(loaders.load_nsdp_current()["state"]) \
        | set(loaders.load_unemployment_by_state()["state"]) | set(loaders.load_hces_urban_mpce()["state_ut"]) \
        | set(loaders.load_state_gsdp_nsdp_percapita()["state"]) \
        | set(loaders.load_nsdp_constant_as_published()["state"])
    matched, unmatched = C.tile_coverage(raw_names)
    assert unmatched == []
    assert set(matched.values()) <= set(C.TILE_GRID)


def test_tile_coverage_reports_unknown_names_instead_of_guessing():
    _, unmatched = C.tile_coverage(["Kerala", "Atlantis", "India"])
    assert unmatched == ["Atlantis"]


def test_tile_frame_keeps_missing_as_nan_and_ranks_reporting_tiles():
    tf = C.tile_frame({"Kerala": 10.0, "Bihar": 5.0, "Goa": float("nan")})
    assert len(tf) == len(C.TILE_GRID)
    k = tf.set_index("state")
    assert k.at["Kerala", "rank"] == 1 and k.at["Bihar", "rank"] == 2
    assert math.isnan(k.at["Goa", "value"]) and math.isnan(k.at["Goa", "rank"])
    assert (k["n_reporting"] == 2).all()
    with pytest.raises(ValueError):
        C.tile_frame({"Atlantis": 1.0})


# ---------------------------------------------------------------------------
# β regression vs statsmodels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("robust", [False, True])
def test_ols_matches_statsmodels(robust):
    rng = np.random.default_rng(7)
    x = rng.normal(10, 1, 25)
    y = 3 - 0.8 * x + rng.normal(0, 1 + 0.5 * (x - 10) ** 2, 25)  # heteroskedastic
    fit = C.ols(x, y, robust=robust)
    X = sm.add_constant(x)
    ref = sm.OLS(y, X).fit(cov_type="HC1", use_t=True) if robust else sm.OLS(y, X).fit()
    assert fit.slope == pytest.approx(ref.params[1], rel=1e-10)
    assert fit.intercept == pytest.approx(ref.params[0], rel=1e-10)
    assert fit.se == pytest.approx(ref.bse[1], rel=1e-10)
    assert fit.r_squared == pytest.approx(ref.rsquared, rel=1e-10)
    assert fit.p == pytest.approx(ref.pvalues[1], rel=1e-8)
    lo, hi = ref.conf_int(alpha=0.05)[1]
    assert fit.ci_low == pytest.approx(lo, rel=1e-8) and fit.ci_high == pytest.approx(hi, rel=1e-8)


@pytest.mark.parametrize("window", [("2004-05", "2022-23"), ("2004-05", "2021-22"), ("2011-12", "2019-20")])
@pytest.mark.parametrize("robust", [False, True])
def test_beta_window_on_real_series_matches_statsmodels(window, robust):
    nsdp = loaders.load_nsdp_spliced()
    res = C.beta_window(nsdp, *window, robust=robust)
    ps = res.per_state
    X = sm.add_constant(np.log(ps["initial_value"].to_numpy()))
    model = sm.OLS(ps["avg_annual_growth_pct"].to_numpy(), X)
    ref = model.fit(cov_type="HC1", use_t=True) if robust else model.fit()
    assert res.fit.slope == pytest.approx(ref.params[1], rel=1e-9)
    assert res.fit.se == pytest.approx(ref.bse[1], rel=1e-9)
    assert res.fit.r_squared == pytest.approx(ref.rsquared, rel=1e-9)
    assert res.fit.n == int(ref.nobs)


def test_beta_window_full_period_reproduces_regional_beta_convergence():
    nsdp = loaders.load_nsdp_spliced()
    old = regional.beta_convergence(nsdp)
    new = C.beta_window(nsdp, "2004-05", "2022-23")
    assert new.fit.slope == pytest.approx(old.slope, rel=1e-9)
    assert new.fit.r_squared == pytest.approx(old.r_squared, rel=1e-9)
    assert len(new.per_state) == len(old.per_state)


def test_beta_window_excludes_states_missing_an_endpoint_without_substitution():
    table = {s: {"2000-01": 100.0 * (i + 1), "2001-02": 110.0 * (i + 1), "2002-03": 120.0 * (i + 1)}
             for i, s in enumerate("ABCDEF")}
    table["F"]["2002-03"] = float("nan")
    res = C.beta_window(_long(table), "2000-01", "2002-03")
    assert "F" not in set(res.per_state["state"])
    assert list(res.excluded["state"]) == ["F"]
    assert "2002-03" in res.excluded["reason"].iloc[0]
    assert res.years == 2


def test_half_life_formula():
    # slope −2 (% a year per log point) over 20 years: b = −0.02, 1 + bT = 0.6
    lam, hl, note = C.speed_of_convergence(-2.0, 20)
    assert note == ""
    assert lam == pytest.approx(-math.log(0.6) / 20)
    assert hl == pytest.approx(math.log(2) / lam)
    # round trip: b = −(1 − e^(−λT)) / T
    assert -(1 - math.exp(-lam * 20)) / 20 == pytest.approx(-0.02)
    assert math.isnan(C.speed_of_convergence(0.5, 20)[0])
    assert math.isnan(C.speed_of_convergence(-6.0, 20)[1])  # 1 + bT < 0: undefined


# ---------------------------------------------------------------------------
# σ measures on a hand example
# ---------------------------------------------------------------------------

def test_dispersion_measures_on_hand_example():
    x = [1.0, 2.0, 3.0, 4.0]
    # SD of log, population: ln values 0, .6931, 1.0986, 1.3863
    logs = [math.log(v) for v in x]
    m = sum(logs) / 4
    assert C.dispersion(x, "sd_log") == pytest.approx(math.sqrt(sum((v - m) ** 2 for v in logs) / 4))
    # CV: population SD sqrt(1.25) / mean 2.5
    assert C.dispersion(x, "cv") == pytest.approx(math.sqrt(1.25) / 2.5 * 100)
    # Gini: Σ|xi − xj| over all ordered pairs = 20; 20 / (2·16·2.5) = 0.25
    assert C.dispersion(x, "gini") == pytest.approx(0.25)
    assert C.dispersion(x, "max_min") == pytest.approx(4.0)
    # numpy linear percentiles: P90 = 3.7, P10 = 1.3
    assert C.dispersion(x, "p90_p10") == pytest.approx(3.7 / 1.3)


def test_dispersion_edge_cases():
    assert C.dispersion([5, 5, 5], "gini") == 0.0
    assert C.dispersion([5, 5, 5], "sd_log") == 0.0
    assert math.isnan(C.dispersion([5], "cv"))
    assert math.isnan(C.dispersion([5, 0, 3], "sd_log"))  # log undefined
    assert math.isnan(C.dispersion([5, float("nan")], "cv"))  # one value left
    with pytest.raises(ValueError):
        C.dispersion([1, 2], "variance")


def test_classify_trend_rule():
    assert C.classify_trend(-4.99) == "stable"
    assert C.classify_trend(4.99) == "stable"
    assert C.classify_trend(-5.0) == "falling"
    assert C.classify_trend(12.0) == "rising"
    assert C.classify_trend(float("nan")) == "insufficient data"


def _composition_panel() -> pd.DataFrame:
    """Five 'core' states whose spread steadily WIDENS, plus two very
    rich/very poor states that report only in the first two years. Over
    all reporting states the spread appears to shrink (the extremes drop
    out); over the same states every year it rises."""
    years = [f"{2000 + i}-{str(2001 + i)[-2:]}" for i in range(6)]
    table = {}
    for k, base in enumerate([80, 90, 100, 110, 120]):
        table[f"Core{k}"] = {y: 100 + (base - 100) * (1 + 0.2 * i) for i, y in enumerate(years)}
    table["VeryRich"] = {y: (400.0 if i < 2 else float("nan")) for i, y in enumerate(years)}
    table["VeryPoor"] = {y: (20.0 if i < 2 else float("nan")) for i, y in enumerate(years)}
    return _long(table)


def test_changing_state_set_cannot_flip_the_balanced_verdict():
    panel = _composition_panel()
    start, end = "2000-01", "2005-06"
    for m in C.MEASURES:
        bal = C.sigma_dispersion(panel, start, end, m, balanced=True)
        assert bal.verdict == "rising", m
        assert sorted(bal.excluded["state"]) == ["VeryPoor", "VeryRich"]
        assert set(bal.by_year["n_states"]) == {5}
        unbal = C.sigma_dispersion(panel, start, end, m, balanced=False)
        assert unbal.composition_changes
    # The artefact this guards against: the unbalanced CV calls it falling.
    assert C.sigma_dispersion(panel, start, end, "cv", balanced=False).verdict == "falling"
    # Adding or dropping the part-coverage states does not change the balanced result.
    core_only = panel[panel["state"].str.startswith("Core")]
    a = C.sigma_dispersion(panel, start, end, "sd_log").by_year["value"].to_numpy()
    b = C.sigma_dispersion(core_only, start, end, "sd_log").by_year["value"].to_numpy()
    np.testing.assert_allclose(a, b)


def test_regional_sigma_convergence_balanced_default_and_unbalanced_option():
    panel = _composition_panel()
    bal = regional.sigma_convergence(panel)
    assert bal.balanced and bal.direction == "diverging"
    assert set(bal.excluded_states) == {"VeryRich", "VeryPoor"}
    assert set(bal.by_year["n_states"]) == {5}
    unbal = regional.sigma_convergence(panel, balanced=False)
    assert unbal.direction == "converging"  # the composition artefact
    assert unbal.excluded_states == {}


def test_regional_sigma_convergence_real_series_balanced_rises():
    nsdp = loaders.load_nsdp_spliced()
    res = regional.sigma_convergence(nsdp)
    assert set(res.by_year["n_states"]) == {21}
    assert len(res.excluded_states) == 11
    assert res.by_year["cv_pct"].iloc[0] == pytest.approx(45.255, abs=1e-3)
    assert res.by_year["cv_pct"].iloc[-1] == pytest.approx(53.448, abs=1e-3)
    assert res.direction == "diverging"


def test_sigma_dispersion_cv_matches_regional_on_balanced_panel():
    nsdp = loaders.load_nsdp_spliced()
    a = C.sigma_dispersion(nsdp, "2004-05", "2022-23", "cv")
    b = regional.sigma_convergence(nsdp)
    np.testing.assert_allclose(a.by_year["value"].to_numpy(), b.by_year["cv_pct"].to_numpy())


# ---------------------------------------------------------------------------
# Workbench
# ---------------------------------------------------------------------------

def test_index_to_base_and_missing_base():
    wide = pd.DataFrame({"2010-11": [50.0, np.nan], "2011-12": [100.0, 80.0], "2012-13": [110.0, 88.0]},
                        index=["A", "B"])
    idx, reasons = C.index_to_base(wide, "2011-12")
    assert idx.loc["A"].tolist() == pytest.approx([50.0, 100.0, 110.0])
    assert idx.loc["B", "2011-12"] == 100.0 and math.isnan(idx.loc["B", "2010-11"])
    idx2, reasons2 = C.index_to_base(wide, "2010-11")
    assert idx2.loc["B"].isna().all()  # no base value -> no index, not rebased elsewhere
    assert "B" in reasons2 and reasons == {}


def test_annual_growth_only_between_consecutive_reported_years():
    wide = pd.DataFrame({"2010-11": [100.0], "2011-12": [np.nan], "2012-13": [121.0], "2013-14": [133.1]},
                        index=["A"])
    g = C.annual_growth(wide)
    assert math.isnan(g.at["A", "2010-11"]) and math.isnan(g.at["A", "2011-12"])
    assert math.isnan(g.at["A", "2012-13"])  # previous year blank -> no growth, no interpolation
    assert g.at["A", "2013-14"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Research notes
# ---------------------------------------------------------------------------

def test_research_notes_are_built_from_the_computed_numbers():
    years = [f"{2000 + i}-{str(2001 + i)[-2:]}" for i in range(11)]
    starts = {"P1": 20.0, "P2": 25.0, "M1": 50.0, "M2": 55.0, "R1": 90.0, "R2": 100.0}
    growth = {"P1": 0.08, "P2": 0.12, "M1": 0.05, "M2": 0.045, "R1": 0.02, "R2": 0.01}
    table = {s: {y: starts[s] * math.exp(growth[s] * i) for i, y in enumerate(years)} for s in starts}
    panel = _long(table)
    beta = C.beta_window(panel, years[0], years[-1])
    sigma = C.sigma_dispersion(panel, years[0], years[-1], "sd_log")
    ranks = C.rank_changes(panel, years[0], years[-1])
    notes = C.research_notes(beta, sigma, ranks)
    assert set(notes) == {"observed", "statistical", "interpretation", "questions"}
    text = " ".join(sum(notes.values(), []))
    fastest = beta.per_state.sort_values("avg_annual_growth_pct").iloc[-1]
    assert fastest["state"] == "P2"
    assert f"P2 ({fastest['avg_annual_growth_pct']:.2f}%)" in text
    assert f"slope = {beta.fit.slope:+.3f}" in text
    assert f"SE {beta.fit.se:.3f}" in text
    assert f"R² = {beta.fit.r_squared:.3f}" in text
    assert f"half-life = {beta.half_life:.1f} years" in text
    assert sigma.verdict == "falling" and "**falling**" in text
    top = ranks.iloc[0]
    assert top["state"] == "P2" and top["places"] == 1
    assert f"Biggest rank gain: P2, from {int(top['rank_start'])} to {int(top['rank_end'])} of 6 (+1 place)" in text
    assert "statistically significant" in text
    assert "consistent with" in " ".join(notes["interpretation"])
    assert any("not causal" in s for s in notes["interpretation"])
    # deterministic
    assert notes == C.research_notes(beta, sigma, ranks)


def test_research_notes_handle_insufficient_data():
    panel = _long({"A": {"2000-01": 1.0, "2001-02": 2.0}})
    beta = C.beta_window(panel, "2000-01", "2001-02")
    sigma = C.sigma_dispersion(panel, "2000-01", "2001-02")
    notes = C.research_notes(beta, sigma, C.rank_changes(panel, "2000-01", "2001-02"))
    assert any("not estimated" in s for s in notes["statistical"])
    assert any("not computed" in s for s in notes["statistical"])


def test_as_published_blocks_match_spliced_where_published_and_drop_jk():
    raw = loaders.load_nsdp_constant_as_published()
    new, notes = C.as_published_block(raw, "2011-12")
    old, _ = C.as_published_block(raw, "2004-05")
    assert "Jammu & Kashmir" not in set(new["state"]) | set(old["state"])
    assert notes and "Jammu" in notes[0]
    assert set(new["state"]) == set(loaders.load_nsdp_spliced()["state"])
    sp = loaders.load_nsdp_spliced()
    sp = sp[sp["method"].str.startswith("new-base")]
    m = sp.merge(new, on=["state", "financial_year"], suffixes=("_sp", "_pub"))
    both = m.dropna(subset=[C.VALUE_COL + "_sp", C.VALUE_COL + "_pub"])
    assert len(both) > 300
    np.testing.assert_allclose(both[C.VALUE_COL + "_sp"], both[C.VALUE_COL + "_pub"])
    # A per-state link factor cancels out of within-block growth rates (not out of log initial income).
    b_old = C.beta_window(old, "2004-05", "2010-11")
    b_sp = C.beta_window(loaders.load_nsdp_spliced(), "2004-05", "2010-11")
    g = b_old.per_state.merge(b_sp.per_state, on="state")
    np.testing.assert_allclose(g["avg_annual_growth_pct_x"], g["avg_annual_growth_pct_y"], rtol=1e-9)
