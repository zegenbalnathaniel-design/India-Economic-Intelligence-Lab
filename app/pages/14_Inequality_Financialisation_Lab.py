"""Inequality & Financialisation Lab.

Who holds India's income and wealth, what households hold it in, and
whether the growth of India's financial system shows up as broader
ownership. Sections:

    A. Income and wealth inequality (WIL Tables B.1 / C.1): Lorenz curves,
       lower-bound Gini, income vs wealth concentration
    B. Wealth composition (Paper A Table 1, RBI 2017) + DATA REQUIRED by group
    C. Financialisation: live World Bank WDI series, one request per code,
       + DATA REQUIRED panels for AMFI / NSDL / CDSL
    D. Distributional questions, answered only as far as the data allow
    E. Compare any two indicators (aligned table, dual chart, CSV)
    F. Findings, built only from the values computed on this page

Every number is either from a file in data/raw (WIL, Paper A), fetched live
from the World Bank, or arithmetic on those. Nothing is typed in, filled or
interpolated; a missing source is shown as DATA REQUIRED or DATA UNAVAILABLE.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import financialisation as F, inequality
from data_sources import financialisation_uploads as UP, loaders, wdi_financial as WF, worldbank as WB
from app.components.theme import (
    setup, set_chart_source, chart_source, kicker, callout, source_badge, stat_card, footnote,
    GOLD, VERMILLION, COBALT, LEAF, TURQUOISE, WARM_WHITE, MUTED, SERIES,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel

setup("Inequality & Financialisation Lab", accent=GOLD)
set_chart_source("World Inequality Lab WP 2024/09 (Bharti, Chancel, Piketty & Somanchi); calculations on this site")

THIS_YEAR = date.today().year
WIL_SRC = "World Inequality Lab WP 2024/09, Tables B.1 and C.1; Lorenz/Gini calculated on this site"
WDI_SRC = "World Bank WDI API (live)"
UNAVAILABLE = "DATA UNAVAILABLE"


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


@st.cache_data(ttl=6 * 60 * 60, show_spinner="Fetching from the World Bank API…")
def _fetch_code(code: str, countries: tuple[str, ...], start: int, end: int) -> pd.DataFrame:
    # Errors propagate (and are therefore not cached), so a failed series is
    # retried on the next run instead of being remembered as "no data".
    return WB.fetch(code, countries, start, end)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Inequality & Financialisation")
    st.caption("Sections")
    st.markdown(
        "- A · Income and wealth inequality\n"
        "- B · What households hold\n"
        "- C · Financialisation (live WDI)\n"
        "- D · Distributional questions\n"
        "- E · Compare two indicators\n"
        "- F · Findings"
    )
    st.markdown("---")
    wdi_start, wdi_end = st.slider("World Bank years", 1960, THIS_YEAR, (1990, THIS_YEAR), key="fin_years")
    if st.button("Refresh from the API", use_container_width=True, key="fin_refresh"):
        _fetch_code.clear()
        st.rerun()
    st.caption("World Bank results are cached for 6 hours. WIL and Paper A figures are stored files.")


kicker("Inequality & Financialisation · India")
st.title("Who holds India's income and wealth — and does financial growth reach everyone?")
st.markdown(
    "India's top income and wealth shares rose sharply after the 1980s, while its financial system "
    "deepened and account ownership spread. This page puts the two side by side — and is explicit about "
    "where the aggregate numbers stop being able to say *who* gained."
)

income = loaders.load_wil_income_shares()
wealth = loaders.load_wil_wealth_shares()
vhnwi = loaders.load_wil_vhnwi()
paper_a = loaders.load_paper_a_returns()
wealth_firm = wealth[~wealth["tentative"].astype(bool)]
TENT_YEARS = set(wealth.loc[wealth["tentative"].astype(bool), "year"].astype(int))


# ===========================================================================
# A. Income and wealth inequality
# ===========================================================================
st.header("A · Income and wealth inequality")
source_badge("WIL Working Paper 2024/09", "Table B.1 income 1951–2022", "Table C.1 wealth 1961–2023")
callout(
    "**What these numbers measure.** WIL's income series is **pre-tax national income** per adult — "
    "distributional national accounts that combine national accounts, tax tabulations, surveys and rich "
    "lists. It is *not* consumption inequality as measured by household consumption surveys (e.g. MoSPI's "
    "HCES). Consumption inequality generally reads lower: richer households consume a smaller share of their "
    "income, and surveys under-capture the top. "
    "**No comparable consumption-Gini series is in this project — DATA REQUIRED.**",
    kind="warn",
)

measure = st.radio("Distribution", ["Income (Table B.1)", "Wealth (Table C.1)"], horizontal=True, key="fin_lz_measure")
is_inc = measure.startswith("Income")
series = income if is_inc else wealth
years_all = series["year"].astype(int).tolist()
default_years = [y for y in ((1951, 1982, 2022) if is_inc else (1961, 1991, 2022)) if y in years_all]
lz_years = st.multiselect("Years to draw (up to 5)", years_all, default=default_years, max_selections=5,
                          key=f"fin_lz_years_{'inc' if is_inc else 'w'}",
                          format_func=lambda y: f"{y} (tentative)" if (not is_inc and y in TENT_YEARS) else str(y))

lz = F.lorenz_table(series, sorted(lz_years)) if lz_years else F.lorenz_table(series, [])
gini_all = inequality.gini_series(series).set_index("year")["gini_lower_bound"]
fig_lz = go.Figure()
fig_lz.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect equality",
                            line=dict(color=MUTED, width=1, dash="dash"), hoverinfo="skip"))
for i, y in enumerate(sorted(lz_years)):
    d = lz[lz["year"] == y]
    tent = bool(d["tentative"].iloc[0]) if not d.empty else False
    fig_lz.add_trace(go.Scatter(
        x=d["pop_share"] * 100, y=d["cum_share"] * 100, mode="lines+markers",
        name=f"{y}{' (tentative)' if tent else ''} · Gini ≥ {gini_all.loc[y]:.3f}",
        line=dict(color=SERIES[i % len(SERIES)], width=2.5, dash="dot" if tent else "solid"),
        marker=dict(size=7),
        hovertemplate=f"{y}: poorest %{{x:.1f}}% hold %{{y:.1f}}%<extra></extra>",
    ))
fig_lz.update_layout(
    height=480, title=f"Lorenz curves, {'pre-tax national income' if is_inc else 'net wealth'} "
                      "(piecewise-linear through the published group shares)",
    xaxis=dict(title="Cumulative % of adults, poorest first", range=[0, 100], ticksuffix="%"),
    yaxis=dict(title=f"Cumulative % of {'income' if is_inc else 'wealth'}", range=[0, 100], ticksuffix="%"),
    legend=dict(orientation="h", y=-0.18),
)
st.plotly_chart(chart_source(fig_lz, WIL_SRC), use_container_width=True, key="fin_lorenz")
if not lz_years:
    st.info("Pick at least one year to draw.")
st.caption(
    "Each curve has only six known points — P0, P50, P90, P99, P99.9 and P100 — from the published Bottom 50%, "
    "Middle 40%, Top 1% and Top 0.1% shares (Top 10% follows from the partition). Straight lines join them, "
    "which treats everyone inside a group as equal, so the Gini shown is a **lower bound**."
)
indicator_note(
    "the lower-bound Gini",
    "**Calculation.** Area under the piecewise-linear Lorenz curve by the trapezium rule; Gini = 1 − 2 × area. "
    "Uses only the published shares (`analysis/inequality.py`, `gini_lower_bound`).\n\n"
    "**Why a lower bound.** Within-group inequality is ignored, so the true Gini is higher. The bound is a "
    "consistent way to track the trend, not a survey Gini, and is not comparable with the World Bank's "
    "consumption-based Gini for India.\n\n"
    "**Rounding check.** The table's Bottom 50% + Middle 40% + Top 10% add to 100 within "
    f"{F.partition_gap(series)['sum_minus_100_pp'].abs().max():.1f} pp in every year (printed rounding).",
    kind="method",
)

# Gini trend
g_inc = inequality.gini_series(income)
g_w = inequality.gini_series(wealth)
fig_g = go.Figure()
fig_g.add_trace(go.Scatter(x=g_inc["year"], y=g_inc["gini_lower_bound"], name="Income (annual)", mode="lines",
                           line=dict(color=GOLD, width=3), hovertemplate="Income %{x}: %{y:.3f}<extra></extra>"))
gw_firm = g_w[~g_w["tentative"].astype(bool)]
fig_g.add_trace(go.Scatter(x=gw_firm["year"], y=gw_firm["gini_lower_bound"], name="Wealth (survey years to 1991)",
                           mode="lines+markers", line=dict(color=VERMILLION, width=3),
                           hovertemplate="Wealth %{x}: %{y:.3f}<extra></extra>"))
gw_tail = g_w[g_w["year"] >= gw_firm["year"].max()]
if len(gw_tail) > 1:
    fig_g.add_trace(go.Scatter(x=gw_tail["year"], y=gw_tail["gini_lower_bound"], mode="lines+markers",
                               showlegend=False, line=dict(color=VERMILLION, width=2, dash="dot"),
                               marker=dict(symbol="circle-open", size=9),
                               hovertemplate="Wealth %{x}: %{y:.3f} (tentative)<extra></extra>"))
fig_g.update_layout(height=400, title="Lower-bound Gini from the WIL group shares, 1951–2023",
                    yaxis=dict(title="Gini (lower bound)", range=[0, 1]), legend=dict(orientation="h", y=-0.15))
st.plotly_chart(chart_source(fig_g, WIL_SRC), use_container_width=True, key="fin_gini")
st.caption("Before 2002 wealth has one point per survey (1961, 1971, 1981, 1991); lines only connect the dots — "
           "nothing is interpolated. Dotted = 2023, marked tentative by the authors.")

# Income vs wealth side by side
st.subheader("Income vs wealth concentration, side by side")
cc = F.concentration_compare(income, wealth_firm)
common_years = cc["year"].tolist()
c_year = st.select_slider("Year (both tables report it)", options=common_years, value=common_years[-1],
                          key="fin_cc_year")
col1, col2 = st.columns(2)
with col1:
    both_lz = pd.concat([F.lorenz_table(income, [c_year]).assign(kind="Income"),
                         F.lorenz_table(wealth_firm, [c_year]).assign(kind="Wealth")])
    fig_iw = go.Figure()
    fig_iw.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Equality",
                                line=dict(color=MUTED, width=1, dash="dash"), hoverinfo="skip"))
    for kind, colour in (("Income", GOLD), ("Wealth", VERMILLION)):
        d = both_lz[both_lz["kind"] == kind]
        fig_iw.add_trace(go.Scatter(x=d["pop_share"] * 100, y=d["cum_share"] * 100, mode="lines+markers",
                                    name=kind, line=dict(color=colour, width=3),
                                    hovertemplate=f"{kind}: poorest %{{x:.1f}}% hold %{{y:.1f}}%<extra></extra>"))
    fig_iw.update_layout(height=400, title=f"Income vs wealth Lorenz curves, {c_year}",
                         xaxis=dict(title="Cumulative % of adults", ticksuffix="%"),
                         yaxis=dict(title="Cumulative % held", ticksuffix="%"), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(chart_source(fig_iw, WIL_SRC), use_container_width=True, key="fin_iw_lorenz")
with col2:
    fig_t = go.Figure()
    for col, name, colour, dash in (("income_top_10", "Income · Top 10%", GOLD, "solid"),
                                    ("wealth_top_10", "Wealth · Top 10%", VERMILLION, "solid"),
                                    ("income_top_1", "Income · Top 1%", GOLD, "dot"),
                                    ("wealth_top_1", "Wealth · Top 1%", VERMILLION, "dot")):
        fig_t.add_trace(go.Scatter(x=cc["year"], y=cc[col], name=name, mode="lines+markers",
                                   line=dict(color=colour, width=2.5, dash=dash), marker=dict(size=5),
                                   hovertemplate=f"{name} %{{x}}: %{{y:.1f}}%<extra></extra>"))
    fig_t.update_layout(height=400, title="Top 10% and Top 1% shares: income vs wealth",
                        yaxis=dict(title="% of total", rangemode="tozero"), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(chart_source(fig_t, WIL_SRC), use_container_width=True, key="fin_iw_tops")
row = cc.set_index("year").loc[c_year]
k1, k2, k3, k4 = st.columns(4)
with k1:
    stat_card(f"Top 10% income share · {c_year}", f"{row['income_top_10']:.1f}%", "WIL Table B.1")
with k2:
    stat_card(f"Top 10% wealth share · {c_year}", f"{row['wealth_top_10']:.1f}%",
              f"{row['top_10_gap_pp']:+.1f} pp vs income")
with k3:
    stat_card(f"Income Gini (lower bound) · {c_year}", f"{row['income_gini_lb']:.3f}", "calculated here")
with k4:
    stat_card(f"Wealth Gini (lower bound) · {c_year}", f"{row['wealth_gini_lb']:.3f}",
              f"{row['gini_gap']:+.3f} vs income")
st.caption(f"Common years: {len(common_years)} ({common_years[0]}–{common_years[-1]}); wealth before 2002 is "
           "survey years only. The 2023 wealth row (tentative) has no income counterpart.")
with st.expander("Table: income vs wealth concentration by year"):
    st.dataframe(cc, hide_index=True, use_container_width=True)
    st.download_button("Download (CSV)", _csv(cc), file_name="wil_income_vs_wealth_concentration.csv",
                       mime="text/csv", key="fin_dl_cc")

callout(
    "**Consumption inequality — DATA REQUIRED.** A comparable consumption-Gini series would need MoSPI's "
    "household consumption survey rounds (HCES / earlier NSS consumer-expenditure rounds) harmonised for "
    "changes in recall period and questionnaire. The project holds one HCES 2023-24 urban MPCE cross-section "
    "by state, which cannot produce a national Gini or a trend.",
    kind="note",
)


# ===========================================================================
# B. Wealth composition
# ===========================================================================
st.header("B · What households hold")
source_badge("Paper A, Table 1", "Shares: RBI (2017)", "Returns 1991–2021: Wahengbam (2023, CSEP)")
comp = F.composition_table(paper_a)
bounds = F.portfolio_return_bounds(paper_a)
b1, b2 = st.columns([1.1, 1])
with b1:
    colours = {"Residential property": VERMILLION, "Gold": GOLD, "Durable goods": MUTED, "Financial assets": COBALT}
    fig_c = go.Figure(go.Bar(
        y=comp["asset"], x=comp["share_pct"], orientation="h",
        marker_color=[colours[a] for a in comp["asset"]],
        text=[f"{v:g}%" for v in comp["share_pct"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:g}% of household assets<extra></extra>",
    ))
    fig_c.update_layout(height=320, title="Average Indian household's assets, by type",
                        xaxis=dict(title="% of household assets", range=[0, 90]),
                        yaxis=dict(autorange="reversed"), showlegend=False)
    st.plotly_chart(chart_source(fig_c, "Paper A Table 1; shares from RBI (2017)"), use_container_width=True,
                    key="fin_comp")
with b2:
    st.dataframe(pd.DataFrame({
        "Asset": comp["asset"], "Share of assets": comp["share_pct"].map(lambda v: f"{v:g}%"),
        "Nominal return, 1991–2021 (per year)": comp["return_text"],
    }), hide_index=True, use_container_width=True)
    st.caption(f"Shares add to {F.composition_sum(comp):g}%. Durable goods have no return figure in the paper "
               "(stated only as negative), so none is plotted — not zero.")
callout(
    "**This is an aggregate composition** — the average across all households, from RBI (2017) — not a breakdown "
    "by household group. It cannot show whether richer households hold more financial assets.",
    kind="note",
)
st.markdown(
    f"**Representative portfolio return.** Paper A states a weighted nominal return of **{bounds['stated']:.1f}%** a "
    f"year (durables excluded, weights renormalised over {bounds['weight_base_pct']:g}%). Because the paper does not "
    f"split the {comp.set_index('asset').loc['Financial assets', 'share_pct']:g}% financial share between deposits "
    f"and equity, the weighted return can only be bounded: **{bounds['lower_all_deposits']:.2f}%** if it were all "
    f"deposits, **{bounds['upper_all_equity']:.2f}%** if all listed equity (calculated here)."
)
indicator_note(
    "the asset composition",
    "**Source.** Paper A, Table 1: shares of household assets from RBI (2017), as cited in the paper, "
    "and long-run nominal returns 1991–2021 from Wahengbam (2023, CSEP). Deposits' 6.5% is the midpoint "
    "of the paper's stated 6–7%.\n\n**Limits.** Returns are long-run averages before costs and taxes, with no "
    "volatility; the composition is a single snapshot for the average household.",
    kind="caveat",
)


def data_required_panel(name: str, title: str, key: str) -> None:
    """DATA REQUIRED box for an upload contract; shows the file only if a
    user has added it and it passes validation."""
    c = UP.CONTRACTS[name]
    df, problems = UP.load(name)
    st.markdown(f"**{title}**")
    if df is None:
        callout(
            f"**DATA REQUIRED — no file in this project, so no figures are shown.** "
            f"Source: {c.publisher} ({c.url}). Series: {c.series}.<br>**Safeguard:** {c.safeguard}",
            kind="warn",
        )
    elif problems:
        st.error(f"`{c.relpath}` is present but fails the loader contract: " + "; ".join(problems))
    else:
        st.success(f"`{c.relpath}` loaded ({len(df):,} rows) — user-supplied; register it in "
                   "data_sources/meta_financialisation.py. **Safeguard:** " + c.safeguard)
        st.dataframe(df, hide_index=True, use_container_width=True, height=240)
    with st.expander(f"Loader contract · {c.relpath}"):
        st.dataframe(pd.DataFrame({"column": list(c.columns), "type": list(c.columns.values()),
                                   "required": ["optional" if k in c.optional else "required" for k in c.columns]}),
                     hide_index=True, use_container_width=True)
        st.download_button("Download empty CSV template (header only)", _csv(UP.template(name)),
                           file_name=c.path.name, mime="text/csv", key=f"fin_tpl_{key}")
        st.caption("Full contract and safeguards: data_sources/financialisation_uploads.py.")


st.subheader("Composition by household group")
data_required_panel("aidis_composition",
                    "Asset composition by asset-holding class — NSS 77th round AIDIS (2019)", "aidis")


# ===========================================================================
# C. Financialisation (live WDI)
# ===========================================================================
st.header("C · Financialisation — live World Bank series")
source_badge("World Bank WDI · API v2", "Global Findex (survey years)", "One request per series")
codes = list(WF.ACCOUNT_CODES) + list(WF.DEPTH_CODES)
results = WF.fetch_each(codes, (WB.INDIA,), int(wdi_start), int(wdi_end),
                        fetch=lambda c, ctry, s, e: _fetch_code(c, ctry, s, e))
wdi_all = WF.combined_frame(results)
status = WF.status_table(results)
wdi_down = WF.all_unreachable(results)
S = {c: F.wdi_series(results[c].frame if results[c].status == WF.OK else None, c) for c in codes}

if wdi_down:
    first_err = next((r.error for r in results.values() if r.status == WF.UNREACHABLE), "")
    st.error(
        f"**{UNAVAILABLE} — the World Bank API could not be reached.** No financial-inclusion or financial-depth "
        "figures are shown rather than stale or placeholder ones. Sections A, B and the WIL parts of D–F still "
        f"work.\n\nDetails: `{first_err}`\n\nTry **Refresh from the API** in the sidebar."
    )
    st.dataframe(pd.DataFrame([{"WDI code": m.code, "Indicator": m.label, "Unit": m.unit,
                                "Definition": m.definition} for m in WF.INDICATORS.values()]),
                 hide_index=True, use_container_width=True)
else:
    retrieved = wdi_all["retrieved_at"].dropna().max() if not wdi_all.empty else None
    st.caption(f"Retrieved {retrieved or '—'} (UTC) · India · {wdi_start}–{wdi_end}. Each series is fetched "
               "separately; a failure affects only that series.")
st.dataframe(status.rename(columns={"code": "WDI code", "indicator": "Indicator", "status": "Status",
                                    "observations": "Observations", "first_year": "First year",
                                    "latest_year": "Latest year", "detail": "Detail"}),
             hide_index=True, use_container_width=True)

if not wdi_down:
    st.subheader("Account ownership (Global Findex)")
    acct_codes = [c for c in WF.ACCOUNT_CODES if not S[c].empty]
    if not acct_codes:
        st.warning(f"{UNAVAILABLE}: no account-ownership series returned observations for {wdi_start}–{wdi_end}.")
    else:
        fig_a = go.Figure()
        acct_colour = dict(zip(WF.ACCOUNT_CODES, (WARM_WHITE, TURQUOISE, VERMILLION, COBALT)))
        for c in acct_codes:
            s = S[c]
            fig_a.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines+markers", name=WF.INDICATORS[c].label,
                                       line=dict(color=acct_colour[c], width=2.5, dash="dot"), marker=dict(size=9),
                                       hovertemplate=f"{WF.INDICATORS[c].label} %{{x}}: %{{y:.1f}}%<extra></extra>"))
        fig_a.update_layout(height=420, title="Account ownership in India, adults 15+ (Findex survey years)",
                            yaxis=dict(title="% of adults (group)", range=[0, 100]),
                            legend=dict(orientation="h", y=-0.18))
        st.plotly_chart(chart_source(fig_a, "World Bank Global Findex via WDI API (live)"),
                        use_container_width=True, key="fin_acct")
        st.caption("Markers are survey years; dotted lines only connect them — no value between surveys is estimated.")
    gap = F.participation_gap(S[WF.RICHEST_60], S[WF.POOREST_40])
    if gap.empty:
        st.info(f"Poorest-40% vs richest-60% gap: {UNAVAILABLE} — needs both series in the same survey year.")
    else:
        fig_gap = go.Figure(go.Bar(x=gap["year"].astype(str), y=gap["gap_pp"], marker_color=GOLD,
                                   text=[f"{v:.1f} pp" for v in gap["gap_pp"]], textposition="outside",
                                   cliponaxis=False, hovertemplate="%{x}: %{y:.1f} pp<extra></extra>"))
        fig_gap.update_layout(height=320, title="Account-ownership gap: richest 60% minus poorest 40%",
                              yaxis_title="percentage points", xaxis=dict(title="Findex survey year", type="category"),
                              showlegend=False)
        st.plotly_chart(chart_source(fig_gap, "World Bank Global Findex via WDI API (live); gap calculated here"),
                        use_container_width=True, key="fin_gap")

    st.subheader("Financial depth")
    depth_codes = [c for c in WF.DEPTH_CODES if not S[c].empty]
    if not depth_codes:
        st.warning(f"{UNAVAILABLE}: no financial-depth series returned observations for {wdi_start}–{wdi_end}.")
    else:
        fig_d = go.Figure()
        for c, colour in zip(WF.DEPTH_CODES, (COBALT, TURQUOISE, GOLD)):
            if c not in depth_codes:
                continue
            s = WF.INDICATORS[c]
            d = results[c].frame
            d = d[d["iso3"] == WB.INDIA].sort_values("year")
            fig_d.add_trace(go.Scatter(x=d["year"], y=d["value"], mode="lines+markers", name=s.label,
                                       line=dict(color=colour, width=2.5), marker=dict(size=4), connectgaps=False,
                                       hovertemplate=f"{s.label} %{{x}}: %{{y:.1f}}% of GDP<extra></extra>"))
        fig_d.update_layout(height=420, title="Private credit and stock-market capitalisation, India (% of GDP)",
                            yaxis=dict(title="% of GDP", rangemode="tozero"), legend=dict(orientation="h", y=-0.18))
        st.plotly_chart(chart_source(fig_d, "World Bank WDI API (live)"), use_container_width=True, key="fin_depth")
        st.caption("Gaps are years the World Bank reports as missing — not filled in.")
    for c in codes:
        m = WF.INDICATORS[c]
        indicator_note(m.label, f"**Definition.** {m.definition}\n\n**Source & caveats.** {m.source_note}\n\n"
                                f"[WDI page for {m.code}]({m.url})")

st.subheader("Mutual funds and demat accounts")
callout(
    "**Counting accounts is not counting people.** Demat accounts ≠ unique investors (one person can hold "
    "several, at one depository or across NSDL and CDSL). Mutual-fund folios ≠ unique people (one investor can "
    "hold many folios). Aggregate SIP inflows are a flow of saving — not a measure of how wealth is distributed.",
    kind="warn",
)
m1, m2 = st.columns(2)
with m1:
    data_required_panel("amfi_folios", "AMFI · mutual-fund folios", "folios")
with m2:
    data_required_panel("amfi_sip", "AMFI · SIP inflows", "sip")
data_required_panel("demat_accounts", "NSDL and CDSL · demat accounts", "demat")


# ===========================================================================
# D. Distributional questions
# ===========================================================================
st.header("D · Distributional questions")

st.subheader("1 · Is financial participation broadening?")
tot = F.change_summary(S["FX.OWN.TOTL.ZS"])
gap = F.participation_gap(S[WF.RICHEST_60], S[WF.POOREST_40])
if tot is None and gap.empty:
    st.warning(f"**{UNAVAILABLE}** — account-ownership series did not load on this run, so this question "
               "cannot be answered here. Nothing is substituted.")
else:
    q1, q2 = st.columns(2)
    with q1:
        if tot is None:
            stat_card("Account ownership, adults 15+", "no data", "fewer than two survey years returned")
        else:
            stat_card("Account ownership, adults 15+", f"{tot['last']:.1f}%",
                      f"{tot['last_year']} · {tot['change']:+.1f} pp since {tot['first_year']}")
    with q2:
        if len(gap) < 2:
            stat_card("Richest 60% − poorest 40% gap", "no data", "needs both groups in two survey years")
        else:
            g0, g1 = gap.iloc[0], gap.iloc[-1]
            stat_card("Richest 60% − poorest 40% gap", f"{g1['gap_pp']:.1f} pp",
                      f"{int(g1['year'])} · {g1['gap_pp'] - g0['gap_pp']:+.1f} pp since {int(g0['year'])}")
st.markdown(
    "**What this can and cannot show.** Account ownership measures *access* — whether an adult has an account. "
    "It does not measure balances, use, or ownership of market-linked assets (shares, mutual funds). A fully "
    "answered question needs the **distribution of financial-asset ownership**: e.g. holdings by wealth group "
    "from AIDIS unit-level data, or unique-investor counts by income group — neither is in this project "
    "(DATA REQUIRED)."
)

st.subheader("2 · Does aggregate financial-market expansion show inclusive wealth creation?")
top_choice = st.radio("Compare market capitalisation with", ["Top 1% wealth share", "Top 10% wealth share"],
                      horizontal=True, key="fin_q2_top")
top_col = "top_1" if top_choice.startswith("Top 1%") else "top_10"
wil_top = wealth_firm.set_index("year")[top_col].astype(float)
mcap = S[WF.MARKET_CAP]
al_mt = F.align_two(mcap, wil_top, int(wdi_start), int(wdi_end), names=("market_cap_pct_gdp", f"wil_wealth_{top_col}"))
ch_mt = F.overlap_change(al_mt)
corr_mt = F.pearson(al_mt)
corr_mt_d = F.pearson(F.first_differences(al_mt), min_n=5)
if mcap.empty:
    st.warning(f"**{UNAVAILABLE}** — market capitalisation (CM.MKT.LCAP.GD.ZS) did not load on this run. "
               f"The WIL {top_choice.lower()} is shown on its own below; no comparison is made.")
both = al_mt[al_mt["both_observed"]]
fig_q2 = go.Figure()
wt = wil_top[(wil_top.index >= wdi_start) & (wil_top.index <= wdi_end)]
fig_q2.add_trace(go.Scatter(x=wt.index, y=wt.values, name=f"WIL {top_choice} (left)", mode="lines+markers",
                            line=dict(color=VERMILLION, width=3),
                            hovertemplate="%{x}: %{y:.1f}% of wealth<extra></extra>"))
if not mcap.empty:
    mc = mcap[(mcap.index >= wdi_start) & (mcap.index <= wdi_end)]
    fig_q2.add_trace(go.Scatter(x=mc.index, y=mc.values, name="Market cap, % of GDP (right)", mode="lines+markers",
                                yaxis="y2", line=dict(color=COBALT, width=2.5), connectgaps=False,
                                hovertemplate="%{x}: %{y:.1f}% of GDP<extra></extra>"))
fig_q2.update_layout(height=420, title=f"Stock-market size vs the WIL {top_choice}, India",
                     yaxis=dict(title="% of net wealth", rangemode="tozero"),
                     yaxis2=dict(title="% of GDP", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
                     legend=dict(orientation="h", y=-0.18))
st.plotly_chart(chart_source(fig_q2, "WIL Table C.1; World Bank WDI API (live)"), use_container_width=True,
                key="fin_q2")
if ch_mt is not None:
    st.markdown(
        f"Over the **{ch_mt['n_common']} years both are observed** ({ch_mt['first_year']}–{ch_mt['last_year']}): "
        f"market capitalisation {ch_mt['a_first']:.1f}% → {ch_mt['a_last']:.1f}% of GDP "
        f"(**{ch_mt['a_change']:+.1f} pp**); WIL {top_choice} {ch_mt['b_first']:.1f}% → {ch_mt['b_last']:.1f}% "
        f"(**{ch_mt['b_change']:+.1f} pp**)."
        + (f" Correlation of levels r = {corr_mt['r']:.2f} (n = {corr_mt['n']})" if corr_mt else
           " Too few overlapping years for a correlation (needs 5)")
        + (f"; of year-on-year changes r = {corr_mt_d['r']:.2f} (n = {corr_mt_d['n']})." if corr_mt_d else ".")
    )
callout(
    "**Timing alignment is not attribution.** Both series are aggregates; a rising stock market and a rising top "
    "wealth share can move together because the top holds most listed equity — or because both respond to growth, "
    "valuations or measurement choices (WIL uses rich lists and valuations for the top). Correlation between two "
    "trending series is weak evidence and is not causation. **To answer properly** one needs the distribution of "
    "financial-asset ownership — who holds listed equity and mutual funds by wealth group — which no aggregate "
    "market series provides (DATA REQUIRED: AIDIS unit-level holdings; depository holdings by holder size).",
    kind="warn",
)
with st.expander("Aligned data used for question 2"):
    st.dataframe(al_mt, hide_index=True, use_container_width=True)
    st.download_button("Download (CSV)", _csv(al_mt), file_name=f"market_cap_vs_wil_{top_col}.csv",
                       mime="text/csv", key="fin_dl_q2")


# ===========================================================================
# E. Compare any two indicators
# ===========================================================================
st.header("E · Compare two indicators")
catalogue = F.wil_catalogue(income, wealth, vhnwi)
for c in codes:
    if not S[c].empty:
        m = WF.INDICATORS[c]
        catalogue[f"WDI · {m.label}"] = {"series": S[c], "unit": m.unit, "source": f"World Bank WDI ({c}), live"}
labels = list(catalogue)
e1, e2 = st.columns(2)
with e1:
    a_lab = st.selectbox("Indicator A (left axis)", labels, index=labels.index("WIL wealth share · Top 1%"),
                         key="fin_cmp_a")
with e2:
    default_b = next((l for l in labels if l.startswith("WDI · Market")), "WIL income share · Top 10%")
    b_lab = st.selectbox("Indicator B (right axis)", labels, index=labels.index(default_b), key="fin_cmp_b")
cmp_years = st.slider("Years", 1951, THIS_YEAR, (1980, THIS_YEAR), key="fin_cmp_years")
if not any(l.startswith("WDI") for l in labels):
    st.caption(f"World Bank series are {UNAVAILABLE} on this run, so only WIL series are offered.")
A, B = catalogue[a_lab], catalogue[b_lab]
aligned = F.align_two(A["series"], B["series"], cmp_years[0], cmp_years[1], names=(a_lab, b_lab))
a_col, b_col = [c for c in aligned.columns if c not in ("year", "both_observed")]
if aligned.empty:
    st.info("Neither indicator has observations in the selected years.")
else:
    fig_e = go.Figure()
    fig_e.add_trace(go.Scatter(x=aligned["year"], y=aligned[a_col], name=f"A · {a_lab}", mode="lines+markers",
                               line=dict(color=GOLD, width=2.5), connectgaps=False,
                               hovertemplate="%{x}: %{y:.3f}<extra>A</extra>"))
    fig_e.add_trace(go.Scatter(x=aligned["year"], y=aligned[b_col], name=f"B · {b_lab}", mode="lines+markers",
                               yaxis="y2", line=dict(color=COBALT, width=2.5), connectgaps=False,
                               hovertemplate="%{x}: %{y:.3f}<extra>B</extra>"))
    fig_e.update_layout(height=440, title=f"{a_lab} vs {b_lab}",
                        yaxis=dict(title=A["unit"]),
                        yaxis2=dict(title=B["unit"], overlaying="y", side="right", showgrid=False),
                        legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(chart_source(fig_e, f"{A['source']}; {B['source']}"), use_container_width=True, key="fin_cmp")
    st.caption("Gaps are years a source does not report; lines are not joined across them and nothing is filled.")
    r_e, ch_e = F.pearson(aligned), F.overlap_change(aligned)
    n_both = int(aligned["both_observed"].sum())
    s1, s2, s3 = st.columns(3)
    with s1:
        stat_card("Years with both observed", f"{n_both}", f"of {len(aligned)} years with either")
    with s2:
        stat_card("Change in A (common years)", "no data" if ch_e is None else f"{ch_e['a_change']:+.3g}",
                  "" if ch_e is None else f"{ch_e['first_year']}–{ch_e['last_year']} · {A['unit']}")
    with s3:
        stat_card("Correlation of levels", "n < 5" if r_e is None else f"r = {r_e['r']:.2f}",
                  "" if r_e is None else f"n = {r_e['n']} · descriptive only")
    st.dataframe(aligned, hide_index=True, use_container_width=True, height=260)
    st.download_button("Download aligned table (CSV)", _csv(aligned), file_name="aligned_comparison.csv",
                       mime="text/csv", key="fin_dl_cmp")
if "tentative" in wealth.columns:
    st.caption("WIL wealth series here exclude the 2023 row, which the authors mark tentative.")

st.markdown("**All data shown on this page**")
dl = st.columns(4)
with dl[0]:
    st.download_button("WIL income shares (B.1)", _csv(income), file_name="wil_tableB1_income_shares.csv",
                       mime="text/csv", key="fin_dl_b1", use_container_width=True)
with dl[1]:
    st.download_button("WIL wealth shares (C.1)", _csv(wealth), file_name="wil_tableC1_wealth_shares.csv",
                       mime="text/csv", key="fin_dl_c1", use_container_width=True)
with dl[2]:
    gini_both = g_inc.rename(columns={"gini_lower_bound": "income_gini_lb"}).merge(
        g_w.rename(columns={"gini_lower_bound": "wealth_gini_lb", "tentative": "wealth_tentative"}),
        on="year", how="outer").sort_values("year")
    st.download_button("Lower-bound Ginis", _csv(gini_both), file_name="wil_lower_bound_gini.csv",
                       mime="text/csv", key="fin_dl_gini", use_container_width=True)
with dl[3]:
    st.download_button("Lorenz points (selected)", _csv(lz), file_name="lorenz_points.csv",
                       mime="text/csv", key="fin_dl_lz", use_container_width=True)
dl2 = st.columns(4)
with dl2[0]:
    st.download_button("Asset composition", _csv(comp), file_name="paperA_asset_composition.csv",
                       mime="text/csv", key="fin_dl_comp", use_container_width=True)
with dl2[1]:
    st.download_button("WDI series (tidy)", _csv(wdi_all), file_name=f"wdi_financial_{wdi_start}_{wdi_end}.csv",
                       mime="text/csv", key="fin_dl_wdi", use_container_width=True, disabled=wdi_all.empty)
with dl2[2]:
    st.download_button("WDI per-series status", _csv(status), file_name="wdi_financial_status.csv",
                       mime="text/csv", key="fin_dl_status", use_container_width=True)
with dl2[3]:
    st.download_button("Account-ownership gap", _csv(gap), file_name="findex_ownership_gap.csv",
                       mime="text/csv", key="fin_dl_gap", use_container_width=True, disabled=gap.empty)


# ===========================================================================
# F. Findings
# ===========================================================================
st.header("F · Findings")
st.caption("Generated from the values computed above on this run — no sentence contains a number that is not "
           "on this page. If a source did not load, the sentence says so.")
_al1 = F.align_two(mcap, wealth_firm.set_index("year")["top_1"].astype(float), int(wdi_start), int(wdi_end))
mv = {"change": F.overlap_change(_al1), "corr": F.pearson(_al1), "corr_diff": F.pearson(F.first_differences(_al1))}
findings = F.build_findings(
    income, wealth, comp,
    account={"total": S["FX.OWN.TOTL.ZS"], "poorest_40": S[WF.POOREST_40], "richest_60": S[WF.RICHEST_60]},
    market_vs_top1=mv, wdi_status=UNAVAILABLE,
)
for section, items in findings.items():
    st.subheader(section)
    if items:
        st.markdown("\n".join(f"- {t}" for t in items))
    else:
        st.markdown("- Nothing can be stated from the data loaded on this run.")

footnote(
    "Status: WIL tables VERIFIED (extracted from the paper); Paper A Table 1 VERIFIED; World Bank series LIVE "
    "(retrieved at run time, verified only on the deployed app); AMFI, NSDL, CDSL, AIDIS-by-group and a "
    "consumption-Gini series are DATA REQUIRED. Lorenz points, Ginis, gaps, changes and correlations are "
    "calculated on this site. See DATA_REGISTRY.md."
)
sources_panel("wil_india", "paper_a", "wdi_financial_inclusion", "wdi_financial_depth", "amfi_mf_folios_sip",
              "nsdl_demat_accounts", "cdsl_demat_accounts", "aidis77_asset_composition", "consumption_gini_series")
