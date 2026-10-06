"""Unit tests for portfolio_lab.optimizer — checked against closed-form
2-asset algebra and internal consistency between the analytic (Lagrangian)
and numerically-constrained (KKT/SLSQP) solvers, not against real market
outcomes (this module takes mu/cov as given inputs; see data_loader.py for
where those numbers come from in the app)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from portfolio_lab import optimizer as opt


def test_weights_sum_to_one_min_variance_closed_form():
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    w = opt.min_variance_weights_closed_form(cov)
    assert math.isclose(w.sum(), 1.0, abs_tol=1e-9)


def test_min_variance_two_uncorrelated_assets_matches_inverse_variance_formula():
    sigma1_sq, sigma2_sq = 0.04, 0.09  # uncorrelated: off-diagonal = 0
    cov = np.array([[sigma1_sq, 0.0], [0.0, sigma2_sq]])
    w = opt.min_variance_weights_closed_form(cov)
    expected_w1 = (1 / sigma1_sq) / (1 / sigma1_sq + 1 / sigma2_sq)
    assert math.isclose(w[0], expected_w1, rel_tol=1e-9)
    assert math.isclose(w[1], 1 - expected_w1, rel_tol=1e-9)


def test_min_variance_closed_form_actually_minimizes_variance():
    # Perturbing the closed-form weights (while keeping sum=1) should never
    # lower variance — this is the first-order optimality condition made
    # empirical: check many random feasible perturbations.
    rng = np.random.default_rng(0)
    cov = np.array([[0.05, 0.015, 0.0], [0.015, 0.08, 0.01], [0.0, 0.01, 0.03]])
    w_star = opt.min_variance_weights_closed_form(cov)
    v_star = opt.portfolio_variance(w_star, cov)
    for _ in range(200):
        perturb = rng.normal(0, 0.01, size=3)
        perturb -= perturb.mean()  # keep sum(w) = 1
        w_try = w_star + perturb
        assert opt.portfolio_variance(w_try, cov) >= v_star - 1e-12


def test_tangency_weights_two_uncorrelated_assets_closed_form():
    mu = np.array([0.08, 0.14])
    cov = np.array([[0.04, 0.0], [0.0, 0.09]])
    rf = 0.02
    w = opt.tangency_weights_closed_form(mu, cov, rf)
    assert math.isclose(w.sum(), 1.0, abs_tol=1e-9)
    # Direction should be proportional to Sigma^-1 (mu - rf*1) = (0.06/0.04, 0.12/0.09)
    expected_direction = np.array([0.06 / 0.04, 0.12 / 0.09])
    ratio = w / expected_direction
    assert math.isclose(ratio[0], ratio[1], rel_tol=1e-9)


def test_tangency_weights_maximize_sharpe_vs_random_portfolios():
    mu = np.array([0.08, 0.12, 0.15])
    cov = np.array([[0.04, 0.01, 0.0], [0.01, 0.06, 0.02], [0.0, 0.02, 0.09]])
    rf = 0.01
    w_tan = opt.tangency_weights_closed_form(mu, cov, rf)
    sharpe_tan = opt.sharpe_ratio(w_tan, mu, cov, rf)

    rng = np.random.default_rng(1)
    for _ in range(500):
        w = rng.normal(0, 1, size=3)
        w = w / w.sum()  # random portfolio, budget constraint only (short-selling allowed)
        assert opt.sharpe_ratio(w, mu, cov, rf) <= sharpe_tan + 1e-9


def test_efficient_frontier_closed_form_vertex_matches_min_variance_portfolio():
    mu = np.array([0.07, 0.11, 0.14])
    cov = np.array([[0.03, 0.005, 0.0], [0.005, 0.05, 0.01], [0.0, 0.01, 0.08]])
    w_mv = opt.min_variance_weights_closed_form(cov)
    r_mv = opt.portfolio_return(w_mv, mu)
    frontier = opt.efficient_frontier_closed_form(mu, cov, [r_mv])
    assert math.isclose(frontier.iloc[0]["volatility"], opt.portfolio_volatility(w_mv, cov), rel_tol=1e-6)


def test_efficient_frontier_volatility_increases_away_from_vertex():
    mu = np.array([0.07, 0.11, 0.14])
    cov = np.array([[0.03, 0.005, 0.0], [0.005, 0.05, 0.01], [0.0, 0.01, 0.08]])
    v_vertex = opt.frontier_vertex_closed_form(mu, cov)
    targets = [v_vertex, v_vertex + 0.02, v_vertex + 0.05]
    frontier = opt.efficient_frontier_closed_form(mu, cov, targets)
    vols = frontier["volatility"].values
    assert vols[0] <= vols[1] <= vols[2]


def test_constrained_min_variance_matches_closed_form_when_bounds_wide():
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    mu = np.array([0.08, 0.1])
    constraints = opt.Constraints(long_only=False, max_weight=5.0, min_weight=-5.0)
    w_numeric = opt.min_variance_weights_constrained(mu, cov, constraints)
    w_closed = opt.min_variance_weights_closed_form(cov)
    assert np.allclose(w_numeric, w_closed, atol=1e-3)


def test_constrained_min_variance_respects_long_only_bounds():
    cov = np.array([[0.04, -0.02], [-0.02, 0.09]])  # negative correlation would push unconstrained weights outside [0,1]
    mu = np.array([0.08, 0.1])
    constraints = opt.Constraints(long_only=True, max_weight=1.0, min_weight=0.0)
    w = opt.min_variance_weights_constrained(mu, cov, constraints)
    assert np.all(w >= -1e-8)
    assert np.all(w <= 1.0 + 1e-8)
    assert math.isclose(w.sum(), 1.0, abs_tol=1e-6)


def test_max_sharpe_constrained_matches_closed_form_when_bounds_wide():
    mu = np.array([0.08, 0.12, 0.15])
    cov = np.array([[0.04, 0.01, 0.0], [0.01, 0.06, 0.02], [0.0, 0.02, 0.09]])
    rf = 0.01
    constraints = opt.Constraints(long_only=False, max_weight=5.0, min_weight=-5.0)
    w_numeric = opt.max_sharpe_weights_constrained(mu, cov, rf, constraints)
    w_closed = opt.tangency_weights_closed_form(mu, cov, rf)
    assert math.isclose(
        opt.sharpe_ratio(w_numeric, mu, cov, rf),
        opt.sharpe_ratio(w_closed, mu, cov, rf),
        rel_tol=1e-3,
    )


def test_allocate_investment_proportional():
    w = np.array([0.6, 0.4])
    alloc = opt.allocate_investment(w, ["A", "B"], 1000.0)
    assert math.isclose(alloc["A"], 600.0)
    assert math.isclose(alloc["B"], 400.0)


def test_allocate_investment_rejects_negative():
    with pytest.raises(ValueError):
        opt.allocate_investment(np.array([0.5, 0.5]), ["A", "B"], -100.0)


def test_project_portfolio_value_bands_ordered_and_grow_with_positive_drift():
    df = opt.project_portfolio_value(10_000, expected_return=0.10, volatility=0.15, years=10)
    assert (df["p90"] >= df["expected"]).all()
    assert (df["expected"] >= df["p10"]).all()
    assert df["expected"].iloc[-1] > df["expected"].iloc[0]


def test_expected_returns_and_covariance_shapes():
    dates = pd.bdate_range("2023-01-01", periods=100)
    rng = np.random.default_rng(2)
    prices = pd.DataFrame(
        {"A": 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 100))),
         "B": 50 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, 100)))},
        index=dates,
    )
    mu = opt.expected_returns(prices)
    cov = opt.covariance_matrix(prices)
    assert list(mu.index) == ["A", "B"]
    assert cov.shape == (2, 2)
    assert math.isclose(cov.loc["A", "B"], cov.loc["B", "A"])
