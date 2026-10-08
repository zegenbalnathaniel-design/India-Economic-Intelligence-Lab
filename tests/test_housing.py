"""Unit tests for analysis.housing."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from analysis import housing


def test_parse_residex_quarter_handles_format_variants():
    # The real source data mixes 'Jun-2013', 'JUN-2018', 'DEC 2018', 'Mar 2019'
    # in the SAME column across different years -- all four must parse to the
    # correct, comparable period.
    assert housing.parse_residex_quarter("Jun-2013") == housing.parse_residex_quarter("JUN 2013")
    assert housing.parse_residex_quarter("Dec-2018") == housing.parse_residex_quarter("DEC 2018")
    assert housing.parse_residex_quarter("Mar 2019") < housing.parse_residex_quarter("Jun 2019")


def test_parse_residex_quarter_rejects_garbage():
    with pytest.raises(ValueError):
        housing.parse_residex_quarter("not a quarter")


def test_sort_quarters_fixes_alphabetical_misordering():
    # Alphabetically, 'Dec' < 'Jun' < 'Mar' < 'Sep' -- a naive string sort
    # would put Dec-2024 before Jun-2013. sort_quarters must not do that.
    df = pd.DataFrame({"quarter": ["Dec 2024", "Jun-2013", "Mar 2019", "Sep-2017"]})
    sorted_df = housing.sort_quarters(df)
    assert list(sorted_df["quarter"]) == ["Jun-2013", "Sep-2017", "Mar 2019", "Dec 2024"]


def test_emi_matches_closed_form_annuity():
    P, r, n_years = 1_000_000, 0.09, 20
    result = housing.emi(P, r, n_years)
    n = n_years * 12
    rm = r / 12
    expected = P * rm * (1 + rm) ** n / ((1 + rm) ** n - 1)
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_emi_zero_rate_is_principal_over_months():
    P, n_years = 1_200_000, 10
    result = housing.emi(P, 0.0, n_years)
    assert math.isclose(result, P / (n_years * 12))


def test_emi_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        housing.emi(-100, 0.08, 20)
    with pytest.raises(ValueError):
        housing.emi(100, 0.08, 0)
    with pytest.raises(ValueError):
        housing.emi(100, -0.01, 20)


def test_price_to_income_ratio_basic():
    assert math.isclose(housing.price_to_income_ratio(500_000, 100_000), 5.0)


def test_price_to_income_rejects_nonpositive_income():
    with pytest.raises(ValueError):
        housing.price_to_income_ratio(100, 0)


def test_mortgage_payment_to_income_ratio_basic():
    assert math.isclose(housing.mortgage_payment_to_income_ratio(10_000, 50_000), 0.2)


def test_mortgage_payment_rejects_nonpositive_income():
    with pytest.raises(ValueError):
        housing.mortgage_payment_to_income_ratio(1000, 0)


def _mini_price_levels() -> pd.DataFrame:
    return pd.DataFrame({
        "city": ["Mumbai", "Mumbai", "Pune"],
        "quarter": ["Jun-2024", "Sep-2024", "Sep-2024"],
        "composite_price_inr_per_sqm": [100000, 105000, 60000],
    })


def _mini_nsdp_current() -> pd.DataFrame:
    return pd.DataFrame({
        "state": ["Maharashtra", "Maharashtra"],
        "financial_year": ["2023-24", "2024-25"],
        "percapita_nsdp_current_prices_inr": [278681, 309340],
    })


def test_city_affordability_uses_latest_quarter_by_default():
    result = housing.city_affordability(_mini_price_levels(), _mini_nsdp_current(), "Mumbai")
    assert result.quarter == "Sep-2024"
    assert result.state == "Maharashtra"
    assert result.price_per_sqm == 105000
    assert result.income_is_state_proxy is True


def test_city_affordability_uses_latest_income_year():
    result = housing.city_affordability(_mini_price_levels(), _mini_nsdp_current(), "Pune")
    assert math.isclose(result.annual_income_proxy, 309340)


def test_city_affordability_unknown_city_raises():
    with pytest.raises(KeyError):
        housing.city_affordability(_mini_price_levels(), _mini_nsdp_current(), "Atlantis")


def test_city_affordability_price_to_income_consistent_with_formula():
    result = housing.city_affordability(_mini_price_levels(), _mini_nsdp_current(), "Mumbai", unit_size_sqm=70.0)
    expected_unit_price = 105000 * 70.0
    expected_pi = expected_unit_price / result.annual_income_proxy
    assert math.isclose(result.unit_price, expected_unit_price)
    assert math.isclose(result.price_to_income, expected_pi)


def test_affordability_across_cities_sorted_descending():
    df = housing.affordability_across_cities(_mini_price_levels(), _mini_nsdp_current())
    assert len(df) == 2
    assert df["price_to_income"].is_monotonic_decreasing
