"""Tests for the public indicator functions and IndicatorResult."""

from __future__ import annotations

import pandas as pd
import pytest

import india_econ as ie
from india_econ._registry import REGISTRY

ALL_FUNCTIONS = [
    ie.gdp,
    ie.inflation,
    ie.unemployment,
    ie.trade,
    ie.exchange_rate,
    ie.interest_rates,
    ie.government_finance,
    ie.household_finance,
]


@pytest.mark.parametrize("func", ALL_FUNCTIONS)
def test_each_function_returns_indicator_result(func):
    result = func(allow_live=False)
    assert isinstance(result, ie.IndicatorResult)
    assert isinstance(result.data, (pd.Series, pd.DataFrame))
    assert len(result.data) > 0


@pytest.mark.parametrize("func", ALL_FUNCTIONS)
def test_each_function_is_synthetic_when_live_disabled(func):
    result = func(allow_live=False)
    assert result.source == "synthetic"
    assert result.metadata["status"] == "synthetic"


@pytest.mark.parametrize("func", ALL_FUNCTIONS)
def test_metadata_has_required_fields(func):
    result = func(allow_live=False)
    for key in ("indicator", "provider", "url", "definition", "unit", "frequency", "status", "source"):
        assert key in result.metadata, f"missing metadata key: {key}"


def test_metadata_is_attached_to_pandas_attrs():
    result = ie.inflation(allow_live=False)
    assert result.data.attrs.get("status") == "synthetic"
    assert result.data.attrs.get("indicator") == "inflation"


def test_is_live_helper():
    result = ie.inflation(allow_live=False)
    assert result.is_live() is False


def test_gdp_has_level_and_growth_columns():
    result = ie.gdp(allow_live=False)
    assert isinstance(result.data, pd.DataFrame)
    assert "gdp_current_usd" in result.data.columns
    assert "gdp_growth_pct" in result.data.columns


def test_trade_has_exports_and_imports():
    result = ie.trade(allow_live=False)
    assert set(result.data.columns) == {"exports_usd", "imports_usd"}


def test_government_finance_columns():
    result = ie.government_finance(allow_live=False)
    assert set(result.data.columns) == {"fiscal_balance_pct_gdp", "government_debt_pct_gdp"}


def test_household_finance_columns():
    result = ie.household_finance(allow_live=False)
    assert set(result.data.columns) == {"gross_savings_pct_gdp", "domestic_credit_private_pct_gdp"}


def test_inflation_is_a_named_series():
    result = ie.inflation(allow_live=False)
    assert isinstance(result.data, pd.Series)
    assert result.data.name == "cpi_inflation_pct"


def test_date_range_filtering():
    result = ie.inflation(start=2015, end=2018, allow_live=False)
    assert list(result.data.index) == [2015, 2016, 2017, 2018]


def test_date_range_filtering_open_start():
    result = ie.unemployment(end=2003, allow_live=False)
    assert max(result.data.index) == 2003
    assert min(result.data.index) <= 2003


def test_date_range_filtering_open_end():
    result = ie.unemployment(start=2020, allow_live=False)
    assert min(result.data.index) == 2020


def test_synthetic_data_is_deterministic_across_calls():
    first = ie.exchange_rate(start=2005, end=2010, allow_live=False)
    second = ie.exchange_rate(start=2005, end=2010, allow_live=False)
    pd.testing.assert_series_equal(first.data, second.data)


def test_get_metadata_matches_registry_for_all_indicators():
    for name in REGISTRY:
        meta = ie.get_metadata(name)
        assert meta["name"] == name
        assert meta["url"].startswith("https://api.worldbank.org/")


def test_get_metadata_unknown_indicator_raises():
    with pytest.raises(ie.UnknownIndicatorError):
        ie.get_metadata("definitely_not_a_real_indicator")


def test_invalid_date_range_raises():
    with pytest.raises(ie.InvalidDateRangeError):
        ie.gdp(start=2020, end=2010, allow_live=False)


def test_invalid_date_type_raises():
    with pytest.raises(ie.InvalidDateRangeError):
        ie.gdp(start="not-a-year", allow_live=False)


def test_unknown_indicator_error_is_an_india_econ_error():
    assert issubclass(ie.UnknownIndicatorError, ie.IndiaEconError)
    assert issubclass(ie.InvalidDateRangeError, ie.IndiaEconError)
    assert issubclass(ie.DataFetchError, ie.IndiaEconError)
