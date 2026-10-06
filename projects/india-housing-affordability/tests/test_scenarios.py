"""Tests for housing_affordability.scenarios."""
from __future__ import annotations

import pytest

from housing_affordability.scenarios import (
    STANDARD_SCENARIOS,
    Scenario,
    project_scenario,
    run_standard_scenarios,
)


def test_project_scenario_basic_shape():
    scenario = Scenario(
        name="Test", house_price_growth=0.07, income_growth=0.08, mortgage_rate=0.085, savings_rate=0.2
    )
    projection = project_scenario(
        initial_house_price=8_000_000,
        initial_annual_income=1_500_000,
        scenario=scenario,
        horizon_years=10,
    )
    table = projection.table
    assert len(table) == 10
    assert list(table.index) == list(range(1, 11))

    # House price and income should grow monotonically each year under
    # positive growth rates.
    assert (table["house_price"].diff().dropna() > 0).all()
    assert (table["annual_income"].diff().dropna() > 0).all()

    # Year 1 values should match the growth formula directly.
    assert table.loc[1, "house_price"] == pytest.approx(8_000_000 * 1.07)
    assert table.loc[1, "annual_income"] == pytest.approx(1_500_000 * 1.08)


def test_project_scenario_income_outpacing_price_eventually_affords_down_payment():
    # Optimistic-style scenario: income grows much faster than price, and
    # the household saves a healthy share of income -> down payment target
    # should be met within a generous horizon.
    scenario = Scenario(
        name="FastIncome", house_price_growth=0.03, income_growth=0.12, mortgage_rate=0.08, savings_rate=0.3
    )
    projection = project_scenario(
        initial_house_price=5_000_000,
        initial_annual_income=1_500_000,
        scenario=scenario,
        horizon_years=25,
    )
    assert projection.years_to_afford_down_payment is not None
    met_year = projection.years_to_afford_down_payment
    assert projection.table.loc[met_year, "down_payment_met"]
    # Every year before the met year should NOT have met the target yet.
    for y in range(1, met_year):
        assert not projection.table.loc[y, "down_payment_met"]


def test_project_scenario_price_outpacing_income_may_never_afford_within_horizon():
    # Price grows much faster than income and the household barely saves ->
    # over a short horizon the target should not be met.
    scenario = Scenario(
        name="RunawayPrice",
        house_price_growth=0.20,
        income_growth=0.03,
        mortgage_rate=0.09,
        savings_rate=0.05,
    )
    projection = project_scenario(
        initial_house_price=10_000_000,
        initial_annual_income=1_200_000,
        scenario=scenario,
        horizon_years=5,
    )
    assert projection.years_to_afford_down_payment is None
    assert not projection.table["down_payment_met"].any()


def test_project_scenario_rejects_invalid_inputs():
    scenario = STANDARD_SCENARIOS["baseline"]
    with pytest.raises(ValueError):
        project_scenario(-1, 1_000_000, scenario, 10)
    with pytest.raises(ValueError):
        project_scenario(1_000_000, -1, scenario, 10)
    with pytest.raises(ValueError):
        project_scenario(1_000_000, 1_000_000, scenario, 0)
    with pytest.raises(ValueError):
        project_scenario(1_000_000, 1_000_000, scenario, 10, down_payment_pct=1.5)


def test_run_standard_scenarios_returns_all_three():
    results = run_standard_scenarios(
        initial_house_price=8_000_000, initial_annual_income=1_500_000, horizon_years=10
    )
    assert set(results.keys()) == {"conservative", "baseline", "optimistic"}
    for projection in results.values():
        assert len(projection.table) == 10


def test_conservative_scenario_worsens_price_to_income_more_than_optimistic():
    # Conservative assumptions (house prices outrunning income) should
    # produce a higher terminal price-to-income ratio than optimistic
    # assumptions (income outrunning house prices), holding the starting
    # point fixed. This checks the mechanical direction of the model, not
    # any real-world claim.
    results = run_standard_scenarios(
        initial_house_price=8_000_000, initial_annual_income=1_500_000, horizon_years=15
    )
    conservative_final_pir = results["conservative"].table.iloc[-1]["price_to_income"]
    optimistic_final_pir = results["optimistic"].table.iloc[-1]["price_to_income"]
    assert conservative_final_pir > optimistic_final_pir


def test_emi_columns_in_projection_are_consistent_with_metrics_emi():
    from housing_affordability.metrics import emi as emi_fn

    scenario = STANDARD_SCENARIOS["baseline"]
    projection = project_scenario(
        initial_house_price=8_000_000,
        initial_annual_income=1_500_000,
        scenario=scenario,
        horizon_years=5,
        down_payment_pct=0.2,
        loan_years=20,
    )
    row = projection.table.loc[3]
    expected_emi = emi_fn(row["loan_amount"], scenario.mortgage_rate, 20)
    assert row["monthly_emi"] == pytest.approx(expected_emi)
