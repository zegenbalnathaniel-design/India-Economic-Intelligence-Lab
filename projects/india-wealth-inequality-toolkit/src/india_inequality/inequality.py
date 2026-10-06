"""Income and wealth inequality measures.

Every function takes a 1-D array-like of non-negative numeric values — one
row per unit of observation (person, household, taxpayer...). None of these
functions fetch, fabricate, or assume any particular dataset: they are pure
statistics of whatever distribution you pass in.

Mathematical notes
-------------------
Let x_1 <= x_2 <= ... <= x_n be the sorted values, with cumulative sums
S_k = sum_{i<=k} x_i and S_n = total.

**Gini coefficient** (discrete, rank-based form — algebraically identical to
the area between the Lorenz curve and the line of equality):

    G = [2 * sum_{i=1}^{n} i * x_i  -  (n + 1) * S_n] / (n * S_n)

G = 0 is perfect equality, G -> 1 is maximal concentration in the limit of
large n. This formula assumes x_i >= 0; it is not well-defined for
distributions with negative net worth without a separate convention (see
Limitations in METHODOLOGY.md), so negative values raise.

**Lorenz curve**: the cumulative population share (x-axis) against the
cumulative value share (y-axis), both running from (0,0) to (1,1).

**Percentile share**: the fraction of total value held by units between the
`lower` and `upper` population percentiles (0-100), e.g. percentile_share(x,
90, 100) is the top-10% share.

**Palma ratio**: ratio of the top-10% share to the bottom-40% share
(Palma, 2011) — designed to be insensitive to the "stable middle" and to
focus on the tails where most of the cross-country variation in inequality
actually occurs.

**Concentration ratio**: the share of total value held by the top `n` units
by value (a market-concentration-style measure; useful on short lists such
as "top 100 billionaires" where percentile shares are noisy).
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def _sorted_values(values) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    if x.ndim != 1:
        raise ValueError("values must be a 1-D array-like.")
    if x.size == 0:
        raise ValueError("values must contain at least one observation.")
    if np.any(np.isnan(x)):
        raise ValueError("values must not contain NaN; drop or impute first.")
    if np.any(x < 0):
        raise ValueError(
            "calculate_gini and friends assume non-negative values. "
            "Negative net worth (debt exceeding assets) requires a different "
            "convention — see METHODOLOGY.md, section 'Negative wealth'."
        )
    return np.sort(x)


def calculate_gini(values) -> float:
    """Gini coefficient of a distribution of non-negative values.

    Edge cases: a single observation returns 0.0 (no inequality is
    measurable among one unit); a distribution that sums to zero (everyone
    has nothing) also returns 0.0 rather than dividing by zero.
    """
    x = _sorted_values(values)
    n = x.size
    total = x.sum()
    if n == 1 or total == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * x) - (n + 1) * total) / (n * total))


def lorenz_curve(values) -> pd.DataFrame:
    """Lorenz curve as a DataFrame with columns `population_share` and
    `value_share`, starting at (0, 0) and ending at (1, 1).
    """
    x = _sorted_values(values)
    n = x.size
    total = x.sum()
    cum = np.cumsum(x)
    value_share = np.concatenate([[0.0], cum / total if total > 0 else cum])
    population_share = np.arange(0, n + 1) / n
    return pd.DataFrame(
        {"population_share": population_share, "value_share": value_share}
    )


def percentile_share(values, lower: float, upper: float) -> float:
    """Share of total value held by population percentiles [lower, upper].

    `lower` and `upper` are in [0, 100] with lower < upper. Boundaries fall
    on population rank, not value rank — e.g. `percentile_share(x, 90, 100)`
    is literally "the richest 10% of units by count."
    """
    if not (0 <= lower < upper <= 100):
        raise ValueError("Require 0 <= lower < upper <= 100.")
    x = _sorted_values(values)
    n = x.size
    total = x.sum()
    if total == 0:
        return 0.0
    cum = np.cumsum(x)
    lo_idx = int(round(lower / 100.0 * n))
    hi_idx = int(round(upper / 100.0 * n))
    hi_idx = max(hi_idx, lo_idx + 1)  # guarantee at least one unit in a tiny sample
    hi_idx = min(hi_idx, n)
    lo_sum = cum[lo_idx - 1] if lo_idx > 0 else 0.0
    hi_sum = cum[hi_idx - 1]
    return float((hi_sum - lo_sum) / total)


def top_decile_share(values) -> float:
    """Share of total value held by the top 10% of units. Shorthand for
    `percentile_share(values, 90, 100)`."""
    return percentile_share(values, 90, 100)


def bottom_half_share(values) -> float:
    """Share of total value held by the bottom 50% of units. Shorthand for
    `percentile_share(values, 0, 50)`."""
    return percentile_share(values, 0, 50)


def palma_ratio(values) -> float:
    """Palma ratio: top-10% share divided by bottom-40% share.

    Undefined (returns `inf`) if the bottom 40% holds exactly zero, which is
    possible — and informative — for wealth (as opposed to income)
    distributions where many households have ~zero net worth.
    """
    bottom_40 = percentile_share(values, 0, 40)
    top_10 = percentile_share(values, 90, 100)
    if bottom_40 == 0:
        return float("inf")
    return float(top_10 / bottom_40)


def concentration_ratio(values, n: int) -> float:
    """Share of total value held by the top `n` units (by value), not by
    percentile. Useful for small, discrete populations (e.g. "top 10 firms
    by market cap") where a percentile cut would be too coarse.
    """
    x = _sorted_values(values)
    total = x.sum()
    if n <= 0:
        raise ValueError("n must be a positive integer.")
    if total == 0:
        return 0.0
    n = min(n, x.size)
    return float(x[-n:].sum() / total)


def summary_table(values) -> pd.DataFrame:
    """One-row convenience summary combining the measures above, for
    quick reporting (e.g. in a notebook or Streamlit metric row)."""
    return pd.DataFrame(
        [
            {
                "n": len(np.asarray(values)),
                "gini": calculate_gini(values),
                "top_10_share": top_decile_share(values),
                "bottom_50_share": bottom_half_share(values),
                "palma_ratio": palma_ratio(values),
            }
        ]
    )
