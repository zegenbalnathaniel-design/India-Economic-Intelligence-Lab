from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from portfolio_lab import optimizer as opt

st.set_page_config(page_title="Efficient Frontier (3D)", page_icon="🌐", layout="wide")
st.title("🌐 Efficient Frontier — 3D (Return × Volatility × Sharpe)")

state = st.session_state.get("portfolio_lab")
if state is None:
    st.warning("Build a portfolio on the **Portfolio Builder** page first — the frontier needs its μ and Σ.")
    st.stop()

mu, cov, tickers = state["mu"].values, state["cov"].values, state["tickers"]
rf = state["rf"]
constraints = state["constraints"]

r_min = opt.frontier_vertex_closed_form(mu, cov)
r_max = float(np.max(mu)) * 1.15
targets = np.linspace(r_min, r_max, 40)

use_constrained = constraints.long_only or constraints.max_weight < 1.0
if use_constrained:
    frontier = opt.efficient_frontier_constrained(mu, cov, targets, constraints)
    frontier = frontier[frontier["feasible"]]
else:
    frontier = opt.efficient_frontier_closed_form(mu, cov, targets)

frontier["sharpe"] = (frontier["target_return"] - rf) / frontier["volatility"]

st.caption(
    "Solid line/surface: the efficient frontier (minimum volatility for each target return), "
    f"computed {'numerically under your long-only / max-weight constraints (KKT via SLSQP)' if use_constrained else 'in closed form via the unconstrained Lagrangian solution'}. "
    "Scattered points: 2,000 random long-only portfolios, for scale."
)

rng = np.random.default_rng(42)
n = len(tickers)
random_w = rng.dirichlet(np.ones(n), size=2000)
random_ret = random_w @ mu
random_vol = np.sqrt(np.einsum("ij,jk,ik->i", random_w, cov, random_w))
random_sharpe = (random_ret - rf) / random_vol

fig = go.Figure()
fig.add_trace(go.Scatter3d(
    x=random_vol, y=random_ret, z=random_sharpe, mode="markers",
    marker=dict(size=2, color=random_sharpe, colorscale="Viridis", opacity=0.35),
    name="Random long-only portfolios",
))
fig.add_trace(go.Scatter3d(
    x=frontier["volatility"], y=frontier["target_return"], z=frontier["sharpe"],
    mode="lines+markers", line=dict(color="crimson", width=6),
    marker=dict(size=3, color="crimson"), name="Efficient frontier",
))

w_tan = state["w_maxsharpe"]
w_mv = state["w_minvar"]
for w, name, color in [(w_tan, "Max-Sharpe (tangency)", "gold"), (w_mv, "Min-variance", "cyan")]:
    ret = opt.portfolio_return(w, mu)
    vol = opt.portfolio_volatility(w, cov)
    sharpe = (ret - rf) / vol if vol > 0 else 0
    fig.add_trace(go.Scatter3d(x=[vol], y=[ret], z=[sharpe], mode="markers+text",
                                marker=dict(size=7, color=color, symbol="diamond"),
                                text=[name], textposition="top center", name=name))

fig.update_layout(
    scene=dict(xaxis_title="Volatility (σ)", yaxis_title="Expected return", zaxis_title="Sharpe ratio"),
    height=700, margin=dict(l=0, r=0, t=30, b=0),
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Why 3D instead of the usual 2D return-vs-volatility chart?"):
    st.markdown(
        "The classic chart plots return against volatility; the Sharpe ratio (their ratio, adjusted "
        "for the risk-free rate) is then just the slope of a line from the risk-free point. Plotting "
        "it as an explicit third axis makes that slope visible directly, and makes it easy to see "
        "that the tangency portfolio sits at the point of maximum slope — maximum Sharpe — by "
        "construction, not by inspection."
    )
