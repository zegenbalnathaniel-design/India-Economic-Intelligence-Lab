"""Unit tests for policy_simulator.macro_model — checked against closed-form
algebra and documented qualitative directions, not against real GDP data
(this is an explicitly pedagogical model; see METHODOLOGY.md)."""
from __future__ import annotations

import math

import pytest

from policy_simulator.macro_model import (
    CalibrationParams, ScenarioInputs, constant_path, run_scenario,
    compare_scenarios, equilibrium_output, fiscal_multiplier,
    debt_dynamics_step, okuns_law_unemployment, phillips_curve_inflation,
)


def test_fiscal_multiplier_matches_closed_form():
    p = CalibrationParams()
    expected = 1.0 / (1.0 - p.c1 * (1 - p.tax_rate) + p.m1)
    assert math.isclose(fiscal_multiplier(p.tax_rate, p), expected)


def test_higher_government_spending_raises_equilibrium_gdp_by_the_multiplier():
    p = CalibrationParams()
    common = dict(
        tax_rate=p.tax_rate, real_interest_rate=0.03, foreign_demand=20.0,
        exchange_rate_gap=0.0, oil_price=80.0, exchange_rate_level=83.0,
        consumer_confidence=50.0, investment_confidence=50.0, params=p,
    )
    y_low = equilibrium_output(government_spending=20.0, **common)
    y_high = equilibrium_output(government_spending=21.0, **common)
    mult = fiscal_multiplier(p.tax_rate, p)
    assert math.isclose(y_high - y_low, mult, rel_tol=1e-9)


def test_higher_real_rate_lowers_gdp_via_investment():
    p = CalibrationParams()
    common = dict(
        government_spending=20.0, tax_rate=p.tax_rate, foreign_demand=20.0,
        exchange_rate_gap=0.0, oil_price=80.0, exchange_rate_level=83.0,
        consumer_confidence=50.0, investment_confidence=50.0, params=p,
    )
    y_lowrate = equilibrium_output(real_interest_rate=0.01, **common)
    y_highrate = equilibrium_output(real_interest_rate=0.05, **common)
    assert y_highrate < y_lowrate


def test_phillips_curve_rises_with_positive_output_gap():
    p = CalibrationParams()
    pi_neg_gap = phillips_curve_inflation(-0.02, 0.0, p)
    pi_pos_gap = phillips_curve_inflation(0.02, 0.0, p)
    assert pi_pos_gap > pi_neg_gap


def test_okuns_law_unemployment_falls_with_positive_output_gap():
    p = CalibrationParams()
    u_neg = okuns_law_unemployment(-0.02, p)
    u_pos = okuns_law_unemployment(0.02, p)
    assert u_pos < u_neg
    assert u_pos >= 0.0  # never negative


def test_debt_dynamics_primary_surplus_reduces_debt_when_growth_exceeds_rate():
    p = CalibrationParams(debt_interest_rate=0.05, nominal_growth_rate=0.10)
    b_next = debt_dynamics_step(0.80, primary_balance_ratio=0.01, params=p)
    # growth > interest rate and a primary surplus should both pull debt/GDP down
    assert b_next < 0.80


def test_run_scenario_returns_expected_columns_and_length():
    p = CalibrationParams()
    path = constant_path(ScenarioInputs(), years=5)
    df = run_scenario(path, p)
    assert len(df) == 5
    for col in ["gdp", "inflation_pct", "unemployment_pct", "debt_to_gdp_pct",
                "exports", "imports", "exchange_rate", "govt_deficit"]:
        assert col in df.columns


def test_run_scenario_rejects_empty_path():
    with pytest.raises(ValueError):
        run_scenario([])


def test_compare_scenarios_delta_columns_present_and_consistent():
    p = CalibrationParams()
    baseline = constant_path(ScenarioInputs(), years=4)
    shock_inputs = ScenarioInputs(government_spending=30.0)
    shock = constant_path(shock_inputs, years=4)
    merged = compare_scenarios(baseline, shock, p)
    assert "gdp_delta" in merged.columns
    # A larger fiscal expansion scenario should raise GDP in every period.
    assert (merged["gdp_delta"] > 0).all()
