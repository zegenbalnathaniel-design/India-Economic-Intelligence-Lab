"""india_inequality — a small, dependency-light toolkit for income and wealth
inequality measurement, plus a deterministic household wealth-composition
simulator used to illustrate why asset mix (not just income) drives long-run
wealth accumulation.

Two independent surfaces:

- ``india_inequality.inequality``: Gini coefficient, Lorenz curve, percentile
  shares, Palma ratio and concentration ratios for any numeric distribution
  (income, wealth, or anything else you hand it).
- ``india_inequality.wealth``: the composition-effect / r-g simulator.

Nothing in this package fetches or fabricates real survey data. Bring your
own CSV, or use the clearly-labelled synthetic example shipped in ``data/``.
"""
from .inequality import (
    calculate_gini,
    lorenz_curve,
    percentile_share,
    top_decile_share,
    bottom_half_share,
    palma_ratio,
    concentration_ratio,
)
from .wealth import composition_effect, monte_carlo, rminusg_frame

__all__ = [
    "calculate_gini",
    "lorenz_curve",
    "percentile_share",
    "top_decile_share",
    "bottom_half_share",
    "palma_ratio",
    "concentration_ratio",
    "composition_effect",
    "monte_carlo",
    "rminusg_frame",
]

__version__ = "0.1.0"
