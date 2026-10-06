"""Deterministic, clearly-labelled synthetic fallback data.

These series are NOT real economic data. They exist so the package still
returns something usable (with the right shape, column names, and units)
when a live fetch to the World Bank API fails or is disabled, and every
value produced here is tagged with ``status="synthetic"`` by the calling
code in :mod:`india_econ.indicators` -- never silently presented as real.

Generation is seeded from a hash of the indicator name and column name, so
the same call always returns the same numbers (useful for tests and for
not misleading anyone into thinking the numbers are "live but different
each time").
"""

from __future__ import annotations

import hashlib

import numpy as np

from ._registry import SyntheticSpec


def _seed_for(indicator_name: str, column: str) -> int:
    digest = hashlib.sha256(f"india_econ::{indicator_name}::{column}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big")


def synthetic_series(
    indicator_name: str, column: str, spec: SyntheticSpec, start_year: int, end_year: int
) -> dict:
    """Generate one deterministic synthetic column as {year: value}."""
    if end_year < start_year:
        return {}

    rng = np.random.default_rng(_seed_for(indicator_name, column))
    n_years = end_year - start_year + 1
    values = np.empty(n_years, dtype=float)
    level = spec.base
    for i in range(n_years):
        noise = rng.normal(loc=0.0, scale=spec.vol)
        if spec.mean_revert_to is not None:
            pull = 0.15 * (spec.mean_revert_to - level)
            level = level + pull + noise
        else:
            level = level + spec.drift + noise
        values[i] = level

    values = np.round(values, spec.round_to)
    if spec.round_to == 0:
        values = values.astype(float)

    years = range(start_year, end_year + 1)
    return {year: float(value) for year, value in zip(years, values)}
