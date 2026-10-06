"""Household wealth accumulation, composition effect and r-g analytics.

Implements the composition-effect simulation described in the author's
accompanying research on income and wealth inequality in India: two
households that save the *same* amount can end up with very different
long-run wealth purely because of *where* they hold it (property vs. gold
vs. equities vs. bank deposits...), not because of their income.

All monetary results are returned in nominal Indian rupees unless the
`inflation` argument is used to deflate to constant-purchasing-power terms.
Every default below is an explicitly labelled illustrative reference point,
never a forecast, and every one of them is a function argument you can
override.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


ASSET_KEYS = ["property", "gold", "equities", "gov_bonds", "bank_deposits", "cash"]

ASSET_LABELS: Dict[str, str] = {
    "property": "Real estate",
    "gold": "Gold",
    "equities": "Equities",
    "gov_bonds": "Government bonds",
    "bank_deposits": "Bank deposits",
    "cash": "Cash",
}

# Illustrative long-horizon nominal returns used as defaults. These are
# indicative reference points drawn from long-run averages reported in RBI
# and NSE historical data; they are NOT forecasts and should not be
# interpreted as guaranteed. The caller can override every value.
DEFAULT_NOMINAL_RETURNS: Dict[str, float] = {
    "property": 0.085,
    "gold": 0.090,
    "equities": 0.120,
    "gov_bonds": 0.070,
    "bank_deposits": 0.060,
    "cash": 0.000,
}

# Rough volatility reference (annualised standard deviation) — illustrative,
# used only to communicate that assets differ in risk, not for VaR.
DEFAULT_VOLATILITY: Dict[str, float] = {
    "property": 0.08,
    "gold": 0.16,
    "equities": 0.22,
    "gov_bonds": 0.05,
    "bank_deposits": 0.005,
    "cash": 0.00,
}

LIQUIDITY: Dict[str, str] = {
    "property": "Low",
    "gold": "Medium",
    "equities": "High",
    "gov_bonds": "Medium",
    "bank_deposits": "High",
    "cash": "Immediate",
}

# Default allocation used in the research write-up for the composition-effect
# scenario. Rounds to 1.0.
DEFAULT_ALLOCATION: Dict[str, float] = {
    "property": 0.51,
    "gold": 0.15,
    "equities": 0.06,
    "gov_bonds": 0.05,
    "bank_deposits": 0.20,
    "cash": 0.03,
}


@dataclass
class CompositionResult:
    years: np.ndarray
    nominal_wealth: np.ndarray
    real_wealth: np.ndarray
    total_contributions: np.ndarray
    investment_gains: np.ndarray
    composition: pd.DataFrame  # one column per asset, nominal balances
    weighted_return: float
    inflation: float
    real_weighted_return: float


def normalise_allocation(allocation: Dict[str, float]) -> Dict[str, float]:
    total = sum(allocation.get(k, 0.0) for k in ASSET_KEYS)
    if total <= 0:
        raise ValueError("Allocation weights must sum to a positive value.")
    return {k: (allocation.get(k, 0.0) / total) for k in ASSET_KEYS}


def portfolio_return(allocation: Dict[str, float], returns: Dict[str, float]) -> float:
    """Weighted nominal return on the portfolio in one year."""
    alloc = normalise_allocation(allocation)
    return float(sum(alloc[k] * returns.get(k, 0.0) for k in ASSET_KEYS))


def real_return(nominal: float, inflation: float) -> float:
    """Fisher-style exact relation: r_real = (1+r_nom)/(1+pi) - 1."""
    return (1.0 + nominal) / (1.0 + inflation) - 1.0


def composition_effect(
    annual_contribution: float,
    years: int,
    allocation: Dict[str, float],
    returns: Dict[str, float] | None = None,
    inflation: float = 0.05,
    rebalance: bool = True,
) -> CompositionResult:
    """Simulate wealth accumulation for one household over `years` years.

    The household contributes `annual_contribution` at the start of every
    year. Each asset compounds at its nominal return. When `rebalance` is
    True the portfolio is rebalanced back to the target allocation at each
    year-end (matches the research write-up's static-allocation assumption).

    This is a **deterministic model**: it shows what a fixed allocation and
    fixed returns imply, not what will happen. Use `monte_carlo` below to see
    a distribution of outcomes under return uncertainty.
    """
    if years <= 0:
        raise ValueError("years must be positive.")
    if annual_contribution < 0:
        raise ValueError("annual_contribution must be non-negative.")

    rets = {**DEFAULT_NOMINAL_RETURNS, **(returns or {})}
    alloc = normalise_allocation(allocation)

    balances = {k: 0.0 for k in ASSET_KEYS}
    history: List[Dict[str, float]] = []
    yr_axis = np.arange(1, years + 1)
    nominal = np.zeros(years)
    contrib_cum = np.zeros(years)
    total_contribution = 0.0

    for i, _yr in enumerate(yr_axis):
        for k in ASSET_KEYS:
            balances[k] += annual_contribution * alloc[k]
        total_contribution += annual_contribution

        for k in ASSET_KEYS:
            balances[k] *= 1.0 + rets[k]

        if rebalance:
            total = sum(balances.values())
            for k in ASSET_KEYS:
                balances[k] = total * alloc[k]

        nominal[i] = sum(balances.values())
        contrib_cum[i] = total_contribution
        history.append({k: balances[k] for k in ASSET_KEYS})

    r_nom = portfolio_return(alloc, rets)
    r_real = real_return(r_nom, inflation)
    real_wealth = nominal / ((1.0 + inflation) ** yr_axis)

    return CompositionResult(
        years=yr_axis,
        nominal_wealth=nominal,
        real_wealth=real_wealth,
        total_contributions=contrib_cum,
        investment_gains=nominal - contrib_cum,
        composition=pd.DataFrame(history, index=yr_axis),
        weighted_return=r_nom,
        inflation=inflation,
        real_weighted_return=r_real,
    )


def single_asset_projection(
    annual_contribution: float, years: int, nominal_return: float, inflation: float
) -> Dict[str, float]:
    """Final wealth if 100% is invested in one asset — used for A/B comparison."""
    balance = 0.0
    for _ in range(years):
        balance += annual_contribution
        balance *= 1.0 + nominal_return
    real = balance / ((1.0 + inflation) ** years)
    return {
        "nominal_return": nominal_return,
        "final_nominal": balance,
        "final_real": real,
        "total_contribution": annual_contribution * years,
        "gain": balance - annual_contribution * years,
    }


@dataclass
class MonteCarloResult:
    years: np.ndarray
    percentiles: pd.DataFrame  # columns: p05, p25, p50, p75, p95 — nominal
    final_nominal: np.ndarray  # shape (n_paths,)
    final_real: np.ndarray
    n_paths: int
    inflation: float


def monte_carlo(
    annual_contribution: float,
    years: int,
    allocation: Dict[str, float],
    returns: Dict[str, float] | None = None,
    volatilities: Dict[str, float] | None = None,
    inflation: float = 0.05,
    n_paths: int = 2000,
    seed: int = 7,
) -> MonteCarloResult:
    """Stochastic version of `composition_effect`.

    Draws annual asset returns from independent normal distributions with
    the specified per-asset mean and volatility, applies annual
    rebalancing, and reports the cross-path percentiles of nominal wealth.
    Returns are assumed independent across assets — a deliberate
    simplification that avoids implying a covariance structure this model
    does not estimate. For a covariance-aware treatment, see the
    `portfolio-optimization-lab` project in this portfolio.
    """
    if n_paths <= 0:
        raise ValueError("n_paths must be positive.")
    if years <= 0:
        raise ValueError("years must be positive.")

    rets = {**DEFAULT_NOMINAL_RETURNS, **(returns or {})}
    vols = {**DEFAULT_VOLATILITY, **(volatilities or {})}
    alloc = normalise_allocation(allocation)
    rng = np.random.default_rng(seed)

    keys = list(ASSET_KEYS)
    mu = np.array([rets[k] for k in keys])
    sigma = np.array([vols[k] for k in keys])
    w = np.array([alloc[k] for k in keys])

    balances = np.zeros((n_paths, len(keys)))
    nominal = np.zeros((n_paths, years))
    for t in range(years):
        balances += annual_contribution * w
        shocks = rng.normal(loc=mu, scale=sigma, size=(n_paths, len(keys)))
        balances *= 1.0 + shocks
        totals = balances.sum(axis=1, keepdims=True)
        balances = totals * w
        nominal[:, t] = totals.ravel()

    yr_axis = np.arange(1, years + 1)
    pct_df = pd.DataFrame(
        {
            "p05": np.percentile(nominal, 5, axis=0),
            "p25": np.percentile(nominal, 25, axis=0),
            "p50": np.percentile(nominal, 50, axis=0),
            "p75": np.percentile(nominal, 75, axis=0),
            "p95": np.percentile(nominal, 95, axis=0),
        },
        index=yr_axis,
    )

    real_final = nominal[:, -1] / ((1.0 + inflation) ** years)
    return MonteCarloResult(
        years=yr_axis,
        percentiles=pct_df,
        final_nominal=nominal[:, -1],
        final_real=real_final,
        n_paths=n_paths,
        inflation=inflation,
    )


def rminusg_frame(r_nominal: float, inflation: float, g_real: float) -> Dict[str, float]:
    """r - g on a consistent real basis, plus components.

    `r > g` (Piketty's capital-income identity) implies capital's share of
    national income tends to rise relative to labour income over time. It
    does **not**, on its own, imply that inequality among individuals must
    rise — that also depends on who owns the capital, savings rates by
    wealth level, and bequest patterns, none of which are inside this
    identity.
    """
    r_real = real_return(r_nominal, inflation)
    return {
        "r_nominal": r_nominal,
        "inflation": inflation,
        "r_real": r_real,
        "g_real": g_real,
        "r_minus_g": r_real - g_real,
    }
