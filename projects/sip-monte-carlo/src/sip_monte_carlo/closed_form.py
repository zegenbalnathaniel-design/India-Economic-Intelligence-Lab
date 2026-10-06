"""Deterministic (zero-volatility) closed-form reference for a SIP.

This module implements the exact algebraic future value of a systematic
investment plan (SIP) with monthly contributions that step up once per
year, compounding at a constant monthly rate. It exists so that the Monte
Carlo engine in :mod:`sip_monte_carlo.engine` can be checked against an
*exact* number when volatility is set to zero -- a necessary (not merely
nice-to-have) correctness property for any simulator that claims to
generalize ordinary compound interest.

Convention
----------
Within each month, growth is applied to the balance that already exists,
and then that month's contribution is added at the end of the month (the
"ordinary annuity" convention). This exactly matches the month-by-month
loop used in :func:`sip_monte_carlo.engine.run_simulation` when volatility
is zero, so the two must agree to floating-point precision.

Contributions step up once per *year*: during year ``k`` (0-indexed, so
the first year is ``k = 0``), the monthly contribution is::

    C_k = monthly_contribution * (1 + contribution_growth_rate) ** k

Derivation
----------
Let ``r`` be the constant monthly rate and ``N = 12 * duration_years`` the
total number of months. For year block ``k`` (months ``12k+1 .. 12k+12``,
1-indexed from the start), the twelve contributions of size ``C_k``
accumulate, by the end of that year, to ``C_k * FVA_12(r)`` where

    FVA_12(r) = ((1 + r)**12 - 1) / r          (r != 0)
    FVA_12(0) = 12                              (r == 0, limiting case)

is the future-value-of-an-ordinary-annuity factor for 12 level payments.
That lump sum then compounds forward for the remaining ``12 * (T - k - 1)``
months to the end of the horizon. Summing over all years and adding the
compounded initial capital gives the closed form implemented below.
"""
from __future__ import annotations

import numpy as np


def annuity_factor(monthly_rate: float, n_periods: int = 12) -> float:
    """Future-value-of-an-ordinary-annuity factor for ``n_periods`` level
    unit payments compounding at ``monthly_rate`` per period.

    ``FVA(r) = ((1 + r)**n - 1) / r``, with the limit ``FVA(0) = n``.
    """
    if abs(monthly_rate) < 1e-14:
        return float(n_periods)
    return ((1.0 + monthly_rate) ** n_periods - 1.0) / monthly_rate


def future_value_growing_annuity(
    monthly_contribution: float,
    duration_years: int,
    monthly_rate: float,
    contribution_growth_rate: float = 0.0,
    initial_capital: float = 0.0,
) -> float:
    """Exact future value of a SIP with annually-stepping contributions.

    Parameters
    ----------
    monthly_contribution:
        The monthly contribution paid during year 0 (the first year).
    duration_years:
        Number of years the plan runs (an integer number of 12-month
        blocks).
    monthly_rate:
        The constant monthly compounding rate ``r`` (net of any fee drag
        already folded in by the caller -- see
        :func:`sip_monte_carlo.engine.net_monthly_rate`).
    contribution_growth_rate:
        Fractional step-up applied to the monthly contribution once per
        year (e.g. ``0.05`` for a 5% per year increase).
    initial_capital:
        Lump sum already invested at time zero.

    Returns
    -------
    float
        The nominal future value at the end of ``duration_years`` years,
        i.e. after ``N = 12 * duration_years`` months.
    """
    if duration_years <= 0:
        raise ValueError("duration_years must be positive.")

    n_months = 12 * duration_years
    fva_12 = annuity_factor(monthly_rate, 12)

    fv_initial_capital = initial_capital * (1.0 + monthly_rate) ** n_months

    years = np.arange(duration_years)  # k = 0 .. T-1
    contributions_k = monthly_contribution * (1.0 + contribution_growth_rate) ** years
    remaining_months = 12 * (duration_years - 1 - years)  # months after year k's block
    fv_contributions = np.sum(
        contributions_k * fva_12 * (1.0 + monthly_rate) ** remaining_months
    )

    return float(fv_initial_capital + fv_contributions)
