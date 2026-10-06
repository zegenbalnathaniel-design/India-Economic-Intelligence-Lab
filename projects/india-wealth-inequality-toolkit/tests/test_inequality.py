"""Unit tests for india_inequality.inequality — verified against closed-form
and textbook edge cases, not against any particular real dataset."""
from __future__ import annotations

import math

import numpy as np
import pytest

from india_inequality import inequality as ineq


def test_gini_zero_for_perfect_equality():
    x = np.full(50, 7.0)
    assert math.isclose(ineq.calculate_gini(x), 0.0, abs_tol=1e-12)


def test_gini_single_observation_is_zero():
    assert ineq.calculate_gini([42.0]) == 0.0


def test_gini_all_zero_is_zero_not_nan():
    assert ineq.calculate_gini([0.0, 0.0, 0.0]) == 0.0


def test_gini_matches_closed_form_for_one_holder_of_everything():
    # n-1 units have 0, one unit has everything: G = (n-1)/n exactly.
    n = 5
    x = np.zeros(n)
    x[-1] = 100.0
    assert math.isclose(ineq.calculate_gini(x), (n - 1) / n, rel_tol=1e-9)


def test_gini_rejects_negative_values():
    with pytest.raises(ValueError):
        ineq.calculate_gini([-1.0, 2.0, 3.0])


def test_gini_rejects_empty_input():
    with pytest.raises(ValueError):
        ineq.calculate_gini([])


def test_lorenz_curve_endpoints_and_monotone():
    x = [1, 4, 2, 9, 3, 7, 5]
    curve = ineq.lorenz_curve(x)
    assert math.isclose(curve["population_share"].iloc[0], 0.0)
    assert math.isclose(curve["value_share"].iloc[0], 0.0)
    assert math.isclose(curve["population_share"].iloc[-1], 1.0)
    assert math.isclose(curve["value_share"].iloc[-1], 1.0)
    assert curve["value_share"].is_monotonic_increasing


def test_percentile_share_full_population_is_one():
    x = np.random.default_rng(0).uniform(1, 100, size=200)
    assert math.isclose(ineq.percentile_share(x, 0, 100), 1.0, rel_tol=1e-9)


def test_percentile_share_rejects_bad_bounds():
    with pytest.raises(ValueError):
        ineq.percentile_share([1, 2, 3], 50, 10)
    with pytest.raises(ValueError):
        ineq.percentile_share([1, 2, 3], -5, 10)


def test_top_and_bottom_share_near_expected_for_uniform_distribution():
    x = np.full(1000, 5.0)  # perfectly equal -> every slice gets its pop share
    assert math.isclose(ineq.top_decile_share(x), 0.10, rel_tol=1e-6)
    assert math.isclose(ineq.bottom_half_share(x), 0.50, rel_tol=1e-6)


def test_palma_ratio_equal_distribution():
    x = np.full(1000, 2.0)
    # top-10 share / bottom-40 share = 0.10 / 0.40 under perfect equality
    assert math.isclose(ineq.palma_ratio(x), 0.25, rel_tol=1e-6)


def test_palma_ratio_infinite_when_bottom_40_has_nothing():
    x = np.array([0.0, 0.0, 0.0, 0.0, 10.0])
    assert ineq.palma_ratio(x) == float("inf")


def test_concentration_ratio_top_one_matches_max_share():
    x = np.array([1.0, 1.0, 1.0, 1.0, 6.0])
    assert math.isclose(ineq.concentration_ratio(x, 1), 6.0 / 10.0)


def test_concentration_ratio_rejects_non_positive_n():
    with pytest.raises(ValueError):
        ineq.concentration_ratio([1, 2, 3], 0)


def test_summary_table_has_expected_columns():
    out = ineq.summary_table([1, 2, 3, 4, 5])
    for col in ("n", "gini", "top_10_share", "bottom_50_share", "palma_ratio"):
        assert col in out.columns
