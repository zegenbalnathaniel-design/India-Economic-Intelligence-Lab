"""Unit tests for analysis.wealth."""
from __future__ import annotations

import math

import numpy as np
import pytest

from analysis import wealth


def test_normalise_allocation_sums_to_one():
    alloc = {"property": 2, "gold": 1, "equities": 1,
             "gov_bonds": 0, "bank_deposits": 0, "cash": 0}
    n = wealth.normalise_allocation(alloc)
    assert math.isclose(sum(n.values()), 1.0)
    assert math.isclose(n["property"], 0.5)


def test_normalise_allocation_rejects_zero():
    with pytest.raises(ValueError):
        wealth.normalise_allocation({k: 0.0 for k in wealth.ASSET_KEYS})


def test_real_return_matches_fisher():
    # (1.10)/(1.05) - 1 ≈ 0.04762
    assert math.isclose(wealth.real_return(0.10, 0.05), (1.10 / 1.05) - 1)


def test_single_asset_100pct_matches_closed_form_annuity_due():
    # C at start of year, T years, one asset at r → FV = C * ((1+r)^T - 1)/r * (1+r)
    C, T, r = 100_000, 10, 0.10
    proj = wealth.single_asset_projection(
        annual_contribution=C, years=T, nominal_return=r, inflation=0.0,
    )
    expected = C * ((1 + r) ** T - 1) / r * (1 + r)
    assert math.isclose(proj["final_nominal"], expected, rel_tol=1e-9)


def test_composition_effect_reduces_to_single_asset_when_100pct():
    C, T, r = 50_000, 5, 0.08
    alloc = {k: 0.0 for k in wealth.ASSET_KEYS}
    alloc["equities"] = 1.0
    returns = {k: 0.0 for k in wealth.ASSET_KEYS}
    returns["equities"] = r
    result = wealth.composition_effect(
        annual_contribution=C, years=T, allocation=alloc, returns=returns,
        inflation=0.0, rebalance=True,
    )
    expected = C * ((1 + r) ** T - 1) / r * (1 + r)
    assert math.isclose(result.nominal_wealth[-1], expected, rel_tol=1e-9)
    assert math.isclose(result.total_contributions[-1], C * T)


def test_composition_effect_real_wealth_lower_when_inflation_positive():
    result = wealth.composition_effect(
        annual_contribution=100_000, years=20,
        allocation=wealth.DEFAULT_ALLOCATION,
        inflation=0.05,
    )
    assert result.real_wealth[-1] < result.nominal_wealth[-1]


def test_rminusg_uses_real_r():
    frame = wealth.rminusg_frame(r_nominal=0.10, inflation=0.05, g_real=0.03)
    expected_real = (1.10 / 1.05) - 1
    assert math.isclose(frame["r_real"], expected_real)
    assert math.isclose(frame["r_minus_g"], expected_real - 0.03)


def test_monte_carlo_percentiles_monotone_and_median_near_deterministic():
    alloc = wealth.DEFAULT_ALLOCATION
    mc = wealth.monte_carlo(
        annual_contribution=100_000, years=30, allocation=alloc,
        inflation=0.05, n_paths=1500, seed=1,
    )
    p = mc.percentiles.iloc[-1]
    assert p["p05"] <= p["p25"] <= p["p50"] <= p["p75"] <= p["p95"]
    det = wealth.composition_effect(100_000, 30, alloc, inflation=0.05)
    # Median of the stochastic run should be within ~20% of the deterministic
    # figure at 30y under the default volatilities. Log-normality of paths
    # makes the median lower than the mean; the tolerance reflects that.
    assert 0.5 * det.nominal_wealth[-1] < p["p50"] < 1.5 * det.nominal_wealth[-1]


def test_monte_carlo_rejects_bad_input():
    with pytest.raises(ValueError):
        wealth.monte_carlo(100_000, 10, wealth.DEFAULT_ALLOCATION, n_paths=0)
    with pytest.raises(ValueError):
        wealth.monte_carlo(100_000, 0, wealth.DEFAULT_ALLOCATION)


def test_composition_effect_rejects_bad_input():
    with pytest.raises(ValueError):
        wealth.composition_effect(annual_contribution=-1, years=10,
                                  allocation=wealth.DEFAULT_ALLOCATION)
    with pytest.raises(ValueError):
        wealth.composition_effect(annual_contribution=100, years=0,
                                  allocation=wealth.DEFAULT_ALLOCATION)
