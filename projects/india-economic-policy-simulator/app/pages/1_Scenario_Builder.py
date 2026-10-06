from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import plotly.graph_objects as go
import streamlit as st

from policy_simulator.macro_model import (
    CalibrationParams, ScenarioInputs, constant_path, compare_scenarios, fiscal_multiplier,
)

st.set_page_config(page_title="Scenario Builder", page_icon="🎛️", layout="wide")
st.title("🎛️ Scenario Builder: Baseline vs. Shock")

params = CalibrationParams()

st.sidebar.header("Baseline inputs")
baseline = ScenarioInputs(
    government_spending=st.sidebar.slider("Govt. spending (G)", 10.0, 40.0, 22.0),
    tax_rate=st.sidebar.slider("Tax rate (τ)", 0.05, 0.35, params.tax_rate),
    subsidies=st.sidebar.slider("Subsidies", 0.0, 10.0, 2.0),
    policy_rate=st.sidebar.slider("Policy rate (%)", 2.0, 10.0, 6.5) / 100,
    oil_price=st.sidebar.slider("Oil price index", 40.0, 150.0, 80.0),
    exchange_rate=st.sidebar.slider("Exchange rate (₹/$)", 70.0, 95.0, 83.0),
    foreign_demand=st.sidebar.slider("Foreign demand index", 5.0, 40.0, 20.0),
    consumer_confidence=st.sidebar.slider("Consumer confidence (0-100)", 0, 100, 50),
    investment_confidence=st.sidebar.slider("Investment confidence (0-100)", 0, 100, 50),
    use_taylor_rule=st.sidebar.checkbox("Endogenous policy rate (Taylor rule)", value=False),
)
years = st.sidebar.slider("Horizon (years)", 1, 15, 8)

st.subheader("Shock")
shock_var = st.selectbox(
    "Which input changes in the shock scenario?",
    ["government_spending", "tax_rate", "policy_rate", "oil_price", "foreign_demand",
     "consumer_confidence", "investment_confidence"],
)
shock_delta = st.slider("Shock size (added to baseline value)", -20.0, 20.0, 5.0)

shock_inputs = ScenarioInputs(**{**baseline.__dict__, shock_var: getattr(baseline, shock_var) + shock_delta})

baseline_path = constant_path(baseline, years)
shock_path = constant_path(shock_inputs, years)
merged = compare_scenarios(baseline_path, shock_path, params)

mult = fiscal_multiplier(baseline.tax_rate, params)
st.metric("Implied fiscal multiplier (dY/dG, this calibration)", f"{mult:.2f}")

tabs = st.tabs(["GDP & components", "Inflation & unemployment", "Fiscal & debt", "External sector", "Raw table"])

with tabs[0]:
    fig = go.Figure()
    for col, name in [("gdp_baseline", "GDP (baseline)"), ("gdp_shock", "GDP (shock)")]:
        fig.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig.update_layout(title="GDP: baseline vs. shock", xaxis_title="Year", yaxis_title="Index")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"GDP delta by year {years}: {merged['gdp_delta'].iloc[-1]:.2f} (index points)")

with tabs[1]:
    fig = go.Figure()
    for col, name in [("inflation_pct_baseline", "Inflation % (baseline)"), ("inflation_pct_shock", "Inflation % (shock)")]:
        fig.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig.update_layout(title="Inflation (Phillips curve)", xaxis_title="Year", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)

    fig_u = go.Figure()
    for col, name in [("unemployment_pct_baseline", "Unemployment % (baseline)"), ("unemployment_pct_shock", "Unemployment % (shock)")]:
        fig_u.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig_u.update_layout(title="Unemployment (Okun's law)", xaxis_title="Year", yaxis_title="%")
    st.plotly_chart(fig_u, use_container_width=True)

with tabs[2]:
    fig = go.Figure()
    for col, name in [("debt_to_gdp_pct_baseline", "Debt/GDP % (baseline)"), ("debt_to_gdp_pct_shock", "Debt/GDP % (shock)")]:
        fig.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig.update_layout(title="Public debt-to-GDP ratio", xaxis_title="Year", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Deficit = G + subsidies − τ·Y. Debt dynamics: b_t = b_{t-1}·(1+i)/(1+g) − primary_balance_ratio_t.")

with tabs[3]:
    fig = go.Figure()
    for col, name in [("exchange_rate_baseline", "₹/$ (baseline)"), ("exchange_rate_shock", "₹/$ (shock)")]:
        fig.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig.update_layout(title="Exchange rate", xaxis_title="Year", yaxis_title="₹ per $")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    for col, name in [("net_exports_baseline", "Net exports (baseline)"), ("net_exports_shock", "Net exports (shock)")]:
        fig2.add_trace(go.Scatter(x=merged["period"], y=merged[col], name=name))
    fig2.update_layout(title="Net exports", xaxis_title="Year", yaxis_title="Index")
    st.plotly_chart(fig2, use_container_width=True)

with tabs[4]:
    st.dataframe(merged, use_container_width=True)

st.divider()
with st.expander("Transmission mechanism (what moves what)"):
    st.markdown(
        """
1. **Fiscal** (`G`, `τ`, subsidies) → directly shifts aggregate demand →
   GDP, via the multiplier `1 / [1 − c₁(1−τ) + m₁]`.
2. **Monetary** (policy rate) → real interest rate `r` → investment
   (`I = i₀ − i₁r`) → GDP. If "endogenous policy rate" is on, a fiscal
   expansion raises the policy rate via the Taylor rule, which *crowds out*
   some investment — the model's crowding-out channel.
3. **GDP → inflation** via the Phillips curve (output gap) and **GDP →
   unemployment** via Okun's law.
4. **Oil price** → import bill → both the trade balance and (via the
   Phillips curve's cost-push term) inflation.
5. **Exchange rate** responds heuristically to the domestic-foreign rate
   differential, then feeds back into exports/imports next period.
"""
    )
