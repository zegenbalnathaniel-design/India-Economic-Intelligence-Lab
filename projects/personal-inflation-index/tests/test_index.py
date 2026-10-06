"""Tests for personal_inflation.index.

Run with:
    cd projects/personal-inflation-index && python3 -m pytest tests/ -q
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from personal_inflation.index import (
    DEFAULT_CATEGORIES,
    compare_to_reference,
    laspeyres_index,
    normalize_weights,
    personal_index_time_series,
)


# ---------------------------------------------------------------------------
# normalize_weights
# ---------------------------------------------------------------------------

def test_normalize_weights_sums_to_one():
    weights = {"food": 2.0, "housing": 1.0, "transport": 1.0}
    norm = normalize_weights(weights)
    assert pytest.approx(sum(norm.values()), rel=1e-12) == 1.0
    # relative proportions preserved
    assert pytest.approx(norm["food"], rel=1e-12) == 0.5
    assert pytest.approx(norm["housing"], rel=1e-12) == 0.25


def test_normalize_weights_handles_percentage_style_input():
    weights = {"food": 50.0, "housing": 30.0, "other": 20.0}
    norm = normalize_weights(weights)
    assert pytest.approx(sum(norm.values()), rel=1e-12) == 1.0
    assert pytest.approx(norm["food"], rel=1e-9) == 0.5


def test_normalize_weights_already_normalized_is_unchanged():
    weights = {"food": 0.6, "housing": 0.4}
    norm = normalize_weights(weights)
    assert pytest.approx(norm["food"], rel=1e-12) == 0.6
    assert pytest.approx(norm["housing"], rel=1e-12) == 0.4


def test_normalize_weights_rejects_negative_weight():
    with pytest.raises(ValueError):
        normalize_weights({"food": 0.5, "housing": -0.1})


def test_normalize_weights_rejects_all_zero():
    with pytest.raises(ValueError):
        normalize_weights({"food": 0.0, "housing": 0.0})


def test_normalize_weights_rejects_empty():
    with pytest.raises(ValueError):
        normalize_weights({})


# ---------------------------------------------------------------------------
# laspeyres_index: hand-computed example (REQUIRED correctness check)
# ---------------------------------------------------------------------------

def test_laspeyres_hand_computed_three_category_example():
    """Hand-compute a 3-category Laspeyres index and compare to the function.

    Basket: food (w=0.5), housing (w=0.3), transport (w=0.2).
    Base prices:    food=100, housing=200, transport=50
    Current prices: food=110, housing=220, transport=40

    Price relatives:
        food:      110/100 = 1.10
        housing:   220/200 = 1.10
        transport:  40/50  = 0.80

    By hand:
        I = 100 * (0.5*1.10 + 0.3*1.10 + 0.2*0.80)
          = 100 * (0.55 + 0.33 + 0.16)
          = 100 * 1.04
          = 104.0
    """
    weights = {"food": 0.5, "housing": 0.3, "transport": 0.2}
    base_prices = {"food": 100.0, "housing": 200.0, "transport": 50.0}
    current_prices = {"food": 110.0, "housing": 220.0, "transport": 40.0}

    expected = 104.0
    result = laspeyres_index(base_prices, current_prices, weights)
    assert pytest.approx(result, rel=1e-9) == expected


def test_laspeyres_hand_computed_two_category_example():
    """A second, independent hand-computed check with just two categories.

    Basket: food (w=0.7), other (w=0.3).
    Base prices:    food=50,  other=100
    Current prices: food=60,  other=90

    Price relatives: food = 60/50 = 1.20, other = 90/100 = 0.90

    By hand:
        I = 100 * (0.7*1.20 + 0.3*0.90) = 100 * (0.84 + 0.27) = 111.0
    """
    weights = {"food": 0.7, "other": 0.3}
    base_prices = {"food": 50.0, "other": 100.0}
    current_prices = {"food": 60.0, "other": 90.0}

    assert pytest.approx(laspeyres_index(base_prices, current_prices, weights), rel=1e-9) == 111.0


# ---------------------------------------------------------------------------
# laspeyres_index: unchanged basket must equal exactly 100 (REQUIRED check)
# ---------------------------------------------------------------------------

def test_unchanged_prices_give_exactly_100():
    weights = {cat: 1.0 for cat in DEFAULT_CATEGORIES}
    base_prices = {cat: 100.0 + i for i, cat in enumerate(DEFAULT_CATEGORIES)}
    current_prices = dict(base_prices)  # identical -> no price change anywhere

    result = laspeyres_index(base_prices, current_prices, weights)
    assert result == pytest.approx(100.0, abs=1e-9)


def test_unchanged_prices_give_exactly_100_with_uneven_weights():
    weights = {"food": 0.6, "housing": 0.25, "other": 0.15}
    base_prices = {"food": 42.0, "housing": 1337.0, "other": 7.5}
    result = laspeyres_index(base_prices, base_prices, weights)
    assert result == pytest.approx(100.0, abs=1e-9)


# ---------------------------------------------------------------------------
# weights not summing to 1 -> normalized (REQUIRED check, documented choice)
# ---------------------------------------------------------------------------

def test_laspeyres_normalizes_weights_not_summing_to_one():
    base_prices = {"food": 100.0, "housing": 100.0}
    current_prices = {"food": 120.0, "housing": 100.0}

    # weights sum to 2, not 1 -- should behave identically to the
    # normalized {food: 0.5, housing: 0.5} after rescaling
    unnormalized_weights = {"food": 1.0, "housing": 1.0}
    normalized_weights = {"food": 0.5, "housing": 0.5}

    result_unnormalized = laspeyres_index(base_prices, current_prices, unnormalized_weights)
    result_normalized = laspeyres_index(base_prices, current_prices, normalized_weights)

    assert result_unnormalized == pytest.approx(result_normalized, rel=1e-9)
    assert result_unnormalized == pytest.approx(110.0, rel=1e-9)


# ---------------------------------------------------------------------------
# basket skewed toward faster-growing category -> higher index
# (REQUIRED check)
# ---------------------------------------------------------------------------

def test_skew_toward_faster_growing_category_yields_higher_index():
    base_prices = {"fast": 100.0, "slow": 100.0}
    current_prices = {"fast": 150.0, "slow": 105.0}  # fast grows much more

    skew_toward_fast = {"fast": 0.8, "slow": 0.2}
    skew_toward_slow = {"fast": 0.2, "slow": 0.8}

    index_fast_heavy = laspeyres_index(base_prices, current_prices, skew_toward_fast)
    index_slow_heavy = laspeyres_index(base_prices, current_prices, skew_toward_slow)

    assert index_fast_heavy > index_slow_heavy


# ---------------------------------------------------------------------------
# invalid inputs: missing price, negative price, zero price
# ---------------------------------------------------------------------------

def test_missing_category_price_raises_value_error():
    weights = {"food": 0.5, "housing": 0.5}
    base_prices = {"food": 100.0, "housing": 100.0}
    current_prices = {"food": 110.0}  # housing missing

    with pytest.raises(ValueError, match="missing current price"):
        laspeyres_index(base_prices, current_prices, weights)


def test_missing_base_price_raises_value_error():
    weights = {"food": 0.5, "housing": 0.5}
    base_prices = {"food": 100.0}  # housing missing
    current_prices = {"food": 110.0, "housing": 105.0}

    with pytest.raises(ValueError, match="missing base price"):
        laspeyres_index(base_prices, current_prices, weights)


def test_negative_price_raises_value_error():
    weights = {"food": 1.0}
    with pytest.raises(ValueError):
        laspeyres_index({"food": -10.0}, {"food": 20.0}, weights)

    with pytest.raises(ValueError):
        laspeyres_index({"food": 10.0}, {"food": -20.0}, weights)


def test_zero_price_raises_value_error():
    weights = {"food": 1.0}
    with pytest.raises(ValueError):
        laspeyres_index({"food": 0.0}, {"food": 20.0}, weights)


# ---------------------------------------------------------------------------
# personal_index_time_series
# ---------------------------------------------------------------------------

def test_time_series_base_period_equals_100():
    df = pd.DataFrame(
        {
            "food": [100.0, 110.0, 120.0],
            "housing": [100.0, 102.0, 104.0],
        },
        index=["2020-01", "2020-02", "2020-03"],
    )
    weights = {"food": 0.5, "housing": 0.5}
    series = personal_index_time_series(df, weights)

    assert series.loc["2020-01"] == pytest.approx(100.0, abs=1e-9)
    # matches a hand check for period 2: 100*(0.5*1.10 + 0.5*1.02) = 106.0
    assert series.loc["2020-02"] == pytest.approx(106.0, rel=1e-9)
    # period 3: 100*(0.5*1.20 + 0.5*1.04) = 112.0
    assert series.loc["2020-03"] == pytest.approx(112.0, rel=1e-9)


def test_time_series_respects_explicit_base_period():
    df = pd.DataFrame(
        {"food": [100.0, 200.0, 100.0]},
        index=["t0", "t1", "t2"],
    )
    weights = {"food": 1.0}
    series = personal_index_time_series(df, weights, base_period="t1")
    assert series.loc["t1"] == pytest.approx(100.0, abs=1e-9)
    assert series.loc["t0"] == pytest.approx(50.0, rel=1e-9)
    assert series.loc["t2"] == pytest.approx(50.0, rel=1e-9)


def test_time_series_missing_column_raises():
    df = pd.DataFrame({"food": [100.0, 110.0]}, index=["a", "b"])
    with pytest.raises(ValueError, match="missing a column"):
        personal_index_time_series(df, {"food": 0.5, "housing": 0.5})


def test_time_series_empty_dataframe_raises():
    with pytest.raises(ValueError, match="at least one period"):
        personal_index_time_series(pd.DataFrame(), {"food": 1.0})


def test_time_series_invalid_base_period_raises():
    df = pd.DataFrame({"food": [100.0, 110.0]}, index=["a", "b"])
    with pytest.raises(ValueError, match="not present"):
        personal_index_time_series(df, {"food": 1.0}, base_period="nonexistent")


# ---------------------------------------------------------------------------
# compare_to_reference
# ---------------------------------------------------------------------------

def test_compare_to_reference_computes_gap():
    personal = pd.Series([100.0, 112.0, 120.0], index=["t0", "t1", "t2"])
    reference = pd.Series([100.0, 105.0, 110.0], index=["t0", "t1", "t2"])

    out = compare_to_reference(personal, reference)

    assert list(out.columns) == ["personal_index", "reference_index", "gap_points", "gap_pct"]
    assert out.loc["t1", "gap_points"] == pytest.approx(7.0, rel=1e-9)
    assert out.loc["t2", "gap_points"] == pytest.approx(10.0, rel=1e-9)
    assert out.loc["t1", "gap_pct"] == pytest.approx(100.0 * 7.0 / 105.0, rel=1e-9)


def test_compare_to_reference_uses_only_common_periods():
    personal = pd.Series([100.0, 110.0], index=["t0", "t1"])
    reference = pd.Series([100.0, 103.0, 108.0], index=["t0", "t1", "t2"])

    out = compare_to_reference(personal, reference)
    assert set(out.index) == {"t0", "t1"}


def test_compare_to_reference_raises_on_no_overlap():
    personal = pd.Series([100.0], index=["t0"])
    reference = pd.Series([100.0], index=["other_period"])
    with pytest.raises(ValueError, match="no common periods"):
        compare_to_reference(personal, reference)


# ---------------------------------------------------------------------------
# default categories sanity
# ---------------------------------------------------------------------------

def test_default_categories_nonempty_and_unique():
    assert len(DEFAULT_CATEGORIES) == len(set(DEFAULT_CATEGORIES))
    assert len(DEFAULT_CATEGORIES) > 0
    assert "food" in DEFAULT_CATEGORIES
    assert "housing" in DEFAULT_CATEGORIES
