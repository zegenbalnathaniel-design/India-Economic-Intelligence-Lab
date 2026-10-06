import numpy as np
import pytest

from sip_monte_carlo.closed_form import annuity_factor, future_value_growing_annuity


def test_annuity_factor_zero_rate_is_n_periods():
    assert annuity_factor(0.0, 12) == 12.0


def test_annuity_factor_positive_rate():
    r = 0.01
    expected = ((1.01) ** 12 - 1) / 0.01
    assert annuity_factor(r, 12) == pytest.approx(expected)


def test_future_value_no_growth_matches_manual_loop():
    r = 0.008
    monthly_contribution = 1000.0
    years = 5
    balance = 0.0
    for _year in range(years):
        for _month in range(12):
            balance = balance * (1 + r) + monthly_contribution
    fv = future_value_growing_annuity(monthly_contribution, years, r, 0.0, 0.0)
    assert fv == pytest.approx(balance, rel=1e-12)


def test_future_value_with_growth_matches_manual_loop():
    r = 0.006
    monthly_contribution = 2000.0
    years = 7
    growth = 0.1
    initial_capital = 50000.0
    balance = initial_capital
    for year in range(years):
        contribution = monthly_contribution * (1 + growth) ** year
        for _month in range(12):
            balance = balance * (1 + r) + contribution
    fv = future_value_growing_annuity(monthly_contribution, years, r, growth, initial_capital)
    assert fv == pytest.approx(balance, rel=1e-12)


def test_future_value_requires_positive_duration():
    with pytest.raises(ValueError):
        future_value_growing_annuity(1000.0, 0, 0.01, 0.0, 0.0)
