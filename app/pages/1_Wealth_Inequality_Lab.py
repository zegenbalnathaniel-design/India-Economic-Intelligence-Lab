"""Wealth & Inequality Lab.

Interactive extension of the research paper on income and wealth
inequality in India. Contents:

    W. Who gets what -- income & wealth shares by group (WIL, 2022-23)
    A. Income → Wealth framework (clickable stage explanations)
    B. Composition-effect simulator
    C. Asset-allocation comparison
    D. r - g explorer
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import inequality, wealth
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote, GOLD, CRIMSON, MUTED, VERMILLION,
)
from app.components.glossary import indicator_note
from app.components import hairline_display
from data_sources import loaders


setup("Wealth & Inequality Lab", accent=VERMILLION)


# ---------- Sidebar -----------------------------------------------------------

with st.sidebar:
    st.markdown("## Wealth Lab")
    st.caption("Sections")
    st.markdown(
        "- Who gets what (WIL data)\n"
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

wil_dist = loaders.load_wil_distribution()
wil_facts = loaders.load_wil_facts()
wil_table = inequality.group_table(wil_dist, wil_facts)
wil_wealth = inequality.wealth_change(loaders.load_wil_wealth_shares())

fig_col, text_col = st.columns([5, 4], vertical_alignment="center")
with fig_col:
    hairline_display.render(
        "riffle", hero=True, accent=VERMILLION,
        bands=json.dumps(inequality.riffle_captions(wil_table)),
    )
with text_col:
    st.markdown(
        "### Who gets what?\n"
        "Eight cards, one per population group, from the poorest 10% "
        "(bottom card) to the richest 0.1% (top card). **Hover a card**, or "
        "tab in and use the arrow keys, to read that group's share of "
        "India's income and wealth in 2022-23.\n\n"
        "Figures are World Inequality Lab estimates. A **\\*** marks a "
        "value calculated here from the published ones (for example, "
        "Upper middle = Top 10% − Top 1%). The two lowest cards say "
        "**DATA REQUIRED** because the source gives no figure for them, "
        "and none is invented."
    )
    source_badge("World Inequality Lab · 2022-23", "PARTIAL — not yet checked against the paper's tables")

indicator_note(
    "percentile bands",
    "**What they are.** Economists split a population into bands by "
    "where each person sits in the income or wealth distribution — by "
    "*rank*, not by income *level*. 'Top 1%' means the richest 1% of "
    "adults, whatever income that takes in a given year, not a fixed "
    "rupee threshold.\n\n"
    "**Nested vs side-by-side groups.** Bottom 50% + Middle 40% + Top 10% "
    "cover everyone exactly once, so their shares add to 100%. Top 1% and "
    "Top 0.1% sit *inside* the Top 10%; Upper middle (P90–P99) is the Top "
    "10% with the Top 1% taken out.\n\n"
    "**Why they matter.** A single summary number (like a Gini "
    "coefficient) can hide *where* change is happening. Bands let you ask "
    "'who, specifically' instead of just 'how unequal, overall.'",
)


# ---------- W. Who gets what ---------------------------------------------------

st.markdown("---")
kicker("W · Distribution")
st.header("India's income and wealth, by group")
st.markdown(
    "The average Indian adult earned **₹2.35 lakh** in 2022-23. The bottom "
    "half earned about **0.3×** that average; the top 1%, about **22.6×**. "
    "Wealth is more concentrated than income because land, housing, "
    "businesses and financial assets are concentrated and compound over time."
)


def _cell(v, status, fmt):
    if pd.isna(v):
        return "DATA REQUIRED"
    return fmt(v) + (" *" if status == inequality.DERIVED else "")


view = pd.DataFrame({
    "Group": wil_table["group"],
    "Percentiles": wil_table["percentile_range"],
    "Share of adults": wil_table["population_share_pct"].map(lambda v: f"{v:g}%"),
    "Average income / yr": [_cell(v, s, inequality.fmt_inr) for v, s in
                            zip(wil_table["avg_income_inr"], wil_table["avg_income_status"])],
    "× national average": [("—" if pd.isna(v) else f"{v:.2f}×") for v in wil_table["multiple_of_average"]],
    "Share of income": [_cell(v, s, lambda x: f"{x:.1f}%") for v, s in
                        zip(wil_table["income_share_pct"], wil_table["income_share_status"])],
    "Share of wealth": [_cell(v, s, lambda x: f"{x:.1f}%") for v, s in
                        zip(wil_table["wealth_share_pct"], wil_table["wealth_share_status"])],
})
st.dataframe(view, hide_index=True, use_container_width=True)
derived_notes = []
for _, r in wil_table.iterrows():
    for what, col in (("income share", "income_share"), ("wealth share", "wealth_share"),
                      ("average income", "avg_income")):
        if r[f"{col}_status"] == inequality.DERIVED:
            derived_notes.append(f"- **{r['group']} {what}** = {r[f'{col}_formula']}")
with st.expander("\\* How the starred values are calculated"):
    st.markdown("\n".join(derived_notes))

# Side-by-side groups only, so the bars are comparable (they partition 100%).
part = wil_table[wil_table["group"].isin(["Bottom 50%", "Middle 40%", "Top 10%"])]
fig_share = go.Figure()
for col, name, colour in (("population_share_pct", "Share of adults", MUTED),
                          ("income_share_pct", "Share of income", GOLD),
                          ("wealth_share_pct", "Share of wealth", VERMILLION)):
    fig_share.add_trace(go.Bar(
        x=part["group"], y=part[col], name=name, marker_color=colour,
        text=[f"{v:.1f}%" for v in part[col]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x} · " + name + ": %{y:.1f}%<extra></extra>",
    ))
fig_share.update_layout(
    barmode="group", height=430, yaxis=dict(title="% of total", range=[0, 75]),
    title="Each group's share of adults, income and wealth, 2022-23",
    legend=dict(orientation="h", y=-0.15),
)
st.plotly_chart(fig_share, use_container_width=True, key="wil_shares")
st.caption(
    "Read across each group: if income were shared equally, the gold and red bars would "
    "match the grey one. The Top 10% are 10% of adults but hold 57.7% of income and 64.6% "
    "of wealth; the Bottom 50% are half of adults but hold 15.0% and 6.4%. "
    "Middle 40% shares are the remainder (100 − the other two)."
)

c1, c2 = st.columns(2)
with c1:
    mult = wil_table.dropna(subset=["multiple_of_average"])
    fig_mult = go.Figure(go.Bar(
        y=mult["group"], x=mult["multiple_of_average"], orientation="h",
        marker_color=[VERMILLION if s == inequality.STATED else MUTED for s in mult["avg_income_status"]],
        text=[f"{v:.1f}×" for v in mult["multiple_of_average"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.2f}× the national average<extra></extra>",
    ))
    fig_mult.update_layout(
        height=380,
        xaxis=dict(title="× national average income (log scale)", type="log", range=[-0.8, 2.45],
                   tickvals=[0.3, 1, 3, 10, 30, 100], ticktext=["0.3×", "1×", "3×", "10×", "30×", "100×"]),
        yaxis=dict(autorange="reversed"), title="Average income vs the national average", showlegend=False,
    )
    st.plotly_chart(fig_mult, use_container_width=True, key="wil_mult")
    st.caption("Grey bar = calculated (Upper middle). Log scale, so the 0.3× and 95.7× bars both fit; 1× is the national average.")
with c2:
    w = wil_wealth.dropna(subset=["share_1961_pct", "share_2022_23_pct"])
    fig_w = go.Figure()
    for _, r in w.iterrows():
        fig_w.add_trace(go.Scatter(
            x=[r["share_1961_pct"], r["share_2022_23_pct"]], y=[r["group"], r["group"]],
            mode="lines", line=dict(color=MUTED, width=3), showlegend=False, hoverinfo="skip",
        ))
    fig_w.add_trace(go.Scatter(x=w["share_1961_pct"], y=w["group"], mode="markers", name="1961",
                               marker=dict(color=MUTED, size=13),
                               hovertemplate="%{y} · 1961: %{x:.1f}%<extra></extra>"))
    fig_w.add_trace(go.Scatter(x=w["share_2022_23_pct"], y=w["group"], mode="markers+text", name="2022-23",
                               marker=dict(color=VERMILLION, size=15),
                               text=[f"{v:.1f}%" for v in w["share_2022_23_pct"]], textposition="top center",
                               hovertemplate="%{y} · 2022-23: %{x:.1f}%<extra></extra>"))
    fig_w.update_layout(height=380, xaxis=dict(title="% of national wealth", range=[0, 75]),
                        yaxis=dict(autorange="reversed"), title="Wealth share, 1961 → 2022-23",
                        legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_w, use_container_width=True, key="wil_wealth")
    st.caption(
        "Top 0.1%: 3.2% → 29.0%, a ninefold rise. Middle 40% is the remainder in each year "
        "(43.7% → 29.0%). The Top 1% is not plotted: its 1961 share is given only as "
        "'about 13–15%'."
    )

kicker("Long run")
facts = wil_facts.set_index(["metric", "period"])["value"]
f1, f2, f3, f4 = st.columns(4)
with f1:
    stat_card("Real income growth", f"{facts[('Real average income growth', '1990-2022')]:.1f}% / yr",
              f"1990-2022 · vs {facts[('Real average income growth', 'before 1990')]:.1f}% before 1990")
with f2:
    stat_card("Wealth ÷ income", f"{facts[('Wealth-to-income ratio', '2022')]:.2f}×",
              f"2022 · up from {facts[('Wealth-to-income ratio', '1995')]:.2f}× in 1995")
with f3:
    stat_card("USD billionaires", f"{facts[('USD billionaires', '2022')]:.0f}",
              f"2022 · {facts[('USD billionaires', '1991')]:.0f} in 1991")
with f4:
    stat_card("Billionaire wealth", f"{facts[('Billionaire wealth', '2022')]:.0f}% of NNI",
              "2022 · under 1% in 1991")
st.caption(
    "Top 1% income share: under 21% in the late 1930s, about 6% in the early 1980s, "
    "22.6% in 2022-23 — the highest in the WIL series since 1922."
)

indicator_note(
    "these estimates",
    "**Where they come from.** The World Inequality Lab combines national "
    "accounts, income-tax tabulations, household surveys and rich lists "
    "into one consistent long-run series. Read them as a consistent "
    "series, not census-precise measurements.\n\n"
    "**Likely understated at the top.** Rich households under-report "
    "assets and are under-sampled in surveys; the authors caution that "
    "India's data quality has deteriorated and that their estimates may "
    "understate true inequality.\n\n"
    "**Weakest for the bottom and middle since 2011-12.** India has no "
    "comparable, publicly released consumption-survey microdata after "
    "2011-12, which is why this page has no figure for the Bottom 10% or "
    "the Lower middle (P10–P50).\n\n"
    "**What is checked here.** The three side-by-side groups add to 100% "
    "for both income and wealth, and each group's average income implies "
    "its stated share to within 0.2 percentage points — except the Middle "
    "40%: its average (₹1,65,273 in coverage reproducing the paper's "
    "table) implies about 28.1% against the 27.3% remainder. That 27.3% is "
    "the paper's own figure, so the 0.8 pp gap sits in the source's "
    "averages, not in rounding here.\n\n"
    "**Status: PARTIAL.** Values are transcribed from a summary of Bharti, "
    "Chancel, Piketty & Somanchi (2024), *Income and Wealth Inequality in "
    "India, 1922-2023: The Rise of the Billionaire Raj*, WIL Working Paper "
    "2024/09, and have not yet been checked against the paper's tables.",
    kind="method",
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

indicator_note(
    "the composition effect",
    "**What it measures.** Two households can save the exact same amount, "
    "every year, for the exact same number of years, and still end up with "
    "very different final wealth — purely because of *what* they bought with "
    "those savings. The composition effect isolates that gap: it holds the "
    "savings rate and horizon fixed and varies only the asset mix (property, "
    "gold, equities, bonds, deposits, cash), so whatever difference in final "
    "wealth remains is attributable to composition, not effort or thrift.\n\n"
    "**How to read it.** A portfolio tilted toward a higher-expected-return "
    "asset compounds to a larger number over a long horizon — not because "
    "the household did anything differently in terms of saving, but because "
    "money sitting in a higher-return asset for decades grows geometrically "
    "faster. The gap widens with the horizon: over 5 years, two reasonable "
    "allocations barely diverge; over 30-40 years, the same return gap "
    "compounds into a materially different outcome.\n\n"
    "**What moves it.** The weighted average return of the portfolio — which "
    "is a function of the allocation *and* the return assumptions you set "
    "above — and, when rebalancing is off, the way winning assets grow to "
    "dominate the portfolio's weight over time (drift), which itself changes "
    "the effective weighted return as the simulation runs.\n\n"
    "**Caveat.** This is an accounting identity about compounding, not a "
    "claim that any one allocation is the 'right' one for a given household. "
    "It says nothing about the risk, liquidity or tax consequences of holding "
    "more of a higher-return asset — those are shown separately in module C, "
    "specifically because folding them into one number would hide the "
    "trade-off rather than illuminate it.",
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

indicator_note(
    "real return vs. nominal return",
    "**What it measures.** A *nominal* return is the percentage growth in "
    "the rupee number on a statement — it says nothing about what those "
    "rupees can buy. A *real* return subtracts out inflation, so it measures "
    "growth in **purchasing power**: `real ≈ nominal − inflation` (the exact "
    "relationship is `(1+real) = (1+nominal)/(1+inflation)`, which this page "
    "uses rather than the approximation).\n\n"
    "**How to read it.** 'Nominal wealth' above is the number that would "
    "appear on an account statement at year *T*. 'Real wealth' deflates that "
    "same path by the inflation assumption you set, so it answers a "
    "different question: how much could this pile of money actually buy, in "
    "today's terms, at year *T*? The two lines on the chart below diverge "
    "more the higher the inflation assumption and the longer the horizon — "
    "they are the same underlying wealth path, just two different rulers "
    "held up to it.\n\n"
    "**What moves it.** The gap between nominal and real wealth is driven "
    "entirely by the inflation slider — raise it, and the real line falls "
    "further below the nominal line even though nothing about the "
    "portfolio's actual returns changed.\n\n"
    "**Caveat.** A single inflation assumption applied uniformly is a "
    "simplification: in reality, different assets have different exposure "
    "to inflation (property and gold are often considered partial inflation "
    "hedges; a fixed-rate bank deposit is not), and a household's own cost "
    "of living may run above or below the general inflation rate used here.",
)

# Path chart
path_fig = go.Figure()
path_fig.add_scatter(x=result.years, y=result.nominal_wealth,
                     mode="lines", name="Nominal wealth", line=dict(width=2.4))
path_fig.add_scatter(x=result.years, y=result.real_wealth,
                     mode="lines", name="Real wealth (deflated)", line=dict(width=2.4, dash="dot"))
path_fig.add_scatter(x=result.years, y=result.total_contributions,
                     mode="lines", name="Cumulative contributions",
                     line=dict(width=1.6, color=MUTED))
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

indicator_note(
    "the Monte Carlo simulation",
    "**What it is doing.** For each of the simulated paths, every asset's "
    "annual return is redrawn at random from a distribution centred on the "
    "mean return you set, with a spread equal to that asset's assumed "
    "volatility — then the same contribution-and-compounding arithmetic from "
    "module B is run on that one random path. Doing this thousands of times "
    "produces a *distribution* of possible final-wealth outcomes rather "
    "than a single number, and the chart shows the 5th, 25th, 50th "
    "(median), 75th and 95th percentiles of that distribution at each year.\n\n"
    "**How to read it.** The median line is the typical simulated outcome "
    "under these assumptions — it will usually sit close to, but not "
    "exactly on, the deterministic path above, because compounding "
    "volatile returns is not the same arithmetic as compounding a fixed "
    "average return. The bands show *how wide* the range of plausible "
    "outcomes is, which is itself useful information: a wide band at year "
    "30 means the long-run outcome is genuinely uncertain, even if the "
    "assumptions you set are reasonable on average.\n\n"
    "**What this is *not*.** This is not a forecast of what will actually "
    "happen to Indian asset returns over the next few decades. It is a "
    "mechanical exercise in propagating the volatility assumptions you "
    "chose through the same compounding model — garbage assumptions in, "
    "garbage (but precisely quantified) distribution out. Treat the spread "
    "as illustrating 'returns are uncertain, and here is one way to "
    "quantify that uncertainty under stated assumptions', not as a "
    "probability of any specific rupee amount occurring in reality.\n\n"
    "**Caveat.** Each asset's returns are drawn independently year to year "
    "and, as the warning below notes, independently across assets within a "
    "year too — real asset returns show serial correlation (a bad year can "
    "be followed by a partial rebound) and cross-asset correlation that "
    "this simplified version does not capture.",
)

mc_c1, mc_c2 = st.columns([1, 1])
with mc_c1:
    n_paths = st.slider("Monte Carlo paths", 200, 5000, 2000, 100)
with mc_c2:
    mc_seed = st.number_input("Seed (for reproducibility)", value=7, step=1)

st.markdown("**Assumed annualised volatility (std. dev., decimal)**")
st.caption(
    "User-set assumption, not measured risk — these default to the same "
    "illustrative reference points used elsewhere on this page "
    "(`wealth.DEFAULT_VOLATILITY`), only used here to communicate that "
    "assets differ in risk, not for a VaR model. Edit to see how the "
    "5th-95th percentile band below widens or narrows."
)
vol_inputs = {}
vcols = st.columns(3)
for idx, k in enumerate(keys):
    with vcols[idx % 3]:
        vol_inputs[k] = st.number_input(
            wealth.ASSET_LABELS[k],
            min_value=0.0, max_value=0.60,
            value=float(wealth.DEFAULT_VOLATILITY[k]),
            step=0.005, format="%.3f",
            key=f"vol_{k}",
        )

mc = wealth.monte_carlo(
    annual_contribution=annual,
    years=years,
    allocation=alloc_inputs,
    returns=ret_inputs,
    volatilities=vol_inputs,
    inflation=inflation,
    n_paths=int(n_paths),
    seed=int(mc_seed),
)

mc_fig = go.Figure()
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p95"], mode="lines", name="95th pct",
    line=dict(width=0, color=GOLD), showlegend=False,
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p05"], mode="lines", name="5-95% band",
    fill="tonexty", fillcolor="rgba(10,77,104,0.12)",
    line=dict(width=0, color=GOLD),
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p75"], mode="lines", name="75th pct",
    line=dict(width=0, color=GOLD), showlegend=False,
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p25"], mode="lines", name="25-75% band",
    fill="tonexty", fillcolor="rgba(10,77,104,0.22)",
    line=dict(width=0, color=GOLD),
)
mc_fig.add_scatter(
    x=mc.years, y=mc.percentiles["p50"], mode="lines", name="Median",
    line=dict(width=2.4, color=GOLD),
)
mc_fig.add_scatter(
    x=result.years, y=result.nominal_wealth, mode="lines",
    name="Deterministic path (mean returns)",
    line=dict(width=1.6, dash="dot", color=CRIMSON),
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

indicator_note(
    "the asset-allocation comparison",
    "**What it measures.** Each row re-runs the identical savings plan "
    "(same annual contribution, same horizon) as if the household held "
    "*only* that one asset for the entire period — a deliberately extreme "
    "case that makes the return-driven gap between assets as visible as "
    "possible, before diversification blends it away.\n\n"
    "**How to read it.** 'Final real wealth' is the fair comparison across "
    "rows, because it controls for the inflation assumption that applies "
    "equally to all of them; 'nominal return' and 'real return' show the "
    "assumed annual growth rate each asset compounds at, which is the "
    "entire reason the final-wealth column differs row to row. The "
    "volatility and liquidity columns are shown next to, not folded into, "
    "the wealth figures — a higher final number from an all-equities "
    "scenario did not 'cost' anything in this table, because the table "
    "does not price risk or liquidity, only return.\n\n"
    "**What moves it.** Purely the return assumption you set for each asset "
    "in module B above (volatility does not enter the deterministic "
    "wealth path at all — see the Monte Carlo module for that).\n\n"
    "**Caveat — read this before treating any row as advice.** A single-"
    "asset household is not a realistic recommendation; it is an analytic "
    "device. A real household concentrated entirely in equities would face "
    "a very different, much wider range of actual outcomes than the single "
    "number shown here (compare to the Monte Carlo band above), and would "
    "also bear transaction costs, taxes and liquidity constraints this "
    "table excludes by design, exactly as the warning below states.",
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
        Volatility=vol_inputs[k],
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
bar.add_bar(x=compare["Asset"], y=compare["Final real"], name="Final real wealth", marker_color=GOLD)
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

indicator_note(
    "r − g",
    "**What it measures.** `r` is the real rate of return earned on capital "
    "(property, equities, bonds — anything owned rather than earned as a "
    "wage); `g` is the real growth rate of the overall economy (and, over "
    "the long run, of average labour income). `r − g` compares how fast "
    "money invested grows against how fast the economy — and with it, "
    "typical wages — grows.\n\n"
    "**How to read it.** When `r > g`, wealth that is simply held and "
    "reinvested grows faster than the economy as a whole, so **the share "
    "of total income flowing to owners of capital tends to rise relative "
    "to the share flowing to labour** over time, all else equal. When "
    "`r < g`, the reverse holds — capital's share tends to shrink relative "
    "to labour's. This is the core mechanism popularised by Thomas "
    "Piketty's work on long-run inequality: it is an argument about the "
    "*functional* distribution of income (capital vs. labour), not "
    "directly a statement about how unequal individual people's incomes "
    "or wealth are.\n\n"
    "**What moves it.** `r` responds to asset returns and inflation (see "
    "the nominal-vs-real note above); `g` responds to productivity growth, "
    "labour-force growth and capital investment in the real economy — the "
    "two are driven by largely different forces, which is exactly why "
    "comparing them is informative rather than circular.\n\n"
    "**Caveat.** `r > g` is an accounting relationship about *aggregate* "
    "capital and labour shares. Whether it translates into rising "
    "inequality *between individuals* also depends on how concentrated "
    "capital ownership already is, how much of capital income is saved "
    "versus consumed, and bequest and tax policy — none of which this "
    "identity speaks to on its own. Treat it as one necessary ingredient "
    "in an inequality story, not the whole story.",
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
