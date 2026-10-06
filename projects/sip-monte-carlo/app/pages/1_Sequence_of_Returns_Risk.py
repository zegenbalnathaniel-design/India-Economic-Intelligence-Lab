"""Dedicated page: sequence-of-returns risk, made visual."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from sip_monte_carlo.sequence_risk import demo_sequence_of_returns_risk  # noqa: E402

FORWARD_COLOR = "#2a78d6"   # categorical slot 1 (blue)
REVERSED_COLOR = "#eb6834"  # categorical slot 2 (orange)
GRID_COLOR = "#e1e0d9"

st.set_page_config(page_title="Sequence of Returns Risk", page_icon="🔀", layout="wide")

st.title("Sequence of Returns Risk")
st.markdown(
    """
**Same multiset of annual returns. Same arithmetic mean. Different order.
Different final wealth.**

This is a specific, well-known phenomenon in SIP and retirement planning,
separate from "what will the average return be?" uncertainty: when money is
flowing in or out regularly, **the order in which good and bad years occur
matters**, because later returns apply to a bigger accumulated base than
earlier returns do.

This page uses a small, fixed, user-editable set of annual returns — it is
a worked example, not a Monte Carlo simulation, and it makes no claim about
which ordering is more likely to happen in real markets.
"""
)

st.subheader("Edit the annual returns (%)")
default_returns = [30.0, -10.0, 20.0, -5.0, 15.0, 25.0, -15.0, 10.0]
cols = st.columns(len(default_returns))
returns_pct = []
for i, col in enumerate(cols):
    with col:
        val = st.number_input(f"Year {i + 1}", value=default_returns[i], step=1.0, key=f"yr_{i}")
        returns_pct.append(val)
annual_returns = [v / 100.0 for v in returns_pct]

c1, c2 = st.columns(2)
with c1:
    annual_contribution = st.number_input(
        "Annual contribution (₹, added at year-end)", min_value=0.0, value=180_000.0, step=10_000.0
    )
with c2:
    initial_capital = st.number_input("Initial capital (₹)", min_value=0.0, value=0.0, step=10_000.0)

result = demo_sequence_of_returns_risk(
    annual_returns, annual_contribution=annual_contribution, initial_capital=initial_capital
)

st.metric("Arithmetic mean annual return (identical in both orderings)", f"{result.arithmetic_mean_return * 100:.2f}%")

m1, m2, m3 = st.columns(3)
m1.metric("Final value — returns as entered (order A)", f"₹{result.forward_final:,.0f}")
m2.metric("Final value — reversed order (order B)", f"₹{result.reversed_final:,.0f}")
m3.metric(
    "Difference (A − B)",
    f"₹{result.difference:,.0f}",
    delta=f"{result.percent_difference * 100:,.1f}% of order B's value",
)

if annual_contribution == 0:
    st.warning(
        "With zero ongoing contributions, order doesn't matter: multiplying "
        "the same set of growth factors together gives the same product "
        "regardless of order. Set a contribution above zero to see sequence "
        "risk appear — it is specifically a consequence of adding money "
        "to a growing balance."
    )

years_axis = np.arange(len(annual_returns) + 1)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=years_axis, y=result.forward_path, mode="lines+markers",
    name="Order A (returns as entered)", line=dict(color=FORWARD_COLOR, width=2.5),
    marker=dict(size=7),
    hovertemplate="Year %{x}<br>₹%{y:,.0f}<extra>Order A</extra>",
))
fig.add_trace(go.Scatter(
    x=years_axis, y=result.reversed_path, mode="lines+markers",
    name="Order B (reversed)", line=dict(color=REVERSED_COLOR, width=2.5, dash="dash"),
    marker=dict(size=7, symbol="diamond"),
    hovertemplate="Year %{x}<br>₹%{y:,.0f}<extra>Order B</extra>",
))
fig.update_layout(
    template="plotly_white",
    height=440,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(title="Year", gridcolor=GRID_COLOR, dtick=1, zeroline=False),
    yaxis=dict(title="Wealth (₹)", gridcolor=GRID_COLOR, tickformat=",", zeroline=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("The returns used in each order"):
    st.write("Order A:", [f"{r * 100:.1f}%" for r in result.annual_returns_forward])
    st.write("Order B (reversed):", [f"{r * 100:.1f}%" for r in result.annual_returns_reversed])

st.markdown(
    """
### Why this happens

With regular contributions, the balance at year *t* depends on *when* each
return was applied: a return that lands in year 8, after years of
contributions have piled up, is multiplied against a much larger base than
the same return would be if it landed in year 1. Reversing the order
doesn't change the arithmetic mean of the returns, but it changes **which
years were large and which were small when each return hit** — so the two
final values generally differ, often substantially, from the same inputs.

This is exactly why a Monte Carlo simulation (see the Home page) is more
informative than a single "average return" projection: it doesn't just
show uncertainty in the *average*, it implicitly samples many different
*sequences*, which is where a meaningful share of real-world outcome
variation comes from.
"""
)
