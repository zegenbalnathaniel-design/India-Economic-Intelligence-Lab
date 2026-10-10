"""Wealth & Inequality Lab.

Interactive extension of the research paper on income and wealth
inequality in India. Contents:

    W. Who gets what -- income & wealth by group, 2022-23, and shares since 1951 (WIL)
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

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import inequality, wealth
from app.components.theme import (
    setup, set_chart_source, chart_source, kicker, callout, source_badge, stat_card, footnote, GOLD, CRIMSON, MUTED, VERMILLION,
    TURQUOISE, WARM_WHITE, COBALT,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel
from app.components import hairline_display
from data_sources import loaders


setup("Wealth & Inequality Lab", accent=VERMILLION)
set_chart_source("World Inequality Lab WP 2024/09 (Bharti, Chancel, Piketty & Somanchi); calculations on this site")


# ---------- Sidebar -----------------------------------------------------------

with st.sidebar:
    st.markdown("## Wealth Lab")
    st.caption("Sections")
    st.markdown(
        "- Who gets what (WIL data)\n"
        "- A · Framework\n"
        "- B · Composition effect\n"
        "- C · Asset allocation\n"
        "- D · r − g explorer\n"
        "- E · Which allocation built the most wealth"
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

wil_income = loaders.load_wil_income_2022()
wil_wealth22 = loaders.load_wil_wealth_2022()
wil_table = inequality.group_table(wil_income, wil_wealth22)
wil_inc_series = loaders.load_wil_income_shares()
wil_wealth_series = loaders.load_wil_wealth_shares()
wil_vhnwi = loaders.load_wil_vhnwi()
wil_facts = loaders.load_wil_facts()
AVG_INCOME = inequality.average(wil_income, "avg_income_inr")
AVG_WEALTH = inequality.average(wil_wealth22, "avg_wealth_inr")
GROUP_COLOUR = {"Bottom 50%": TURQUOISE, "Middle 40%": GOLD, "Top 10%": VERMILLION,
                "Top 1%": WARM_WHITE, "Top 0.1%": MUTED}

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
        "Every figure is from the World Inequality Lab's tables. A **\\*** "
        "marks a value calculated here from them (Upper middle = Top 10% − "
        "Top 1%). The two lowest cards say **DATA REQUIRED** because the "
        "paper does not split the bottom half, and nothing is invented."
    )
    source_badge("WIL Working Paper 2024/09 · Tables 2 & 3", "VERIFIED")

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
    f"The average Indian adult had an income of **{inequality.fmt_inr(AVG_INCOME)}** and "
    f"wealth of **{inequality.fmt_inr(AVG_WEALTH)}** in 2022-23. The bottom half earned "
    f"**{wil_table.set_index('group').loc['Bottom 50%', 'multiple_of_average']:.1f}×** the "
    f"average income; the top 1%, **{wil_table.set_index('group').loc['Top 1%', 'multiple_of_average']:.1f}×**. "
    "Wealth is more concentrated than income because land, housing, businesses and "
    "financial assets are concentrated and compound over time."
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
                            zip(wil_table["avg_income"], wil_table["avg_income_status"])],
    "× average income": [("—" if pd.isna(v) else f"{v:.2f}×") for v in wil_table["multiple_of_average"]],
    "Share of income": [_cell(v, s, lambda x: f"{x:.1f}%") for v, s in
                        zip(wil_table["income_share"], wil_table["income_share_status"])],
    "Average wealth": [_cell(v, s, inequality.fmt_inr) for v, s in
                       zip(wil_table["avg_wealth"], wil_table["avg_wealth_status"])],
    "Share of wealth": [_cell(v, s, lambda x: f"{x:.1f}%") for v, s in
                        zip(wil_table["wealth_share"], wil_table["wealth_share_status"])],
})
st.dataframe(view, hide_index=True, width="stretch")
with st.expander("\\* How the starred values are calculated, and the very top"):
    notes = [f"- **{r['group']} {what}** = {r[f'{key}_formula']}"
             for _, r in wil_table.iterrows()
             for what, key in (("income share", "income_share"), ("wealth share", "wealth_share"),
                               ("average income", "avg_income"), ("average wealth", "avg_wealth"))
             if r[f"{key}_status"] == inequality.DERIVED]
    st.markdown("\n".join(notes))
    st.markdown("The paper also reports the top 0.01% and top 0.001% (about 9,200 adults):")
    top = wil_income[wil_income["group"].isin(["Top 0.01%", "Top 0.001%"])][["group", "adults", "income_share_pct", "avg_income_inr"]] \
        .merge(wil_wealth22[["group", "wealth_share_pct", "avg_wealth_inr"]], on="group")
    st.dataframe(top.assign(avg_income_inr=top["avg_income_inr"].map(inequality.fmt_inr),
                            avg_wealth_inr=top["avg_wealth_inr"].map(inequality.fmt_inr))
                 .rename(columns={"adults": "Adults", "income_share_pct": "Income share %",
                                  "avg_income_inr": "Avg income", "wealth_share_pct": "Wealth share %",
                                  "avg_wealth_inr": "Avg wealth", "group": "Group"}),
                 hide_index=True, width="stretch")

# Side-by-side groups only, so the bars are comparable (they partition 100%).
part = wil_table[wil_table["group"].isin(["Bottom 50%", "Middle 40%", "Top 10%"])]
fig_share = go.Figure()
for col, name, colour in (("population_share_pct", "Share of adults", MUTED),
                          ("income_share", "Share of income", GOLD),
                          ("wealth_share", "Share of wealth", VERMILLION)):
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
st.plotly_chart(fig_share, width="stretch", key="wil_shares")
st.caption(
    "Read across each group: if income and wealth were shared equally, the gold and red bars "
    "would match the grey one. The Top 10% are 10% of adults but hold 57.7% of income and 65.0% "
    "of wealth; the Bottom 50% are half of adults but hold 15.0% and 6.4%."
)

mult = wil_table.dropna(subset=["multiple_of_average"])
fig_mult = go.Figure(go.Bar(
    y=mult["group"], x=mult["multiple_of_average"], orientation="h",
    marker_color=[VERMILLION if s == inequality.VERIFIED else MUTED for s in mult["avg_income_status"]],
    text=[f"{v:.1f}×" for v in mult["multiple_of_average"]], textposition="outside", cliponaxis=False,
    hovertemplate="%{y}: %{x:.2f}× the national average<extra></extra>",
))
fig_mult.update_layout(
    height=360,
    xaxis=dict(title="× average income (log scale)", type="log", range=[-0.8, 2.45],
               tickvals=[0.3, 1, 3, 10, 30, 100], ticktext=["0.3×", "1×", "3×", "10×", "30×", "100×"]),
    yaxis=dict(autorange="reversed"), title="Average income vs the national average, 2022-23", showlegend=False,
)
st.plotly_chart(fig_mult, width="stretch", key="wil_mult")
st.caption("Grey bar = calculated (Upper middle). Log scale, so the 0.3× and 95.8× bars both fit; "
           "1× is the national average.")


# ---------- W2. Over time ---------------------------------------------------------

kicker("W · Over time")
st.subheader("A century of change")
measure = st.radio("Show", ["Income shares, 1951-2022 (every year)", "Wealth shares, 1961-2023"],
                   horizontal=True, key="wil_measure")
is_income = measure.startswith("Income")
series = wil_inc_series if is_income else wil_wealth_series
groups = st.multiselect("Groups", list(inequality.SERIES.values()),
                        default=["Bottom 50%", "Middle 40%", "Top 10%", "Top 1%"], key="wil_groups")
long = inequality.shares_long(series)
fig_t = go.Figure()
for g in groups:
    s = long[long["group"] == g].sort_values("year")
    firm = s[~s["tentative"]] if "tentative" in s else s
    fig_t.add_trace(go.Scatter(
        x=firm["year"], y=firm["share_pct"], name=g, mode="lines" if is_income else "lines+markers",
        line=dict(color=GROUP_COLOUR[g], width=3), marker=dict(size=6),
        hovertemplate=f"{g} %{{x}}: %{{y:.1f}}%<extra></extra>",
    ))
    if "tentative" in s and s["tentative"].any():
        seg = s[s["year"] >= firm["year"].max()]
        fig_t.add_trace(go.Scatter(
            x=seg["year"], y=seg["share_pct"], mode="lines+markers", showlegend=False,
            line=dict(color=GROUP_COLOUR[g], width=2, dash="dot"),
            marker=dict(size=8, symbol="circle-open"),
            hovertemplate=f"{g} %{{x}}: %{{y:.1f}}% (tentative)<extra></extra>",
        ))
if is_income:
    fig_t.add_vline(x=1991, line_dash="dash", line_color=MUTED, annotation_text="1991 liberalisation",
                    annotation_position="top left")
fig_t.update_layout(height=460, yaxis=dict(title="% of total", rangemode="tozero"), xaxis_title=None,
                    title=("Pre-tax national income shares" if is_income else "Net wealth shares"),
                    legend=dict(orientation="h", y=-0.12))
st.plotly_chart(fig_t, width="stretch", key="wil_time")
if is_income:
    st.caption("Table B.1. Top 10% overtook the Middle 40% in the early 2000s.")
else:
    st.caption("Table C.1. Before 2002 there is one point per wealth survey (1961, 1971, 1981, 1991); "
               "the lines between them only connect the dots — no values are interpolated. The dotted "
               "2023 point is marked tentative by the authors (based on a truncated Hurun list).")

years = series["year"].tolist()
y0, y1 = st.select_slider("Compare two years", options=years,
                          value=(1980 if is_income else 1961, years[-2] if not is_income else years[-1]),
                          key="wil_years")
if y0 == y1:
    st.info("Pick two different years.")
else:
    ch = inequality.change_between(series, y0, y1)
    ch = ch[ch["group"].isin(groups)] if groups else ch
    st.dataframe(pd.DataFrame({
        "Group": ch["group"],
        f"{y0}": ch["start_pct"].map(lambda v: f"{v:.1f}%"),
        f"{y1}": ch["end_pct"].map(lambda v: f"{v:.1f}%"),
        "Change": ch["change_pp"].map(lambda v: f"{v:+.1f} pp"),
        "Relative change": ch["change_rel_pct"].map(lambda v: f"{v:+.0f}%"),
    }), hide_index=True, width="stretch")
    st.caption("Changes are calculated here from the two printed values.")

vh = wil_vhnwi
fig_b = go.Figure()
fig_b.add_trace(go.Bar(x=vh["year"], y=vh["forbes_count"], name="Forbes USD billionaires (count)",
                       marker_color=GOLD, hovertemplate="%{x}: %{y} billionaires<extra></extra>"))
fig_b.add_trace(go.Scatter(x=vh["year"], y=vh["forbes_wealth_pct_nni"], name="Their wealth, % of national income",
                           yaxis="y2", mode="lines+markers", line=dict(color=VERMILLION, width=3),
                           hovertemplate="%{x}: %{y:.1f}% of NNI<extra></extra>"))
fig_b.update_layout(height=400, title="The billionaire raj: Forbes USD billionaires, 1988-2022",
                    yaxis=dict(title="count", rangemode="tozero"),
                    yaxis2=dict(title="% of NNI", overlaying="y", side="right", showgrid=False,
                                range=[0, 30], tickmode="array", tickvals=[0, 10, 20, 30], ticksuffix="%"),
                    legend=dict(orientation="h", y=-0.15))
st.plotly_chart(fig_b, width="stretch", key="wil_billionaires")
st.caption("Table C.2. Hurun's broader list (net wealth above ₹1,000 crore) had 1,103 people holding "
           "27.5% of national income in 2022.")

kicker("W · One number")
st.subheader("A distributional Gini, from the group shares")
g_inc = inequality.gini_series(wil_inc_series)
g_w = inequality.gini_series(wil_wealth_series)
fig_g = go.Figure()
fig_g.add_trace(go.Scatter(x=g_inc["year"], y=g_inc["gini_lower_bound"], name="Income", mode="lines",
                           line=dict(color=GOLD, width=3), hovertemplate="Income %{x}: %{y:.3f}<extra></extra>"))
gw_firm = g_w[~g_w["tentative"]]
fig_g.add_trace(go.Scatter(x=gw_firm["year"], y=gw_firm["gini_lower_bound"], name="Wealth", mode="lines+markers",
                           line=dict(color=VERMILLION, width=3), hovertemplate="Wealth %{x}: %{y:.3f}<extra></extra>"))
gw_tail = g_w[g_w["year"] >= gw_firm["year"].max()]
fig_g.add_trace(go.Scatter(x=gw_tail["year"], y=gw_tail["gini_lower_bound"], mode="lines+markers", showlegend=False,
                           line=dict(color=VERMILLION, width=2, dash="dot"), marker=dict(symbol="circle-open", size=9),
                           hovertemplate="Wealth %{x}: %{y:.3f} (tentative)<extra></extra>"))
fig_g.update_layout(height=380, yaxis=dict(title="Gini (lower bound)", range=[0, 1]),
                    title="Gini coefficient implied by the WIL group shares", legend=dict(orientation="h", y=-0.15))
st.plotly_chart(fig_g, width="stretch", key="wil_gini")
gi = g_inc.set_index("year")["gini_lower_bound"]
gwi = g_w.set_index("year")["gini_lower_bound"]
st.caption(
    f"Income: {gi.loc[1982]:.2f} in 1982 → {gi.loc[2022]:.2f} in 2022. Wealth: {gwi.loc[1961]:.2f} in 1961 → "
    f"{gwi.loc[2022]:.2f} in 2022. Calculated here from Tables B.1 and C.1."
)
indicator_note(
    "this Gini",
    "**How it is calculated.** Each year's shares give five points on the Lorenz curve: the poorest 50% "
    "hold X%, the poorest 90% hold X + Y%, the poorest 99% and 99.9% hold everything except the Top 1% "
    "and Top 0.1%. Joining those points with straight lines and measuring the gap from perfect equality "
    "gives the Gini.\n\n**Why it is a lower bound.** Straight lines treat everyone *inside* a group as "
    "equal, so the true Gini — which also counts inequality within each group — is higher. It is a "
    "consistent way to track the trend from published shares, not a survey Gini.\n\n"
    "**What would make it complete.** Household-level data (AIDIS for wealth, NSS/PLFS for "
    "consumption) would give the full distribution. Those microdata need a registered login at "
    "microdata.gov.in and are not in this project.",
    kind="method",
)

st.markdown("**What if some of the Top 1%'s share went to the Bottom 50%?**")
sc1, sc2 = st.columns([1, 2])
with sc1:
    sc_measure = st.radio("Of", ["Income (2022)", "Wealth (2022)"], key="gini_measure")
    sc_src = (wil_inc_series if sc_measure.startswith("Income") else wil_wealth_series).set_index("year").loc[2022]
    base_shares = {k: float(sc_src[k]) for k in inequality.SERIES}
    moved = st.slider("Percentage points moved", 0.0, float(base_shares["top_1"]), 5.0, 0.5, key="gini_pp")
new_shares = inequality.redistribute(base_shares, moved)
g_before = inequality.gini_lower_bound(base_shares["bottom_50"], base_shares["middle_40"],
                                       base_shares["top_1"], base_shares["top_0_1"])
g_after = inequality.gini_lower_bound(new_shares["bottom_50"], new_shares["middle_40"],
                                      new_shares["top_1"], new_shares["top_0_1"])
with sc2:
    st.dataframe(pd.DataFrame({
        "Group": list(inequality.SERIES.values()),
        "Actual 2022": [f"{base_shares[k]:.1f}%" for k in inequality.SERIES],
        "Scenario": [f"{new_shares[k]:.1f}%" for k in inequality.SERIES],
    }), hide_index=True, width="stretch")
    stat_card("Gini (lower bound)", f"{g_before:.3f} → {g_after:.3f}", f"{g_after - g_before:+.3f}")
st.caption(
    "A mechanical scenario, not a policy forecast: it moves shares on paper and recomputes the Gini. The Top "
    "0.1% is assumed to give up the same fraction of its share as the Top 1% as a whole."
)

kicker("Long run")
facts = wil_facts.set_index(["metric", "period"])["value"]
vhy = vh.set_index("year")
f1, f2, f3, f4 = st.columns(4)
with f1:
    stat_card("Real income growth", f"{facts[('Real average income growth', '1990-2022')]:.1f}% / yr",
              f"1990-2022 · vs {facts[('Real average income growth', '1960-1990')]:.1f}% in 1960-1990")
with f2:
    stat_card("Wealth ÷ income", f"{facts[('Wealth-to-income ratio', '2022')]:.2f}×",
              f"2022 · up from {facts[('Wealth-to-income ratio', '1995')]:.2f}× in 1995")
with f3:
    stat_card("USD billionaires", f"{vhy.loc[2022, 'forbes_count']:.0f}",
              f"2022 · {vhy.loc[1991, 'forbes_count']:.0f} in 1991")
with f4:
    stat_card("Billionaire wealth", f"{vhy.loc[2022, 'forbes_wealth_pct_nni']:.1f}% of NNI",
              f"2022 · {vhy.loc[1991, 'forbes_wealth_pct_nni']:.1f}% in 1991")
b1 = wil_inc_series.set_index("year")
st.caption(
    f"Top 1% income share: 13% in 1922, over 20% between the wars, 13% at independence, "
    f"{b1.loc[1982, 'top_1']:.1f}% in 1982, {b1.loc[2022, 'top_1']:.1f}% in 2022 — the highest "
    "since the series begins in 1922."
)

kicker("Reading these numbers")
st.subheader("What each group means, how we got here, and the caveats")
st.caption("Everything below is from the paper, with the table or section it comes from. Statements that "
           "are not in the paper have been left out.")

inc_t = wil_income.set_index("group")
wt_t = wil_wealth22.set_index("group")
c1 = wil_wealth_series.set_index("year")
crossover = int(b1[b1["top_10"] > b1["middle_40"]].index[b1[b1["top_10"] > b1["middle_40"]].index > 1990].min())
F = lambda metric, period: facts[(metric, period)]


def tier(name: str) -> str:
    r = wil_table.set_index("group").loc[name]
    if r["income_share_status"] == inequality.REQUIRED:
        return (f"**{name} ({r['percentile_range']}).** The paper does not split the bottom half, so there "
                "is no figure for this group — DATA REQUIRED.")
    entry = ""
    if name in inc_t.index and inc_t.loc[name, "threshold_inr"] > 0:
        entry = (f" Entry takes an income of **{inequality.fmt_inr(inc_t.loc[name, 'threshold_inr'])}** a year "
                 f"(wealth: {inequality.fmt_inr(wt_t.loc[name, 'threshold_inr'])}).")
    star = " (calculated: Top 10% minus Top 1%)" if r["income_share_status"] == inequality.DERIVED else ""
    return (f"**{name} ({r['percentile_range']}){star}.** {r['income_share']:.1f}% of income and "
            f"{r['wealth_share']:.1f}% of wealth. Average income {inequality.fmt_inr(r['avg_income'])} a year "
            f"(≈ {inequality.fmt_inr(r['avg_income'] / 12)} a month), {r['multiple_of_average']:.1f}× the "
            f"national average; average wealth {inequality.fmt_inr(r['avg_wealth'])}.{entry}")


with st.expander("What each group means, 2022-23 (Tables 2 and 3)", expanded=True):
    st.markdown("\n\n".join(tier(g) for g in inequality.GROUPS))
    st.caption(
        "Monthly figures are the yearly average ÷ 12, per adult. The paper describes the Middle 40% as "
        "having 'lost out significantly' since liberalisation and links this to India's 'missing middle "
        "class' (Sections 4.2 and 7.2)."
    )

with st.expander("The long-run pattern (Sections 1, 3, 4 and 7; Tables B.1, C.1, C.2)"):
    st.markdown(
        f"- **1922 to independence.** The top 1% income share went from **{F('Top 1% income share', '1922'):.0f}%** "
        f"in 1922 to **over {F('Top 1% income share', 'inter-war period'):.0f}%** between the wars, then fell "
        f"back to about **{F('Top 1% income share', '1947'):.0f}%** by independence.\n"
        f"- **1950s to early 1980s — inequality fell.** Top 1%: {b1.loc[1951, 'top_1']:.1f}% (1951) → "
        f"**{b1.loc[1982, 'top_1']:.1f}%** (1982). Top 10%: {b1.loc[1951, 'top_10']:.1f}% → "
        f"{b1.loc[1982, 'top_10']:.1f}%. The paper links this to nationalisation (rail, air, banking, oil), "
        f"strong market regulation and high tax progressivity — a top marginal rate of "
        f"**{F('Top marginal income tax rate', '1973'):.1f}%** in 1973 (Section 3.1). An inheritance tax ran from 1953 to "
        "1985 and a wealth tax from 1957 to 2016, though with a very low base (Section 1.2).\n"
        f"- **1980s–1990s — the decline stops.** From the early-1980s reforms and the 1991 liberalisation, top "
        f"shares rose: Top 1% {b1.loc[1990, 'top_1']:.1f}% (1990) → {b1.loc[2000, 'top_1']:.1f}% (2000).\n"
        f"- **2000s onward — sharp rise.** The Top 10% overtook the Middle 40% in **{crossover}** "
        f"({b1.loc[crossover, 'top_10']:.1f}% vs {b1.loc[crossover, 'middle_40']:.1f}%). USD billionaires: "
        f"{vhy.loc[1991, 'forbes_count']:.0f} (1991) → {vhy.loc[2011, 'forbes_count']:.0f} (2011) → "
        f"{vhy.loc[2022, 'forbes_count']:.0f} (2022); their wealth {vhy.loc[1991, 'forbes_wealth_pct_nni']:.1f}% → "
        f"{vhy.loc[2022, 'forbes_wealth_pct_nni']:.1f}% of national income.\n"
        f"- **2014-15 to 2022-23 — 'particularly pronounced' in wealth.** Billionaire net wealth grew "
        f"**over {F('Billionaire net wealth growth (real)', '2014-2022'):.0f}%** in real terms, against "
        f"{F('National income growth (real)', '2014-2022'):.1f}% for national income. The Middle 40% grew more "
        "slowly than the Bottom 50% in both income and wealth over 2014-2022 (Section 7.2).\n"
        f"- **Wealth: the middle squeezed.** Middle 40% and Top 10% were both 40–45% of wealth in 1961–1981. "
        f"The Middle 40% then fell to {c1.loc[2012, 'middle_40']:.1f}% (2012), {c1.loc[2018, 'middle_40']:.1f}% "
        f"(2018) and {c1.loc[2022, 'middle_40']:.1f}% (2022), while the Top 10% reached "
        f"{c1.loc[2022, 'top_10']:.1f}%. The Bottom 50% already held only {c1.loc[1991, 'bottom_50']:.1f}% "
        "in 1991.\n"
        f"- **2022-23:** Top 1% income share {b1.loc[2022, 'top_1']:.1f}% and wealth share "
        f"{c1.loc[2022, 'top_1']:.1f}% — the highest in each series. The wealth-to-income ratio rose from "
        f"{F('Wealth-to-income ratio', '1995'):.2f} (1995) to {F('Wealth-to-income ratio', '2022'):.2f} (2022)."
    )

with st.expander("Caveats the paper itself states"):
    st.markdown(
        "- **Probably a lower bound.** The authors say India's economic data are 'notably poor' and have "
        "declined recently, so their results 'likely represent a lower bound to actual inequality levels' "
        "(Abstract).\n"
        "- **No comparable consumption survey after 2011-12.** The absence of a comparable NSSO consumption "
        "survey is a key challenge for the last decade, so recent bottom and middle shares are the least "
        "certain (Section 7.3).\n"
        "- **Same under-reporting at every level.** The method assumes the same fraction of income is hidden "
        "across the whole distribution, in surveys and tax data alike. If the very rich hide more — for "
        "example through income shifting — top incomes may be 'severely' underestimated (Section 7.5).\n"
        "- **Early wealth figures are lower bounds.** Wealth inequality up to 1991 rests on surveys alone and "
        "is likely understated; changes between 1991 and 2002 should be read with caution (Section 2.3). "
        "Before 2002 there is only one point per survey (1961, 1971, 1981, 1991).\n"
        "- **2023 wealth is tentative** — it uses Hurun's 2023 list truncated at the top 100 (Table C.1 note).\n"
        "- **Scaled to national accounts.** Averages are scaled to WID national-income and national-wealth "
        "totals, which differ marginally from official figures (Table 2–3 notes).\n"
        "- **One extreme debtor.** The Bottom 50% wealth threshold of −₹4.1 crore comes from a single AIDIS "
        "household with enormous debt; without it, the Bottom 50% average is ₹1,93,031 instead of "
        f"{inequality.fmt_inr(wt_t.loc['Bottom 50%', 'avg_wealth_inr'])} (Table 3 note)."
    )
    st.markdown(
        "**Checks run on this site.** Bottom 50% + Middle 40% + Top 10% add to 100% (±0.1 from rounding) in "
        "every year of both series, and the 2022 rows match Tables 2 and 3. In Table 2, each group's average "
        "income implies its printed share to within 0.2 pp, except the Middle 40%: 40% × ₹1,65,273 ÷ "
        "₹2,34,551 = 28.2% against the printed 27.3%. That 0.9 pp gap is in the paper."
    )

with st.expander("What changed from the earlier summary you supplied"):
    st.markdown(
        "Checked line by line against the paper; the paper's figures are now used everywhere.\n\n"
        "| Earlier summary | Paper | Where |\n|---|---|---|\n"
        "| Top 10% wealth 64.6% (2022-23) | **65.0%** — 64.6% is the tentative 2023 row | Table 3, C.1 |\n"
        "| Top 0.1% wealth 29.0% | **29.7%** — 29.0% is the 2023 row | Table 3, C.1 |\n"
        "| Middle 40% wealth 'about 29%' | **28.6%** | Table 3 |\n"
        "| Middle 40% income 'about 29–30%' | **27.3%** | Table 2 |\n"
        "| Middle 40% wealth 'about 35%' in 2012 | **30.8%** in 2012 (35–36% was 2002–05) | C.1 |\n"
        "| Top 1% wealth 1961 'about 13–15%' | **12.9%** | C.1 |\n"
        "| Bottom 50% income share 'down ~40% since 1980' | 23.3% → 15.0%: **−36%** | B.1 |\n"
        "| Top 1% income share 'up ~180% since 1980' | 7.3% → 22.6%: **+210%** | B.1 |\n"
        "| Top 1% 'under 21%' in the late 1930s | 'over 20% in the inter-war period' | Section 3.1 |\n"
        "| Billionaire wealth '25%' of NNI, 2022 | **24.6%** (Forbes) | C.2 |\n"
        "| Average income ₹2.35 lakh | **₹2,34,551** | Table 2 |\n"
        "| Middle 40% ≈ ₹13,750 a month | **₹13,773** (₹1,65,273 ÷ 12) | Table 2 |\n"
        "| Upper middle 'in the middle 40% or the top 10%' | Defined here as **P90–P99** (Top 10% − Top 1%) | Tables 2–3 |\n"
        "| Government puts the middle class at ~31% | **Not in the paper** — removed | — |\n"
        "| Who each tier is (informal workers, salaried professionals…) | **Not in the paper** — replaced by its figures | — |\n"
        "| Post-independence decline from land reforms, wealth & inheritance taxes | Paper: nationalisation, regulation, 97.5% top tax rate; inheritance tax 1953–85, wealth tax 1957–2016 (low base); land redistribution in a footnote | 1.2, 3.1 |"
    )


# ---------- A. Framework ------------------------------------------------------

st.markdown("---")
kicker("A · Framework")
st.header("From capability to intergenerational mobility")
st.markdown(
    "The paper argues that wealth accumulation is not the outcome of income "
    "alone — it is a chain of transitions. **Figure 1** of the paper draws "
    "it as a ladder with one weak rung: the step from *income* to "
    "*ownership*. Everything above that line is about earning; everything "
    "below it is about owning, and that is where Indian households get stuck."
)

FIG1 = [
    ("CAPABILITY", "Education, skills, health, freedoms", True),
    ("EMPLOYMENT", "Capability put to economic use", True),
    ("INCOME", "A flow — earned, taxed, largely spent", True),
    ("OWNERSHIP", "Equity, business, property, financial assets", False),
    ("WEALTH", "A compounding, appreciating stock", False),
    ("ECONOMIC FREEDOM", "Income independent of labour; optionality", False),
    ("INTERGENERATIONAL MOBILITY", "Freedom transmitted across generations", False),
]


def _fig1_html() -> str:
    boxes = []
    for i, (title, sub, earn) in enumerate(FIG1):
        colour = TURQUOISE if earn else VERMILLION
        boxes.append(
            f"<div style='border:2px solid {colour};border-radius:8px;padding:10px 14px;"
            f"background:{colour}1A;text-align:center;max-width:460px;margin:0 auto;'>"
            f"<div style='color:{colour};font-weight:800;letter-spacing:.06em;font-size:15px'>{title}</div>"
            f"<div style='color:#C9C5BA;font-size:13px;margin-top:2px'>{sub}</div></div>"
        )
        if i == 2:
            boxes.append(
                "<div style='position:relative;max-width:560px;margin:6px auto;text-align:center;'>"
                "<div style='border-top:2px dashed #F5F0E6;opacity:.6;'></div>"
                f"<div style='color:{VERMILLION};font-weight:800;font-size:14px;margin-top:-11px;"
                "display:inline-block;background:#11131A;padding:0 10px'>▼ Weak</div>"
                "<div style='color:#F5F0E6;font-size:12px;font-weight:700;margin-top:2px'>"
                "Binding constraint: income does not turn into ownership</div></div>"
            )
        elif i < len(FIG1) - 1:
            boxes.append("<div style='text-align:center;color:#8B8D99;font-size:18px;line-height:20px'>▼</div>")
    return "<div style='padding:6px 0 4px'>" + "".join(boxes) + "</div>"


f1c1, f1c2 = st.columns([5, 4], vertical_alignment="center")
with f1c1:
    st.markdown(_fig1_html(), unsafe_allow_html=True)
    st.caption("Figure 1 of the paper: Income & Wealth Framework, redrawn.")
with f1c2:
    st.markdown(
        "**How to read it.** The three teal rungs are what most policy targets: "
        "skills, jobs and incomes. The four red rungs are what actually builds "
        "wealth. The dashed line is the paper's *binding constraint*: rising "
        "incomes do not automatically become ownership of productive assets, "
        "because most household saving goes into property and gold (Table 1).\n\n"
        "**Why it matters for r − g.** Once wealth is held, it grows at the "
        "return *r* of the assets owned. Section D below shows that those "
        "returns differ hugely by asset, and section E shows what that does to "
        "two identical savers."
    )
st.markdown("Open any stage for the argument as it appears in the paper:")

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
st.plotly_chart(chart_source(path_fig, "Simulation under the assumptions set on this page — not data"), width="stretch")

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
st.plotly_chart(chart_source(comp_fig, "Simulation under the assumptions set on this page — not data"), width="stretch")

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
    "**Correlation and fat tails.** By default each asset is drawn "
    "independently of the others, from a normal distribution. Below you can "
    "set correlations between assets (assets that fall together widen the "
    "band) and switch to fat-tailed Student-t draws (more extreme years, "
    "same volatility). Both are your assumptions — this project has no "
    "Indian asset-return history to estimate them from. Returns are still "
    "independent from one year to the next (no momentum or rebound).",
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

st.markdown("**How assets move together, and how extreme bad years are**")
cc1, cc2 = st.columns([3, 2])
with cc1:
    corr_mode = st.radio("Correlation between assets", ["Independent (none)", "Set correlations"],
                         horizontal=True, key="mc_corr_mode")
with cc2:
    fat_tails = st.toggle("Fat tails (Student-t draws)", key="mc_fat")
    t_df = st.slider("Tail heaviness — degrees of freedom (lower = fatter)", 3, 30, 5,
                     key="mc_df", disabled=not fat_tails)
mc_corr = None
if corr_mode == "Set correlations":
    st.caption(
        "Edit the cells **above the diagonal** (−1 to 1); the lower half mirrors them. These are your "
        "assumptions — no Indian return history is in this project to estimate them. Starts at 0."
    )
    labels = [wealth.ASSET_LABELS[k] for k in wealth.ASSET_KEYS]
    base = pd.DataFrame(np.eye(len(labels)), index=labels, columns=labels)
    edited = st.data_editor(base, key="mc_corr_editor", width="stretch",
                            column_config={c: st.column_config.NumberColumn(c, min_value=-1.0, max_value=1.0,
                                                                            step=0.05, format="%.2f")
                                           for c in labels})
    upper = np.triu(edited.to_numpy(dtype=float), 1)
    candidate = upper + upper.T + np.eye(len(labels))
    try:
        mc_corr = wealth.validate_correlation(candidate, len(labels))
    except ValueError as exc:
        st.error(f"{exc} Showing the independent model until this is fixed.")
        mc_corr = None

mc = wealth.monte_carlo(
    annual_contribution=annual,
    years=years,
    allocation=alloc_inputs,
    returns=ret_inputs,
    volatilities=vol_inputs,
    inflation=inflation,
    n_paths=int(n_paths),
    seed=int(mc_seed),
    correlation=mc_corr,
    t_df=float(t_df) if fat_tails else None,
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
st.plotly_chart(chart_source(mc_fig, "Simulation under the assumptions set on this page — not data"), width="stretch")

p5, p25, p50, p75, p95 = np.percentile(mc.final_nominal, [5, 25, 50, 75, 95])
q1, q2, q3, q4, q5 = st.columns(5)
with q1: stat_card("5th pct", _rupee(p5), "worst-case tail")
with q2: stat_card("25th pct", _rupee(p25), "")
with q3: stat_card("Median", _rupee(p50), "central outcome")
with q4: stat_card("75th pct", _rupee(p75), "")
with q5: stat_card("95th pct", _rupee(p95), "best-case tail")

model_desc = ("independent" if mc_corr is None else "correlated (your matrix)") + \
    (f", Student-t with {t_df} degrees of freedom" if fat_tails else ", normal")
callout(
    f"Model in use: <b>{model_desc}</b> returns. Correlations and tail heaviness are assumptions you "
    "set, not estimates. With positive correlations or fat tails the band widens — the independent, "
    "normal default understates real-world dispersion if Indian assets fall together.",
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
st.dataframe(display, hide_index=True, width="stretch")

bar = go.Figure()
bar.add_bar(x=compare["Asset"], y=compare["Final real"], name="Final real wealth", marker_color=GOLD)
bar.update_layout(
    title="Final wealth if concentrated in one asset (real terms)",
    yaxis_title="₹ (real)", xaxis_title="", height=360, showlegend=False,
)
st.plotly_chart(chart_source(bar, "Simulation under the assumptions set on this page — not data"), width="stretch")

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

paper_ret = loaders.load_paper_a_returns().set_index("asset")
PAPER_R = {
    "Listed equity": paper_ret.loc["Financial assets: listed equity", "nominal_return_1991_2021_pct"] / 100,
    "Residential property": paper_ret.loc["Residential property", "nominal_return_1991_2021_pct"] / 100,
    "Gold": paper_ret.loc["Gold", "nominal_return_1991_2021_pct"] / 100,
    "Typical household portfolio": paper_ret.loc["Representative household portfolio", "nominal_return_1991_2021_pct"] / 100,
    "Bank deposits": paper_ret.loc["Financial assets: deposits", "nominal_return_1991_2021_pct"] / 100,
}
ASSET_COLOUR = {"Listed equity": TURQUOISE, "Residential property": VERMILLION, "Gold": GOLD,
                "Typical household portfolio": COBALT, "Bank deposits": MUTED}

st.markdown(
    "**Defaults come from the paper.** Inflation 6.5% and growth 6.5% reproduce Table 1: at those values "
    "property earns about 2.6% real, gold 2.5%, deposits about 0% and listed equity 6.6% — the paper's "
    "'return heterogeneity'. Change any slider to test a different world."
)
cA, cB, cC = st.columns(3)
with cA:
    r_nom = st.slider("Nominal return on capital r (%)", 0.0, 20.0,
                      float(round(PAPER_R["Typical household portfolio"] * 100, 2)), 0.25,
                      help="Default: the typical household portfolio's 9.2% (paper, Figure 2).") / 100
with cB:
    infl = st.slider("Inflation π (%)", 0.0, 15.0, 6.5, 0.25,
                     help="6.5% reproduces Table 1's real-return column.") / 100
with cC:
    g_real = st.slider("Real income / GDP growth g (%)", -5.0, 15.0, 6.5, 0.25,
                       help="Paper: real GDP growth of 6–7%.") / 100

rg = wealth.rminusg_frame(r_nominal=r_nom, inflation=infl, g_real=g_real)
c1, c2, c3, c4 = st.columns(4)
with c1: stat_card("r nominal", f"{rg['r_nominal']*100:.2f}%")
with c2: stat_card("Inflation π", f"{rg['inflation']*100:.2f}%")
with c3: stat_card("r real", f"{rg['r_real']*100:.2f}%")
with c4:
    diff = rg['r_minus_g']
    stat_card("r − g (real)", f"{diff*100:+.2f} pts",
              "capital outgrows the economy" if diff > 0 else "the economy outgrows this capital")

callout(
    "Consistency check: r and g must be on the same basis. r is converted to a real rate before it is "
    "compared with real growth g. The paper's point: comparing equity's <b>nominal</b> 13.5% with "
    "<b>real</b> growth of 6–7% makes r > g look obvious; in real terms equity earns about g.",
    kind="warn",
)

# 1. Return heterogeneity: each asset's real r against g.
st.subheader("Which assets beat the economy?")
rmg = wealth.real_minus_g(PAPER_R, infl, g_real)
fig_rg = go.Figure(go.Bar(
    y=rmg["asset"], x=rmg["real"] * 100, orientation="h",
    marker_color=[ASSET_COLOUR[a] for a in rmg["asset"]],
    text=[f"{r*100:.1f}% real  ({d*100:+.1f} pts vs g)" for r, d in zip(rmg["real"], rmg["r_minus_g"])],
    textposition="outside", cliponaxis=False,
    hovertemplate="%{y}: %{x:.2f}% real<extra></extra>",
))
fig_rg.add_vline(x=g_real * 100, line_color=WARM_WHITE, line_dash="dash", line_width=2,
                 annotation_text=f"g = {g_real*100:.1f}%", annotation_position="top")
fig_rg.update_layout(height=340, xaxis=dict(title="Real return, % a year (1991–2021 nominal returns, your π)",
                                            range=[min(-2, rmg["real"].min() * 100 - 1), max(14, rmg["real"].max() * 100 + 6)]),
                     yaxis=dict(autorange="reversed"), showlegend=False,
                     title="Real return of each asset vs real growth g")
st.plotly_chart(chart_source(fig_rg, "Author's paper, Table 1 (returns 1991-2021, Wahengbam 2023); inflation and g as set on this page"), width="stretch", key="rg_assets")
beats = rmg[rmg["r_minus_g"] > 0]["asset"].tolist()
st.markdown(
    f"**At these settings, {('only ' + ', '.join(beats)) if beats else 'no asset'} "
    f"{'earns' if len(beats) == 1 else 'earn'} more than the economy grows.** "
    f"The typical household portfolio — about 77% property and 11% gold — earns "
    f"{rmg.set_index('asset').loc['Typical household portfolio', 'real']*100:.1f}% real, "
    f"{abs(rmg.set_index('asset').loc['Typical household portfolio', 'r_minus_g'])*100:.1f} points "
    f"{'below' if rmg.set_index('asset').loc['Typical household portfolio', 'r_minus_g'] < 0 else 'above'} g. "
    "That is the paper's argument: India does not show a general r > g; it shows *return heterogeneity* — "
    "the typical portfolio earns below g, broad equity earns roughly g, and the households who own the "
    "highest-return assets are already the wealthiest."
)

# 2. What r - g does to capital vs the economy over time.
st.subheader("What a gap does over time")
horizon = st.slider("Years", 5, 50, 30, key="rg_years")
t = np.arange(horizon + 1)
fig_div = go.Figure()
fig_div.add_trace(go.Scatter(x=t, y=(1 + g_real) ** t, name=f"Economy / average income (g = {g_real*100:.1f}%)",
                             line=dict(color=WARM_WHITE, width=3, dash="dash")))
for a in ("Listed equity", "Typical household portfolio", "Bank deposits"):
    rr = rmg.set_index("asset").loc[a, "real"]
    fig_div.add_trace(go.Scatter(x=t, y=(1 + rr) ** t, name=f"{a} ({rr*100:.1f}% real)",
                                 line=dict(color=ASSET_COLOUR[a], width=3)))
fig_div.update_layout(height=360, yaxis_title="Real value of ₹1 (×)", xaxis_title="Years",
                      title="₹1 of capital vs ₹1 of national income, in real terms",
                      legend=dict(orientation="h", y=-0.2), hovermode="x unified")
st.plotly_chart(chart_source(fig_div, "Author's paper, Table 1; illustrative compounding at the rates set on this page"), width="stretch", key="rg_paths")
hh_r = rmg.set_index("asset").loc["Typical household portfolio", "real"]
st.caption(
    f"After {horizon} years, national income has grown {(1+g_real)**horizon:.1f}× in real terms; the typical "
    f"household portfolio {(1+hh_r)**horizon:.1f}×; listed equity "
    f"{(1+rmg.set_index('asset').loc['Listed equity', 'real'])**horizon:.1f}×. Capital held in the typical "
    "portfolio shrinks relative to the economy; capital in equity roughly keeps pace."
)

# 3. What India's data show for the economy as a whole.
w95, w22 = facts[("Wealth-to-income ratio", "1995")], facts[("Wealth-to-income ratio", "2022")]
excess = wealth.implied_excess_growth(w95, w22, 2022 - 1995)
callout(
    f"<b>What the data show for India as a whole.</b> National wealth rose from {w95:.2f}× to {w22:.2f}× "
    f"national income between 1995 and 2022 (World Inequality Lab). That means wealth grew about "
    f"<b>{excess*100:.1f}% a year faster</b> than income over 27 years — aggregate capital did outgrow the "
    "economy. Combined with the asset view above, the gains went to whoever held the fast-growing assets: "
    f"the Top 1%'s wealth share rose from {wil_wealth_series.set_index('year').loc[1991, 'top_1']:.1f}% (1991) "
    f"to {wil_wealth_series.set_index('year').loc[2022, 'top_1']:.1f}% (2022).",
    kind="note",
)
st.caption("The 1.5%-a-year figure is calculated here from the paper's two ratios: (5.75 ÷ 3.83)^(1/27) − 1.")


# ---------- E. Which allocation built the most wealth (Paper Figure 2) -------------

st.markdown("---")
kicker("E · Composition effect, from the paper")
st.header("Which allocation built the most wealth, 1991–2021?")
st.markdown(
    "**Figure 2 of the paper, rebuilt from its own numbers.** Two households each save **₹1 lakh at the end "
    "of every year for 30 years** — ₹30 lakh in total. One holds listed equity; the other holds what the "
    "typical Indian household holds. Each grows at the asset's observed nominal return over 1991–2021."
)
fig2_end = loaders.load_paper_a_figure2().set_index("series")
FIG2_SERIES = {"Listed equity": "Equity capital", "Residential property": "Residential property",
               "Gold": "Gold", "Typical household portfolio": "Representative household portfolio"}
yrs = 30
fig2 = go.Figure()
paths = {
    "Listed equity": wealth.annuity_path(100000, PAPER_R["Listed equity"], yrs),
    "Residential property": wealth.annuity_path(100000, PAPER_R["Residential property"], yrs),
    "Gold": wealth.annuity_path(100000, PAPER_R["Gold"], yrs),
    "Typical household portfolio": wealth.annuity_path(100000, PAPER_R["Typical household portfolio"], yrs),
}
saving = wealth.annuity_path(100000, 0.0, yrs)
fig2.add_trace(go.Scatter(x=np.arange(yrs + 1), y=paths["Typical household portfolio"] / 1e7, showlegend=False,
                          line=dict(width=0), hoverinfo="skip"))
fig2.add_trace(go.Scatter(x=np.arange(yrs + 1), y=paths["Listed equity"] / 1e7, fill="tonexty",
                          fillcolor="rgba(36,166,161,0.15)", showlegend=False, line=dict(width=0), hoverinfo="skip"))
for name, path in paths.items():
    fig2.add_trace(go.Scatter(
        x=np.arange(yrs + 1), y=path / 1e7, name=f"{name} — {PAPER_R[name]*100:.1f}% a year",
        line=dict(color=ASSET_COLOUR[name], width=4 if name == "Listed equity" else 2.5,
                  dash="dash" if name == "Typical household portfolio" else "solid"),
        hovertemplate=f"{name}, year %{{x}}: ₹%{{y:.2f}} crore<extra></extra>",
    ))
fig2.add_trace(go.Scatter(x=np.arange(yrs + 1), y=saving / 1e7, name="Cumulative saving (r = 0)",
                          line=dict(color=MUTED, width=1.5, dash="dot"),
                          hovertemplate="Saved by year %{x}: ₹%{y:.2f} crore<extra></extra>"))
eq_end, hh_end = paths["Listed equity"][-1] / 1e7, paths["Typical household portfolio"][-1] / 1e7
gap = eq_end - hh_end
low_ends = [paths[n][-1] / 1e7 for n in ("Residential property", "Gold", "Typical household portfolio")]
fig2.add_annotation(x=yrs, y=eq_end, text=f"<b>₹{eq_end:.2f} cr</b>", showarrow=False, xanchor="left",
                    xshift=8, font=dict(color=TURQUOISE, size=14))
fig2.add_annotation(x=yrs, y=max(low_ends), text=f"₹{min(low_ends):.2f}–{max(low_ends):.2f} cr", showarrow=False,
                    xanchor="left", xshift=8, yshift=-4, font=dict(color=WARM_WHITE, size=13))
fig2.add_annotation(x=yrs, y=saving[-1] / 1e7, text=f"₹{saving[-1]/1e7:.2f} cr saved", showarrow=False,
                    xanchor="left", xshift=8, font=dict(color=MUTED, size=12))
fig2.add_shape(type="line", x0=yrs, x1=yrs, y0=hh_end, y1=eq_end, line=dict(color=WARM_WHITE, width=2))
fig2.add_annotation(x=yrs - 0.5, y=hh_end + 0.2 * gap, text=f"<b>₹{gap:.2f} cr gap</b>",
                    showarrow=False, xanchor="right", align="right", font=dict(color=WARM_WHITE, size=13))
fig2.update_layout(height=520, xaxis=dict(title="Years of saving", range=[0, yrs + 4]),
                   yaxis_title="Accumulated wealth (₹ crore, nominal)",
                   title="The composition effect: why identical savers end up unequal",
                   legend=dict(orientation="h", y=-0.18), hovermode="x unified")
st.plotly_chart(chart_source(fig2, "Author's paper, Figure 2 (returns 1991-2021, Wahengbam 2023; RBI 2017 asset shares)"), width="stretch", key="paper_fig2")

chk = pd.DataFrame([
    {"Series": n, "Return (paper)": f"{PAPER_R[n]*100:.1f}%",
     "Recomputed here": f"₹{paths[n][-1]/1e7:.2f} cr",
     "Printed in Figure 2": f"₹{fig2_end.loc[FIG2_SERIES[n], 'final_value_crore_stated']:.2f} cr"}
    for n in paths
])
with st.expander("Check against the paper's printed figure"):
    st.dataframe(chk, hide_index=True, width="stretch")
    st.caption("Future value of ₹1 lakh saved at the end of each year: FV = 1 lakh × ((1 + r)^30 − 1) ÷ r. "
               "Equity recomputes to ₹3.23 crore against the printed ₹3.24 crore (rounding); the rest match. "
               "Returns: Wahengbam (2023, CSEP), 1991–2021; household weights: RBI (2017) — 77% property, 11% "
               "gold, 5% financial assets, renormalised over 93% (durables excluded). The paper reports the "
               "weighted return as 9.2%.")

st.subheader("Rank the options")
st.caption("Same ₹1 lakh a year. Mixes are rebalanced every year between listed equity and the typical "
           "household portfolio.")
ec1, ec2, ec3 = st.columns(3)
with ec1:
    my_eq = st.slider("Your mix: share in listed equity (%)", 0, 100, 40, 5, key="fig2_eq") / 100
with ec2:
    e_years = st.slider("Years of saving", 5, 30, 30, key="fig2_years",
                        help="Up to 30, the length of the 1991–2021 window the returns come from.")
with ec3:
    e_infl = st.slider("Inflation for today's-rupee values (%)", 0.0, 12.0, 6.5, 0.5, key="fig2_infl") / 100
options = {
    "100% listed equity": PAPER_R["Listed equity"],
    "75% equity / 25% household mix": wealth.equity_mix_return(.75, PAPER_R["Listed equity"], PAPER_R["Typical household portfolio"]),
    "50% equity / 50% household mix": wealth.equity_mix_return(.50, PAPER_R["Listed equity"], PAPER_R["Typical household portfolio"]),
    f"Your mix: {my_eq:.0%} equity": wealth.equity_mix_return(my_eq, PAPER_R["Listed equity"], PAPER_R["Typical household portfolio"]),
    "100% residential property": PAPER_R["Residential property"],
    "100% gold": PAPER_R["Gold"],
    "Typical household portfolio": PAPER_R["Typical household portfolio"],
    "100% bank deposits (6.5%, midpoint of 6–7%)": PAPER_R["Bank deposits"],
}
rank = wealth.allocation_ranking(options, 100000, e_years, e_infl)
best = rank.iloc[0]
typical = rank.set_index("allocation").loc["Typical household portfolio"]
b1c, b2c, b3c = st.columns(3)
with b1c:
    stat_card("Most wealth, 1991–2021 returns", best["allocation"], f"₹{best['final_nominal']/1e7:.2f} crore after {e_years} years")
with b2c:
    stat_card("vs the typical household", f"{best['final_nominal']/typical['final_nominal']:.1f}×",
              f"₹{(best['final_nominal']-typical['final_nominal'])/1e7:.2f} crore more from the same saving")
with b3c:
    stat_card("In today's rupees", f"₹{best['final_real']/1e7:.2f} crore",
              f"at {e_infl*100:.1f}% inflation · typical: ₹{typical['final_real']/1e7:.2f} crore")
fig_rank = go.Figure(go.Bar(
    y=rank["allocation"], x=rank["final_nominal"] / 1e7, orientation="h",
    marker_color=[TURQUOISE if i == 0 else (COBALT if a.startswith("Your mix") else MUTED)
                  for i, a in enumerate(rank["allocation"])],
    text=[f"₹{v/1e7:.2f} cr · {r*100:.1f}%/yr" for v, r in zip(rank["final_nominal"], rank["return"])],
    textposition="outside", cliponaxis=False,
    hovertemplate="%{y}: ₹%{x:.2f} crore<extra></extra>",
))
fig_rank.add_vline(x=100000 * e_years / 1e7, line_dash="dot", line_color=MUTED,
                   annotation_text=f"₹{100000*e_years/1e5:.0f} lakh saved", annotation_position="bottom")
fig_rank.update_layout(height=420, yaxis=dict(autorange="reversed", automargin=True),
                       xaxis=dict(title="Final wealth (₹ crore, nominal)",
                                  range=[0, rank["final_nominal"].max() / 1e7 * 1.35]),
                       showlegend=False, title=f"Final wealth after {e_years} years of saving ₹1 lakh a year")
st.plotly_chart(chart_source(fig_rank, "Author's paper, Table 1 returns; future value of ₹1 lakh a year"), width="stretch", key="fig2_rank")

callout(
    f"<b>The answer, on the paper's numbers: the more of the saving held in listed equity, the more wealth "
    f"it built.</b> Over 1991–2021, an all-equity saver ended with {best['final_nominal']/typical['final_nominal']:.1f}× "
    "the wealth of a saver holding the typical household mix — from the same ₹1 lakh a year. Nothing about "
    "thrift differs; only what was owned.<br><br>"
    "<b>Read this with its limits.</b> These are 30-year historical averages, not forecasts. Equity's higher "
    "return came with large falls along the way (e.g. 2008, 2020) that this smooth calculation does not show "
    "— the Monte Carlo above shows how wide the range gets once returns vary. Property also gives a home to "
    "live in (no rent), which this comparison ignores; deposits and gold give liquidity and safety. Costs, "
    "taxes and the order of good and bad years all change the result. This is the paper's evidence about "
    "<i>why households diverge</i>, not personal financial advice.",
    kind="note",
)
indicator_note(
    "the composition effect",
    "**What it shows.** Saving the same amount does not produce the same wealth: the asset decides the "
    "growth rate, and compounding turns a few percentage points into a multiple over decades.\n\n"
    "**Why the typical household is where it is.** About 77% of Indian household assets are property and "
    "11% gold (RBI 2017); financial assets are 5%. The paper's Table 1 shows these are the assets with the "
    "lowest real returns, and property is illiquid, so households cannot easily shift.\n\n"
    "**Link to inequality.** Equity and business ownership are concentrated in the wealthiest households "
    "(see section W). If they hold the assets that compound fastest, the composition effect alone widens "
    "the wealth gap, even with identical saving.",
)

footnote(
    "Framework (Figure 1) and composition effect (Figure 2) are from the author's research paper on income "
    "and wealth inequality in India; returns are its 1991–2021 nominal averages (Wahengbam 2023, CSEP) and "
    "asset shares RBI (2017). r − g framing draws on Piketty (2014). Nothing here is a forecast or advice."
)

sources_panel("wil_india", "paper_a")
