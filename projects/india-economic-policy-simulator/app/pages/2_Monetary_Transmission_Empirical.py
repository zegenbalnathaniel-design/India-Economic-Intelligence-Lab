"""iBFPI vs. RBI repo rate — EMPIRICAL module (not a model simulation)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import plotly.graph_objects as go
import streamlit as st

from policy_simulator import data_loaders as dl
from policy_simulator import monetary_transmission as mt

st.set_page_config(page_title="Monetary Transmission (Empirical)", page_icon="🏦", layout="wide")
st.title("🏦 Monetary Transmission — Empirical Analysis")

st.warning(
    "⚠️ **Illustrative data.** `data/processed/bank_panel.csv` is a seeded "
    "synthetic panel built to demonstrate the iBFPI methodology end-to-end "
    "(see `docs/DATA_SOURCES.md`). It is not a substitute for real bank "
    "disclosures. Replace it with real data to get an empirical result."
)

panel = dl.load_bank_panel()
repo = dl.load_repo_rate()

banks = dl.bank_names()
selected = st.multiselect("Banks", banks, default=banks)
weighting = st.radio("Cross-bank aggregation", ["Equal-weighted", "Custom weights"], horizontal=True)

scored = mt.compute_ibfpi(panel[panel["bank"].isin(selected)])

if weighting == "Equal-weighted":
    agg = mt.cross_bank_aggregate(scored)
else:
    weights = {b: st.slider(f"Weight: {b}", 0.0, 1.0, 1.0 / max(len(selected), 1)) for b in selected}
    agg = mt.cross_bank_aggregate(scored, weights=weights)

joined = agg.merge(repo, on="period", how="left")

fig = go.Figure()
fig.add_trace(go.Scatter(x=joined["period"], y=joined["ibfpi_system"], name="iBFPI (system)", yaxis="y1"))
fig.add_trace(go.Scatter(x=joined["period"], y=joined["repo_rate"], name="RBI repo rate (%)", yaxis="y2"))
fig.update_layout(
    title="iBFPI vs. RBI repo rate",
    yaxis=dict(title="iBFPI (robust z-score units)"),
    yaxis2=dict(title="Repo rate (%)", overlaying="y", side="right"),
    height=480,
)
st.plotly_chart(fig, use_container_width=True)

corr = mt.spearman(joined["repo_rate"], joined["ibfpi_system"])
c1, c2, c3 = st.columns(3)
c1.metric("Spearman ρ", f"{corr.rho:.3f}" if corr.rho == corr.rho else "n/a")
c2.metric("p-value", f"{corr.p_value:.3f}" if corr.p_value == corr.p_value else "n/a")
c3.metric("n (quarters)", corr.n)

st.caption(
    "A two-sided test of H₀: ρ = 0, uncorrected for autocorrelation in the "
    "quarterly series. Correlation ≠ causation — see Limitations."
)

st.subheader("Rate-regime split")
labelled, rising, falling, stable = mt.regime_split(joined)
r1, r2, r3 = st.columns(3)
r1.metric("Rising-rate regime ρ", f"{rising.rho:.3f}" if rising.rho == rising.rho else "n/a", f"n={rising.n}")
r2.metric("Falling-rate regime ρ", f"{falling.rho:.3f}" if falling.rho == falling.rho else "n/a", f"n={falling.n}")
r3.metric("Stable-rate regime ρ", f"{stable.rho:.3f}" if stable.rho == stable.rho else "n/a", f"n={stable.n}")

fig2 = go.Figure()
for regime, color in [("rising", "crimson"), ("falling", "seagreen"), ("stable", "gray")]:
    sub = labelled[labelled["regime"] == regime]
    fig2.add_trace(go.Scatter(x=sub["period"], y=sub["ibfpi_system"], mode="markers", name=regime, marker=dict(color=color)))
fig2.update_layout(title="iBFPI coloured by rate regime", xaxis_title="Quarter", yaxis_title="iBFPI")
st.plotly_chart(fig2, use_container_width=True)

with st.expander("Per-indicator z-scores"):
    st.dataframe(scored, use_container_width=True)
