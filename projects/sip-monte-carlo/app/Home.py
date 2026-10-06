"""SIP & Wealth Accumulation Monte Carlo Simulator — Streamlit entry point."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sip_monte_carlo.engine import PERCENTILES, run_simulation  # noqa: E402

st.set_page_config(
    page_title="SIP Monte Carlo Simulator", page_icon="📊", layout="wide"
)

# --- Color roles (validated sequential-blue ramp + chart chrome) -----------
BAND_OUTER = "rgba(42, 120, 214, 0.14)"   # p10-p90, lightest fill
BAND_INNER = "rgba(42, 120, 214, 0.28)"   # p25-p75
LINE_MEDIAN = "#184f95"                    # step 600, darkest, the headline line
LINE_MEAN = "#eb6834"                      # categorical slot 2 (orange), secondary series
GRID_COLOR = "#e1e0d9"
MUTED = "#898781"

st.title("SIP & Wealth Accumulation Monte Carlo Simulator")
st.markdown(
    "Simulates the **distribution of outcomes** for a systematic investment "
    "plan (SIP) under a set of stated, fully-adjustable assumptions about "
    "returns, volatility, fees, contribution growth and inflation. "
    "**This is not a forecast.** No real market data is used anywhere in "
    "this tool — every number below is a parameterized simulation, and "
    "nothing here is investment advice."
)

with st.sidebar:
    st.header("Assumptions (all illustrative — override freely)")

    st.subheader("Contributions")
    monthly_contribution = st.slider(
        "Monthly SIP contribution (₹)", 500, 200_000, 15_000, step=500
    )
    contribution_growth_rate = st.slider(
        "Annual step-up in contribution (%/year)", 0.0, 20.0, 5.0, step=0.5
    ) / 100.0
    initial_capital = st.slider(
        "Initial lump sum already invested (₹)", 0, 5_000_000, 0, step=10_000
    )

    st.subheader("Horizon")
    duration_years = st.slider("Duration (years)", 1, 40, 20)

    st.subheader("Returns & risk (illustrative, not calibrated)")
    expected_annual_return = st.slider(
        "Expected annual return (%/year)", 0.0, 25.0, 12.0, step=0.5
    ) / 100.0
    annual_volatility = st.slider(
        "Annual volatility / standard deviation (%/year)", 0.0, 40.0, 18.0, step=0.5
    ) / 100.0

    st.subheader("Costs & inflation")
    annual_fee_rate = st.slider(
        "Annual fee / expense ratio drag (%/year)", 0.0, 3.0, 1.0, step=0.05
    ) / 100.0
    annual_inflation = st.slider(
        "Assumed annual inflation (%/year)", 0.0, 12.0, 5.0, step=0.25
    ) / 100.0

    st.subheader("Simulation controls")
    n_paths = st.select_slider(
        "Number of simulated paths", options=[500, 1000, 2000, 5000, 10000], value=2000
    )
    seed = st.number_input("Random seed", min_value=0, max_value=10**6, value=42, step=1)

    st.subheader("Goal")
    target_corpus = st.number_input(
        "Target corpus (₹) — probability of reaching it", min_value=0, value=10_000_000, step=100_000
    )

result = run_simulation(
    monthly_contribution=float(monthly_contribution),
    duration_years=int(duration_years),
    expected_annual_return=float(expected_annual_return),
    annual_volatility=float(annual_volatility),
    annual_inflation=float(annual_inflation),
    contribution_growth_rate=float(contribution_growth_rate),
    initial_capital=float(initial_capital),
    annual_fee_rate=float(annual_fee_rate),
    n_paths=int(n_paths),
    seed=int(seed),
)

# --- Headline metrics --------------------------------------------------------
summary = result.final_summary()
prob = result.probability_of_reaching(float(target_corpus))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Median final value (nominal)", f"₹{summary.loc['p50', 'nominal']:,.0f}")
c2.metric("Median final value (real, today's ₹)", f"₹{summary.loc['p50', 'real']:,.0f}")
c3.metric("Total contributed", f"₹{result.total_contributed + initial_capital:,.0f}")
c4.metric(f"P(reach ₹{target_corpus:,.0f})", f"{prob * 100:,.1f}%")

st.caption(
    "Median final value is reported because wealth distributions are "
    "right-skewed — a few lucky paths pull the **mean** up (currently "
    f"₹{summary.loc['mean', 'nominal']:,.0f} nominal) well above what a "
    "typical path actually experiences. The probability above is simply "
    "the share of simulated paths that happened to clear the target — a "
    "property of this model's assumptions, not a real-world odds-maker."
)

# --- Fan chart ---------------------------------------------------------------
st.subheader("Projected wealth over time — percentile fan chart")
view = st.radio("Show values in", ["Nominal (future rupees)", "Real (today's purchasing power)"], horizontal=True)
use_real = view.startswith("Real")
pdf = result.percentile_dataframe(real=use_real)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["p90"], mode="lines", line=dict(width=0),
    showlegend=False, hoverinfo="skip",
))
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["p10"], mode="lines", line=dict(width=0),
    fill="tonexty", fillcolor=BAND_OUTER, name="p10–p90 range",
    hovertemplate="Year %{x:.1f}<br>p10: ₹%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["p75"], mode="lines", line=dict(width=0),
    showlegend=False, hoverinfo="skip",
))
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["p25"], mode="lines", line=dict(width=0),
    fill="tonexty", fillcolor=BAND_INNER, name="p25–p75 range",
    hovertemplate="Year %{x:.1f}<br>p25: ₹%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["p50"], mode="lines",
    line=dict(width=2.5, color=LINE_MEDIAN), name="Median (p50)",
    hovertemplate="Year %{x:.1f}<br>Median: ₹%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=pdf["year"], y=pdf["mean"], mode="lines",
    line=dict(width=1.5, color=LINE_MEAN, dash="dot"), name="Mean",
    hovertemplate="Year %{x:.1f}<br>Mean: ₹%{y:,.0f}<extra></extra>",
))

fig.update_layout(
    template="plotly_white",
    height=480,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(title="Years", gridcolor=GRID_COLOR, zeroline=False),
    yaxis=dict(title="Wealth (₹)", gridcolor=GRID_COLOR, zeroline=False, tickformat=","),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "The shaded bands are **not** a confidence interval on reality — they "
    "describe the spread of outcomes produced by this specific model under "
    "the assumptions you chose in the sidebar. Widen the volatility slider "
    "and watch the bands widen and the median line sag relative to the "
    "mean: that gap is **volatility drag** (see the Sequence of Returns "
    "Risk page and the Methodology doc)."
)

st.subheader("Final-value summary")
st.dataframe(
    summary.style.format("₹{:,.0f}"),
    use_container_width=True,
)

st.info(
    "Part of a nine-project open-source portfolio exploring economics, "
    "finance and Indian economic data. See the root repository README for "
    "the full set, and the **Sequence of Returns Risk** page in the "
    "sidebar for why *when* good and bad years happen matters, even when "
    "the average doesn't change."
)
