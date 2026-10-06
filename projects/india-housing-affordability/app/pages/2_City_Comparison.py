"""City comparison page: price-to-income and EMI-to-income across all eight
cities under a shared set of financing assumptions, using the synthetic
per-city baseline.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import plotly.graph_objects as go
import streamlit as st

from housing_affordability.data_loader import load_synthetic_city_baseline
from housing_affordability.metrics import affordability_summary

st.set_page_config(page_title="City Comparison", page_icon="🏙️", layout="wide")

st.title("🏙️ City Comparison")
st.caption(
    "Price-to-income and EMI-to-income across all eight cities, applying "
    "the same financing assumptions to each city's synthetic baseline so "
    "only the starting price/income differ."
)
st.warning(
    "⚠️ **SYNTHETIC DATA — illustrative only.** Every house price and "
    "household income figure below comes from "
    "`examples/generate_synthetic_city_housing.py`, a deterministic, "
    "seeded generator — not a real survey or market index. Only the "
    "*relative ordering* across cities is meant to echo commonly-reported "
    "qualitative patterns (Mumbai and Delhi NCR least affordable; Kolkata "
    "and Ahmedabad relatively more affordable among these eight). Treat "
    "every number here as a methodology demonstration, never as an "
    "empirical finding about Indian housing markets. See "
    "`docs/DATA_SOURCES.md` for where to source real data."
)

baseline_df = load_synthetic_city_baseline()

st.sidebar.header("Shared financing assumptions")
down_payment_pct = st.sidebar.slider("Down payment (%)", 0, 100, 20) / 100
mortgage_rate = st.sidebar.slider("Mortgage interest rate (% p.a.)", 0.0, 18.0, 8.5) / 100
loan_years = st.sidebar.slider("Loan tenure (years)", 1, 30, 20)

rows = []
for _, r in baseline_df.iterrows():
    summary = affordability_summary(
        house_price=float(r["synthetic_house_price_inr"]),
        annual_household_income=float(r["synthetic_annual_household_income_inr"]),
        down_payment_pct=down_payment_pct,
        annual_interest_rate=mortgage_rate,
        loan_years=loan_years,
        city=r["city"],
    )
    rows.append(summary)

rows_sorted = sorted(rows, key=lambda s: s.price_to_income, reverse=True)
cities_sorted = [s.city for s in rows_sorted]

fig_pir = go.Figure(
    data=[
        go.Bar(
            x=cities_sorted,
            y=[s.price_to_income for s in rows_sorted],
            marker_color="#4C78A8",
        )
    ]
)
fig_pir.update_layout(
    title="Price-to-income ratio by city (synthetic baseline)",
    yaxis_title="Price-to-income ratio",
    height=440,
)

fig_mpti = go.Figure(
    data=[
        go.Bar(
            x=cities_sorted,
            y=[s.mortgage_payment_to_income for s in rows_sorted],
            marker_color="#E45756",
        )
    ]
)
fig_mpti.update_layout(
    title=f"EMI-to-income ratio by city (at {down_payment_pct:.0%} down, {mortgage_rate:.1%}, {loan_years}y)",
    yaxis_title="EMI-to-income ratio",
    height=440,
)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_pir, use_container_width=True)
with col2:
    st.plotly_chart(fig_mpti, use_container_width=True)

st.subheader("Full comparison table")
table_df = baseline_df.set_index("city").loc[cities_sorted].copy()
table_df["price_to_income"] = [s.price_to_income for s in rows_sorted]
table_df["monthly_emi_inr"] = [s.monthly_emi for s in rows_sorted]
table_df["emi_to_income"] = [s.mortgage_payment_to_income for s in rows_sorted]
table_df["years_to_save_down_payment"] = [s.years_to_save_down_payment for s in rows_sorted]
st.dataframe(
    table_df[
        [
            "synthetic_house_price_inr",
            "synthetic_annual_household_income_inr",
            "price_to_income",
            "monthly_emi_inr",
            "emi_to_income",
            "years_to_save_down_payment",
        ]
    ].style.format(
        {
            "synthetic_house_price_inr": "₹{:,.0f}",
            "synthetic_annual_household_income_inr": "₹{:,.0f}",
            "price_to_income": "{:.2f}x",
            "monthly_emi_inr": "₹{:,.0f}",
            "emi_to_income": "{:.1%}",
            "years_to_save_down_payment": "{:.1f}",
        }
    )
)

st.divider()
st.caption(
    "Part of a nine-project open-source portfolio exploring economics, "
    "finance and Indian economic data. See the root README for the full set."
)
