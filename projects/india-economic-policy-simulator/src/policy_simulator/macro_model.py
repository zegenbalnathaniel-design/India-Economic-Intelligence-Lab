"""A simplified, pedagogical open-economy AD/AS model.

**This is a teaching model, not a forecasting tool.** It is a deliberately
small system of textbook-style equations (IS-curve-style aggregate demand,
an expectations-augmented Phillips curve, Okun's law, standard debt
dynamics) calibrated with illustrative parameters loosely consistent with
publicly reported aggregate ratios for India. It is not fit to data via any
estimation procedure, and its output should never be read as a GDP or
inflation forecast.

Every parameter is a plain field on `CalibrationParams` and every policy
input is a plain function argument — nothing is hard-coded inside the
simulation loop.

Model equations
----------------
**Aggregate demand** (goods-market equilibrium, proportional tax rate `tau`,
imports increasing in both income and the rupee cost of oil):

    Yd = (1 - tau) * Y
    C  = c0 + c1 * Yd                                   (consumption)
    I  = i0 - i1 * r + i2 * invest_confidence            (investment)
    X  = x0 + x1 * foreign_demand - x2 * exchange_gap    (exports)
    M  = m0 + m1 * Y + m2 * oil_price * (1 / exch_rate)  (imports)
    Y  = C + I + G + X - M

Solving for the equilibrium `Y` (closed form, since C and M are linear in Y):

    Y* = A / [1 - c1*(1 - tau) + m1]
    A  = c0 + c1_confidence_shift + i0 - i1*r + i2*invest_confidence
         + G + x0 + x1*foreign_demand - x2*exchange_gap - m0 - m2*oil_price/exch_rate

The denominator `[1 - c1*(1-tau) + m1]` is the **open-economy fiscal
multiplier's reciprocal** — this is the standard textbook result that import
leakage (m1) and taxation (tau) both shrink the multiplier relative to the
closed-economy `1/(1-c1)`.

**Monetary transmission (crowding-out channel)**: the real interest rate
`r` feeds into investment with coefficient `-i1`. An optional Taylor-rule
reaction function lets the policy rate — and hence `r` — respond
endogenously to the inflation and output gaps a fiscal expansion creates,
which is the mechanism behind "crowding out" in this model.

**Phillips curve** (expectations-augmented, with an oil cost-push term):

    pi_t = pi_expected + kappa * output_gap_t + lambda_oil * oil_price_pct_change_t

**Okun's law**:

    u_t = u_natural - okun_coefficient * output_gap_t

**Debt dynamics** (standard law of motion for the debt-to-GDP ratio `b`):

    b_t = b_{t-1} * (1 + i_debt) / (1 + g_nominal) - primary_balance_ratio_t

**Exchange rate** (simplified, heuristic interest-parity direction only —
NOT a rigorous forward-looking UIP/BoP model): a higher domestic policy
rate relative to the foreign rate is assumed to appreciate the rupee
(lower `exchange_rate`, defined as INR per USD).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class CalibrationParams:
    """Illustrative calibration — loosely consistent with publicly reported
    aggregate ratios (RBI, MoSPI) for India, chosen for pedagogical realism,
    **not** estimated econometrically. Every field is overridable.
    """

    # Potential output level (index = 100 at the calibration base year).
    potential_gdp: float = 100.0

    # Consumption function: C = c0 + c1 * (1-tau) * Y
    c0: float = 18.0          # autonomous consumption (shifted by confidence)
    c1: float = 0.70          # marginal propensity to consume (illustrative; India households save a meaningful share of income)
    tax_rate: float = 0.17    # illustrative tax-to-GDP-like proportional rate

    # Investment function: I = i0 - i1*r + i2*confidence
    i0: float = 16.0
    i1: float = 0.9           # interest-rate sensitivity of investment
    i2: float = 0.5           # confidence sensitivity of investment

    # Exports: X = x0 + x1*foreign_demand - x2*exchange_gap
    x0: float = 20.0
    x1: float = 0.6
    x2: float = 0.4

    # Imports: M = m0 + m1*Y + m2*oil_price/exchange_rate
    m0: float = 5.0
    m1: float = 0.22          # illustrative import propensity (India's import-to-GDP ratio is materially above this in reality; this is a model elasticity, not that ratio)
    m2: float = 0.08

    # Phillips curve: pi = pi_e + kappa*output_gap + lambda_oil*oil_pct_change
    kappa: float = 0.30
    lambda_oil: float = 0.05
    expected_inflation: float = 0.045

    # Okun's law: u = u_natural - okun*output_gap
    natural_unemployment: float = 0.07
    okun_coefficient: float = 0.35

    # Debt dynamics
    debt_interest_rate: float = 0.07
    nominal_growth_rate: float = 0.11
    initial_debt_to_gdp: float = 0.82

    # Monetary / exchange-rate transmission
    neutral_real_rate: float = 0.015
    foreign_policy_rate: float = 0.04
    rate_pass_through_to_fx: float = 1.5   # heuristic sensitivity, not a BoP model

    # Optional Taylor-rule reaction function (used only if enabled per scenario)
    taylor_inflation_weight: float = 0.5
    taylor_output_weight: float = 0.5
    inflation_target: float = 0.04


DEFAULT_PARAMS = CalibrationParams()


def _consumption_shift(consumer_confidence: float) -> float:
    """Confidence is on a 0-100 scale, 50 = neutral; shifts c0 linearly."""
    return 0.15 * (consumer_confidence - 50.0)


def equilibrium_output(
    government_spending: float,
    tax_rate: float,
    real_interest_rate: float,
    foreign_demand: float,
    exchange_rate_gap: float,
    oil_price: float,
    exchange_rate_level: float,
    consumer_confidence: float,
    investment_confidence: float,
    params: CalibrationParams,
) -> float:
    """Closed-form equilibrium GDP for one period, given policy/shock inputs."""
    c0_eff = params.c0 + _consumption_shift(consumer_confidence)
    invest_conf_shift = 0.15 * (investment_confidence - 50.0)
    A = (
        c0_eff
        + params.i0 - params.i1 * real_interest_rate + params.i2 * invest_conf_shift
        + government_spending
        + params.x0 + params.x1 * foreign_demand - params.x2 * exchange_rate_gap
        - params.m0 - params.m2 * oil_price / max(exchange_rate_level, 1e-6)
    )
    denom = 1.0 - params.c1 * (1.0 - tax_rate) + params.m1
    return A / denom


def fiscal_multiplier(tax_rate: float, params: CalibrationParams) -> float:
    """dY/dG in closed form — the reciprocal of the equilibrium-output
    denominator. Falls as import leakage (m1) or the tax rate rises."""
    return 1.0 / (1.0 - params.c1 * (1.0 - tax_rate) + params.m1)


def trade_flows(
    gdp: float, foreign_demand: float, exchange_rate_gap: float,
    oil_price: float, exchange_rate_level: float, params: CalibrationParams,
) -> Dict[str, float]:
    exports = params.x0 + params.x1 * foreign_demand - params.x2 * exchange_rate_gap
    imports = params.m0 + params.m1 * gdp + params.m2 * oil_price / max(exchange_rate_level, 1e-6)
    return {"exports": exports, "imports": imports}


def phillips_curve_inflation(
    output_gap_pct: float, oil_price_pct_change: float, params: CalibrationParams,
) -> float:
    return params.expected_inflation + params.kappa * output_gap_pct + params.lambda_oil * oil_price_pct_change


def okuns_law_unemployment(output_gap_pct: float, params: CalibrationParams) -> float:
    return max(params.natural_unemployment - params.okun_coefficient * output_gap_pct, 0.0)


def debt_dynamics_step(
    prior_debt_to_gdp: float, primary_balance_ratio: float, params: CalibrationParams,
) -> float:
    """One step of the standard debt-to-GDP law of motion."""
    growth_adj = (1.0 + params.debt_interest_rate) / (1.0 + params.nominal_growth_rate)
    return prior_debt_to_gdp * growth_adj - primary_balance_ratio


def taylor_rule_rate(inflation: float, output_gap_pct: float, params: CalibrationParams) -> float:
    return (
        params.neutral_real_rate + params.inflation_target
        + params.taylor_inflation_weight * (inflation - params.inflation_target)
        + params.taylor_output_weight * output_gap_pct
    )


def exchange_rate_step(
    prior_rate: float, domestic_policy_rate: float, params: CalibrationParams,
) -> float:
    """Heuristic update: a positive domestic-foreign rate differential
    appreciates the rupee (lower INR-per-USD). Deliberately simplified —
    see METHODOLOGY.md, 'What this model is not,' for why this is not a
    rigorous UIP/balance-of-payments model."""
    differential = domestic_policy_rate - params.foreign_policy_rate
    return prior_rate * (1.0 - params.rate_pass_through_to_fx * differential * 0.1)


@dataclass
class ScenarioInputs:
    """One period's exogenous policy/shock inputs. All fields are the ones
    a user is meant to vary via the scenario builder."""

    government_spending: float = 22.0
    tax_rate: float = DEFAULT_PARAMS.tax_rate
    subsidies: float = 2.0
    policy_rate: float = 0.065
    oil_price: float = 80.0          # USD/barrel-style index
    exchange_rate: float = 83.0      # INR per USD
    foreign_demand: float = 20.0
    consumer_confidence: float = 50.0
    investment_confidence: float = 50.0
    use_taylor_rule: bool = False


def run_scenario(
    inputs_path: List[ScenarioInputs],
    params: CalibrationParams = DEFAULT_PARAMS,
) -> pd.DataFrame:
    """Simulate the model year-by-year given a path of `ScenarioInputs`
    (one entry per year). Returns a tidy DataFrame of every tracked
    variable — GDP, inflation, consumption, investment, unemployment,
    deficit, debt-to-GDP, exchange rate, imports, exports.
    """
    if not inputs_path:
        raise ValueError("inputs_path must contain at least one period.")

    rows = []
    debt_to_gdp = params.initial_debt_to_gdp
    exchange_rate = inputs_path[0].exchange_rate
    oil_price_prev: Optional[float] = None

    for t, inp in enumerate(inputs_path):
        real_rate = (
            taylor_rule_rate(params.expected_inflation, 0.0, params)
            if inp.use_taylor_rule
            else inp.policy_rate
        ) - params.expected_inflation

        exchange_rate_gap = (exchange_rate - inp.exchange_rate) / inp.exchange_rate if inp.exchange_rate else 0.0

        gdp = equilibrium_output(
            government_spending=inp.government_spending + inp.subsidies,
            tax_rate=inp.tax_rate,
            real_interest_rate=real_rate,
            foreign_demand=inp.foreign_demand,
            exchange_rate_gap=exchange_rate_gap,
            oil_price=inp.oil_price,
            exchange_rate_level=exchange_rate,
            consumer_confidence=inp.consumer_confidence,
            investment_confidence=inp.investment_confidence,
            params=params,
        )
        output_gap_pct = (gdp - params.potential_gdp) / params.potential_gdp

        oil_pct_change = 0.0 if oil_price_prev is None else (inp.oil_price - oil_price_prev) / oil_price_prev
        oil_price_prev = inp.oil_price

        inflation = phillips_curve_inflation(output_gap_pct, oil_pct_change, params)
        unemployment = okuns_law_unemployment(output_gap_pct, params)

        consumption = params.c0 + _consumption_shift(inp.consumer_confidence) + params.c1 * (1 - inp.tax_rate) * gdp
        investment = params.i0 - params.i1 * real_rate + params.i2 * 0.15 * (inp.investment_confidence - 50.0)
        flows = trade_flows(gdp, inp.foreign_demand, exchange_rate_gap, inp.oil_price, exchange_rate, params)

        revenue = inp.tax_rate * gdp
        spending = inp.government_spending + inp.subsidies
        deficit = spending - revenue
        primary_balance_ratio = -(deficit) / max(gdp, 1e-6)
        debt_to_gdp = debt_dynamics_step(debt_to_gdp, primary_balance_ratio, params)

        policy_rate_used = (
            taylor_rule_rate(inflation, output_gap_pct, params) if inp.use_taylor_rule else inp.policy_rate
        )
        exchange_rate = exchange_rate_step(exchange_rate, policy_rate_used, params)

        rows.append({
            "period": t,
            "gdp": gdp,
            "output_gap_pct": output_gap_pct * 100,
            "inflation_pct": inflation * 100,
            "unemployment_pct": unemployment * 100,
            "consumption": consumption,
            "investment": investment,
            "exports": flows["exports"],
            "imports": flows["imports"],
            "net_exports": flows["exports"] - flows["imports"],
            "govt_deficit": deficit,
            "debt_to_gdp_pct": debt_to_gdp * 100,
            "exchange_rate": exchange_rate,
            "policy_rate_pct": policy_rate_used * 100,
        })

    return pd.DataFrame(rows)


def compare_scenarios(
    baseline_path: List[ScenarioInputs],
    shock_path: List[ScenarioInputs],
    params: CalibrationParams = DEFAULT_PARAMS,
) -> pd.DataFrame:
    """Run baseline and shock paths and return a merged DataFrame with
    `_baseline` / `_shock` suffixes plus a `_delta` column per variable —
    the core 'baseline vs. shock' scenario-comparison view."""
    base = run_scenario(baseline_path, params)
    shock = run_scenario(shock_path, params)
    merged = base.merge(shock, on="period", suffixes=("_baseline", "_shock"))
    for col in base.columns:
        if col == "period":
            continue
        merged[f"{col}_delta"] = merged[f"{col}_shock"] - merged[f"{col}_baseline"]
    return merged


def constant_path(inputs: ScenarioInputs, years: int) -> List[ScenarioInputs]:
    """Convenience: repeat the same inputs for `years` periods."""
    if years <= 0:
        raise ValueError("years must be positive.")
    return [replace(inputs) for _ in range(years)]
