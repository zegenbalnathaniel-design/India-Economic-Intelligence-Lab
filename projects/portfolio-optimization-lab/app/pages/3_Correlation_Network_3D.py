from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # for network_view.py

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from portfolio_lab import network3d as net
from network_view import build_network_html

st.set_page_config(page_title="Correlation Network (3D)", page_icon="🕸️", layout="wide")
st.title("🕸️ Asset Correlation Network — 3D")

state = st.session_state.get("portfolio_lab")
if state is None:
    st.warning("Build a portfolio on the **Portfolio Builder** page first.")
    st.stop()

cov, tickers = state["cov"], state["tickers"]
# Derive the correlation matrix from the covariance matrix: rho_ij = cov_ij / (sigma_i * sigma_j).
std = pd.Series(cov.values.diagonal() ** 0.5, index=tickers)
corr_df = cov.div(std, axis=0).div(std, axis=1)

threshold = st.slider("Minimum |correlation| to draw an edge", 0.0, 1.0, 0.3, 0.05)

layout = net.layout_from_correlation(corr_df)
edges = net.edge_list(corr_df, threshold=threshold)

weights = pd.Series(state["w_maxsharpe"], index=tickers)
nodes = layout.copy()
nodes["ticker"] = nodes.index
nodes["weight"] = weights.reindex(nodes.index).clip(lower=0).fillna(0)
nodes["exchange"] = pd.Series(state["exchanges"])

st.caption(
    "Node position: a **classical multidimensional scaling (MDS)** embedding of the correlation "
    "distance `sqrt(2(1-ρ))` into 3D — assets that move together sit close together; assets that "
    "move oppositely sit far apart. Node size: this ticker's weight in the max-Sharpe portfolio. "
    "Edge color: green = positive correlation, red = negative; edge opacity scales with |ρ|. "
    "Drag to rotate, scroll to zoom."
)

html = build_network_html(nodes, edges, height_px=600)
components.html(html, height=620, scrolling=False)

with st.expander("Correlation matrix"):
    st.dataframe(corr_df.style.format("{:.2f}").background_gradient(cmap="RdYlGn", vmin=-1, vmax=1), use_container_width=True)
