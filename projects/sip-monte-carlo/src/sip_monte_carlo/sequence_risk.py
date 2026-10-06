"""Sequence-of-returns risk: the same average return, different order, a
different outcome.

This module demonstrates a specific, well-known phenomenon in SIP and
retirement planning: for a compounding process with *ongoing cash flows*
(regular contributions here; regular withdrawals in retirement), the
*order* in which a fixed multiset of returns occurs changes the final
wealth, even though the arithmetic mean return is identical in every
ordering. This happens because later contributions sit on top of a larger
accumulated base, so returns that occur later in the horizon apply to
more money than returns occurring early on.

This is a teaching example with explicit, user-supplied returns -- it is
not a Monte Carlo simulation and makes no claim about which order is more
"likely" to occur in reality. It only shows that order matters at all,
holding the average fixed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def simulate_annual_path(
    annual_returns: list[float] | np.ndarray,
    annual_contribution: float,
    initial_capital: float = 0.0,
    annual_fee_rate: float = 0.0,
) -> np.ndarray:
    """Apply a fixed, ordered sequence of annual returns to a stream of
    annual contributions.

    Convention (matches :mod:`sip_monte_carlo.engine`): each year, the
    existing balance grows by that year's return (net of the fee drag),
    then that year's contribution is added at year end.

    Parameters
    ----------
    annual_returns:
        An ordered sequence of simple annual returns, e.g.
        ``[0.30, -0.10, 0.20, -0.05, 0.15]``.
    annual_contribution:
        The (constant) amount contributed at the end of every year.
    initial_capital:
        Lump sum already invested at time zero. Must be ``>= 0``.
    annual_fee_rate:
        Annual expense-ratio-style drag subtracted from each year's
        return. Must be ``>= 0``.

    Returns
    -------
    np.ndarray
        Balance at the end of each year, length ``len(annual_returns) + 1``
        (including year 0, the initial capital).
    """
    if initial_capital < 0:
        raise ValueError("initial_capital must be non-negative.")
    if annual_contribution < 0:
        raise ValueError("annual_contribution must be non-negative.")
    if annual_fee_rate < 0:
        raise ValueError("annual_fee_rate must be non-negative.")

    returns = np.asarray(annual_returns, dtype=float)
    n_years = len(returns)
    if n_years == 0:
        raise ValueError("annual_returns must contain at least one value.")

    balances = np.empty(n_years + 1, dtype=float)
    balances[0] = initial_capital
    for t in range(n_years):
        net_return = returns[t] - annual_fee_rate
        balances[t + 1] = balances[t] * (1.0 + net_return) + annual_contribution
    return balances


@dataclass
class SequenceRiskResult:
    """Result of comparing a sequence of annual returns against its
    reverse, for the same stream of contributions."""

    annual_returns_forward: np.ndarray
    annual_returns_reversed: np.ndarray
    arithmetic_mean_return: float
    forward_path: np.ndarray
    reversed_path: np.ndarray
    forward_final: float
    reversed_final: float
    difference: float  # forward_final - reversed_final
    percent_difference: float  # difference / reversed_final, as a fraction


def demo_sequence_of_returns_risk(
    annual_returns: list[float] | np.ndarray,
    annual_contribution: float,
    initial_capital: float = 0.0,
    annual_fee_rate: float = 0.0,
) -> SequenceRiskResult:
    """Run the same multiset of annual returns forward and in reverse
    order, over the same contribution stream, and compare final wealth.

    The arithmetic mean return is, by construction, identical in both
    orderings (reversing a list does not change its mean) -- yet the two
    final balances generally differ. This isolates "sequence risk" from
    "average return risk": they are two distinct sources of uncertainty
    in SIP planning.

    Returns
    -------
    SequenceRiskResult
    """
    returns = np.asarray(annual_returns, dtype=float)
    reversed_returns = returns[::-1]

    forward_path = simulate_annual_path(
        returns, annual_contribution, initial_capital, annual_fee_rate
    )
    reversed_path = simulate_annual_path(
        reversed_returns, annual_contribution, initial_capital, annual_fee_rate
    )

    forward_final = float(forward_path[-1])
    reversed_final = float(reversed_path[-1])
    difference = forward_final - reversed_final
    percent_difference = difference / reversed_final if reversed_final != 0 else float("nan")

    return SequenceRiskResult(
        annual_returns_forward=returns,
        annual_returns_reversed=reversed_returns,
        arithmetic_mean_return=float(np.mean(returns)),
        forward_path=forward_path,
        reversed_path=reversed_path,
        forward_final=forward_final,
        reversed_final=reversed_final,
        difference=difference,
        percent_difference=percent_difference,
    )
