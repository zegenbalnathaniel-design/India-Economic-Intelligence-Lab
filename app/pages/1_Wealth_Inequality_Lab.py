"""Wealth & Inequality Lab.

Interactive extension of the research paper on income and wealth
inequality in India. Contents:

    A. Income → Wealth framework (clickable stage explanations)
    B. Composition-effect simulator
    C. Asset-allocation comparison
    D. r - g explorer
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
import streamlit as st

from analysis import wealth
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote,
)


setup("Wealth & Inequality Lab")


# ---------- Sidebar -----------------------------------------------------------

with st.sidebar:
    st.markdown("## Wealth Lab")
    st.caption("Sections")
    st.markdown(
        "- A · Framework\n"
        "- B · Composition effect\n"
        "- C · Asset allocation\n"
        "- D · r − g explorer"
    )
    st.markdown("---")
    st.caption(
        "Every result is a simulation under the assumptions listed in the "
        "controls. Historical returns are not forecasts."
    )


# ---------- Header ------------------------------------------------------------

kicker("Wealth & Inequality · India")
st.title("How income, ownership and returns on capital shape wealth")
st.markdown(
    "Interactive extension of my research paper on income and wealth "
    "inequality in India. Each module below reproduces a piece of the "
    "static paper as a live model you can re-run under your own assumptions."
)


# ---------- A. Framework ------------------------------------------------------

st.markdown("---")
kicker("A · Framework")
st.header("From capability to intergenerational mobility")
st.markdown(
    "The paper argues that wealth accumulation is not the outcome of income "
    "alone — it is a chain of transitions. Click any stage below for the "
    "argument as it appears in the paper."
)

stages = [
    ("Capability",
     "Education, health, networks and institutional access set the ceiling on "
     "earnings potential. The paper draws on the capabilities framework to "
     "argue that inequality of *capability* precedes inequality of income."),
    ("Employment",
     "Formal-sector employment produces stable earnings and access to "
     "credit. India's large informal share compresses the wage distribution "
     "at the bottom while limiting savings capacity."),
    ("Income",
     "Income is a **flow**. On its own it does not accumulate. Two households "
     "with identical income can end at very different wealth levels depending "
     "on the next three stages."),
    ("Ownership",
     "The choice to save and to hold assets (rather than consume the flow) is "
     "the first transition where inequality begins to compound. Ownership "
     "rates vary sharply across the income distribution."),
    ("Wealth",
     "Wealth is a **stock**. It compounds through returns on capital. The "
     "composition of assets held is at least as important as the amount saved "
     "— see module B."),
    ("Economic freedom",
     "A wealth cushion buys optionality: the ability to bear risk, invest in "
     "education, absorb income shocks, or start a business."),
    ("Intergenerational mobility",
     "Bequest, education spending and social networks transmit the previous "
     "stages to the next generation. This is where the model becomes "
     "dynamic across households."),
]

for name, blurb in stages:
    with st.expander(name, expanded=(name == "Wealth")):
        st.markdown(blurb)


# ---------- B. Composition effect ---------------------------------------------

st.markdown("---")
kicker("B · Composition effect")
st.header("Composition-effect simulator")
st.markdown(
    "The paper's central quantitative exhibit. A household contributes a "
    "fixed amount each year for a chosen horizon. Final wealth depends on "
    "**what the household holds** — not just how much it saves. Every "
    "assumption below is editable."
)

with st.container():
    c_input, c_alloc = st.columns([1, 1.3], gap="large")
    with c_input:
        annual = st.number_input(
            "Annual contribution (₹)", min_value=0, max_value=10_00_00_000,
            value=1_00_000, step=10_000, format="%d",
            help="₹1 lakh = ₹100,000. Default matches the research paper.")
        years = st.slider("Investment horizon (years)", 5, 50, 30)
        inflation = st.slider(
            "Assumed inflation (annual, decimal)", 0.0, 0.15, 0.05, 0.005,
            format="%.3f",
            help="Used to convert nominal wealth to constant-purchasing-power terms.")

        rebalance = st.toggle("Rebalance to target allocation each year", value=True)

    with c_alloc:
        st.markdown("**Portfolio allocation (weights, need not sum to 1 — normalised)**")
        alloc_inputs = {}
        cols = st.columns(3)
        keys = list(wealth.ASSET_KEYS)
        for idx, k in enumerate(keys):
            with cols[idx % 3]:
                alloc_inputs[k] = st.number_input(
                    wealth.ASSET_LABELS[k],
                    min_value=0.0, max_value=1.0,
                    value=float(wealth.DEFAULT_ALLOCATION[k]),
                    step=0.01, format="%.2f",
                    key=f"alloc_{k}",
                )

        st.markdown("**Assumed nominal annual returns (decimal)**")
        ret_inputs = {}
        cols = st.columns(3)
        for idx, k in enumerate(keys):
            with cols[idx % 3]:
                ret_inputs[k] = st.number_input(
                    wealth.ASSET_LABELS[k],
                    min_value=-0.20, max_value=0.40,
                    value=float(wealth.DEFAULT_NOMINAL_RETURNS[k]),
                    step=0.005, format="%.3f",
                    key=f"ret_{k}",
                )

try:
    result = wealth.composition_effect(
        annual_contribution=annual,
        years=years,
        allocation=alloc_inputs,
        returns=ret_inputs,
        inflation=inflation,
        rebalance=rebalance,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

def _rupee(x: float) -> str:
    if abs(x) >= 1e7:
        return f"₹{x/1e7:,.2f} cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:,.2f} L"
    return f"₹{x:,.0f}"

final_nom = result.nominal_wealth[-1]
final_real = result.real_wealth[-1]
final_contrib = result.total_contributions[-1]
final_gain = result.investment_gains[-1]

k1, k2, k3, k4 = st.columns(4, gap="small")
with k1:
    stat_card("Nominal wealth", _rupee(final_nom), f"at year {years}")
with k2:
    stat_card("Real wealth", _rupee(final_real),
              f"deflated at {inflation*100:.1f}% p.a.")
with k3:
    stat_card("Total contributions", _rupee(final_contrib),
              f"{years} × {_rupee(annual)}")
with k4:
    stat_card("Investment gains", _rupee(final_gain),
              f"weighted return {result.weighted_return*100:.2f}%")

# Path chart
path_fig = go.Figure()
path_fig.add_scatter(x=result.years, y=result.nominal_wealth,
                     mode="lines", name="Nominal wealth", line=dict(width=2.4))
path_fig.add_scatter(x=result.years, y=result.real_wealth,
                     mode="lines", name="Real wealth (deflated)", line=dict(width=2.4, dash="dot"))
path_fig.add_scatter(x=result.years, y=result.total_contributions,
                     mode="lines", name="Cumulative contributions",
                     line=dict(width=1.6, color="#6B7280"))
path_fig.update_layout(
    title="Wealth accumulation path",
    xaxis_title="Year", yaxis_title="Wealth (₹)",
    hovermode="x unified", height=380,
)
st.plotly_chart(path_fig, use_container_width=True)

# Composition chart
comp = result.composition.rename(columns=wealth.ASSET_LABELS)
comp_fig = go.Figure()
for col in comp.columns:
    comp_fig.add_scatter(x=comp.index, y=comp[col], stackgroup="one",
                         name=col, mode="lines", line=dict(width=0.5))
comp_fig.update_layout(
    title="Asset composition of portfolio through time",
    xaxis_title="Year", yaxis_title="Balance (₹, nominal)",
    hovermode="x unified", height=380,
)
st.plotly_chart(comp_fig, use_container_width=True)

with st.expander("What am I looking at?"):
    st.markdown(
        "**Model.** Each year the household contributes the specified amount, "
        "split across assets by the target allocation. Each asset compounds "
        "at its own nominal return. When rebalancing is on, the portfolio is "
        "reset to the target weights at year-end.\n\n"
        "**Real vs nominal.** Nominal wealth uses the raw returns you set. "
        "Real wealth deflates by the assumed inflation rate to show "
        "constant-purchasing-power value — the number that actually matters "
        "for consumption in year *T*.\n\n"
        "**Why it matters.** Two households with identical income and "
        "identical savings rates can end at radically different final "
        "wealth if their asset composition differs. The composition effect "
        "is the paper's core finding."
    )
source_badge(
    "Source · Author’s calculation",
    "Method · Research paper §Composition Effect",
    "Assumptions · User-editable",
)


# ---------- B2. Monte Carlo overlay ------------------------------------------

st.markdown("---")
kicker("B · Monte Carlo overlay")
st.header("How much does volatility change the picture?")
st.markdown(
    "The deterministic path above assumes returns arrive exactly at their "
    "mean every year. In reality returns are volatile. Below, the same "
    "portfolio is simulated across many paths using the per-asset "
    "volatilities from the research paper, with annual rebalancing to "
    "target weights. The band is the 5th-95th percentile of outcomes; the "
    "dark line is the median."
)

mc_c1, mc_c2 = st.columns([1, 1])
with mc_c1:
    n_paths = st.slider("Monte Carlo paths", 200, 5000, 2000, 100)
with mc_c2:
    mc_seed = st.number_input("Seed (for reproducibility)", value=7, step=1)

mc = wealth.monte_carlo(
    annual_contribution=annual,
    years=years,
    allocation=alloc_inputs,
    returns=ret_inputs,
    inflation=inflation,
    n_paths=int(n_paths),
    seed=int(mc_seed),
)

mc_fig = go.Figure()
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p95"], mode="lines", name="95th pct",
    line=dict(width=0, color="#0A4D68"), showlegend=False,
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p05"], mode="lines", name="5-95% band",
    fill="tonexty", fillcolor="rgba(10,77,104,0.12)",
    line=dict(width=0, color="#0A4D68"),
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p75"], mode="lines", name="75th pct",
    line=dict(width=0, color="#0A4D68"), showlegend=False,
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p25"], mode="lines", name="25-75% band",
    fill="tonexty", fillcolor="rgba(10,77,104,0.22)",
    line=dict(width=0, color="#0A4D68"),
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p50"], mode="lines", name="Median",
    line=dict(width=2.4, color="#0A4D68"),
)
mc_fig.add_scatter(
    x=result.years, y=result.nominal_wealth, mode="lines",
    name="Deterministic path (mean returns)",
    line=dict(width=1.6, dash="dot", color="#B45309"),
)
mc_fig.update_layout(
    title=f"Monte Carlo wealth paths ({mc.n_paths:,} simulations)",
    xaxis_title="Year", yaxis_title="Wealth (₹, nominal)",
    hovermode="x unified", height=380,
)
st.plotly_chart(mc_fig, use_container_width=True)

p5, p25, p50, p75, p95 = np.percentile(mc.final_nominal, [5, 25, 50, 75, 95])
q1, q2, q3, q4, q5 = st.columns(5)
with q1: stat_card("5th pct", _rupee(p5), "worst-case tail")
with q2: stat_card("25th pct", _rupee(p25), "")
with q3: stat_card("Median", _rupee(p50), "central outcome")
with q4: stat_card("75th pct", _rupee(p75), "")
with q5: stat_card("95th pct", _rupee(p95), "best-case tail")

callout(
    "The Monte Carlo assumes returns across assets are <b>independent</b>. "
    "In reality they are not — property, gold and equities show non-trivial "
    "correlation in Indian data. A joint-covariance model is a natural next "
    "step; the width of the band here is a lower bound on real-world "
    "dispersion, not an upper bound.",
    kind="warn",
)


# ---------- C. Asset allocation comparison ------------------------------------

st.markdown("---")
kicker("C · Asset allocation")
st.header("What if the household held only one asset?")
st.markdown(
    "The same annual contribution and horizon, but concentrated in a single "
    "asset class. This isolates the impact of asset choice on final wealth "
    "before diversification."
)

rows = []
for k in wealth.ASSET_KEYS:
    r = ret_inputs[k]
    proj = wealth.single_asset_projection(
        annual_contribution=annual, years=years, nominal_return=r, inflation=inflation,
    )
    rows.append(dict(
        Asset=wealth.ASSET_LABELS[k],
        **{"Nominal return": r, "Real return": wealth.real_return(r, inflation)},
        **{"Final nominal": proj["final_nominal"], "Final real": proj["final_real"]},
        Volatility=wealth.DEFAULT_VOLATILITY[k],
        Liquidity=wealth.LIQUIDITY[k],
    ))
compare = pd.DataFrame(rows)

fmt_pct = lambda v: f"{v*100:.2f}%"
display = compare.copy()
display["Nominal return"] = display["Nominal return"].map(fmt_pct)
display["Real return"] = display["Real return"].map(fmt_pct)
display["Volatility"] = display["Volatility"].map(fmt_pct)
display["Final nominal"] = display["Final nominal"].map(_rupee)
display["Final real"] = display["Final real"].map(_rupee)
st.dataframe(display, hide_index=True, use_container_width=True)

bar = go.Figure()
bar.add_bar(x=compare["Asset"], y=compare["Final real"], name="Final real wealth", marker_color="#0A4D68")
bar.update_layout(
    title="Final wealth if concentrated in one asset (real terms)",
    yaxis_title="₹ (real)", xaxis_title="", height=360, showlegend=False,
)
st.plotly_chart(bar, use_container_width=True)

callout(
    "Do not read this as a ranking of assets. Under the assumptions you have "
    "selected the simulated outcomes are shown above. Volatility, tax "
    "treatment, transaction costs and liquidity are omitted from the wealth "
    "path calculation — they matter for real households and are shown "
    "alongside for context.",
    kind="warn",
)


# ---------- D. r - g explorer -------------------------------------------------

st.markdown("---")
kicker("D · r − g")
st.header("r − g explorer")
st.markdown(
    "A common shorthand in the inequality literature: when the return on "
    "capital *r* exceeds the growth rate of the economy *g*, the "
    "**share** of wealth accruing to owners of capital tends to rise "
    "relative to labour income. It does not, by itself, imply that "
    "inequality of *individuals* must rise. Distributional outcomes also "
    "depend on savings behaviour, bequest patterns and the composition of "
    "wealth across the distribution."
)

cA, cB, cC = st.columns(3)
with cA:
    r_nom = st.slider("Nominal return on capital r (%)", 0.0, 20.0, 8.0, 0.25) / 100
with cB:
    infl = st.slider("Inflation π (%)", 0.0, 15.0, 5.0, 0.25) / 100
with cC:
    g_real = st.slider("Real income / GDP growth g (%)", -5.0, 15.0, 6.0, 0.25) / 100

rg = wealth.rminusg_frame(r_nominal=r_nom, inflation=infl, g_real=g_real)
c1, c2, c3, c4 = st.columns(4)
with c1: stat_card("r nominal", f"{rg['r_nominal']*100:.2f}%")
with c2: stat_card("Inflation π", f"{rg['inflation']*100:.2f}%")
with c3: stat_card("r real", f"{rg['r_real']*100:.2f}%")
with c4:
    diff = rg['r_minus_g']
    stat_card("r − g (real)", f"{diff*100:+.2f}%",
              "capital share tends to rise" if diff > 0 else "capital share tends to fall")

callout(
    "Consistency check: r and g must be measured on the same basis. Here we "
    "convert r to a real rate before comparing to real growth g. Comparing "
    "nominal r with real g is a common error and inflates the apparent gap.",
    kind="warn",
)

footnote(
    "Framework and composition-effect exhibit adapted from the author’s "
    "research paper on income and wealth inequality in India. r − g "
    "framing draws on Piketty and subsequent literature — the module "
    "reports the identity, not a causal claim."
)
