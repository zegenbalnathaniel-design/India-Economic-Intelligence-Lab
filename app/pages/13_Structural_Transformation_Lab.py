"""Structural Transformation & Productivity Lab.

Where India's workers are, where its output comes from, and how far apart
the two are -- for India and peer economies chosen by the reader. Every
number comes from a live World Bank WDI call (data_sources/worldbank.py)
and the transparent calculations in analysis/structural.py. If the call
fails the page still explains the ideas and the method, and says DATA
UNAVAILABLE wherever a number would have been; it never falls back to
stored or placeholder values. State-level comparisons need files the
repository does not have, so that section is DATA REQUIRED.
"""
from __future__ import annotations

import json
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
from plotly.subplots import make_subplots

from analysis import structural as S
from data_sources import worldbank as WB
from app.components.theme import (
    setup, set_chart_source, kicker, callout, source_badge, stat_card, footnote,
    TURQUOISE, COBALT, GOLD, LEAF, VERMILLION, WARM_WHITE, MUTED,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel

setup("Structural Transformation Lab", accent=TURQUOISE)
set_chart_source("World Bank WDI API (national accounts; ILO modelled estimates); calculations on this site")

THIS_YEAR = date.today().year
FIRST_YEAR = 1991  # ILO modelled employment estimates start in 1991
SECTOR_COLOUR = {"Agriculture": LEAF, "Industry": COBALT, "Services": GOLD}
MANUF_COLOUR = VERMILLION
PEER_COLOURS = [COBALT, GOLD, LEAF, VERMILLION, WARM_WHITE, MUTED]
DEFAULT_PEERS = ("CHN", "IDN", "BGD", "VNM")
LABEL = {c: m.label for c, m in S.INDICATORS.items()}


@st.cache_data(ttl=6 * 60 * 60, show_spinner="Fetching from the World Bank API…")
def _fetch(codes: tuple[str, ...], countries: tuple[str, ...], start: int, end: int) -> pd.DataFrame:
    # Errors propagate (and are therefore not cached), so a failed call is
    # retried on the next run instead of being remembered as "no data".
    return WB.fetch(codes, countries, start, end)


def pct(v: float, nd: int = 1) -> str:
    return "no data" if pd.isna(v) else f"{v:.{nd}f}%"


def unavailable(what: str) -> None:
    st.info(f"**DATA UNAVAILABLE** — {what}. The live World Bank series did not load, so no figures are "
            "shown rather than stale or placeholder ones.")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Structural Lab")
    st.caption("Live from the World Bank WDI API")
    start, end = st.slider("Years", FIRST_YEAR, THIS_YEAR, (FIRST_YEAR, THIS_YEAR), key="st_years")
    peers = st.multiselect(
        "Peer economies", list(WB.PEER_COUNTRIES), default=list(DEFAULT_PEERS),
        format_func=lambda c: WB.PEER_COUNTRIES[c], key="st_peers", max_selections=6,
    )
    if st.button("Refresh from the API", use_container_width=True, key="st_refresh"):
        _fetch.clear()
        st.rerun()
    st.caption("Results are cached for 6 hours. Refresh forces a new call.")
    st.markdown(
        "- 1 · What is structural transformation?\n"
        "- 2 · Output vs employment shares\n"
        "- 3 · Relative labour productivity\n"
        "- 4 · GVA composition & manufacturing\n"
        "- 5 · Participation & vulnerable work\n"
        "- 6 · India vs peers\n"
        "- 7 · States (DATA REQUIRED)\n"
        "- 8 · Findings · 9 · Downloads"
    )

countries = (WB.INDIA, *peers)
colour = {WB.INDIA: TURQUOISE, **{iso: PEER_COLOURS[i % len(PEER_COLOURS)] for i, iso in enumerate(peers)}}

kicker("Structural Transformation & Productivity Lab")
st.title("Where India works, and where its output comes from")
st.markdown(
    "As economies grow, workers and output move out of farming into industry and services. This page "
    "tracks that shift for India and the peer economies you choose: each sector's share of output against "
    "its share of jobs, what the gap says about output per worker, how the composition of value added has "
    "changed, and who is in the labour force at all."
)
source_badge("World Bank WDI · API v2", "ILO modelled estimates", "Annual", "Live")

# ---------------------------------------------------------------------------
# Fetch (one call for every series; all-or-nothing)
# ---------------------------------------------------------------------------
data: pd.DataFrame | None = None
try:
    data = _fetch(S.CODES, countries, int(start), int(end))
except WB.WorldBankError as exc:
    kind = ("could not be reached" if isinstance(exc, WB.NETWORK_ERRORS)
            else "returned a response this page could not use")
    st.error(
        f"**DATA UNAVAILABLE — the World Bank API {kind}.** No figures are shown on this page rather than "
        "stale or placeholder ones; the explanations, method and data requirements below still apply.\n\n"
        f"Details: `{type(exc).__name__}: {exc}`\n\n"
        "Try **Refresh from the API** in the sidebar. If this persists, check https://data.worldbank.org "
        "for an outage."
    )
if data is not None and (data.empty or data["value"].notna().sum() == 0):
    st.warning("**DATA UNAVAILABLE** — the API answered, but returned no observations for this selection.")
    data = None

LIVE = data is not None
if LIVE:
    names = S.country_names(data)
    table = S.sector_table(data)
    retrieved = data["retrieved_at"].dropna().max()
    updated = data["lastupdated"].dropna().max()
    st.caption(
        f"Retrieved {retrieved} (UTC) · World Bank last updated: {updated or 'not reported'} · "
        f"{len(data):,} observations, {int(data['value'].isna().sum()):,} reported as missing · "
        f"years {start}–{end}."
    )
    available = [c for c in countries if c in set(table["iso3"])] or list(countries)
else:
    names, table, available = {}, pd.DataFrame(columns=S.SHARE_COLUMNS), list(countries)


def cname(iso: str) -> str:
    return names.get(iso, WB.PEER_COUNTRIES.get(iso, "India" if iso == WB.INDIA else iso))


# ---------------------------------------------------------------------------
# 1 · Explainer
# ---------------------------------------------------------------------------
st.header("1 · What is structural transformation?")
c1, c2 = st.columns(2)
with c1:
    st.markdown(
        "**Structural transformation** is the reallocation of economic activity — workers, capital and "
        "output — from agriculture towards industry and services as incomes rise. In the classic "
        "dual-economy account (Lewis, 1954), a low-productivity traditional sector holds surplus labour that "
        "a higher-productivity modern sector can absorb; moving a worker across that line raises average "
        "output even if neither sector becomes more productive. McMillan & Rodrik (2011) decompose "
        "economy-wide productivity growth into *within-sector* growth and this *between-sector* "
        "reallocation, and show that reallocation can also run the wrong way."
    )
with c2:
    st.markdown(
        "**Why a sector's output share can differ from its employment share.** If agriculture employs a "
        "large share of workers but produces a smaller share of value added, each farm worker produces "
        "less than the average worker. Typical reasons: less capital and land per worker, seasonal or "
        "disguised underemployment (people counted as employed who work few hours), many own-account and "
        "family workers, and output that is hard to measure (own consumption, informal sales). The ratio of "
        "the two shares is *relative labour productivity* (section 3). It is a ratio of averages: it says "
        "nothing about the most or least productive farms or firms."
    )
callout(
    "**Two measurement facts shape everything below.** (1) Value-added shares are shares of GDP at market "
    "prices, which includes *net taxes on products* — so agriculture + industry + services sum to less than "
    "100. The page shows that sum; it does not quietly rescale it. (2) Employment, participation and "
    "vulnerable-employment series are *ILO modelled estimates*, harmonised across countries — not India's "
    "PLFS figures — and come from a different source than value added.",
    kind="warn",
)

# ---------------------------------------------------------------------------
# 2 · Output vs employment shares
# ---------------------------------------------------------------------------
st.header("2 · Output shares vs employment shares")
if not LIVE:
    unavailable("Output vs employment shares by sector")
    focus, focus_years, fy = WB.INDIA, [], None
else:
    focus = st.selectbox("Economy", available, format_func=cname, key="st_focus",
                         index=available.index(WB.INDIA) if WB.INDIA in available else 0)
    focus_years = S.complete_years(table, focus)
    fy = None
    if not focus_years:
        st.warning(f"**DATA UNAVAILABLE** — no year in {start}–{end} has all three value-added shares and all "
                   f"three employment shares for {cname(focus)}, so no same-year comparison is possible. "
                   "Nothing is interpolated.")
    else:
        fy = (st.select_slider("Year", options=focus_years, value=focus_years[-1], key=f"st_year_{focus}")
              if len(focus_years) > 1 else focus_years[0])
        snap = S.snapshot(table, focus, fy)
        sectors = snap["sector"].tolist()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sectors, y=snap["va_share"], name="Share of GDP (value added)",
                             marker_color=TURQUOISE, text=[pct(v) for v in snap["va_share"]],
                             textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y:.1f}% of GDP<extra></extra>"))
        fig.add_trace(go.Bar(x=sectors, y=snap["emp_share"], name="Share of employment (ILO modelled)",
                             marker_color=WARM_WHITE, text=[pct(v) for v in snap["emp_share"]],
                             textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y:.1f}% of employment<extra></extra>"))
        fig.update_layout(barmode="group", height=420, yaxis_title="%",
                          title=f"{cname(focus)}, {fy}: share of output vs share of jobs by sector",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True, key="st_share_bar")
        cols = st.columns(3)
        for col, (_, r) in zip(cols, snap.iterrows()):
            with col:
                stat_card(f"{r['sector']} · output minus jobs", f"{r['gap_pp']:+.1f} pp",
                          f"{pct(r['va_share'])} of GDP vs {pct(r['emp_share'])} of workers, {fy}")
        st.caption("A negative gap means the sector holds a larger share of workers than of output — "
                   "below-average value added per worker.")

        hist = table[table["iso3"] == focus].sort_values("year")
        sfig = make_subplots(rows=1, cols=3, subplot_titles=list(S.SECTORS), shared_yaxes=True)
        for i, sector in enumerate(S.SECTORS, start=1):
            h = hist[hist["sector"] == sector]
            sfig.add_trace(go.Scatter(x=h["year"], y=h["va_share"], mode="lines+markers", name="Share of GDP",
                                      line=dict(color=TURQUOISE, width=2.5), marker=dict(size=4),
                                      connectgaps=False, showlegend=(i == 1), legendgroup="va",
                                      hovertemplate=f"{sector} %{{x}}: %{{y:.1f}}% of GDP<extra></extra>"),
                           row=1, col=i)
            sfig.add_trace(go.Scatter(x=h["year"], y=h["emp_share"], mode="lines+markers",
                                      name="Share of employment", line=dict(color=WARM_WHITE, width=2, dash="dot"),
                                      marker=dict(size=4), connectgaps=False, showlegend=(i == 1),
                                      legendgroup="emp",
                                      hovertemplate=f"{sector} %{{x}}: %{{y:.1f}}% of employment<extra></extra>"),
                           row=1, col=i)
        sfig.update_layout(height=400, title=f"{cname(focus)}: output and employment shares over time",
                           legend=dict(orientation="h", y=-0.18))
        sfig.update_yaxes(title_text="%", row=1, col=1)
        st.plotly_chart(sfig, use_container_width=True, key="st_share_time")

        gfig = go.Figure()
        for sector in S.SECTORS:
            h = hist[hist["sector"] == sector]
            gfig.add_trace(go.Scatter(x=h["year"], y=h["gap_pp"], mode="lines+markers", name=sector,
                                      line=dict(color=SECTOR_COLOUR[sector], width=2.5), marker=dict(size=4),
                                      connectgaps=False,
                                      hovertemplate=f"{sector} %{{x}}: %{{y:+.1f}} pp<extra></extra>"))
        gfig.add_hline(y=0, line_color=MUTED, line_width=1)
        gfig.update_layout(height=380, yaxis_title="percentage points", legend=dict(orientation="h", y=-0.18),
                           title=f"{cname(focus)}: output share minus employment share (the gap)")
        st.plotly_chart(gfig, use_container_width=True, key="st_gap_time")
        st.caption("Gaps in lines are years where either share is missing — they are not filled in.")
indicator_note(
    "the output–employment gap",
    "**What it is.** A sector's share of GDP (value added) minus its share of employment, in percentage "
    "points, for the same country and year.\n\n**How to read it.** Below zero: the sector has more of the "
    "workforce than of output, so value added per worker is below the economy average. Above zero: the "
    "reverse.\n\n**Caveat.** The value-added shares do not sum to 100 (net taxes on products), so the three "
    "gaps sum to (sum of VA shares − sum of employment shares), a negative number — every sector looks "
    "slightly worse than it would against gross value added.",
)

# ---------------------------------------------------------------------------
# 3 · Relative labour productivity
# ---------------------------------------------------------------------------
st.header("3 · Relative labour productivity by sector")
st.markdown("Derived on this page from the two published shares, for the same country and year:")
st.latex(r"\text{RLP}_s \;=\; \frac{\text{VA}_s / \text{GDP}}{L_s / L} \;=\; "
         r"\frac{\text{VA}_s / L_s}{\text{GDP} / L}")
st.markdown(
    "where VA<sub>s</sub> is the sector's value added and L<sub>s</sub> its employment. An RLP of 0.5 means "
    "a worker in that sector produces half the value added of the average worker. **It is relative to the "
    "economy average, not an absolute productivity level**: a rising RLP can mean the sector improved, or "
    "that the rest of the economy slowed.",
    unsafe_allow_html=True,
)
rescaled = st.toggle("Also show the rescaled version (VA shares rescaled to sum to 100 — derived)",
                     value=False, key="st_rescaled")
if not LIVE:
    unavailable("Relative labour productivity")
elif fy is None:
    st.warning(f"**DATA UNAVAILABLE** — no complete year for {cname(focus)}; no ratio can be computed.")
else:
    snap = S.snapshot(table, focus, fy)
    r0 = snap.iloc[0]
    k1, k2, k3 = st.columns(3)
    with k1:
        stat_card(f"Sum of the 3 VA shares · {fy}", pct(r0["va_sum"]), "agriculture + industry + services, % of GDP")
    with k2:
        stat_card("Residual (100 − sum)", f"{r0['va_residual']:.1f} pp",
                  "mainly net taxes on products — not a sector")
    with k3:
        stat_card(f"Sum of the 3 employment shares · {fy}", pct(r0["emp_sum"]), "should be ~100 (rounding)")
    tbl = pd.DataFrame({
        "Sector": snap["sector"],
        "VA share (% of GDP, published)": snap["va_share"].round(2),
        "Employment share (%, ILO modelled)": snap["emp_share"].round(2),
        "RLP (published basis: vs GDP per worker)": snap["rlp"].round(3),
    })
    if rescaled:
        tbl["VA share rescaled to 3-sector total (%, DERIVED)"] = snap["va_share_rescaled"].round(2)
        tbl["RLP rescaled (vs GVA per worker, DERIVED)"] = snap["rlp_rescaled"].round(3)
    st.dataframe(tbl, hide_index=True, use_container_width=True)

    rfig = go.Figure()
    rfig.add_trace(go.Bar(x=snap["sector"], y=snap["rlp"], name="Published basis (vs GDP per worker)",
                          marker_color=[SECTOR_COLOUR[s] for s in snap["sector"]],
                          text=[f"{v:.2f}" for v in snap["rlp"]], textposition="outside", cliponaxis=False,
                          hovertemplate="%{x}: %{y:.2f}× GDP per worker<extra></extra>"))
    if rescaled:
        rfig.add_trace(go.Bar(x=snap["sector"], y=snap["rlp_rescaled"],
                              name="Rescaled to GVA (DERIVED, vs GVA per worker)", marker_color=MUTED,
                              text=[f"{v:.2f}" for v in snap["rlp_rescaled"]], textposition="outside",
                              cliponaxis=False,
                              hovertemplate="%{x}: %{y:.2f}× GVA per worker (rescaled)<extra></extra>"))
    rfig.add_hline(y=1, line_color=WARM_WHITE, line_width=1, line_dash="dash",
                   annotation_text="1 = economy average", annotation_position="top left")
    rfig.update_layout(barmode="group", height=400, yaxis_title="ratio to economy average",
                       title=f"{cname(focus)}, {fy}: relative labour productivity by sector",
                       legend=dict(orientation="h", y=-0.15), showlegend=rescaled)
    st.plotly_chart(rfig, use_container_width=True, key="st_rlp_bar")
    w_pub = S.weighted_rlp(snap)
    w_res = S.weighted_rlp(snap, rescaled=True)
    st.caption(
        f"Check: the employment-weighted average of the published ratios is {w_pub:.3f} (= sum of VA shares ÷ 100), "
        f"not 1, because GDP includes net taxes on products. On the rescaled basis it is {w_res:.3f} "
        "(= sum of employment shares ÷ 100). Ratios *between* sectors (e.g. services ÷ agriculture) are the "
        "same on both bases."
    )

    hist = table[table["iso3"] == focus].sort_values("year")
    col = "rlp_rescaled" if rescaled else "rlp"
    tfig = go.Figure()
    for sector in S.SECTORS:
        h = hist[hist["sector"] == sector]
        tfig.add_trace(go.Scatter(x=h["year"], y=h[col], mode="lines+markers", name=sector,
                                  line=dict(color=SECTOR_COLOUR[sector], width=2.5), marker=dict(size=4),
                                  connectgaps=False, hovertemplate=f"{sector} %{{x}}: %{{y:.2f}}<extra></extra>"))
    tfig.add_hline(y=1, line_color=MUTED, line_width=1, line_dash="dash")
    basis = "rescaled to GVA (DERIVED)" if rescaled else "published basis"
    tfig.update_layout(height=380, yaxis_title="ratio to economy average", legend=dict(orientation="h", y=-0.18),
                       title=f"{cname(focus)}: relative labour productivity over time ({basis})")
    st.plotly_chart(tfig, use_container_width=True, key="st_rlp_time")
indicator_note(
    "relative labour productivity", "**Formula.** RLP = (sector VA as % of GDP) ÷ (sector employment as % of "
    "total employment), both for the same country and year. Computed only when both exist and employment "
    "share > 0.\n\n**Published basis.** Uses the WDI shares as published: the comparison point is GDP per "
    "worker at market prices, so all three ratios sit slightly low.\n\n**Rescaled basis (optional, labelled "
    "DERIVED).** Each VA share is divided by the sum of the three and multiplied by 100, so the comparison "
    "point becomes gross value added per worker. This assumes net taxes are spread across sectors in "
    "proportion to their value added — a convenience, not a measurement.\n\n**Limits.** Shares are in current "
    "prices, so a sector's RLP moves with its relative prices (e.g. food prices) as well as its output per "
    "worker. VA comes from national accounts and employment from ILO models; the two do not share a sampling "
    "frame. Industry employment includes construction, mining and utilities, so there is no separate "
    "manufacturing ratio here.", kind="method",
)

# ---------------------------------------------------------------------------
# 4 · GVA composition & manufacturing
# ---------------------------------------------------------------------------
st.header("4 · How the composition of value added has changed")
if not LIVE:
    unavailable("Value-added composition over time")
else:
    hist = table[table["iso3"] == focus].sort_values("year")
    va_years = sorted(hist.loc[hist["va_sum"].notna(), "year"].unique().tolist())
    cfig = go.Figure()
    for sector in S.SECTORS:
        h = hist[hist["sector"] == sector]
        cfig.add_trace(go.Scatter(x=h["year"], y=h["va_share"], mode="lines+markers", name=sector,
                                  line=dict(color=SECTOR_COLOUR[sector], width=2.5), marker=dict(size=4),
                                  connectgaps=False, hovertemplate=f"{sector} %{{x}}: %{{y:.1f}}% of GDP<extra></extra>"))
    mser = S.series(data, S.MANUF, focus)
    cfig.add_trace(go.Scatter(x=mser["year"], y=mser["value"], mode="lines", name="of which manufacturing",
                              line=dict(color=MANUF_COLOUR, width=2, dash="dash"), connectgaps=False,
                              hovertemplate="Manufacturing %{x}: %{y:.1f}% of GDP<extra></extra>"))
    sums = hist.drop_duplicates("year")
    cfig.add_trace(go.Scatter(x=sums["year"], y=sums["va_sum"], mode="lines", name="Sum of the 3 sectors",
                              line=dict(color=MUTED, width=1.5, dash="dot"), connectgaps=False,
                              hovertemplate="Sum %{x}: %{y:.1f}% of GDP<extra></extra>"))
    cfig.update_layout(height=420, yaxis_title="% of GDP", legend=dict(orientation="h", y=-0.18),
                       title=f"{cname(focus)}: value added by sector, % of GDP")
    st.plotly_chart(cfig, use_container_width=True, key="st_comp_time")
    st.caption("Manufacturing is part of industry and is drawn separately, not added to the sum. The sum "
               "line is shown only for years with all three sectors; the distance to 100 is net taxes on products "
               "and other adjustments.")
    if len(va_years) >= 2:
        y0, y1 = st.select_slider("Compare two years", options=va_years, value=(va_years[0], va_years[-1]),
                                  key=f"st_comp_years_{focus}")
        ch = S.composition_change(table, focus, int(y0), int(y1))
        st.dataframe(ch.round(2), hide_index=True, use_container_width=True)
        st.caption("Changes are in percentage points of the share; employment cells are blank where the ILO "
                   "series has no value for that year.")
    else:
        st.info("Fewer than two years with all three value-added shares — no change can be computed.")

st.subheader("Manufacturing's share: a question, not a claim")
callout(
    "**Is India deindustrialising prematurely?** Rodrik (2016, *Journal of Economic Growth*) documents that "
    "many developing economies are reaching their peak manufacturing shares at lower incomes than early "
    "industrialisers did. Whether that describes India is an open question this page can inform but not "
    "settle: the series here are *nominal* value-added shares (they fall when manufactured goods get "
    "relatively cheaper, even if real output rises), there is no manufacturing-employment series in this set, "
    "and a 'peak' is only the highest value inside the years you selected.",
    kind="note",
)
if not LIVE:
    unavailable("Manufacturing-share trajectory")
else:
    mfig = go.Figure()
    for iso in countries:
        s = S.series(data, S.MANUF, iso)
        if s.empty:
            continue
        mfig.add_trace(go.Scatter(x=s["year"], y=s["value"], mode="lines+markers", name=cname(iso),
                                  line=dict(color=colour[iso], width=3.5 if iso == WB.INDIA else 1.8),
                                  marker=dict(size=5 if iso == WB.INDIA else 3), connectgaps=False,
                                  hovertemplate=f"{cname(iso)} %{{x}}: %{{y:.1f}}% of GDP<extra></extra>"))
    mfig.update_layout(height=420, yaxis_title="% of GDP", legend=dict(orientation="h", y=-0.18),
                       title="Manufacturing value added, % of GDP")
    st.plotly_chart(mfig, use_container_width=True, key="st_manuf_time")
    prow = []
    for iso in countries:
        p = S.peak_and_latest(data, S.MANUF, iso)
        if p is None:
            prow.append({"Economy": cname(iso), "Highest in window": "no data"})
            continue
        prow.append({"Economy": cname(iso), "First": f"{p['first_value']:.1f}% ({p['first_year']})",
                     "Highest in window": f"{p['peak_value']:.1f}% ({p['peak_year']})",
                     "Latest": f"{p['latest_value']:.1f}% ({p['latest_year']})",
                     "Latest − highest (pp)": round(p["change_from_peak_pp"], 1)})
    st.dataframe(pd.DataFrame(prow), hide_index=True, use_container_width=True)

    pfig = go.Figure()
    for iso in countries:
        w = S.panel(data[data["iso3"] == iso], [S.GDP_PER_WORKER, S.MANUF]).dropna().reset_index()
        if w.empty:
            continue
        pfig.add_trace(go.Scatter(x=w[S.GDP_PER_WORKER], y=w[S.MANUF], mode="lines+markers", name=cname(iso),
                                  line=dict(color=colour[iso], width=3 if iso == WB.INDIA else 1.5),
                                  marker=dict(size=5), text=w["year"],
                                  hovertemplate=f"{cname(iso)} %{{text}}: $%{{x:,.0f}} per worker, "
                                                "%{y:.1f}% of GDP<extra></extra>"))
    pfig.update_layout(height=440, xaxis=dict(type="log", title="GDP per person employed, constant PPP $ (log scale)"),
                       yaxis_title="manufacturing VA, % of GDP", legend=dict(orientation="h", y=-0.2),
                       title="Manufacturing share against output per worker (paths over the selected years)")
    st.plotly_chart(pfig, use_container_width=True, key="st_manuf_path")
    st.caption("Each point is a year in which both series exist; at what output per worker each path turns "
               "down is the comparison the premature-deindustrialisation question is about.")

# ---------------------------------------------------------------------------
# 5 · Participation and vulnerable employment
# ---------------------------------------------------------------------------
st.header("5 · Who is in the labour force, and in what kind of work")
callout("All three series in this section are **ILO modelled estimates**. For India they are not the PLFS "
        "figures published by MoSPI and can differ from them materially, including in recent trend.",
        kind="warn")
if not LIVE:
    unavailable("Labour force participation and vulnerable employment")
else:
    lfp = S.lfp_table(data)
    a, b = st.columns(2)
    with a:
        lf = lfp[lfp["iso3"] == focus].sort_values("year")
        lfig = go.Figure()
        lfig.add_trace(go.Scatter(x=lf["year"], y=lf["male"], mode="lines+markers", name="Men 15+",
                                  line=dict(color=COBALT, width=2.5), marker=dict(size=4), connectgaps=False,
                                  hovertemplate="Men %{x}: %{y:.1f}%<extra></extra>"))
        lfig.add_trace(go.Scatter(x=lf["year"], y=lf["female"], mode="lines+markers", name="Women 15+",
                                  line=dict(color=GOLD, width=2.5), marker=dict(size=4), connectgaps=False,
                                  hovertemplate="Women %{x}: %{y:.1f}%<extra></extra>"))
        lfig.update_layout(height=400, yaxis=dict(title="% of population 15+", range=[0, 100]),
                           legend=dict(orientation="h", y=-0.18),
                           title=f"{cname(focus)}: labour force participation by sex (ILO modelled)")
        st.plotly_chart(lfig, use_container_width=True, key="st_lfp_focus")
        last = lf.dropna(subset=["female", "male"])
        if not last.empty:
            r = last.iloc[-1]
            st.caption(f"{int(r['year'])}: women {r['female']:.1f}%, men {r['male']:.1f}% — gap {r['gap_pp']:.1f} pp.")
    with b:
        ffig = go.Figure()
        for iso in countries:
            s = lfp[lfp["iso3"] == iso].dropna(subset=["female"]).sort_values("year")
            if s.empty:
                continue
            ffig.add_trace(go.Scatter(x=s["year"], y=s["female"], mode="lines", name=cname(iso),
                                      line=dict(color=colour[iso], width=3.5 if iso == WB.INDIA else 1.8),
                                      connectgaps=False,
                                      hovertemplate=f"{cname(iso)} %{{x}}: %{{y:.1f}}%<extra></extra>"))
        ffig.update_layout(height=400, yaxis=dict(title="% of women 15+", range=[0, 100]),
                           legend=dict(orientation="h", y=-0.18),
                           title="Female labour force participation, India and peers (ILO modelled)")
        st.plotly_chart(ffig, use_container_width=True, key="st_lfp_peers")

    vfig = go.Figure()
    for iso in countries:
        s = S.series(data, S.VULNERABLE, iso)
        if s.empty:
            continue
        vfig.add_trace(go.Scatter(x=s["year"], y=s["value"], mode="lines", name=cname(iso),
                                  line=dict(color=colour[iso], width=3.5 if iso == WB.INDIA else 1.8),
                                  connectgaps=False, hovertemplate=f"{cname(iso)} %{{x}}: %{{y:.1f}}%<extra></extra>"))
    vfig.update_layout(height=400, yaxis=dict(title="% of total employment", range=[0, 100]),
                       legend=dict(orientation="h", y=-0.18),
                       title="Vulnerable employment: own-account and contributing family workers (ILO modelled)")
    st.plotly_chart(vfig, use_container_width=True, key="st_vuln")
indicator_note(
    "vulnerable employment",
    "**What it is.** Own-account workers plus contributing family workers, as a share of all employed — "
    "people less likely to have a formal contract, a regular wage or social protection.\n\n**How to read it.** "
    "It usually falls as workers move from farms and household enterprises into wage jobs, so it is one lens "
    "on the *quality* of structural change, not just its direction.\n\n**Caveat.** It is a status-in-employment "
    "measure: a salaried informal worker is not counted as vulnerable, and a prosperous self-employed "
    "professional is.",
)

# ---------------------------------------------------------------------------
# 6 · India vs peers
# ---------------------------------------------------------------------------
st.header("6 · India vs peers: farm jobs against output per worker")
if not LIVE:
    unavailable("India vs peers comparison")
elif not peers:
    st.info("Choose at least one peer economy in the sidebar to compare.")
else:
    pair = S.latest_pair(data, S.GDP_PER_WORKER, "SL.AGR.EMPL.ZS")
    show_paths = st.toggle("Show each economy's path over the selected years", value=True, key="st_paths")
    xfig = go.Figure()
    for iso in countries:
        if show_paths:
            w = S.panel(data[data["iso3"] == iso], [S.GDP_PER_WORKER, "SL.AGR.EMPL.ZS"]).dropna().reset_index()
            if len(w) > 1:
                xfig.add_trace(go.Scatter(x=w[S.GDP_PER_WORKER], y=w["SL.AGR.EMPL.ZS"], mode="lines",
                                          line=dict(color=colour[iso], width=1.2), opacity=0.6, showlegend=False,
                                          text=w["year"], hovertemplate=f"{cname(iso)} %{{text}}<extra></extra>"))
        p = pair[pair["iso3"] == iso]
        if p.empty:
            continue
        r = p.iloc[0]
        xfig.add_trace(go.Scatter(x=[r["x"]], y=[r["y"]], mode="markers+text", name=f"{cname(iso)} ({r['year']})",
                                  marker=dict(color=colour[iso], size=16 if iso == WB.INDIA else 11,
                                              line=dict(color=WARM_WHITE, width=1)),
                                  text=[cname(iso)], textposition="top center",
                                  hovertemplate=f"{cname(iso)} {r['year']}: $%{{x:,.0f}} per worker, "
                                                "%{y:.1f}% of workers in agriculture<extra></extra>"))
    xfig.update_layout(height=480, xaxis=dict(type="log", title="GDP per person employed, constant PPP $ (log scale)"),
                       yaxis=dict(title="employment in agriculture, % of total (ILO modelled)"),
                       legend=dict(orientation="h", y=-0.2),
                       title="Agriculture's share of jobs against GDP per person employed")
    st.plotly_chart(xfig, use_container_width=True, key="st_peer_scatter")
    if not pair.empty:
        yrs = set(pair["year"])
        if len(yrs) > 1:
            st.caption(f"Latest common years differ across economies ({min(yrs)}–{max(yrs)}, in the legend) — "
                       "within each economy both values are from the same year.")
        rows = []
        for iso in countries:
            yrs_i = S.complete_years(table, iso)
            snap_i = S.snapshot(table, iso, yrs_i[-1]) if yrs_i else None
            pr = pair[pair["iso3"] == iso]
            rows.append({
                "Economy": cname(iso),
                "Agri. employment % (year)": f"{pr.iloc[0]['y']:.1f} ({pr.iloc[0]['year']})" if not pr.empty else "no data",
                "GDP per person employed, PPP $": f"{pr.iloc[0]['x']:,.0f}" if not pr.empty else "no data",
                "Agri. RLP (latest complete year)": (f"{snap_i.iloc[0]['rlp']:.2f} ({int(snap_i.iloc[0]['year'])})"
                                                     if snap_i is not None else "no data"),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    ppp_names = data.loc[data["indicator"] == S.GDP_PER_WORKER, "indicator_name"].dropna().unique()
    if len(ppp_names):
        st.caption(f"PPP basis as named by the API: *{ppp_names[0]}*.")

# ---------------------------------------------------------------------------
# 7 · States: DATA REQUIRED
# ---------------------------------------------------------------------------
st.header("7 · State-level industrialisation and productivity")
st.error(
    "**DATA REQUIRED — no state figures are shown.** This repository has state per-capita income (NSDP) and a "
    "single PLFS unemployment cross-section, but **no state-wise value added by sector and no state-wise "
    "employment by industry**. Nothing on this page estimates or proxies them."
)
st.markdown(
    """
Two files would enable state comparisons of output shares, employment shares and relative labour productivity:

| Proposed file | What it must contain | Where it is published |
|---|---|---|
| `data/raw/state_structural/state_gsva_by_sector.csv` | `state, financial_year, sector, gsva_crore, price_basis, base_year, source_table` — gross state value added by industry of origin (at least agriculture, forestry & fishing; mining; manufacturing; construction; electricity, gas & water; services), constant 2011-12 prices | MoSPI state-wise GSVA (compiled from state Directorates of Economics & Statistics), reproduced in the RBI *Handbook of Statistics on Indian States* |
| `data/raw/state_structural/plfs_state_workers_by_industry.csv` | `state, survey_year, sector, workers_pct, status_basis, area` — percentage distribution of workers by broad industry (NIC-2008), usual status (principal + subsidiary), rural + urban | MoSPI *Periodic Labour Force Survey* annual reports, state-wise tables |

**Before the comparison could be shown:** each file needs a registry record (`data_sources/meta_*.py`) with its
exact source table and release; sector definitions must be mapped explicitly between national-accounts
industries and NIC-2008 sections; and PLFS survey years (July–June) must be paired with financial years
(April–March) by a stated rule, not silently. State RLP would then be GSVA share ÷ worker share within each
state, with the same caveats as section 3.
"""
)

# ---------------------------------------------------------------------------
# 8 · Findings
# ---------------------------------------------------------------------------
st.header("8 · Auto-generated findings")
if not LIVE:
    unavailable("Findings")
else:
    st.caption(f"Generated from the fetched values for {cname(focus)}, {start}–{end}, by fixed rules "
               "(analysis/structural.py · findings). A sentence appears only if every number it needs exists.")
    fs = S.findings(data, focus)
    if fs:
        st.markdown("\n".join(f"- {f}" for f in fs))
    else:
        st.info(f"No finding could be generated: the selected years hold too few observations for {cname(focus)}.")
    st.caption("Descriptive statements about published estimates — not causal claims or forecasts.")

# ---------------------------------------------------------------------------
# 9 · Downloads
# ---------------------------------------------------------------------------
st.header("9 · The data behind this page")
if not LIVE:
    unavailable("Downloads")
else:
    settings = {
        "page": "Structural Transformation Lab",
        "source": "World Bank WDI API v2",
        "years": [int(start), int(end)],
        "countries": list(countries),
        "focus_economy": focus,
        "snapshot_year": int(fy) if fy is not None else None,
        "rlp_rescaled_shown": bool(rescaled),
        "retrieved_at_utc": str(retrieved),
        "wdi_lastupdated": str(updated) if updated else None,
        "indicators": list(S.CODES),
    }
    wide = data.pivot_table(index=["country", "year"], columns="indicator", values="value", aggfunc="first",
                            dropna=False).reset_index()
    st.dataframe(wide.sort_values(["country", "year"], ascending=[True, False]), hide_index=True,
                 use_container_width=True, height=320)
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "Fetched data (CSV)",
            S.csv_with_header(data, settings, "WDI observations as fetched (tidy)").encode("utf-8"),
            file_name=f"structural_wdi_{start}_{end}.csv", mime="text/csv", key="st_dl_raw",
            use_container_width=True)
    with d2:
        st.download_button(
            "Derived sector table (CSV)",
            S.csv_with_header(table, settings, "Derived: shares, gaps, sums, relative labour productivity "
                                               "(rlp = va_share / emp_share; *_rescaled = DERIVED rescaling)").encode("utf-8"),
            file_name=f"structural_derived_{start}_{end}.csv", mime="text/csv", key="st_dl_derived",
            use_container_width=True)
    with d3:
        st.download_button(
            "Settings (JSON)", json.dumps(S.settings_record(settings), indent=2).encode("utf-8"),
            file_name=f"structural_settings_{start}_{end}.json", mime="application/json", key="st_dl_json",
            use_container_width=True)
    st.caption("CSV files start with `#` lines recording the settings; read them with "
               "`pandas.read_csv(path, comment='#')`.")

# ---------------------------------------------------------------------------
# 10 · Method
# ---------------------------------------------------------------------------
st.header("Method, indicators and limitations")
st.dataframe(
    pd.DataFrame([{"Indicator": m.label, "WDI code": m.code, "Unit": m.unit, "Definition": m.definition}
                  for m in S.INDICATORS.values()]),
    hide_index=True, use_container_width=True,
)
with st.expander("Methodology & limitations"):
    st.markdown(
        """
**Source.** World Bank World Development Indicators, API v2, one request per indicator for all selected economies, via `data_sources/worldbank.py`. Value-added shares come from national accounts; employment, participation and vulnerable employment are ILO modelled estimates. Nothing is stored in the repository.

**No fallback.** If any request fails, the page shows DATA UNAVAILABLE and no numbers — partial or stored figures are never mixed in. Successful responses are cached for 6 hours.

**Same country, same year.** Every derived value (gap, sum, relative productivity) uses observations for one economy in one year. Missing values stay missing; nothing is interpolated or carried forward.

**Sums are shown, not hidden.** Value-added shares are of GDP at market prices and sum to less than 100 because of net taxes on products. The rescaled version (shares of the three-sector total) is optional and labelled DERIVED.

**Limitations.** Shares are nominal, so they reflect relative prices as well as volumes. ILO modelled employment for India differs from PLFS. National-accounts years for India follow a fiscal-year convention and ILO data a calendar year, so the same year label may not cover exactly the same twelve months. Industry employment includes construction, mining and utilities — there is no manufacturing employment or manufacturing productivity here. Relative productivity is an average ratio, silent on distribution within sectors.

**References.** Lewis, W. A. (1954), "Economic Development with Unlimited Supplies of Labour", *The Manchester School* 22(2). McMillan, M. & Rodrik, D. (2011), "Globalization, Structural Change and Productivity Growth", NBER Working Paper 17143. Rodrik, D. (2016), "Premature deindustrialization", *Journal of Economic Growth* 21(1).
"""
    )

sources_panel("wdi_structural", "worldbank_wdi", "state_sectoral_gva", "plfs_state_industry")
footnote(
    "Status: World Bank values are retrieved live and labelled with the API's last-updated date; this page "
    "computes only gaps, sums and ratios between published values. State sectoral data: DATA REQUIRED. "
    "See DATA_REGISTRY.md."
)
