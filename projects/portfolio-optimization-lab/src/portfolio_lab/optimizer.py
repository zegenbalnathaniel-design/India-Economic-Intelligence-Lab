"""Modern Portfolio Theory core: expected return, covariance, Sharpe ratio,
the minimum-variance and maximum-Sharpe (tangency) portfolios derived via
Lagrange multipliers, and the efficient frontier (closed-form unconstrained,
numerically constrained for long-only / weight-capped portfolios).

Notation (matches METHODOLOGY.md exactly)
-------------------------------------------
- `mu`  : (n,) vector of annualized expected returns, E(R) = w^T mu
- `cov` : (n,n) annualized covariance matrix, sigma_p^2 = w^T cov w
- `w`   : (n,) portfolio weight vector
- `rf`  : scalar risk-free rate

Every "closed-form" function below assumes **no inequality constraints**
(short-selling allowed) — that is exactly the case where a Lagrangian with
only equality constraints has an analytic solution. The moment you add
`w >= 0` or `w <= w_max`, the problem becomes a KKT (Karush-Kuhn-Tucker)
system with no general closed form, which is why the constrained functions
below call `scipy.optimize.minimize` (SLSQP) — numerically solving the same
first-order conditions the Lagrangian would give you, now with inequality
constraints included.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize


TRADING_DAYS_PER_YEAR = 252


def expected_returns(price_df: pd.DataFrame, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> pd.Series:
    """Annualized expected return per asset, from a wide DataFrame of prices
    (one column per ticker, one row per trading day)."""
    daily_returns = price_df.pct_change().dropna()
    return daily_returns.mean() * periods_per_year


def covariance_matrix(price_df: pd.DataFrame, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> pd.DataFrame:
    """Annualized covariance matrix of daily simple returns."""
    daily_returns = price_df.pct_change().dropna()
    return daily_returns.cov() * periods_per_year


def portfolio_return(weights: np.ndarray, mu: np.ndarray) -> float:
    """E(Rp) = w^T mu."""
    return float(np.dot(weights, mu))


def portfolio_variance(weights: np.ndarray, cov: np.ndarray) -> float:
    """sigma_p^2 = w^T Sigma w."""
    return float(weights @ cov @ weights)


def portfolio_volatility(weights: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(portfolio_variance(weights, cov), 0.0)))


def sharpe_ratio(weights: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float = 0.0) -> float:
    """Sharpe ratio: (E(Rp) - rf) / sigma_p. Returns -inf if volatility is
    exactly zero and excess return is negative, +inf if positive (both are
    degenerate edge cases that should not arise for a real covariance
    matrix with more than one genuinely different asset)."""
    vol = portfolio_volatility(weights, cov)
    excess = portfolio_return(weights, mu) - rf
    if vol == 0:
        return float("inf") if excess > 0 else (float("-inf") if excess < 0 else 0.0)
    return excess / vol


def _validate_square(cov: np.ndarray) -> int:
    n = cov.shape[0]
    if cov.shape != (n, n):
        raise ValueError("cov must be a square matrix.")
    return n


# ---------------------------------------------------------------------------
# Closed-form (unconstrained, short-selling allowed) solutions via Lagrange
# multipliers — see METHODOLOGY.md for the full derivation of each formula.
# ---------------------------------------------------------------------------

def min_variance_weights_closed_form(cov: np.ndarray) -> np.ndarray:
    """Global minimum-variance portfolio weights.

    Derivation: minimize (1/2) w^T Sigma w subject to w^T 1 = 1.
        L(w, lambda) = (1/2) w^T Sigma w - lambda (w^T 1 - 1)
        dL/dw = Sigma w - lambda 1 = 0  =>  w = lambda Sigma^-1 1
        Impose 1^T w = 1  =>  lambda = 1 / (1^T Sigma^-1 1)
        w_mv = Sigma^-1 1 / (1^T Sigma^-1 1)
    """
    n = _validate_square(cov)
    ones = np.ones(n)
    inv_cov_ones = np.linalg.solve(cov, ones)
    return inv_cov_ones / (ones @ inv_cov_ones)


def tangency_weights_closed_form(mu: np.ndarray, cov: np.ndarray, rf: float = 0.0) -> np.ndarray:
    """Maximum-Sharpe (tangency) portfolio weights.

    Derivation (Tobin separation / capital allocation line tangency point):
    the Sharpe ratio (w^T mu - rf) / sqrt(w^T Sigma w) is scale-invariant in
    `w`, so maximizing it is equivalent to minimizing variance for a *fixed*
    excess return kappa:
        L(w, lambda) = (1/2) w^T Sigma w - lambda (w^T (mu - rf*1) - kappa)
        dL/dw = Sigma w - lambda (mu - rf*1) = 0  =>  w proportional to Sigma^-1 (mu - rf*1)
    The proportionality constant is then fixed by the budget constraint
    w^T 1 = 1 (a genuine portfolio, not just a direction):
        w_tan = Sigma^-1 (mu - rf*1) / [1^T Sigma^-1 (mu - rf*1)]
    """
    n = _validate_square(cov)
    excess = mu - rf
    inv_cov_excess = np.linalg.solve(cov, excess)
    denom = np.ones(n) @ inv_cov_excess
    if abs(denom) < 1e-12:
        raise ValueError("Degenerate tangency portfolio (1^T Sigma^-1 (mu - rf*1) ~= 0).")
    return inv_cov_excess / denom


def efficient_frontier_closed_form(mu: np.ndarray, cov: np.ndarray, target_returns: Sequence[float]) -> pd.DataFrame:
    """Analytic (Merton 1972) efficient frontier — minimum variance for each
    target return, with short-selling allowed (no inequality constraints).

    Derivation: minimize (1/2) w^T Sigma w subject to TWO equality
    constraints, w^T mu = r_target and w^T 1 = 1:
        L(w, lam, gam) = (1/2) w^T Sigma w - lam(w^T mu - r_target) - gam(w^T 1 - 1)
        dL/dw = Sigma w - lam*mu - gam*1 = 0  =>  w = Sigma^-1 (lam*mu + gam*1)

    Substituting into the two constraints and defining the scalars
        a = 1^T Sigma^-1 1,  b = 1^T Sigma^-1 mu,  c = mu^T Sigma^-1 mu,  d = a*c - b^2
    gives a 2x2 linear system solved by
        lam = (a*r_target - b) / d
        gam = (c - b*r_target) / d
    so the weights for target return r are
        w*(r) = Sigma^-1 [ (c - b*r)*1 + (a*r - b)*mu ] / d
    """
    n = _validate_square(cov)
    ones = np.ones(n)
    inv_cov = np.linalg.inv(cov)
    a = ones @ inv_cov @ ones
    b = ones @ inv_cov @ mu
    c = mu @ inv_cov @ mu
    d = a * c - b ** 2
    if abs(d) < 1e-12:
        raise ValueError("Degenerate frontier (a*c - b^2 ~= 0) — check for collinear/duplicate assets.")

    rows = []
    for r in target_returns:
        w = inv_cov @ (((c - b * r) * ones) + ((a * r - b) * mu)) / d
        rows.append({
            "target_return": r,
            "volatility": portfolio_volatility(w, cov),
            "weights": w,
        })
    return pd.DataFrame(rows)


def frontier_vertex_closed_form(mu: np.ndarray, cov: np.ndarray) -> float:
    """The return at the frontier's vertex — i.e. the return earned by the
    global minimum-variance portfolio, `w_mv^T mu`. Every target return
    below this value is infeasible on the (short-selling-allowed) frontier
    without additional constraints, and volatility increases monotonically
    as the target return moves away from this point in either direction."""
    w_mv = min_variance_weights_closed_form(cov)
    return portfolio_return(w_mv, mu)


# ---------------------------------------------------------------------------
# Numerically constrained solutions (long-only, per-asset weight caps,
# optional target return/volatility). These solve the same optimization
# problem but with inequality constraints added, via SLSQP — the numerical
# generalization of the Lagrangian to KKT conditions.
# ---------------------------------------------------------------------------

@dataclass
class Constraints:
    long_only: bool = True
    max_weight: float = 1.0        # per-asset cap, e.g. 0.4 = no asset above 40%
    min_weight: float = 0.0        # per-asset floor (only used if long_only)
    target_return: Optional[float] = None
    target_volatility: Optional[float] = None


def _bounds(n: int, constraints: Constraints):
    lo = constraints.min_weight if constraints.long_only else -1.0
    hi = constraints.max_weight
    return [(lo, hi) for _ in range(n)]


def min_variance_weights_constrained(mu: np.ndarray, cov: np.ndarray, constraints: Constraints) -> np.ndarray:
    n = _validate_square(cov)
    x0 = np.full(n, 1.0 / n)
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if constraints.target_return is not None:
        cons.append({"type": "eq", "fun": lambda w, mu=mu: w @ mu - constraints.target_return})

    result = minimize(
        lambda w: portfolio_variance(w, cov), x0, method="SLSQP",
        bounds=_bounds(n, constraints), constraints=cons,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Minimum-variance optimization failed to converge: {result.message}")
    return result.x


def max_sharpe_weights_constrained(mu: np.ndarray, cov: np.ndarray, rf: float, constraints: Constraints) -> np.ndarray:
    n = _validate_square(cov)
    x0 = np.full(n, 1.0 / n)
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def neg_sharpe(w):
        return -sharpe_ratio(w, mu, cov, rf)

    result = minimize(
        neg_sharpe, x0, method="SLSQP",
        bounds=_bounds(n, constraints), constraints=cons,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Maximum-Sharpe optimization failed to converge: {result.message}")
    return result.x


def efficient_frontier_constrained(
    mu: np.ndarray, cov: np.ndarray, target_returns: Sequence[float], constraints: Constraints,
) -> pd.DataFrame:
    rows = []
    for r in target_returns:
        c = Constraints(
            long_only=constraints.long_only, max_weight=constraints.max_weight,
            min_weight=constraints.min_weight, target_return=r,
        )
        try:
            w = min_variance_weights_constrained(mu, cov, c)
            rows.append({"target_return": r, "volatility": portfolio_volatility(w, cov), "weights": w, "feasible": True})
        except RuntimeError:
            rows.append({"target_return": r, "volatility": np.nan, "weights": None, "feasible": False})
    return pd.DataFrame(rows)


def allocate_investment(weights: np.ndarray, tickers: Sequence[str], initial_investment: float) -> pd.Series:
    """Convert a weight vector into rupee/dollar amounts for a given
    initial investment — pure arithmetic, `amount_i = w_i * initial_investment`."""
    if initial_investment < 0:
        raise ValueError("initial_investment must be non-negative.")
    return pd.Series(weights * initial_investment, index=tickers, name="allocation")


def project_portfolio_value(
    initial_investment: float, expected_return: float, volatility: float, years: float, confidence_bands: Sequence[float] = (0.10, 0.90),
) -> pd.DataFrame:
    """Analytic (lognormal) projection of portfolio value over time: the
    expected path and confidence bands implied by geometric Brownian motion
    with the given annualized mean/volatility.

    This is **not** a forecast — it shows what the stated expected return
    and volatility imply mechanically, assuming returns are i.i.d.
    lognormal (itself a simplification; see the SIP Monte Carlo project in
    this portfolio for a simulation-based treatment with explicit
    contribution/fee/inflation modelling).
    """
    if initial_investment < 0:
        raise ValueError("initial_investment must be non-negative.")
    if years <= 0:
        raise ValueError("years must be positive.")
    from scipy.stats import norm

    t = np.linspace(0, years, int(max(years * 12, 12)) + 1)
    # Convert arithmetic mean/vol to the lognormal (geometric) drift.
    mu_log = np.log(1 + expected_return) - 0.5 * volatility ** 2
    expected_path = initial_investment * np.exp(mu_log * t)
    rows = {"year": t, "expected": expected_path}
    for q in confidence_bands:
        z = norm.ppf(q)
        rows[f"p{int(q * 100)}"] = initial_investment * np.exp(mu_log * t + z * volatility * np.sqrt(t))
    return pd.DataFrame(rows)
