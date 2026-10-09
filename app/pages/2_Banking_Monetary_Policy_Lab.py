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
    GOLD, CRIMSON, MUTED, PARCHMENT, COBALT,
)
from app.components import hairline_display
from app.components.glossary import indicator_note


setup("Banking & Monetary Policy Lab", accent=COBALT)


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

indicator_note(
    "iBFPI",
    "**What it is, in plain terms.** iBFPI is a single number per bank per "
    "quarter that summarises, in one figure, whether that bank's financial "
    "performance is running above or below its *own historical norm* on "
    "five dimensions at once — profitability (PPNR/assets), capital "
    "strength (CET1 ratio), credit quality (net charge-off rate), "
    "liquidity (LCR) and balance-sheet interest-rate risk (unrealised "
    "losses relative to CET1). Rather than reading five separate charts "
    "and forming an impression, iBFPI collapses them into one comparable "
    "scale.\n\n"
    "**How to read a high vs. a low value.** A positive iBFPI means the "
    "bank's blended performance that quarter sits *above* its own "
    "historical median across these five indicators; a negative value "
    "means it sits below. Zero is that bank's own typical quarter — it is "
    "a relative, not absolute, scale (see the construction section below "
    "for why).\n\n"
    "**What moves it.** Any quarter-to-quarter change in profitability, "
    "capital, asset quality, liquidity or interest-rate exposure that is "
    "unusual *relative to that bank's own history* — a one-off credit loss, "
    "a capital raise, a liquidity buffer build-up, or (per the regime-"
    "split analysis below) a shift in the interest-rate environment.\n\n"
    "**Caveat.** Because each bank is standardised against its own "
    "history, iBFPI cannot tell you which bank is healthier than another "
    "in absolute terms — a bank with a strong but *stable* balance sheet "
    "will show an iBFPI near zero most quarters, the same as a chronically "
    "weak bank that is simply having an average quarter for itself. It "
    "measures change-from-self, not rank-across-banks.",
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

indicator_note(
    "a robust z-score (vs. a plain average)",
    "**Why robust statistics instead of a plain mean and standard "
    "deviation.** An ordinary z-score, `(x − mean) / std`, is built from "
    "two statistics that are themselves highly sensitive to outliers: one "
    "extreme quarter (a one-off loan write-off, a reporting anomaly) can "
    "drag the mean and inflate the standard deviation enough to distort "
    "every *other* quarter's z-score, not just the outlier's own. Banking "
    "data over a 2018-2024 window that spans COVID-era credit losses and "
    "sharp rate moves is exactly the kind of series where a handful of "
    "unusual quarters is likely.\n\n"
    "**What the robust version does differently.** The **median** replaces "
    "the mean as the centre point — it does not move much even if one or "
    "two quarters are extreme. The **median absolute deviation (MAD)** "
    "replaces the standard deviation as the spread measure, for the same "
    "reason. The constant 1.4826 rescales MAD so that, *if* the underlying "
    "data were normally distributed, the robust z-score would numerically "
    "match an ordinary z-score — this keeps the robust version "
    "interpretable on the same 'roughly how many typical deviations away' "
    "scale, while remaining resistant to outliers.\n\n"
    "**How to read it.** A robust z-score of, say, +2 means the value is "
    "unusually far above that bank's typical (median) quarter, in a way "
    "that a few anomalous quarters elsewhere in the series cannot "
    "manufacture or hide.\n\n"
    "**Caveat.** Robustness to outliers is not free: if MAD happens to be "
    "very small (a bank with an unusually stable history on one "
    "indicator), even a modest absolute change can produce a large robust "
    "z-score. The code handles the degenerate case (MAD = 0) by returning "
    "zero rather than dividing by zero, but a near-zero MAD can still make "
    "the index noisier than it looks.",
)

with st.expander("Direction coefficients"):
    dcoef = pd.DataFrame([
        {"Indicator": banking.INDICATOR_LABELS[k], "Direction D": banking.INDICATOR_DIRECTION[k]}
        for k in banking.INDICATOR_DIRECTION
    ])
    st.dataframe(dcoef, hide_index=True, use_container_width=True)

indicator_note(
    "the direction coefficients",
    "**Why some indicators get multiplied by −1.** iBFPI is built so that "
    "a higher score always means 'better for the bank', consistently "
    "across all five indicators. That is automatically true for "
    "profitability (PPNR/assets), capital strength (CET1 ratio) and "
    "liquidity (LCR) — more of each is unambiguously good, so their "
    "direction coefficient `D` is +1 and the raw robust z-score is used "
    "as-is.\n\n"
    "**Why net charge-offs and unrealised losses flip sign.** For the "
    "net charge-off rate and for unrealised securities losses relative to "
    "CET1, the relationship is reversed: a *higher* value means *worse* "
    "credit quality or *worse* balance-sheet stress. Multiplying their "
    "robust z-score by `D = −1` flips the sign, so that for these two "
    "indicators specifically, a bank doing *better* than its own history "
    "(lower charge-offs, smaller unrealised losses) also produces a "
    "*positive* contribution to iBFPI — matching the other three.\n\n"
    "**What this buys you.** Without the flip, averaging the five raw "
    "z-scores together would be meaningless: an improving bank would push "
    "some indicators up and others down for the same underlying reason "
    "(getting healthier), and they would partially cancel out instead of "
    "reinforcing each other in the composite.\n\n"
    "**Caveat.** Flipping the sign is a modelling choice about what "
    "'good' means for each indicator — it is standard practice for this "
    "kind of composite index, not a measured fact, and it assumes each "
    "indicator's 'badness' direction never reverses (which is a reasonable "
    "assumption for these five, but would need re-checking for any "
    "indicator added later).",
)


# ---------- Aggregate iBFPI plot ---------------------------------------------

st.subheader("Aggregate iBFPI over time")
agg_fig = go.Figure()
agg_fig.add_scatter(
    x=agg["period"], y=agg["ibfpi_system"], mode="lines+markers",
    line=dict(width=2.4, color=GOLD), name="iBFPI (system)",
)
agg_fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dash"))
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
pb_fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dash"))
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

latest_repo_rate = float(repo.sort_values("period")["repo_rate"].iloc[-1])
fig_col, text_col = st.columns([2, 3])
with fig_col:
    hairline_display.render("slow", height=330, repoRate=f"{latest_repo_rate:.2f}")
with text_col:
    st.markdown(
        "Tighter monetary policy is meant to slow credit growth and economic "
        "activity — the figure alongside is a metaphor for that transmission "
        "mechanism, not a literal visualisation of any number. **It is not "
        "driven by a historical rate series**, only by the latest repo rate "
        "shown. The real relationship, over the actual 2018-2024 window, is "
        "the chart below."
    )

indicator_note(
    "the RBI repo rate and its transmission to banks",
    "**What it is.** The repo rate is the interest rate at which the "
    "Reserve Bank of India lends short-term funds to commercial banks "
    "against government securities as collateral. It is the RBI's main "
    "policy lever: raising it is meant to tighten monetary conditions "
    "(cool demand, fight inflation); cutting it is meant to loosen them "
    "(support growth).\n\n"
    "**How it is meant to transmit to bank performance.** A repo-rate "
    "change is meant to pass through to banks' own lending and deposit "
    "rates (loan EMIs, deposit yields), to credit demand and quality over "
    "time, and — specifically relevant to one of the five iBFPI "
    "indicators here — to the **mark-to-market value of banks' existing "
    "fixed-rate bond holdings**: when rates rise, previously-issued bonds "
    "paying a lower fixed coupon become less valuable, which shows up as "
    "unrealised losses relative to CET1. This 'unrealised-loss channel' is "
    "the single most mechanical, fastest-acting link between the repo "
    "rate and iBFPI in this panel.\n\n"
    "**What moves it.** RBI's own policy decisions, set in response to "
    "inflation, growth and external conditions — the repo rate itself is "
    "not something banks or this dashboard can influence.\n\n"
    "**Caveat.** Transmission in practice is neither instant nor "
    "complete — banks reprice loans and deposits with lags that vary by "
    "product and by bank, and the degree of pass-through has historically "
    "been a live policy debate in India. This page measures a "
    "*correlation* between the policy rate and the index level, not an "
    "estimate of transmission speed or strength.",
)

merged = agg.merge(repo, on="period", how="inner").dropna()

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_scatter(x=merged["period"], y=merged["ibfpi_system"], name="iBFPI",
                line=dict(color=GOLD, width=2.4), secondary_y=False)
fig.add_scatter(x=merged["period"], y=merged["repo_rate"], name="RBI repo rate (%)",
                line=dict(color=CRIMSON, width=2.0, dash="dot"), secondary_y=True)
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
palette = {"rising": CRIMSON, "falling": GOLD, "stable": MUTED}
for reg, sub in labelled.groupby("regime"):
    reg_fig.add_scatter(
        x=sub["repo_rate"], y=sub["ibfpi_system"], mode="markers",
        name=reg.title(), marker=dict(size=10, color=palette[reg], line=dict(color=PARCHMENT, width=1)),
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

indicator_note(
    "the regime split and the Spearman correlation",
    "**What the regime split is doing.** The relationship between the "
    "repo rate and iBFPI might not be the same in every interest-rate "
    "environment — a cut might coincide with improving iBFPI for a "
    "different reason than a hike coincides with declining iBFPI. "
    "Splitting the sample into 'rising', 'falling' and 'stable' quarters "
    "(by the three-quarter rolling change in the repo rate) and "
    "re-running the correlation *within each regime* checks whether the "
    "overall association is uniform or is instead concentrated in, say, "
    "the rising-rate quarters only.\n\n"
    "**What Spearman's ρ is.** Spearman correlation measures whether two "
    "series move in the same *rank order* — when one is high, is the "
    "other also high, regardless of whether the relationship between them "
    "is a straight line? It runs from −1 (perfectly opposite ranking) to "
    "+1 (perfectly matching ranking), and is reported here with a "
    "p-value, which indicates how likely a correlation this strong would "
    "arise by chance alone if there were truly no association — a "
    "pragmatic, not definitive, way to flag whether a given regime's "
    "sample is too small or too noisy to read much into.\n\n"
    "**What this is NOT.** This whole panel is explicitly illustrative, "
    "per the warning at the top of this page — the underlying bank panel "
    "is synthetic, so the specific ρ values are a demonstration of the "
    "method, not a finding about real Indian banks. Even with real data, "
    "a correlation — split by regime or not — never by itself establishes "
    "that the repo rate *causes* the change in iBFPI, or vice versa; both "
    "could be responding to a third factor (e.g. the broader macro cycle), "
    "and a small number of quarters per regime makes any single ρ fragile "
    "to one or two unusual observations.",
)

footnote(
    "iBFPI construction follows the BFPI methodology in the author’s "
    "JP Morgan / Fed-rate research paper. See the Methodology page for the "
    "full formal specification, and Data for provenance conventions."
)
