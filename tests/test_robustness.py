"""Tests for the limitation fixes: correlated Monte Carlo, distributional
Gini, iBFPI sensitivity and the fixed-effects / Newey-West regression."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis import banking as B
from analysis import inequality as I
from analysis import wealth as W
from data_sources import loaders as L

ALLOC = dict(property=.3, gold=.1, equities=.3, gov_bonds=.1, bank_deposits=.1, cash=.1)


# --- correlated / fat-tailed Monte Carlo --------------------------------------
def test_identity_correlation_reproduces_independent_model():
    a = W.monte_carlo(100000, 15, ALLOC, n_paths=500)
    b = W.monte_carlo(100000, 15, ALLOC, n_paths=500, correlation=np.eye(6))
    assert np.allclose(a.final_nominal, b.final_nominal)


def test_positive_correlation_widens_the_band():
    R = np.full((6, 6), 0.8)
    np.fill_diagonal(R, 1)
    spread = lambda r: np.percentile(r.final_nominal, 95) - np.percentile(r.final_nominal, 5)
    assert spread(W.monte_carlo(100000, 20, ALLOC, n_paths=3000, correlation=R)) > \
        spread(W.monte_carlo(100000, 20, ALLOC, n_paths=3000))


def test_fat_tails_keep_volatility():
    r = W.monte_carlo(100000, 1, {"equities": 1.0}, n_paths=40000, t_df=5, volatilities={"equities": 0.2})
    growth = r.final_nominal / 100000 - 1
    assert np.std(growth) == pytest.approx(0.2, rel=0.05)


@pytest.mark.parametrize("bad", [
    np.ones((5, 5)),                                           # wrong size
    np.eye(6) + np.triu(np.full((6, 6), 0.3), 1),              # not symmetric
    np.full((6, 6), 0.5),                                      # diagonal not 1
    (lambda m: (m.__setitem__((0, 1), -.9), m.__setitem__((1, 0), -.9),
                m.__setitem__((0, 2), .9), m.__setitem__((2, 0), .9),
                m.__setitem__((1, 2), .9), m.__setitem__((2, 1), .9), m)[-1])(np.eye(6)),  # impossible
])
def test_invalid_correlations_rejected(bad):
    with pytest.raises(ValueError):
        W.validate_correlation(bad, 6)


def test_t_df_must_exceed_two():
    with pytest.raises(ValueError):
        W.monte_carlo(1, 1, ALLOC, n_paths=10, t_df=2)


# --- Gini -------------------------------------------------------------------------
def test_gini_zero_for_equal_shares_and_known_value():
    assert I.gini_lower_bound(50, 40, 1, 0.1) == pytest.approx(0, abs=1e-12)
    # Hand-computed trapezoids for 2022 income shares.
    pts = [(0, 0), (.5, .15), (.9, .423), (.99, .774), (.999, .904), (1, 1)]
    area = sum((x1 - x0) * (y0 + y1) / 2 for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
    assert I.gini_lower_bound(15.0, 27.3, 22.6, 9.6) == pytest.approx(1 - 2 * area)


def test_gini_series_rises_since_1982():
    g = I.gini_series(L.load_wil_income_shares()).set_index("year")["gini_lower_bound"]
    assert g.loc[2022] > g.loc[1982] and 0 < g.min() < g.max() < 1
    w = I.gini_series(L.load_wil_wealth_shares()).set_index("year")
    assert w.loc[2023, "tentative"] and w.loc[2022, "gini_lower_bound"] > w.loc[1961, "gini_lower_bound"]


def test_redistribution_lowers_gini_and_conserves_total():
    s = dict(bottom_50=15.0, middle_40=27.3, top_10=57.7, top_1=22.6, top_0_1=9.6)
    n = I.redistribute(s, 5)
    assert n["bottom_50"] + n["middle_40"] + n["top_10"] == pytest.approx(100.0)
    assert n["top_0_1"] == pytest.approx(9.6 * (1 - 5 / 22.6))
    g0 = I.gini_lower_bound(s["bottom_50"], s["middle_40"], s["top_1"], s["top_0_1"])
    g1 = I.gini_lower_bound(n["bottom_50"], n["middle_40"], n["top_1"], n["top_0_1"])
    assert g1 < g0
    with pytest.raises(ValueError):
        I.redistribute(s, 30)


# --- iBFPI sensitivity and regression ----------------------------------------------
@pytest.fixture(scope="module")
def panel_repo():
    return L.load_bank_panel(), L.load_repo_rate()


def test_default_directions_match_baseline(panel_repo):
    p, r = panel_repo
    a = B.compute_ibfpi(p)["ibfpi"]
    b = B.compute_ibfpi(p, directions=dict(B.INDICATOR_DIRECTION))["ibfpi"]
    assert np.allclose(a, b)


def test_sensitivity_tables_shape(panel_repo):
    p, r = panel_repo
    ws = B.weight_sensitivity(p, r, n_draws=20)
    assert len(ws) == 20 and np.allclose(ws.filter(like="w_").sum(axis=1), 1)
    assert len(B.leave_one_out(p, r)) == 6 and len(B.direction_flips(p, r)) == 5
    assert B.leave_one_out(p, r).iloc[0]["rho"] == pytest.approx(B.system_rho(p, r).rho)


def test_fixed_effects_matches_hand_within_estimator(panel_repo):
    p, r = panel_repo
    sc = B.compute_ibfpi(p)
    res = B.fixed_effects_regression(sc, r)
    d = sc[["bank", "period", "ibfpi"]].merge(r, on="period").dropna()
    y = d["ibfpi"] - d.groupby("bank")["ibfpi"].transform("mean")
    x = d["repo_rate"] - d.groupby("bank")["repo_rate"].transform("mean")
    assert res[0].slope == pytest.approx((x * y).sum() / (x * x).sum())
    assert [x.label for x in res] == ["Bank fixed effects", "Bank fixed effects, clustered by bank",
                                     "System iBFPI, Newey-West"]
    assert all(r_.ci_low < r_.slope < r_.ci_high for r_ in res)
    assert B.newey_west_lags(26) == 2
