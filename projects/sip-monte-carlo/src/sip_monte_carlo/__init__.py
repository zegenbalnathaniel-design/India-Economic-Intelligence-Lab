"""SIP & Wealth Accumulation Monte Carlo Simulator.

A self-contained numerical simulation package: given a set of
user-supplied (and explicitly illustrative) assumptions about returns,
volatility, fees, inflation and contribution growth, it simulates a
distribution of SIP (systematic investment plan) outcomes. It does not
fetch or depend on any external data, and nothing it produces is a
forecast, a guarantee, or investment advice.
"""
from .closed_form import annuity_factor, future_value_growing_annuity
from .engine import (
    PERCENTILES,
    SimulationResult,
    lognormal_monthly_params,
    net_monthly_rate,
    run_simulation,
)
from .sequence_risk import (
    SequenceRiskResult,
    demo_sequence_of_returns_risk,
    simulate_annual_path,
)

__all__ = [
    "PERCENTILES",
    "SimulationResult",
    "run_simulation",
    "lognormal_monthly_params",
    "net_monthly_rate",
    "annuity_factor",
    "future_value_growing_annuity",
    "SequenceRiskResult",
    "demo_sequence_of_returns_risk",
    "simulate_annual_path",
]

__version__ = "0.1.0"
