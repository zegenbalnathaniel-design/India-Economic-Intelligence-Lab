"""Unit tests for analysis.regional."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from analysis import regional


def test_coefficient_of_variation_zero_for_identical_values():
    assert math.isclose(regional.coefficient_of_variation([5, 5, 5, 5]), 0.0, abs_tol=1e-9)


def test_coefficient_of_variation_matches_manual_computation():
    x = [10, 20, 30]
    mean = 20.0
    std = np.std(x, ddof=0)
    expected = std / mean * 100.0
    assert math.isclose(regional.coefficient_of_variation(x), expected)


def test_coefficient_of_variation_nan_for_insufficient_data():
    assert math.isnan(regional.coefficient_of_variation([5]))
    assert math.isnan(regional.coefficient_of_variation([]))


def _synthetic_converging_panel() -> pd.DataFrame:
    # Six states starting far apart, converging to a common band by the end
    # (sigma_convergence requires >=5 states per year to compute a CV).
    years = [f"{2000+i}-{str(2001+i)[-2:]}" for i in range(10)]
    starts = {"Rich1": 100, "Rich2": 95, "Mid1": 60, "Mid2": 58, "Poor1": 20, "Poor2": 18}
    ends = {"Rich1": 80, "Rich2": 78, "Mid1": 60, "Mid2": 58, "Poor1": 40, "Poor2": 38}
    rows = []
    for i, year in enumerate(years):
        frac = i / (len(years) - 1)
        for state in starts:
            value = starts[state] + (ends[state] - starts[state]) * frac
            rows.append({"state": state, "financial_year": year,
                         "percapita_nsdp_constant_prices_inr_SPLICED": value})
    return pd.DataFrame(rows)


def test_sigma_convergence_detects_falling_dispersion():
    panel = _synthetic_converging_panel()
    result = regional.sigma_convergence(panel)
    assert result.direction == "converging"
    assert result.trend_slope_pct_per_year < 0
    # CV at the first year should be much larger than at the last year.
    first_cv = result.by_year.iloc[0]["cv_pct"]
    last_cv = result.by_year.iloc[-1]["cv_pct"]
    assert first_cv > last_cv


def test_sigma_convergence_detects_rising_dispersion():
    panel = _synthetic_converging_panel()
    # Reverse the years to flip convergence into divergence.
    panel["financial_year"] = panel["financial_year"].map(
        dict(zip(panel["financial_year"].unique(), reversed(panel["financial_year"].unique())))
    )
    result = regional.sigma_convergence(panel)
    assert result.direction == "diverging"


def test_beta_convergence_negative_slope_when_poor_states_grow_faster():
    panel = _synthetic_converging_panel()
    result = regional.beta_convergence(panel)
    assert result.direction == "consistent with convergence"
    assert result.slope < 0
    # Poor states' average annual growth should exceed the rich states'.
    by_state = result.per_state.set_index("state")["avg_annual_growth_pct"]
    assert by_state["Poor1"] > by_state["Rich1"]
    assert by_state["Poor2"] > by_state["Rich2"]


def test_beta_convergence_insufficient_data():
    panel = pd.DataFrame({
        "state": ["A", "B"],
        "financial_year": ["2020-21", "2020-21"],
        "percapita_nsdp_constant_prices_inr_SPLICED": [100, 200],
    })
    result = regional.beta_convergence(panel)
    assert result.direction == "insufficient data"


def test_rank_states_latest_sorted_descending():
    panel = _synthetic_converging_panel()
    ranked = regional.rank_states_latest(panel)
    assert list(ranked["rank"]) == list(range(1, len(ranked) + 1))
    assert ranked["percapita_nsdp_inr"].is_monotonic_decreasing
