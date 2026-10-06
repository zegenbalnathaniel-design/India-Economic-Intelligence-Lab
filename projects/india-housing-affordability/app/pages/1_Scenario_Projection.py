"""Scenario projection page: conservative / baseline / optimistic affordability
trajectories over a multi-year horizon, for one city (synthetic baseline) or
custom numbers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import plotly.graph_objects as go
import streamlit as st

from housing_affordability.data_loader import CITY_NAMES, load_synthetic_city_baseline
from housing_affordability.scenarios import STANDARD_SCENARIOS, run_standard_scenarios

st.set_page_config(page_title="Scenario Projection", page_icon="📈", layout="wide")

st.title("📈 Scenario Projection")
st.caption(
    "How affordability evolves over time under three sets of growth "
    "assumptions. These are **mechanical projections of the assumptions you "
    "choose**, not forecasts of any real city's future."
)
st.warning(
    "⚠️ **SYNTHETIC DATA**: starting house price / income come from the "
    "same illustrative per-city baseline as the Home page. Growth rate "
    "assumptions below are scenario inputs you control, not predictions."
)

baseline_df = load_synthetic_city_baseline().set_index("city")

st.sidebar.header("Starting point")
city = st.sidebar.selectbox("City (synthetic baseline)", ["Custom"] + CITY_NAMES, index=1)
if city != "Custom":
    row = baseline_df.loc[city]
    default_price = float(row["synthetic_house_price_inr"])
    default_income = float(row["synthetic_annual_household_income_inr"])
else:
    default_price = 8_000_000.0
    default_income = 1_500_000.0

house_price = st.sidebar.number_input(
    "Starting house price (INR)", min_value=100_000.0, value=default_price, step=100_000.0
)
annual_income = st.sidebar.number_input(
    "Starting annual income (INR)", min_value=50_000.0, value=default_income, step=50_000.0
)
down_payment_pct = st.sidebar.slider("Down payment assumed (%)", 0, 100, 20) / 100
loan_years = st.sidebar.slider("Loan tenure for EMI columns (years)", 1, 30, 20)
horizon = st.sidebar.slider("Projection horizon (years)", 3, 30, 15)

st.subheader("Scenario assumptions")
assumption_cols = st.columns(3)
for col, (key, scenario) in zip(assumption_cols, STANDARD_SCENARIOS.items()):
    with col:
        st.markdown(f"**{scenario.name}**")
        st.markdown(
            f"- House-price growth: {scenario.house_price_growth:.1%}/yr\n"
            f"- Income growth: {scenario.income_growth:.1%}/yr\n"
            f"- Mortgage rate: {scenario.mortgage_rate:.1%}\n"
            f"- Savings rate: {scenario.savings_rate:.0%} of income/yr"
        )

results = run_standard_scenarios(
    initial_house_price=house_price,
    initial_annual_income=annual_income,
    horizon_years=horizon,
    down_payment_pct=down_payment_pct,
    loan_years=loan_years,
)

colors = {"conservative": "#E45756", "baseline": "#4C78A8", "optimistic": "#54A24B"}

fig_pir = go.Figure()
for key, projection in results.items():
    fig_pir.add_trace(
        go.Scatter(
            x=projection.table.index,
            y=projection.table["price_to_income"],
            name=projection.scenario.name,
            line=dict(color=colors[key]),
        )
    )
fig_pir.update_layout(
    title="Price-to-income ratio over time, by scenario",
    xaxis_title="Year",
    yaxis_title="Price-to-income ratio",
    height=440,
)

fig_savings = go.Figure()
for key, projection in results.items():
    fig_savings.add_trace(
        go.Scatter(
            x=projection.table.index,
            y=projection.table["cumulative_savings"],
            name=f"{projection.scenario.name} — cumulative savings",
            line=dict(color=colors[key]),
        )
    )
    fig_savings.add_trace(
        go.Scatter(
            x=projection.table.index,
            y=projection.table["down_payment_target"],
            name=f"{projection.scenario.name} — down payment target",
            line=dict(color=colors[key], dash="dot"),
            opacity=0.6,
        )
    )
fig_savings.update_layout(
    title="Cumulative savings vs. down-payment target",
    xaxis_title="Year",
    yaxis_title="INR",
    height=440,
)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_pir, use_container_width=True)
with col2:
    st.plotly_chart(fig_savings, use_container_width=True)

st.subheader("Years until the down payment is affordable")
cols = st.columns(3)
for col, (key, projection) in zip(cols, results.items()):
    years_to_afford = projection.years_to_afford_down_payment
    label = f"{years_to_afford} years" if years_to_afford is not None else f"> {horizon} years"
    col.metric(projection.scenario.name, label)

st.caption(
    "\"Years to afford the down payment\" is the first projected year in "
    "which cumulative savings (a constant share of growing income) meet or "
    "exceed the down-payment target (a constant share of the growing house "
    "price). It is a direct mechanical consequence of the growth "
    "assumptions above — change them and this number changes accordingly."
)

with st.expander("See the full year-by-year table (baseline scenario)"):
    st.dataframe(results["baseline"].table.style.format("{:,.2f}"))

st.divider()
st.caption(
    "Part of a nine-project open-source portfolio exploring economics, "
    "finance and Indian economic data. See the root README for the full set."
)
