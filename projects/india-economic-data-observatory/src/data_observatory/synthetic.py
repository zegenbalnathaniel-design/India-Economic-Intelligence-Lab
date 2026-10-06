"""Deterministic synthetic fallback series.

Used only when a live fetch fails or `allow_live=False` is passed. Every
series produced here is:

- **Deterministic**: seeded from the indicator's key, so re-running the
  pipeline produces byte-identical synthetic output (reproducibility).
- **Economically plausible in shape**: a mean-reverting (Ornstein–
  Uhlenbeck-like) process for bounded rates (unemployment %, CPI inflation
  %, policy rate %, exchange rate), or a geometric-random-walk-with-drift
  for unbounded growth levels (GDP, exports, imports). The specific
  starting level, drift, and volatility per indicator are *illustrative
  order-of-magnitude choices*, not fitted to or copied from any real
  dataset, and must never be read as a forecast or as real history.
- **Clearly attributable**: every value produced here is always wrapped in
  a `Metadata` with `status=DataStatus.SYNTHETIC` by `loaders.py` before it
  reaches a caller; nothing in this module itself claims to be real data.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def _seed_from_key(key: str) -> int:
    """Deterministic 32-bit seed from an indicator key string."""
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % (2 ** 32)


def synthetic_level_series(
    key: str,
    start: str,
    end: str,
    base_value: float,
    annual_drift: float,
    annual_vol: float,
    freq: str = "A",
) -> pd.Series:
    """Geometric random walk with drift, for unbounded "level" indicators
    (GDP in current US$, exports/imports in current US$, etc.).

    `annual_drift` and `annual_vol` are illustrative annualized log-return
    parameters (e.g. 0.06 and 0.08 for a ~6%/yr-growth, moderately volatile
    series), not estimates from any real series.
    """
    dates = pd.date_range(start=start, end=end, freq=freq)
    if len(dates) == 0:
        dates = pd.DatetimeIndex([pd.Timestamp(start)])
    n = len(dates)
    rng = np.random.default_rng(_seed_from_key(key))
    steps_per_year = {"A": 1, "Y": 1, "Q": 4, "M": 12}.get(freq, 1)
    dt = 1.0 / steps_per_year
    shocks = rng.normal(
        (annual_drift - 0.5 * annual_vol ** 2) * dt,
        annual_vol * np.sqrt(dt),
        size=n,
    )
    log_level = np.log(base_value) + np.cumsum(shocks) - shocks[0] + shocks[0]
    # anchor first observation exactly at base_value, then apply the walk
    log_level = np.log(base_value) + np.concatenate([[0.0], np.cumsum(shocks)[:-1]])
    values = np.exp(log_level)
    return pd.Series(values, index=dates, name=key)


def synthetic_bounded_series(
    key: str,
    start: str,
    end: str,
    mean_value: float,
    mean_reversion_speed: float,
    vol: float,
    lower_bound: float = 0.0,
    upper_bound: float = float("inf"),
    freq: str = "A",
) -> pd.Series:
    """Mean-reverting (discretized Ornstein-Uhlenbeck) process clipped to
    `[lower_bound, upper_bound]`, for indicators that economically cannot
    wander unboundedly (unemployment rate %, CPI inflation %, policy
    interest rate %, LFPR %, fiscal balance % of GDP, exchange rate).
    """
    dates = pd.date_range(start=start, end=end, freq=freq)
    if len(dates) == 0:
        dates = pd.DatetimeIndex([pd.Timestamp(start)])
    n = len(dates)
    rng = np.random.default_rng(_seed_from_key(key + "::bounded"))
    steps_per_year = {"A": 1, "Y": 1, "Q": 4, "M": 12}.get(freq, 1)
    dt = 1.0 / steps_per_year

    values = np.empty(n)
    values[0] = mean_value
    for i in range(1, n):
        shock = rng.normal(0.0, vol * np.sqrt(dt))
        values[i] = values[i - 1] + mean_reversion_speed * (mean_value - values[i - 1]) * dt + shock
    values = np.clip(values, lower_bound, upper_bound)
    return pd.Series(values, index=dates, name=key)
