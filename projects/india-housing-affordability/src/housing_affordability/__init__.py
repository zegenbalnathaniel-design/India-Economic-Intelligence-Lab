"""India Housing Affordability Index — a small toolkit of affordability
metrics (price-to-income, EMI, mortgage-payment-to-income, LTV, down-payment
savings horizon, interest burden) plus a multi-year scenario projector.

Nothing in this package fetches or ships real housing-market data. Any city
figures used by the bundled example/app are explicitly SYNTHETIC — see
`docs/DATA_SOURCES.md` in the project root for where to source real data.
"""
from __future__ import annotations

from .metrics import (
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
from .scenarios import (
    Scenario,
    ScenarioProjection,
    STANDARD_SCENARIOS,
    project_scenario,
    run_standard_scenarios,
)

__all__ = [
    "AffordabilitySummary",
    "affordability_summary",
    "emi",
    "interest_burden_ratio",
    "loan_to_value_ratio",
    "mortgage_payment_to_income_ratio",
    "price_to_income_ratio",
    "total_interest_paid",
    "years_to_save_down_payment",
    "Scenario",
    "ScenarioProjection",
    "STANDARD_SCENARIOS",
    "project_scenario",
    "run_standard_scenarios",
]
