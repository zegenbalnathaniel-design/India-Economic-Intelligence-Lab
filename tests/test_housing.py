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


# ---------------------------------------------------------------------------
# Alternative income proxy: MoSPI HCES urban MPCE (additive, backward compatible)
# ---------------------------------------------------------------------------

def _mini_mpce_urban() -> pd.DataFrame:
    return pd.DataFrame({
        "state_ut": ["Maharashtra"],
        "average_monthly_per_capita_consumption_expenditure_inr": [7363],
    })


def test_city_affordability_default_income_source_is_nsdp():
    result = housing.city_affordability(_mini_price_levels(), _mini_nsdp_current(), "Mumbai")
    assert result.income_source == "nsdp"
    assert math.isclose(result.annual_income_proxy, 309340)
    assert "state per-capita nsdp" in result.income_caveat.lower()


def test_city_affordability_mpce_income_source_annualises_monthly_value():
    result = housing.city_affordability(
        _mini_price_levels(), _mini_nsdp_current(), "Mumbai",
        income_source="mpce", mpce_urban=_mini_mpce_urban(),
    )
    assert result.income_source == "mpce"
    assert math.isclose(result.annual_income_proxy, 7363 * 12)
    assert "do not label as city household income" in result.income_caveat.lower()
    expected_pi = result.unit_price / (7363 * 12)
    assert math.isclose(result.price_to_income, expected_pi)


def test_city_affordability_mpce_without_dataframe_raises():
    with pytest.raises(ValueError):
        housing.city_affordability(
            _mini_price_levels(), _mini_nsdp_current(), "Mumbai", income_source="mpce",
        )


def test_city_affordability_unknown_income_source_raises():
    with pytest.raises(ValueError):
        housing.city_affordability(
            _mini_price_levels(), _mini_nsdp_current(), "Mumbai", income_source="bogus",
        )


def test_affordability_across_cities_mpce_still_backward_compatible_default():
    # Omitting mpce_urban/income_source keeps the original NSDP-only behaviour.
    df = housing.affordability_across_cities(_mini_price_levels(), _mini_nsdp_current())
    assert set(df["income_source"]) == {"nsdp"}


def test_affordability_across_cities_can_use_mpce_proxy():
    df = housing.affordability_across_cities(
        _mini_price_levels(), _mini_nsdp_current(),
        mpce_urban=_mini_mpce_urban(), income_source="mpce",
    )
    assert len(df) == 2
    assert set(df["income_source"]) == {"mpce"}


# ---------------------------------------------------------------------------
# RPIPI -- relative_price_income_pressure
# ---------------------------------------------------------------------------

def _mini_residex_index() -> pd.DataFrame:
    return pd.DataFrame({
        "City": ["Mumbai", "Mumbai", "Mumbai", "Mumbai", "Pune"],
        "quarter_raw": ["Jun-2013", "Jun-2014", "Jun-2015", "Jun-2016", "Jun-2013"],
        "composite_index": [100.0, 150.0, 200.0, 300.0, 100.0],
    })


def _mini_nsdp_income_annual() -> pd.DataFrame:
    return pd.DataFrame({
        "state": ["Maharashtra"] * 4,
        "financial_year": ["2013-14", "2014-15", "2015-16", "2016-17"],
        "percapita_nsdp_current_prices_inr": [100000.0, 110000.0, 121000.0, 150000.0],
    })


def test_financial_year_of_quarter_maps_calendar_quarters_correctly():
    assert housing.financial_year_of_quarter("Jun-2018") == "2018-19"
    assert housing.financial_year_of_quarter("Sep-2018") == "2018-19"
    assert housing.financial_year_of_quarter("Dec-2018") == "2018-19"
    assert housing.financial_year_of_quarter("Mar-2018") == "2017-18"


def test_rpipi_base_period_normalised_to_100():
    result = housing.relative_price_income_pressure(_mini_residex_index(), _mini_nsdp_income_annual(), "Mumbai")
    assert result.base_financial_year == "2013-14"
    base_row = result.series.iloc[0]
    assert base_row["financial_year"] == "2013-14"
    assert math.isclose(base_row["rpipi"], 100.0)


def test_rpipi_known_value_price_outpaces_income():
    # Jun-2014: price ratio = 150/100 = 1.5; income ratio = 110000/100000 = 1.1
    # RPIPI = 100 * 1.5 / 1.1
    result = housing.relative_price_income_pressure(_mini_residex_index(), _mini_nsdp_income_annual(), "Mumbai")
    row = result.series[result.series["financial_year"] == "2014-15"].iloc[0]
    expected = 100.0 * (150.0 / 100.0) / (110000.0 / 100000.0)
    assert math.isclose(row["rpipi"], expected)
    assert row["rpipi"] > 100.0  # price outpaced income


def test_rpipi_known_value_income_outpaces_price_at_some_point():
    # Jun-2016: price ratio = 300/100 = 3.0; income ratio = 150000/100000 = 1.5
    # -> RPIPI = 200, price still ahead; check an engineered case where income wins instead.
    residex = pd.DataFrame({
        "City": ["TestCity"] * 2,
        "quarter_raw": ["Jun-2013", "Jun-2014"],
        "composite_index": [100.0, 110.0],
    })
    income = pd.DataFrame({
        "state": ["Maharashtra"] * 2,
        "financial_year": ["2013-14", "2014-15"],
        "percapita_nsdp_current_prices_inr": [100000.0, 200000.0],
    })
    import analysis.housing as h
    h.CITY_TO_STATE["TestCity"] = "Maharashtra"
    try:
        result = h.relative_price_income_pressure(residex, income, "TestCity")
        expected = 100.0 * 1.1 / 2.0
        assert math.isclose(result.latest_rpipi, expected)
        assert result.latest_rpipi < 100.0  # income outpaced price
    finally:
        del h.CITY_TO_STATE["TestCity"]


def test_rpipi_status_ok_with_sufficient_overlap():
    result = housing.relative_price_income_pressure(_mini_residex_index(), _mini_nsdp_income_annual(), "Mumbai")
    assert result.status == "ok"


def test_rpipi_insufficient_data_single_overlapping_year():
    residex = pd.DataFrame({
        "City": ["Mumbai"],
        "quarter_raw": ["Jun-2013"],
        "composite_index": [100.0],
    })
    income = pd.DataFrame({
        "state": ["Maharashtra"],
        "financial_year": ["2013-14"],
        "percapita_nsdp_current_prices_inr": [100000.0],
    })
    result = housing.relative_price_income_pressure(residex, income, "Mumbai")
    assert result.status == "insufficient data (<2 overlapping years)"
    assert math.isclose(result.latest_rpipi, 100.0)


def test_rpipi_unknown_city_raises():
    with pytest.raises(KeyError):
        housing.relative_price_income_pressure(_mini_residex_index(), _mini_nsdp_income_annual(), "Atlantis")


def test_rpipi_no_overlap_raises():
    residex = pd.DataFrame({
        "City": ["Mumbai"],
        "quarter_raw": ["Jun-2030"],
        "composite_index": [100.0],
    })
    with pytest.raises(ValueError):
        housing.relative_price_income_pressure(residex, _mini_nsdp_income_annual(), "Mumbai")


def test_rpipi_averages_multiple_quarters_within_a_financial_year():
    # Two quarters both inside FY2013-14 (Jun-2013 and Sep-2013) should be
    # averaged into a single annual price_index value, not duplicated rows.
    residex = pd.DataFrame({
        "City": ["Mumbai", "Mumbai", "Mumbai"],
        "quarter_raw": ["Jun-2013", "Sep-2013", "Jun-2014"],
        "composite_index": [100.0, 120.0, 150.0],
    })
    income = pd.DataFrame({
        "state": ["Maharashtra", "Maharashtra"],
        "financial_year": ["2013-14", "2014-15"],
        "percapita_nsdp_current_prices_inr": [100000.0, 110000.0],
    })
    result = housing.relative_price_income_pressure(residex, income, "Mumbai")
    assert len(result.series) == 2
    base_row = result.series.iloc[0]
    assert math.isclose(base_row["price_index"], (100.0 + 120.0) / 2)


# ---------------------------------------------------------------------------
# ICHASI cross-section fallback -- stress_index_cross_section
# ---------------------------------------------------------------------------

def _stress_price_levels() -> pd.DataFrame:
    # 5 cities, same quarter, hand-picked unit prices so price_to_income is
    # known exactly given the mini NSDP income below.
    return pd.DataFrame({
        "city": ["Mumbai", "Pune", "Nashik", "Nagpur", "Kolkata"],
        "quarter": ["Sep-2024"] * 5,
        "composite_price_inr_per_sqm": [100000, 90000, 80000, 70000, 60000],
    })


def _stress_nsdp_current() -> pd.DataFrame:
    return pd.DataFrame({
        "state": ["Maharashtra", "Maharashtra", "Maharashtra", "Maharashtra", "West Bengal"],
        "financial_year": ["2024-25"] * 5,
        "percapita_nsdp_current_prices_inr": [300000, 300000, 300000, 300000, 300000],
    })


def test_stress_index_known_value_scales_min_and_max_to_0_and_100():
    result = housing.stress_index_cross_section(
        _stress_price_levels(), _stress_nsdp_current(), quarter="Sep-2024",
        low_pctile=0.0, high_pctile=100.0,
    )
    scores = result.scores
    assert math.isclose(scores["stress_score_0_100"].max(), 100.0)
    assert math.isclose(scores["stress_score_0_100"].min(), 0.0)
    # Highest unit price (Mumbai) -> highest PTI -> highest stress score.
    assert scores.iloc[0]["city"] == "Mumbai"
    assert scores.iloc[-1]["city"] == "Kolkata"


def test_stress_index_percentile_clip_contains_extreme_outlier():
    # Add an extreme outlier city; its score must still cap at 100, and it
    # must not crush every other city's score toward 0.
    price_levels = pd.concat([
        _stress_price_levels(),
        pd.DataFrame({"city": ["Bhiwadi"], "quarter": ["Sep-2024"], "composite_price_inr_per_sqm": [5_000_000]}),
    ], ignore_index=True)
    nsdp = pd.concat([
        _stress_nsdp_current(),
        pd.DataFrame({"state": ["Rajasthan"], "financial_year": ["2024-25"], "percapita_nsdp_current_prices_inr": [300000]}),
    ], ignore_index=True)

    result = housing.stress_index_cross_section(price_levels, nsdp, quarter="Sep-2024")
    scores = result.scores
    assert scores["stress_score_0_100"].max() <= 100.0 + 1e-9
    assert scores["stress_score_0_100"].min() >= 0.0 - 1e-9
    outlier_row = scores[scores["city"] == "Bhiwadi"].iloc[0]
    assert math.isclose(outlier_row["stress_score_0_100"], 100.0)
    # The outlier's clipped PTI should be well below its raw PTI.
    assert outlier_row["pti_clipped"] < outlier_row["price_to_income"]
    # Mid-pack cities should not all be pinned to 0 just because of the outlier.
    mid_scores = scores[scores["city"] != "Bhiwadi"]["stress_score_0_100"]
    assert (mid_scores > 0).any()


def test_stress_index_insufficient_cities_raises():
    small_price_levels = _stress_price_levels().iloc[:2]
    with pytest.raises(ValueError):
        housing.stress_index_cross_section(small_price_levels, _stress_nsdp_current(), quarter="Sep-2024")


def test_stress_index_rate_disclosure_present_and_labelled():
    result = housing.stress_index_cross_section(_stress_price_levels(), _stress_nsdp_current(), quarter="Sep-2024")
    assert "historical" in result.rate_disclosure.lower()
    assert "not" in result.rate_disclosure.lower()


def test_stress_index_defaults_to_latest_common_quarter_when_omitted():
    result = housing.stress_index_cross_section(_stress_price_levels(), _stress_nsdp_current())
    assert result.quarter == "Sep-2024"
