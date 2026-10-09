"""India Macro & World.

India's annual macro series and a short list of peer economies, fetched
live from the World Bank World Development Indicators API (no key). Every
number on this page comes from that live call via data_sources/worldbank.py;
if the call fails, the page says so and shows no numbers -- it never falls
back to stored, typed-in or placeholder values.
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

from analysis import macro_monthly as MM
from data_sources import loaders, worldbank as WB
from app.components.theme import (
    setup, set_chart_source, chart_source, kicker, callout, source_badge, stat_card, footnote, COBALT, SERIES, MUTED,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel

setup("India Macro & World", accent=COBALT)
set_chart_source("MoSPI and RBI releases; World Bank WDI API")

CODES = list(WB.INDICATORS)
LABEL = {c: m.label for c, m in WB.INDICATORS.items()}
THIS_YEAR = date.today().year


@st.cache_data(ttl=6 * 60 * 60, show_spinner="Fetching from the World Bank API…")
def _fetch(codes: tuple[str, ...], countries: tuple[str, ...], start: int, end: int) -> pd.DataFrame:
    # Errors propagate (and are therefore not cached), so a failed call is
    # retried on the next run instead of being remembered as "no data".
    return WB.fetch(codes, countries, start, end)


def fmt(value: float, code: str) -> str:
    if pd.isna(value):
        return "no data"
    unit = WB.INDICATORS[code].unit if code in WB.INDICATORS else ""
    if unit == "current US$":
        return f"${value / 1e9:,.1f} bn"
    if unit.startswith("constant international"):
        return f"${value:,.0f}"
    if unit.startswith("local currency"):
        return f"{value:,.2f}"
    if unit.startswith("index"):
        return f"{value:.1f}"
    return f"{value:.2f}%"


def change_text(row: pd.Series, code: str) -> str:
    if pd.isna(row["previous_value"]):
        return f"{int(row['latest_year'])} · no earlier observation"
    since = f"vs {int(row['previous_year'])}"
    if row["change_kind"] == "pp":
        return f"{int(row['latest_year'])} · {row['pp_change']:+.2f} pp {since}"
    if row["change_kind"] == "level" and pd.notna(row["pct_change"]):
        return f"{int(row['latest_year'])} · {row['pct_change']:+.1f}% {since}"
    return f"{int(row['latest_year'])} · {row['abs_change']:+.2f} pts {since}"


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Macro & World")
    st.caption("Live from the World Bank WDI API")
    start, end = st.slider("Years", 1990, THIS_YEAR, (2000, THIS_YEAR), key="wb_years")
    peers = st.multiselect(
        "Peer economies", list(WB.PEER_COUNTRIES), default=list(WB.DEFAULT_PEERS),
        format_func=lambda c: WB.PEER_COUNTRIES[c], key="wb_peers", max_selections=6,
    )
    if st.button("Refresh from the API", use_container_width=True, key="wb_refresh"):
        _fetch.clear()
        st.rerun()
    st.caption("Results are cached for 6 hours. Refresh forces a new call.")


kicker("India Macro & World")
st.title("India's macro picture, against its peers")
st.markdown(
    "The latest monthly releases first, then annual headline series for India — growth, prices, jobs, the external "
    "account, reserves, the rupee, debt and inequality — and the same series "
    "for comparator economies you choose. Each figure is the World Bank's "
    "published value, retrieved live; the latest year differs by indicator "
    "because each source reports on its own schedule."
)
# ---------------------------------------------------------------------------
# Now · latest monthly releases (stored files -- shown even if the World
# Bank API below is unreachable)
# ---------------------------------------------------------------------------
st.header("Now · India's latest monthly releases")
st.caption(
    "Entered from the official MoSPI and RBI releases and cross-checked against press "
    "coverage; not fetched live. Each figure keeps its status, base year and release type."
)
mm = loaders.load_macro_monthly()
dec = loaders.load_rbi_policy_decisions()
last_dec = MM.latest_decision(dec)
TODAY = pd.Timestamp(date.today())

def _r(ind, per):
    return MM.row(mm, ind, per)

cpi, cpi_prev = _r("CPI_COMBINED_YOY", "2026-08"), _r("CPI_COMBINED_YOY", "2026-07")
iip, iip_prev = _r("IIP_GENERAL_YOY", "2026-08"), _r("IIP_GENERAL_YOY", "2026-07")
e1y, e1y_prev = _r("HH_INFLATION_EXPECTATION_1Y", "2026-09"), _r("HH_INFLATION_EXPECTATION_1Y", "2026-07")
n1, n2, n3, n4 = st.columns(4)
with n1:
    stat_card("CPI inflation · Aug 2026", f"{cpi['value']:.2f}%",
              f"{cpi['release_type']} · base {cpi['base']} · July {cpi_prev['value']:.2f}%")
with n2:
    stat_card("Industrial output (IIP) · Aug 2026", f"{iip['value']:+.1f}%",
              f"{iip['release_type']} · base {iip['base']} · July {iip_prev['value']:+.1f}%")
with n3:
    stat_card("RBI policy repo rate", f"{last_dec['policy_repo_rate_pct']:.2f}%",
              f"{int(last_dec['change_bp']):+d} bp on {last_dec['decision_date']:%d %b %Y} · "
              f"from {last_dec['previous_rate_pct']:.2f}%")
with n4:
    stat_card("Households expect, 1 yr ahead", f"{e1y['value']:.1f}%",
              f"Sep 2026 survey median · July {e1y_prev['value']:.1f}%")

g1, g2 = st.columns(2)
with g1:
    parts = [("General", "IIP_GENERAL_YOY"), ("Manufacturing", "IIP_MANUFACTURING_YOY"),
             ("Electricity & gas", "IIP_ELECTRICITY_YOY"), ("Mining", "IIP_MINING_YOY")]
    vals = [MM.value(mm, code, "2026-08") for _, code in parts]
    ifig = go.Figure(go.Bar(
        x=[p for p, _ in parts], y=vals,
        marker_color=[COBALT if v >= 0 else "#F04A32" for v in vals],
        text=[f"{v:+.1f}%" for v in vals], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:+.1f}% y/y<extra></extra>",
    ))
    ifig.add_hline(y=0, line_color=MUTED, line_width=1)
    ifig.update_layout(height=360, title="IIP growth by sector, Aug 2026 (y/y)", yaxis_title="% y/y",
                       showlegend=False)
    st.plotly_chart(chart_source(ifig, "MoSPI IIP quick estimates, Aug 2026"), use_container_width=True, key="now_iip")
    i_now, i_ago = MM.value(mm, "IIP_GENERAL_INDEX", "2026-08"), MM.value(mm, "IIP_GENERAL_INDEX", "2025-08")
    st.caption(
        f"Check: index {i_now:.1f} vs {i_ago:.1f} a year earlier implies "
        f"{MM.implied_yoy(i_now, i_ago):.2f}% — matches the published {iip['value']:.1f}%. "
        f"April–August cumulative: {MM.value(mm, 'IIP_GENERAL_YOY_CUMULATIVE', 'FY2026-27 Apr-Aug'):.1f}% "
        f"vs {MM.value(mm, 'IIP_GENERAL_YOY_CUMULATIVE', 'FY2025-26 Apr-Aug'):.1f}% a year earlier."
    )
with g2:
    bars = [("Measured CPI\n(Aug 2026)", cpi["value"], "#F3C542"),
            ("Households' view of\ncurrent inflation", MM.value(mm, "HH_INFLATION_PERCEPTION", "2026-09"), MUTED),
            ("Expected,\n3 months ahead", MM.value(mm, "HH_INFLATION_EXPECTATION_3M", "2026-09"), MUTED),
            ("Expected,\n1 year ahead", e1y["value"], MUTED)]
    efig = go.Figure(go.Bar(
        x=[b[0].replace("\n", "<br>") for b in bars], y=[b[1] for b in bars],
        marker_color=[b[2] for b in bars], text=[f"{b[1]:.1f}%" for b in bars],
        textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    efig.update_layout(height=360, title="Measured inflation vs what households report",
                       yaxis=dict(title="%", range=[0, 12]), showlegend=False)
    st.plotly_chart(chart_source(efig, "MoSPI CPI (Aug 2026); RBI Inflation Expectations Survey of Households (Sep 2026)"), use_container_width=True, key="now_expect")
    st.caption(
        "The grey bars are survey medians from the RBI's household survey (Sep 2026, 19 cities) — "
        "sentiment, not an RBI forecast. The gap between them and measured CPI is itself "
        "something the RBI watches."
    )

with st.expander("RBI policy rate — decisions, daily and monthly tables"):
    st.markdown(
        "The rate is stored as **dated decisions**; the daily and monthly tables are built "
        "from them. Only decisions entered so far are used — earlier days are left blank "
        "rather than assumed."
    )
    st.dataframe(dec.assign(decision_date=dec["decision_date"].dt.date,
                            effective_date=dec["effective_date"].dt.date),
                 hide_index=True, use_container_width=True)
    first_day = (last_dec["effective_date"] - pd.Timedelta(days=last_dec["effective_date"].day - 1))
    daily = MM.daily_policy_rate(dec, first_day, TODAY)
    st.caption(f"Daily rate in force, {first_day:%d %b} → {TODAY:%d %b %Y} (blank = no decision loaded yet):")
    st.dataframe(daily.rename_axis("date").reset_index().assign(date=lambda d: d["date"].dt.date),
                 hide_index=True, use_container_width=True, height=220)
    st.dataframe(MM.monthly_policy_rate(daily, TODAY), hide_index=True, use_container_width=True)

cal = MM.calendar_status(loaders.load_release_calendar(), TODAY)
st.markdown("**Coming up**")
st.dataframe(cal.assign(scheduled_release_date=cal["scheduled_release_date"].dt.date),
             hide_index=True, use_container_width=True)

with st.expander("All monthly figures, with status and source"):
    st.dataframe(mm, hide_index=True, use_container_width=True)
    st.download_button("Download (CSV)", mm.to_csv(index=False).encode("utf-8"),
                       file_name="india_macro_monthly.csv", mime="text/csv", key="now_dl")

sources_panel("macro_monthly", "rbi_policy_decisions", "worldbank_wdi")
st.markdown("---")
st.header("India vs the world · annual series")
source_badge("World Bank WDI · API v2", "Annual", "No API key")
callout(
    "<b>These are internationally harmonised series, not India's official "
    "headline releases.</b> WDI unemployment is an ILO modelled estimate (not "
    "PLFS); WDI inflation may not be MOSPI's CPI-Combined; central-government "
    "debt excludes the states. Use them to compare across countries, and "
    "MOSPI/RBI releases for India-only analysis.",
    kind="warn",
)

countries = (WB.INDIA, *peers)
try:
    data = _fetch(tuple(CODES), countries, int(start), int(end))
except WB.WorldBankError as exc:
    kind = (
        "could not be reached" if isinstance(exc, WB.NETWORK_ERRORS)
        else "returned a response this page could not use"
    )
    st.error(
        f"**DATA UNAVAILABLE — the World Bank API {kind}.** No figures are shown "
        "rather than stale or placeholder ones.\n\n"
        f"Details: `{type(exc).__name__}: {exc}`\n\n"
        "Try **Refresh from the API** in the sidebar. If this persists, check "
        "https://data.worldbank.org for an outage."
    )
    st.subheader("What this page shows when the API is reachable")
    st.dataframe(
        pd.DataFrame([
            {"Indicator": m.label, "WDI code": m.code, "Unit": m.unit, "Definition": m.definition}
            for m in WB.INDICATORS.values()
        ]),
        hide_index=True, use_container_width=True,
    )
    st.stop()

if data.empty or data["value"].notna().sum() == 0:
    st.warning("The API answered, but returned no observations for this selection.")
    st.stop()

names = (
    data.dropna(subset=["country"]).drop_duplicates("iso3").set_index("iso3")["country"].to_dict()
)
colour = {iso: SERIES[i % len(SERIES)] for i, iso in enumerate(countries)}
lvp = WB.latest_vs_previous(data)
retrieved = data["retrieved_at"].dropna().max()
updated = data["lastupdated"].dropna().max()
st.caption(
    f"Retrieved {retrieved} (UTC) · World Bank last updated: {updated or 'not reported'} · "
    f"{len(data):,} observations, {int(data['value'].isna().sum()):,} reported as missing."
)


# ---------------------------------------------------------------------------
# A · India snapshot
# ---------------------------------------------------------------------------
st.header("A · India — latest published value")
st.caption("Each card shows the latest non-missing year for that series and the change from the previous one.")
india = lvp[lvp["iso3"] == WB.INDIA].set_index("indicator")
cols = st.columns(4)
for i, code in enumerate(CODES):
    with cols[i % 4]:
        if code in india.index:
            row = india.loc[code]
            stat_card(LABEL[code], fmt(row["latest_value"], code), change_text(row, code))
        else:
            stat_card(LABEL[code], "no data", f"none reported {start}–{end}")

indicator_note(
    "pp vs %", "**Percentage points (pp)** are used for series that are already "
    "rates (growth, inflation, unemployment, ratios to GDP): going from 5% to 6% is "
    "+1 pp. A percent change of a rate (+20% here) is easy to misread, so it is not "
    "shown.\n\n**% change** is used only for positive levels (reserves, GDP per "
    "capita, the exchange rate).\n\n**Points** are used for the Gini index.",
    kind="method",
)


# ---------------------------------------------------------------------------
# B · One indicator over time
# ---------------------------------------------------------------------------
st.header("B · One indicator over time")
code = st.selectbox("Indicator", CODES, format_func=LABEL.get, key="wb_series")
meta = WB.INDICATORS[code]
series = data[data["indicator"] == code]
show_peers = st.toggle("Overlay the selected peers", value=True, key="wb_overlay")

fig = go.Figure()
for iso in countries:
    if iso != WB.INDIA and not show_peers:
        continue
    s = series[series["iso3"] == iso].sort_values("year")
    if s["value"].notna().sum() == 0:
        continue
    fig.add_trace(go.Scatter(
        x=s["year"], y=s["value"], mode="lines+markers", name=names.get(iso, iso),
        line=dict(color=colour[iso], width=3.5 if iso == WB.INDIA else 1.8),
        marker=dict(size=6 if iso == WB.INDIA else 4),
        connectgaps=False,
        hovertemplate=f"{names.get(iso, iso)} %{{x}}: %{{y:,.2f}}<extra></extra>",
    ))
if code in ("NY.GDP.MKTP.KD.ZG", "BN.CAB.XOKA.GD.ZS"):
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
fig.update_layout(height=440, yaxis_title=meta.unit, xaxis_title=None, legend_title_text=None,
                  title=f"{meta.label} ({meta.unit})")
st.plotly_chart(chart_source(fig, "World Bank WDI API"), use_container_width=True, key="wb_line")
st.caption("Gaps in a line are years the World Bank reports as missing — they are not filled in.")
indicator_note(meta.label, f"**Definition.** {meta.definition}\n\n**Source & caveats.** {meta.source_note}\n\n"
               f"[WDI page for {meta.code}]({meta.url})")


# ---------------------------------------------------------------------------
# C · India vs peers, latest year
# ---------------------------------------------------------------------------
st.header("C · India vs peers — latest year for each")
if not peers:
    st.info("Choose at least one peer economy in the sidebar to compare.")
else:
    cmp_code = st.selectbox("Compare on", CODES, format_func=LABEL.get, key="wb_cmp",
                            index=CODES.index(code))
    c = lvp[lvp["indicator"] == cmp_code].set_index("iso3")
    rows = []
    for iso in countries:
        if iso in c.index:
            rows.append((names.get(iso, iso), float(c.loc[iso, "latest_value"]), int(c.loc[iso, "latest_year"]), iso))
        else:
            rows.append((names.get(iso, WB.PEER_COUNTRIES.get(iso, iso)), float("nan"), None, iso))
    rows.sort(key=lambda r: (pd.isna(r[1]), -(r[1] if pd.notna(r[1]) else 0)))
    labels = [f"{n} ({y})" if y else f"{n} (no data)" for n, _, y, _ in rows]
    vals = [v if pd.notna(v) else None for _, v, _, _ in rows]
    bfig = go.Figure(go.Bar(
        y=labels, x=vals, orientation="h",
        marker_color=[colour[iso] for *_, iso in rows],
        text=[fmt(v, cmp_code) for _, v, _, _ in rows], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    bfig.update_layout(height=max(300, 56 * len(rows) + 100), yaxis=dict(autorange="reversed", automargin=True),
                       xaxis_title=WB.INDICATORS[cmp_code].unit, title=LABEL[cmp_code], showlegend=False)
    st.plotly_chart(chart_source(bfig, "World Bank WDI API"), use_container_width=True, key="wb_bar")
    years = {y for _, _, y, _ in rows if y}
    if len(years) > 1:
        st.caption(f"Latest years differ across countries ({min(years)}–{max(years)}), shown in brackets — "
                   "this is not a same-year comparison.")
    if cmp_code == "PA.NUS.FCRF":
        callout("Exchange rates are in each country's own currency per US$, so the bar lengths are not "
                "comparable across countries.", kind="warn")
    if cmp_code == "SI.POV.GINI":
        callout("India's Gini is consumption-based; several peers' are income-based, which tends to "
                "read higher. Compare with care.", kind="warn")


# ---------------------------------------------------------------------------
# D · Data & download
# ---------------------------------------------------------------------------
st.header("D · The data behind this page")
wide = data.pivot_table(index=["country", "year"], columns="indicator", values="value", aggfunc="first",
                        dropna=False).rename(columns=LABEL).reset_index()
st.dataframe(wide.sort_values(["country", "year"], ascending=[True, False]), hide_index=True,
             use_container_width=True, height=360)
d1, d2 = st.columns(2)
with d1:
    st.download_button("Download tidy data (CSV)", data.to_csv(index=False).encode("utf-8"),
                       file_name=f"wdi_{start}_{end}.csv", mime="text/csv", key="wb_dl_tidy",
                       use_container_width=True)
with d2:
    st.download_button("Download latest-vs-previous table (CSV)", lvp.to_csv(index=False).encode("utf-8"),
                       file_name=f"wdi_latest_{start}_{end}.csv", mime="text/csv", key="wb_dl_lvp",
                       use_container_width=True)

with st.expander("Methodology & limitations"):
    st.markdown(
        """
**Source**: World Bank World Development Indicators, API v2 (`api.worldbank.org/v2`), one request per indicator for all selected countries. No key is used and nothing is stored in the repository.

**No fallback**: if any request fails (timeout, network, HTTP error, API error message, or a response that does not match the documented schema) the whole page shows *data unavailable* — partial or cached-from-elsewhere figures are never mixed in. Successful responses are cached for 6 hours.

**Missing values** reported by the API (`null`) stay missing: they appear as gaps in lines, "no data" in cards, and blanks in the table.

**Latest vs previous** compares the two most recent non-missing years for each series, so for survey-based series (Gini) the previous year may be several years earlier.

**Limitations**: annual data only; WDI values are revised between releases; harmonised series can differ from India's official MOSPI/RBI releases (see the warning at the top); India's fiscal-year national accounts are labelled by WDI's own year convention.
"""
    )

footnote(
    "Status: values are retrieved live from the World Bank and labelled with its last-updated date; "
    "this page computes only differences between published values. See DATA_REGISTRY.md."
)
