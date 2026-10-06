"""Tests for housing_affordability.metrics.

Covers: normal cases, documented edge cases (0% interest, 100% down
payment, very short/long tenure), invalid inputs (negative price/income ->
ValueError), and a hand-computed closed-form EMI correctness check.
"""
from __future__ import annotations

import math

import pytest

from housing_affordability.metrics import (
    AffordabilitySummary,
    affordability_summary,
    emi,
    interest_burden_ratio,
    loan_to_value_ratio,
    mortgage_payment_to_income_ratio,
    price_to_income_ratio,
    total_interest_paid,
    years_to_save_down_payment,
)


# ---------------------------------------------------------------------------
# price_to_income_ratio
# ---------------------------------------------------------------------------

def test_price_to_income_ratio_basic():
    assert price_to_income_ratio(5_000_000, 1_000_000) == pytest.approx(5.0)


def test_price_to_income_ratio_rejects_non_positive():
    with pytest.raises(ValueError):
        price_to_income_ratio(-1, 1_000_000)
    with pytest.raises(ValueError):
        price_to_income_ratio(5_000_000, 0)
    with pytest.raises(ValueError):
        price_to_income_ratio(5_000_000, -100)


# ---------------------------------------------------------------------------
# emi — closed-form correctness, edge cases, invalid inputs
# ---------------------------------------------------------------------------

def test_emi_matches_hand_computed_annuity_formula():
    # Manually computed example: P = 1,000,000; annual rate 9% -> monthly
    # rate r = 0.0075; n = 240 months (20 years).
    principal = 1_000_000.0
    annual_rate = 0.09
    years = 20
    r = annual_rate / 12
    n = years * 12
    expected = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    result = emi(principal, annual_rate, years)
    assert result == pytest.approx(expected, rel=1e-12)
    # Sanity-check the expected value itself lands in a plausible EMI range
    # for this principal (roughly 8,500-9,500/month at 9% over 20y).
    assert 8_500 < expected < 9_500


def test_emi_zero_interest_is_straight_line_division():
    principal = 1_200_000.0
    years = 10
    result = emi(principal, 0.0, years)
    assert result == pytest.approx(principal / (years * 12))


def test_emi_zero_interest_does_not_divide_by_zero():
    # Regression guard: the annuity formula's (1+r)^n - 1 term is 0 at r=0,
    # so this must go through the explicit zero-rate branch rather than
    # raising ZeroDivisionError or returning nan/inf.
    result = emi(500_000.0, 0.0, 5)
    assert math.isfinite(result)
    assert result > 0


def test_emi_very_short_tenure():
    # 1-year loan: n = 12 months.
    result = emi(100_000.0, 0.10, 1)
    r = 0.10 / 12
    n = 12
    expected = 100_000.0 * r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert result == pytest.approx(expected)


def test_emi_very_long_tenure():
    # 30-year loan.
    result = emi(5_000_000.0, 0.08, 30)
    r = 0.08 / 12
    n = 30 * 12
    expected = 5_000_000.0 * r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert result == pytest.approx(expected)


def test_emi_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        emi(-100_000, 0.08, 20)
    with pytest.raises(ValueError):
        emi(100_000, 0.08, 0)
    with pytest.raises(ValueError):
        emi(100_000, 0.08, -5)
    with pytest.raises(ValueError):
        emi(100_000, -0.01, 20)


def test_emi_increases_with_rate_and_decreases_with_tenure():
    low_rate = emi(1_000_000, 0.06, 20)
    high_rate = emi(1_000_000, 0.12, 20)
    assert high_rate > low_rate

    short_tenure = emi(1_000_000, 0.09, 10)
    long_tenure = emi(1_000_000, 0.09, 30)
    assert short_tenure > long_tenure


# ---------------------------------------------------------------------------
# mortgage_payment_to_income_ratio
# ---------------------------------------------------------------------------

def test_mortgage_payment_to_income_ratio_basic():
    assert mortgage_payment_to_income_ratio(40_000, 100_000) == pytest.approx(0.4)


def test_mortgage_payment_to_income_ratio_rejects_non_positive():
    with pytest.raises(ValueError):
        mortgage_payment_to_income_ratio(-100, 100_000)
    with pytest.raises(ValueError):
        mortgage_payment_to_income_ratio(40_000, 0)


# ---------------------------------------------------------------------------
# loan_to_value_ratio
# ---------------------------------------------------------------------------

def test_loan_to_value_ratio_basic():
    assert loan_to_value_ratio(8_000_000, 10_000_000) == pytest.approx(0.8)


def test_loan_to_value_ratio_rejects_non_positive():
    with pytest.raises(ValueError):
        loan_to_value_ratio(-1, 10_000_000)
    with pytest.raises(ValueError):
        loan_to_value_ratio(8_000_000, 0)


# ---------------------------------------------------------------------------
# years_to_save_down_payment
# ---------------------------------------------------------------------------

def test_years_to_save_down_payment_basic():
    assert years_to_save_down_payment(1_000_000, 200_000) == pytest.approx(5.0)


def test_years_to_save_down_payment_zero_target_is_zero_years():
    assert years_to_save_down_payment(0, 0) == 0.0
    # Even with annual_savings omitted/zero, a zero target takes zero years.
    assert years_to_save_down_payment(0, 500_000) == 0.0


def test_years_to_save_down_payment_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        years_to_save_down_payment(-1, 100_000)
    with pytest.raises(ValueError):
        years_to_save_down_payment(1_000_000, 0)
    with pytest.raises(ValueError):
        years_to_save_down_payment(1_000_000, -50_000)


# ---------------------------------------------------------------------------
# total_interest_paid / interest_burden_ratio
# ---------------------------------------------------------------------------

def test_total_interest_paid_positive_for_normal_loan():
    interest = total_interest_paid(1_000_000, 0.09, 20)
    assert interest > 0
    # Total repaid should exceed principal by exactly this amount.
    n = 20 * 12
    monthly = emi(1_000_000, 0.09, 20)
    assert interest == pytest.approx(monthly * n - 1_000_000)


def test_total_interest_paid_zero_at_zero_interest():
    interest = total_interest_paid(1_000_000, 0.0, 15)
    assert interest == pytest.approx(0.0, abs=1e-6)


def test_interest_burden_ratio_basic():
    # 400,000 interest out of 1,400,000 total paid -> ~28.6% interest burden.
    ratio = interest_burden_ratio(400_000, 1_400_000)
    assert ratio == pytest.approx(400_000 / 1_400_000)


def test_interest_burden_ratio_rejects_inconsistent_inputs():
    with pytest.raises(ValueError):
        interest_burden_ratio(-1, 1_000_000)
    with pytest.raises(ValueError):
        interest_burden_ratio(100_000, 0)
    with pytest.raises(ValueError):
        # interest cannot exceed total amount paid
        interest_burden_ratio(2_000_000, 1_000_000)


def test_interest_burden_rises_with_tenure_at_fixed_rate():
    # Longer tenure -> proportionally more interest in total repayments,
    # even holding the rate fixed.
    short = total_interest_paid(1_000_000, 0.09, 10)
    long = total_interest_paid(1_000_000, 0.09, 30)
    short_total = short + 1_000_000
    long_total = long + 1_000_000
    assert interest_burden_ratio(long, long_total) > interest_burden_ratio(short, short_total)


# ---------------------------------------------------------------------------
# affordability_summary — combined bundle, including 100% down payment edge
# case (no loan at all).
# ---------------------------------------------------------------------------

def test_affordability_summary_basic_bundle():
    summary = affordability_summary(
        house_price=8_000_000,
        annual_household_income=1_500_000,
        down_payment_pct=0.20,
        annual_interest_rate=0.085,
        loan_years=20,
        city="TestCity",
    )
    assert isinstance(summary, AffordabilitySummary)
    assert summary.down_payment_amount == pytest.approx(1_600_000)
    assert summary.loan_amount == pytest.approx(6_400_000)
    assert summary.price_to_income == pytest.approx(8_000_000 / 1_500_000)
    assert summary.monthly_emi > 0
    assert summary.loan_to_value == pytest.approx(0.8)
    assert 0 < summary.interest_burden < 1


def test_affordability_summary_100pct_down_payment_has_no_loan():
    summary = affordability_summary(
        house_price=5_000_000,
        annual_household_income=2_000_000,
        down_payment_pct=1.0,
        annual_interest_rate=0.09,
        loan_years=20,
    )
    assert summary.loan_amount == pytest.approx(0.0)
    assert summary.monthly_emi == 0.0
    assert summary.mortgage_payment_to_income == 0.0
    assert summary.loan_to_value == 0.0
    assert summary.total_interest == 0.0
    assert summary.interest_burden == 0.0
    # Down payment is still the full house price, and the price-to-income
    # ratio is unaffected by financing choice.
    assert summary.down_payment_amount == pytest.approx(5_000_000)
    assert summary.price_to_income == pytest.approx(2.5)


def test_affordability_summary_zero_down_payment_is_fully_financed():
    summary = affordability_summary(
        house_price=6_000_000,
        annual_household_income=1_200_000,
        down_payment_pct=0.0,
        annual_interest_rate=0.08,
        loan_years=20,
    )
    assert summary.down_payment_amount == pytest.approx(0.0)
    assert summary.loan_amount == pytest.approx(6_000_000)
    assert summary.loan_to_value == pytest.approx(1.0)
    assert summary.years_to_save_down_payment == 0.0


def test_affordability_summary_rejects_invalid_down_payment_pct():
    with pytest.raises(ValueError):
        affordability_summary(
            house_price=5_000_000,
            annual_household_income=1_000_000,
            down_payment_pct=1.5,
            annual_interest_rate=0.08,
            loan_years=20,
        )
    with pytest.raises(ValueError):
        affordability_summary(
            house_price=5_000_000,
            annual_household_income=1_000_000,
            down_payment_pct=-0.1,
            annual_interest_rate=0.08,
            loan_years=20,
        )


def test_affordability_summary_rejects_invalid_price_or_income():
    with pytest.raises(ValueError):
        affordability_summary(
            house_price=-5_000_000,
            annual_household_income=1_000_000,
            down_payment_pct=0.2,
            annual_interest_rate=0.08,
            loan_years=20,
        )
    with pytest.raises(ValueError):
        affordability_summary(
            house_price=5_000_000,
            annual_household_income=-1_000_000,
            down_payment_pct=0.2,
            annual_interest_rate=0.08,
            loan_years=20,
        )


def test_affordability_summary_custom_savings_for_down_payment():
    summary = affordability_summary(
        house_price=10_000_000,
        annual_household_income=2_000_000,
        down_payment_pct=0.20,
        annual_interest_rate=0.08,
        loan_years=20,
        annual_savings_for_down_payment=400_000,
    )
    # down payment target = 2,000,000; saving 400,000/yr -> 5 years.
    assert summary.years_to_save_down_payment == pytest.approx(5.0)
