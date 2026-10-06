"""Multi-year affordability scenario projections.

These functions project how affordability evolves over a horizon under a
set of growth assumptions (house-price growth, household-income growth,
mortgage rate). They are **mechanical projections of assumptions the caller
supplies**, not forecasts: "the optimistic scenario says affordability
improves in 6 years" means exactly "if income grows faster than house
prices by the assumed margin for 6 years, the ratios computed from those
assumed growth paths cross this threshold in year 6" — nothing more. See
the README's Economic Theory section and `docs/METHODOLOGY.md` for the
distinction between this kind of deterministic projection and an empirical
claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .metrics import emi, mortgage_payment_to_income_ratio, price_to_income_ratio


@dataclass(frozen=True)
class Scenario:
    """One set of multi-year growth assumptions.

    Attributes:
        name: Short label, e.g. "Baseline".
        house_price_growth: Assumed annual house-price growth rate (decimal).
        income_growth: Assumed annual household-income growth rate (decimal).
        mortgage_rate: Assumed annual mortgage interest rate (decimal),
            held constant across the horizon in this simple model.
        savings_rate: Assumed fraction of annual income the household saves
            toward a down payment, held constant across the horizon.
    """

    name: str
    house_price_growth: float
    income_growth: float
    mortgage_rate: float
    savings_rate: float = 0.20


# Three standard scenarios used throughout the app/notebooks. These are
# illustrative planning assumptions, not predictions for any real city.
# "Conservative" = house prices outrun income growth (affordability worsens);
# "Optimistic" = income growth outpaces house-price growth (affordability
# improves); "Baseline" splits the difference.
STANDARD_SCENARIOS: dict[str, Scenario] = {
    "conservative": Scenario(
        name="Conservative",
        house_price_growth=0.09,
        income_growth=0.06,
        mortgage_rate=0.095,
        savings_rate=0.15,
    ),
    "baseline": Scenario(
        name="Baseline",
        house_price_growth=0.07,
        income_growth=0.08,
        mortgage_rate=0.085,
        savings_rate=0.20,
    ),
    "optimistic": Scenario(
        name="Optimistic",
        house_price_growth=0.05,
        income_growth=0.10,
        mortgage_rate=0.075,
        savings_rate=0.25,
    ),
}


@dataclass
class ScenarioProjection:
    """Year-by-year projection for one scenario.

    Attributes:
        scenario: The `Scenario` this projection was run under.
        table: A `pandas.DataFrame` indexed by year (1..horizon_years) with
            columns: house_price, annual_income, monthly_income,
            down_payment_target, cumulative_savings, down_payment_met,
            loan_amount, monthly_emi, price_to_income,
            mortgage_payment_to_income.
        years_to_afford_down_payment: First year (1-indexed) in which
            cumulative savings reach the down-payment target for that
            year's house price, or None if it is not reached within the
            projected horizon.
    """

    scenario: Scenario
    table: pd.DataFrame
    years_to_afford_down_payment: int | None = field(default=None)


def project_scenario(
    initial_house_price: float,
    initial_annual_income: float,
    scenario: Scenario,
    horizon_years: int,
    down_payment_pct: float = 0.20,
    loan_years: float = 20.0,
) -> ScenarioProjection:
    """Project house price, income, and affordability metrics forward under
    one scenario's growth assumptions.

    At each year t (1..horizon_years):
        house_price_t = initial_house_price * (1 + house_price_growth)^t
        annual_income_t = initial_annual_income * (1 + income_growth)^t
        down_payment_target_t = down_payment_pct * house_price_t
        cumulative_savings_t = sum_{k=1}^{t} savings_rate * annual_income_k

    i.e. the household saves a constant fraction of its (growing) income
    every year, while the down-payment target grows with the (growing)
    house price. "Years to afford the down payment" is the first year the
    cumulative savings meet or exceed that year's target.

    The EMI and mortgage-payment-to-income columns are computed as if the
    household bought the house in that year, at that year's price and the
    scenario's (constant) mortgage rate, financing (1 - down_payment_pct) of
    the price over `loan_years` — they describe affordability-at-purchase
    in each year, not a single household's actual loan.

    Args:
        initial_house_price: House price in year 0 (currency units), > 0.
        initial_annual_income: Household income in year 0, > 0.
        scenario: Growth/rate assumptions to apply.
        horizon_years: Number of years to project forward, > 0 (integer).
        down_payment_pct: Down payment fraction assumed at purchase, in
            [0, 1]. Defaults to 20%.
        loan_years: Loan tenure used for the EMI columns. Defaults to 20.

    Returns:
        A `ScenarioProjection` with the full year-by-year table and the
        first year (if any, within the horizon) the down payment target is
        met by cumulative savings.

    Raises:
        ValueError: If initial_house_price/initial_annual_income are not
            positive, horizon_years is not a positive integer, or
            down_payment_pct is outside [0, 1].
    """
    if initial_house_price <= 0:
        raise ValueError("initial_house_price must be positive.")
    if initial_annual_income <= 0:
        raise ValueError("initial_annual_income must be positive.")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be a positive integer.")
    if not (0.0 <= down_payment_pct <= 1.0):
        raise ValueError(f"down_payment_pct must be in [0, 1], got {down_payment_pct!r}.")

    rows = []
    cumulative_savings = 0.0
    years_to_afford: int | None = None

    for t in range(1, int(horizon_years) + 1):
        house_price_t = initial_house_price * (1.0 + scenario.house_price_growth) ** t
        annual_income_t = initial_annual_income * (1.0 + scenario.income_growth) ** t
        monthly_income_t = annual_income_t / 12.0

        down_payment_target_t = down_payment_pct * house_price_t
        cumulative_savings += scenario.savings_rate * annual_income_t
        down_payment_met = cumulative_savings >= down_payment_target_t

        if down_payment_met and years_to_afford is None:
            years_to_afford = t

        loan_amount_t = house_price_t * (1.0 - down_payment_pct)
        if loan_amount_t > 0:
            monthly_emi_t = emi(loan_amount_t, scenario.mortgage_rate, loan_years)
            mpti_t = mortgage_payment_to_income_ratio(monthly_emi_t, monthly_income_t)
        else:
            monthly_emi_t = 0.0
            mpti_t = 0.0

        pir_t = price_to_income_ratio(house_price_t, annual_income_t)

        rows.append(
            {
                "year": t,
                "house_price": house_price_t,
                "annual_income": annual_income_t,
                "monthly_income": monthly_income_t,
                "down_payment_target": down_payment_target_t,
                "cumulative_savings": cumulative_savings,
                "down_payment_met": down_payment_met,
                "loan_amount": loan_amount_t,
                "monthly_emi": monthly_emi_t,
                "price_to_income": pir_t,
                "mortgage_payment_to_income": mpti_t,
            }
        )

    table = pd.DataFrame(rows).set_index("year")
    return ScenarioProjection(scenario=scenario, table=table, years_to_afford_down_payment=years_to_afford)


def run_standard_scenarios(
    initial_house_price: float,
    initial_annual_income: float,
    horizon_years: int,
    down_payment_pct: float = 0.20,
    loan_years: float = 20.0,
    scenarios: dict[str, Scenario] | None = None,
) -> dict[str, ScenarioProjection]:
    """Run `project_scenario` for conservative/baseline/optimistic (or a
    caller-supplied scenario dict) and return all projections keyed by
    scenario key.

    Args:
        initial_house_price: House price in year 0.
        initial_annual_income: Household income in year 0.
        horizon_years: Number of years to project forward.
        down_payment_pct: Down payment fraction assumed at purchase.
        loan_years: Loan tenure used for the EMI columns.
        scenarios: Optional override of `STANDARD_SCENARIOS` (e.g. to run a
            custom sensitivity set); defaults to the three standard ones.

    Returns:
        Dict mapping scenario key -> `ScenarioProjection`.
    """
    scenario_set = scenarios if scenarios is not None else STANDARD_SCENARIOS
    return {
        key: project_scenario(
            initial_house_price,
            initial_annual_income,
            scenario,
            horizon_years,
            down_payment_pct=down_payment_pct,
            loan_years=loan_years,
        )
        for key, scenario in scenario_set.items()
    }
