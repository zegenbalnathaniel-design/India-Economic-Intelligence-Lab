"""Core housing-affordability metrics.

Every function here is a pure, stateless calculation on plain numbers. None
of them know about "India" or any particular city — city-specific inputs
(synthetic or otherwise) are assembled elsewhere (`scenarios.py`,
`examples/generate_synthetic_city_data.py`) and passed in as arguments.

Conventions used throughout this module:
  * All monetary amounts are in a single consistent currency unit chosen by
    the caller (the bundled example data uses INR). Mixing units across
    arguments is the caller's responsibility to avoid.
  * Rates (`annual_interest_rate`, growth rates, etc.) are decimals, e.g.
    0.085 for 8.5%, not 8.5.
  * "Income" always means *gross* household income unless a docstring says
    otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass


def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}.")


def _require_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value!r}.")


def price_to_income_ratio(house_price: float, annual_household_income: float) -> float:
    """Price-to-income ratio (PIR): house price divided by annual household
    income.

    This is the most widely quoted affordability "headline number"
    (used by, e.g., the Demographia survey and the RBI House Price Index
    commentary) because it needs only two inputs. A PIR of 5 means a
    household would need five full years of gross income, saved with zero
    consumption, to pay for the house outright. Conventional rules of thumb
    treat PIR <= 3 as "affordable" and PIR >= 5 as "severely unaffordable",
    but the threshold is a convention, not a law of economics — see the
    README's Economic Theory section for why PIR alone is a weak proxy for
    affordability (it ignores financing cost, loan tenure, and income
    growth).

    Args:
        house_price: Total price of the dwelling (currency units).
        annual_household_income: Gross annual household income (same units).

    Returns:
        Unitless ratio (house_price / annual_household_income).

    Raises:
        ValueError: If either input is not strictly positive.
    """
    _require_positive(house_price, "house_price")
    _require_positive(annual_household_income, "annual_household_income")
    return house_price / annual_household_income


def emi(principal: float, annual_interest_rate: float, loan_years: float) -> float:
    """Equated Monthly Instalment for a standard fixed-rate amortising loan.

    Closed-form annuity formula:
        EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where:
        P = principal (loan amount)
        r = monthly interest rate = annual_interest_rate / 12
        n = number of monthly instalments = loan_years * 12

    Derivation sketch: a loan is repaid by n equal instalments whose present
    value, discounted monthly at rate r, equals P. Solving the annuity
    present-value identity P = EMI * [1 - (1+r)^-n] / r for EMI gives the
    formula above. This is the formula Indian banks and NBFCs use to quote
    EMIs on home loans (it is also used for car loans, personal loans, etc.).

    At r = 0 (a zero-interest loan), the annuity formula is 0/0 and must be
    handled separately: with no interest, the loan is simply repaid in n
    equal instalments of P / n.

    Args:
        principal: Loan amount financed (currency units), must be > 0.
        annual_interest_rate: Nominal annual interest rate as a decimal
            (e.g. 0.085 for 8.5%). May be 0 but not negative.
        loan_years: Loan tenure in years, must be > 0.

    Returns:
        The fixed monthly instalment amount.

    Raises:
        ValueError: If principal or loan_years is not strictly positive, or
            if annual_interest_rate is negative.
    """
    _require_positive(principal, "principal")
    _require_positive(loan_years, "loan_years")
    _require_non_negative(annual_interest_rate, "annual_interest_rate")

    n_months = loan_years * 12
    if annual_interest_rate == 0:
        return principal / n_months

    r = annual_interest_rate / 12.0
    growth = (1.0 + r) ** n_months
    return principal * r * growth / (growth - 1.0)


def mortgage_payment_to_income_ratio(emi_monthly: float, monthly_income: float) -> float:
    """Mortgage-payment-to-income ratio (a.k.a. EMI-to-income ratio or
    "debt service ratio" for the housing leg of debt).

    Indian retail-lending underwriting commonly caps total EMI obligations
    at roughly 40-50% of monthly take-home income (the exact cap varies by
    lender and borrower income band); this function simply computes the
    ratio so the caller can apply whatever threshold is relevant.

    Args:
        emi_monthly: Monthly loan instalment (currency units).
        monthly_income: Gross monthly household income (same units).

    Returns:
        Unitless ratio (emi_monthly / monthly_income).

    Raises:
        ValueError: If either input is not strictly positive.
    """
    _require_positive(emi_monthly, "emi_monthly")
    _require_positive(monthly_income, "monthly_income")
    return emi_monthly / monthly_income


def loan_to_value_ratio(loan_amount: float, house_price: float) -> float:
    """Loan-to-value ratio (LTV): fraction of the house price financed by
    debt rather than the buyer's own down payment.

    Indian regulatory guidance (RBI) caps LTV at roughly 75-90% depending on
    loan size for scheduled commercial banks; a lower LTV generally means a
    larger down payment and (all else equal) a smaller EMI.

    Args:
        loan_amount: Amount borrowed (currency units), must be > 0.
        house_price: Total price of the dwelling (same units), must be > 0.

    Returns:
        Unitless ratio (loan_amount / house_price). Values > 1 are not
        blocked here (the function does not enforce regulatory caps) but
        are economically unusual and the caller should treat them as
        suspicious input.

    Raises:
        ValueError: If either input is not strictly positive.
    """
    _require_positive(loan_amount, "loan_amount")
    _require_positive(house_price, "house_price")
    return loan_amount / house_price


def years_to_save_down_payment(target_down_payment: float, annual_savings: float) -> float:
    """Years of saving (at a constant annual savings rate, no return on
    savings) needed to accumulate a target down payment.

    This is deliberately the simplest possible model — straight-line
    accumulation with no interest/investment growth on the savings pot —
    so that it is easy to reason about and to compose with the scenario
    projections in `scenarios.py`, which add house-price and income growth
    on top. A target of 0 takes 0 years.

    Args:
        target_down_payment: Amount still needed (currency units), must be
            >= 0.
        annual_savings: Amount saved per year (currency units), must be > 0
            unless target_down_payment is 0.

    Returns:
        Number of years (may be fractional) required to reach the target.

    Raises:
        ValueError: If target_down_payment is negative, or if
            annual_savings is not strictly positive while a positive target
            remains.
    """
    _require_non_negative(target_down_payment, "target_down_payment")
    if target_down_payment == 0:
        return 0.0
    _require_positive(annual_savings, "annual_savings")
    return target_down_payment / annual_savings


def total_interest_paid(principal: float, annual_interest_rate: float, loan_years: float) -> float:
    """Total interest paid over the full life of an amortising loan.

    Computed as (EMI * number_of_instalments) - principal, i.e. the total
    amount repaid minus the amount borrowed. At 0% interest this is exactly
    0, since EMI = principal / n_months by construction.

    Args:
        principal: Loan amount financed, must be > 0.
        annual_interest_rate: Nominal annual interest rate as a decimal,
            must be >= 0.
        loan_years: Loan tenure in years, must be > 0.

    Returns:
        Total interest paid over the life of the loan (currency units).

    Raises:
        ValueError: Propagated from `emi` for invalid inputs.
    """
    n_months = loan_years * 12
    monthly_payment = emi(principal, annual_interest_rate, loan_years)
    return monthly_payment * n_months - principal


def interest_burden_ratio(total_interest: float, total_amount_paid: float) -> float:
    """Fraction of total loan repayments that is interest rather than
    principal: total_interest / total_amount_paid.

    A ratio of 0.4 means 40% of every rupee repaid over the life of the loan
    is interest, 60% is principal. This rises with the interest rate and
    with loan tenure (longer loans pay proportionally more interest even at
    the same rate, because the principal is outstanding for longer).

    Args:
        total_interest: Total interest paid (currency units), must be >= 0.
        total_amount_paid: Total of all repayments, principal + interest
            (currency units), must be > 0.

    Returns:
        Unitless ratio in [0, 1) for any economically sane loan.

    Raises:
        ValueError: If total_interest is negative, or total_amount_paid is
            not strictly positive, or total_interest exceeds
            total_amount_paid (which would be inconsistent inputs).
    """
    _require_non_negative(total_interest, "total_interest")
    _require_positive(total_amount_paid, "total_amount_paid")
    if total_interest > total_amount_paid:
        raise ValueError("total_interest cannot exceed total_amount_paid.")
    return total_interest / total_amount_paid


@dataclass(frozen=True)
class AffordabilitySummary:
    """Bundled affordability metrics for a single city/scenario snapshot.

    All fields are derived deterministically from the constructor inputs via
    `affordability_summary`; this dataclass exists purely to hand a complete,
    self-describing bundle to callers (the Streamlit app, notebooks, tests)
    instead of a loose tuple.
    """

    city: str
    house_price: float
    annual_household_income: float
    down_payment_pct: float
    annual_interest_rate: float
    loan_years: float

    down_payment_amount: float
    loan_amount: float
    monthly_income: float
    monthly_emi: float
    price_to_income: float
    mortgage_payment_to_income: float
    loan_to_value: float
    total_interest: float
    total_amount_paid: float
    interest_burden: float
    years_to_save_down_payment: float


def affordability_summary(
    house_price: float,
    annual_household_income: float,
    down_payment_pct: float,
    annual_interest_rate: float,
    loan_years: float,
    annual_savings_for_down_payment: float | None = None,
    city: str = "Custom",
) -> AffordabilitySummary:
    """Compute every affordability metric for one city/scenario in one call.

    This is a thin convenience wrapper around the individual metric
    functions above — it does not introduce any new formula, it only wires
    the shared inputs (house price, income, financing terms) through to
    each metric so callers (the Streamlit app, notebooks) don't have to
    repeat that plumbing.

    Args:
        house_price: Total price of the dwelling (currency units).
        annual_household_income: Gross annual household income.
        down_payment_pct: Down payment as a fraction of house price, in
            [0, 1] (e.g. 0.2 for 20%).
        annual_interest_rate: Nominal annual mortgage rate as a decimal.
        loan_years: Loan tenure in years.
        annual_savings_for_down_payment: Amount saved per year toward a
            *future* down payment of this size, used only to compute
            `years_to_save_down_payment`. Defaults to 20% of annual income
            when not supplied (an illustrative savings-rate assumption, not
            a claim about actual Indian household savings behaviour).
        city: Free-text label for the scenario (e.g. a city name); purely
            descriptive and not used in any calculation.

    Returns:
        An `AffordabilitySummary` with every metric filled in.

    Raises:
        ValueError: If down_payment_pct is not in [0, 1], or propagated from
            the underlying metric functions for other invalid inputs.
    """
    if not (0.0 <= down_payment_pct <= 1.0):
        raise ValueError(f"down_payment_pct must be in [0, 1], got {down_payment_pct!r}.")
    _require_positive(house_price, "house_price")
    _require_positive(annual_household_income, "annual_household_income")

    down_payment_amount = house_price * down_payment_pct
    loan_amount = house_price - down_payment_amount
    monthly_income = annual_household_income / 12.0

    pir = price_to_income_ratio(house_price, annual_household_income)

    if loan_amount <= 0:
        # 100% down payment: no loan is taken, so every loan-dependent
        # metric is trivially zero rather than undefined.
        monthly_emi = 0.0
        mpti = 0.0
        ltv = 0.0
        total_interest = 0.0
        total_amount_paid = 0.0
        interest_burden = 0.0
    else:
        monthly_emi = emi(loan_amount, annual_interest_rate, loan_years)
        mpti = mortgage_payment_to_income_ratio(monthly_emi, monthly_income)
        ltv = loan_to_value_ratio(loan_amount, house_price)
        total_interest = total_interest_paid(loan_amount, annual_interest_rate, loan_years)
        total_amount_paid = loan_amount + total_interest
        interest_burden = (
            interest_burden_ratio(total_interest, total_amount_paid) if total_interest > 0 else 0.0
        )

    if annual_savings_for_down_payment is None:
        annual_savings_for_down_payment = 0.20 * annual_household_income
    years_to_save = years_to_save_down_payment(down_payment_amount, annual_savings_for_down_payment)

    return AffordabilitySummary(
        city=city,
        house_price=house_price,
        annual_household_income=annual_household_income,
        down_payment_pct=down_payment_pct,
        annual_interest_rate=annual_interest_rate,
        loan_years=loan_years,
        down_payment_amount=down_payment_amount,
        loan_amount=loan_amount,
        monthly_income=monthly_income,
        monthly_emi=monthly_emi,
        price_to_income=pir,
        mortgage_payment_to_income=mpti,
        loan_to_value=ltv,
        total_interest=total_interest,
        total_amount_paid=total_amount_paid,
        interest_burden=interest_burden,
        years_to_save_down_payment=years_to_save,
    )
