import pandas as pd

from data_observatory.synthetic import (
    _seed_from_key,
    synthetic_bounded_series,
    synthetic_level_series,
)


def test_seed_deterministic_for_same_key():
    assert _seed_from_key("gdp") == _seed_from_key("gdp")


def test_seed_differs_across_keys():
    assert _seed_from_key("gdp") != _seed_from_key("cpi")


def test_level_series_deterministic_reproducibility():
    s1 = synthetic_level_series("gdp", "2000-01-01", "2010-01-01", 1.0e12, 0.07, 0.05)
    s2 = synthetic_level_series("gdp", "2000-01-01", "2010-01-01", 1.0e12, 0.07, 0.05)
    pd.testing.assert_series_equal(s1, s2)


def test_level_series_anchors_first_value_at_base():
    s = synthetic_level_series("gdp", "2000-01-01", "2010-01-01", 1.0e12, 0.07, 0.05)
    # exp(log(x)) round-trips to within float64 precision, not bit-exactly
    assert abs(s.iloc[0] - 1.0e12) / 1.0e12 < 1e-9


def test_level_series_always_positive():
    s = synthetic_level_series("exports", "2000-01-01", "2020-01-01", 1.5e11, 0.08, 0.10)
    assert (s > 0).all()


def test_bounded_series_respects_bounds():
    s = synthetic_bounded_series(
        "unemployment_rate", "1995-01-01", "2023-01-01",
        mean_value=7.0, mean_reversion_speed=0.3, vol=5.0,  # deliberately high vol to try to escape bounds
        lower_bound=2.0, upper_bound=20.0,
    )
    assert (s >= 2.0).all()
    assert (s <= 20.0).all()


def test_bounded_series_deterministic_reproducibility():
    s1 = synthetic_bounded_series("cpi", "2000-01-01", "2015-01-01", 5.5, 0.4, 2.2, -2.0, 16.0)
    s2 = synthetic_bounded_series("cpi", "2000-01-01", "2015-01-01", 5.5, 0.4, 2.2, -2.0, 16.0)
    pd.testing.assert_series_equal(s1, s2)


def test_different_indicators_do_not_produce_identical_paths():
    s1 = synthetic_bounded_series("cpi", "2000-01-01", "2015-01-01", 5.5, 0.4, 2.2, -2.0, 16.0)
    s2 = synthetic_bounded_series("policy_rate", "2000-01-01", "2015-01-01", 5.5, 0.4, 2.2, -2.0, 16.0)
    assert not s1.equals(s2)
