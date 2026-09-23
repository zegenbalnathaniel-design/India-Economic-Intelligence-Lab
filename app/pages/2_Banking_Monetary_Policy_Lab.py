"""Banking & Monetary Policy Lab.

Adapts the BFPI methodology developed in the JP Morgan research paper to a
five-bank Indian panel (iBFPI), and compares the aggregate iBFPI to the
RBI repo rate through 2018-2024.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analysis import banking
from data_sources.loaders import (
    load_bank_panel, load_repo_rate, bank_names, joined_panel,
)
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote,
)


setup("Banking & Monetary Policy Lab")


with st.sidebar:
    st.markdown("## Banking Lab")
    st.caption("Sections")
    st.markdown(
        "- iBFPI construction\n"
        "- Aggregate iBFPI over time\n"
        "- RBI repo rate vs iBFPI\n"
        "- Regime split"
    )
    st.markdown("---")
    st.caption(
        "The iBFPI is my adaptation of the BFPI methodology from my JP Morgan "
        "research paper — not a published index."
    )


kicker("Banking & Monetary Policy · India")
st.title("iBFPI — a robust composite index of bank financial performance")
st.markdown(
    "The BFPI methodology from my Federal-Reserve / JP Morgan paper, applied "
    "to five Indian scheduled commercial banks over 2018-Q2 to 2024-Q3. "
    "Every step is transparent below; the illustrative panel is labelled "
    "as such and can be replaced with real disclosures without changing "
    "the code."
)

callout(
    "The panel shipped in the MVP is <b>illustrative and synthetic</b> — "
    "constructed to demonstrate the methodology end-to-end. Replace "
    "<code>data/processed/bank_panel.csv</code> and "
    "<code>repo_rate.csv</code> with values sourced from bank annual "
    "reports and RBI’s DBIE portal to reproduce with real numbers.",
    kind="warn",
)
source_badge(
    "Data · Illustrative (this build)",
    "Method · BFPI, adapted",
    "Reference · Author’s JP Morgan / Fed-rate paper",
)


# ---------- Controls ----------------------------------------------------------

panel = load_bank_panel()
repo = load_repo_rate()

with st.container():
    c1, c2 = st.columns([1.3, 1])
    with c1:
        selected = st.multiselect(
            "Banks in the panel",
            options=bank_names(),
            default=bank_names(),
            help="Deselect a bank to exclude it from the aggregate iBFPI.",
        )
    with c2:
        weighting = st.selectbox(
            "Cross-bank aggregation",
            options=["Equal-weighted", "Asset-weighted (illustrative)"],
            index=0,
        )

if not selected:
    st.warning("Select at least one bank.")
    st.stop()

sub = panel[panel["bank"].isin(selected)].copy()
scored = banking.compute_ibfpi(sub)

if weighting == "Equal-weighted":
    agg = banking.cross_bank_aggregate(scored)
else:
    # Illustrative weights roughly proportional to total assets FY24. NOT a
    # substitute for real weights; user-editable via the CSV.
    illustrative_weights = {
        "State Bank of India": 55.0,
        "HDFC Bank": 32.0,
        "ICICI Bank": 17.0,
        "Axis Bank": 12.0,
        "Kotak Mahindra Bank": 5.0,
    }
    active = {k: v for k, v in illustrative_weights.items() if k in selected}
    agg = banking.cross_bank_aggregate(scored, weights=active)


# ---------- iBFPI construction detail -----------------------------------------

st.header("Construction of iBFPI")
st.markdown(
    "For each indicator, a robust z-score is computed **per bank** using the "
    "bank's own historical median and MAD. The direction coefficient flips "
    "the sign for indicators where higher values are bad (net charge-offs, "
    "unrealised losses / CET1). The iBFPI is the equal-weight mean of the "
    "five standardised indicators."
)
st.latex(r"Z^*_{it} = D \cdot \frac{X_{it} - \mathrm{median}_i(X)}{1.4826 \cdot \mathrm{MAD}_i(X)}")
st.latex(r"iBFPI_{it} = \frac{1}{5} \sum_{k=1}^{5} Z^*_{k,it}")

with st.expander("Direction coefficients"):
    dcoef = pd.DataFrame([
        {"Indicator": banking.INDICATOR_LABELS[k], "Direction D": banking.INDICATOR_DIRECTION[k]}
        for k in banking.INDICATOR_DIRECTION
    ])
    st.dataframe(dcoef, hide_index=True, use_container_width=True)


# ---------- Aggregate iBFPI plot ---------------------------------------------

st.subheader("Aggregate iBFPI over time")
agg_fig = go.Figure()
agg_fig.add_scatter(
    x=agg["period"], y=agg["ibfpi_system"], mode="lines+markers",
    line=dict(width=2.4, color="#0A4D68"), name="iBFPI (system)",
)
agg_fig.add_hline(y=0, line=dict(color="#9CA3AF", width=1, dash="dash"))
agg_fig.update_layout(
    title=f"iBFPI, {weighting.lower()} across {len(selected)} bank(s)",
    yaxis_title="iBFPI (robust z-units)",
    xaxis_title="", height=360, hovermode="x unified",
)
st.plotly_chart(agg_fig, use_container_width=True)

with st.expander("What am I looking at?"):
    st.markdown(
        "A single scalar per quarter. Positive values indicate bank "
        "financial performance is above each bank's own historical median; "
        "negative values are below. Because indicators are standardised "
        "per bank, the aggregate is comparable across time but is not a "
        "level statement about the health of the sector in absolute terms."
    )


# ---------- Per-bank iBFPI ----------------------------------------------------

st.subheader("iBFPI by bank")
pb = scored[["bank", "period", "ibfpi"]].pivot(index="period", columns="bank", values="ibfpi")
pb_fig = go.Figure()
for col in pb.columns:
    pb_fig.add_scatter(x=pb.index, y=pb[col], mode="lines", name=col, line=dict(width=1.8))
pb_fig.add_hline(y=0, line=dict(color="#9CA3AF", width=1, dash="dash"))
pb_fig.update_layout(
    title="Per-bank iBFPI — each series is standardised to its own history",
    yaxis_title="iBFPI (robust z-units)",
    xaxis_title="", height=380, hovermode="x unified",
)
st.plotly_chart(pb_fig, use_container_width=True)


# ---------- Indicator inspector ----------------------------------------------

st.subheader("Component indicators")
tabs = st.tabs([banking.INDICATOR_LABELS[k] for k in banking.INDICATOR_DIRECTION])
for tab, key in zip(tabs, banking.INDICATOR_DIRECTION):
    with tab:
        wide = scored.pivot(index="period", columns="bank", values=key)
        fig = go.Figure()
        for col in wide.columns:
            fig.add_scatter(x=wide.index, y=wide[col], mode="lines", name=col, line=dict(width=1.8))
        fig.update_layout(
            title=banking.INDICATOR_LABELS[key],
            yaxis_title="Native units (see data dictionary)",
            xaxis_title="", height=320, hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Direction coefficient D = {banking.INDICATOR_DIRECTION[key]:+d}. "
            "Values are standardised per bank before entering the iBFPI."
        )


# ---------- RBI rate vs iBFPI -------------------------------------------------

st.markdown("---")
kicker("Monetary policy · financial conditions")
st.header("RBI repo rate vs iBFPI")

merged = agg.merge(repo, on="period", how="inner").dropna()

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_scatter(x=merged["period"], y=merged["ibfpi_system"], name="iBFPI",
                line=dict(color="#0A4D68", width=2.4), secondary_y=False)
fig.add_scatter(x=merged["period"], y=merged["repo_rate"], name="RBI repo rate (%)",
                line=dict(color="#B45309", width=2.0, dash="dot"), secondary_y=True)
fig.update_yaxes(title_text="iBFPI (robust z-units)", secondary_y=False)
fig.update_yaxes(title_text="Repo rate (%)", secondary_y=True)
fig.update_layout(title="iBFPI vs RBI repo rate", height=380, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

corr = banking.spearman(merged["repo_rate"], merged["ibfpi_system"])
c1, c2, c3 = st.columns(3)
with c1:
    stat_card("Spearman ρ", f"{corr.rho:+.3f}", "monotonic association")
with c2:
    stat_card("p-value", f"{corr.p_value:.3f}", "two-sided")
with c3:
    stat_card("n (quarters)", f"{corr.n}", f"{merged['period'].min():%Y-Q%q} to {merged['period'].max():%Y-Q%q}"
              if False else f"{merged['period'].min().year}-{merged['period'].max().year}")

callout(
    "Correlation is not causation. A negative Spearman ρ suggests that "
    "higher repo rates coincide with lower iBFPI values in the sample "
    "period — driven mechanically by the unrealised-loss channel — but "
    "identifies no causal effect. A proper event study or panel regression "
    "with controls would be needed to move beyond association.",
    kind="warn",
)


# ---------- Regime split ------------------------------------------------------

st.subheader("Rate-regime split")
labelled, rising, falling, stable = banking.regime_split(
    merged, rate_col="repo_rate", ibfpi_col="ibfpi_system",
)

reg_fig = go.Figure()
palette = {"rising": "#B45309", "falling": "#0F766E", "stable": "#6B7280"}
for reg, sub in labelled.groupby("regime"):
    reg_fig.add_scatter(
        x=sub["repo_rate"], y=sub["ibfpi_system"], mode="markers",
        name=reg.title(), marker=dict(size=10, color=palette[reg], line=dict(color="#FFFFFF", width=1)),
    )
reg_fig.update_layout(
    title="iBFPI vs repo rate by regime",
    xaxis_title="Repo rate (%)", yaxis_title="iBFPI (robust z-units)",
    height=380,
)
st.plotly_chart(reg_fig, use_container_width=True)

rc1, rc2, rc3 = st.columns(3)
with rc1: stat_card("Rising · ρ", f"{rising.rho:+.3f}", f"n = {rising.n}, p = {rising.p_value:.3f}")
with rc2: stat_card("Falling · ρ", f"{falling.rho:+.3f}", f"n = {falling.n}, p = {falling.p_value:.3f}")
with rc3: stat_card("Stable · ρ", f"{stable.rho:+.3f}", f"n = {stable.n}, p = {stable.p_value:.3f}")

st.caption(
    "Regime classification: three-quarter rolling change in the repo rate. "
    "> +25bp = rising, < −25bp = falling, otherwise stable."
)

footnote(
    "iBFPI construction follows the BFPI methodology in the author’s "
    "JP Morgan / Fed-rate research paper. See the Methodology page for the "
    "full formal specification, and Data for provenance conventions."
)
