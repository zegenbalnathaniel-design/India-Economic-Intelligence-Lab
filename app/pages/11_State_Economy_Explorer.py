"""State Economy Explorer.

One place to look up any Indian state or UT across every real state-level
indicator in this repository: a per-state profile, side-by-side
comparison, a full ranking, and first-vs-latest change for the series that
have more than one year. All values come from analysis/states.py, which
reads data/raw/ through data_sources/loaders.py -- nothing on this page is
estimated, filled or typed in.
"""
from __future__ import annotations

import sys
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

from analysis import states as S
from app.components.theme import (
    setup, kicker, callout, source_badge, footnote, GOLD, LEAF, MUTED,
)
from app.components.glossary import indicator_note

setup("State Economy Explorer", accent=LEAF)

UNIT_TEXT = {
    "₹": "₹ per person, per year",
    "₹/month": "₹ per person, per month",
    "%": "% of labour force",
}


@st.cache_data(show_spinner=False)
def _load():
    panel = S.build_panel()
    bms = S.national_benchmarks()
    return panel, bms, S.inventory(panel, bms)


panel, benchmarks, inv = _load()
ALL_STATES = S.states_in_panel(panel)
IND_KEYS = list(S.INDICATORS)
LABEL = {k: m.label for k, m in S.INDICATORS.items()}
MULTI_YEAR = [k for k in IND_KEYS if len(S.periods_for(panel, k)) >= 2]


def fmt(value, unit: str) -> str:
    return S.format_value(value, unit)


def badge(text: str) -> str:
    return f"<span class='source-badge'>{text}</span>"


def bar_with_gaps(categories, values, unit, *, highlight=None, horizontal=False, benchmark=None,
                  benchmark_label="", title="", height=380):
    """Bar chart that keeps every category: missing values get a visible
    'no data' label instead of a bar (and are never drawn as 0)."""
    colours = [LEAF if (highlight is None or c == highlight) else MUTED for c in categories]
    texts = [fmt(v, unit) if pd.notna(v) else "" for v in values]
    ys = [v if pd.notna(v) else None for v in values]
    fig = go.Figure()
    if horizontal:
        fig.add_trace(go.Bar(y=categories, x=ys, orientation="h", marker_color=colours, text=texts,
                             textposition="outside", cliponaxis=False, name="value",
                             hovertemplate="%{y}: %{text}<extra></extra>"))
    else:
        fig.add_trace(go.Bar(x=categories, y=ys, marker_color=colours, text=texts, textposition="outside",
                             cliponaxis=False, name="value", hovertemplate="%{x}: %{text}<extra></extra>"))
    missing = [c for c, v in zip(categories, values) if pd.isna(v)]
    if missing:
        if horizontal:
            fig.add_trace(go.Scatter(y=missing, x=[0] * len(missing), mode="text", text=["no data"] * len(missing),
                                     textposition="middle right", textfont=dict(color=MUTED), showlegend=False,
                                     hoverinfo="skip"))
        else:
            fig.add_trace(go.Scatter(x=missing, y=[0] * len(missing), mode="text", text=["no data"] * len(missing),
                                     textposition="top center", textfont=dict(color=MUTED), showlegend=False,
                                     hoverinfo="skip"))
    if benchmark is not None:
        if horizontal:
            fig.add_vline(x=benchmark, line_dash="dash", line_color=GOLD,
                          annotation_text=benchmark_label, annotation_font_color=GOLD)
        else:
            fig.add_hline(y=benchmark, line_dash="dash", line_color=GOLD,
                          annotation_text=benchmark_label, annotation_font_color=GOLD)
    fig.update_layout(title=title, height=height, showlegend=False,
                      xaxis_title="" if not horizontal else unit, yaxis_title=unit if not horizontal else "")
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    return fig


# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## State Economy Explorer")
    st.caption("Sections")
    st.markdown(
        "- Indicator inventory\n"
        "- A · State lookup\n"
        "- B · Compare states\n"
        "- C · Rank all states\n"
        "- D · Change over time"
    )
    st.markdown("---")
    st.caption(
        "Status labels follow DATA_REGISTRY.md: VERIFIED (source confirmed), PARTIAL "
        "(real, source or coverage not fully confirmed), SPLICED (two real base-year "
        "series linked by a documented factor)."
    )

kicker("STATE ECONOMY EXPLORER · INDIA")
st.title("Every real state indicator, in one place")
st.markdown(
    f"Look up any of **{len(ALL_STATES)} states and union territories** across the "
    f"**{len(IND_KEYS)} state-level indicators** this repository holds — output per person, "
    "unemployment and urban consumption — then compare, rank and track them. Every number "
    "is read straight from a file in `data/raw/`. Where a source has no value, the page "
    "says **no data** and why; it never shows a zero in its place."
)
source_badge("RBI Handbook of Statistics on Indian States", "RBI DBIE", "PLFS 2023-24",
             "MoSPI HCES 2023-24", "VERIFIED / PARTIAL / SPLICED")

# ---------- Inventory ------------------------------------------------------
st.header("Indicator inventory")
st.markdown(
    "What exists, for which years, for how many states/UTs, and whether the source itself "
    "supplies a national figure. National benchmarks are shown **only** where the source "
    "file has an India / All-India row; none is computed here, because none of these files "
    "includes the population weights a national average would need."
)
inv_view = inv.assign(
    period=lambda d: d.apply(lambda r: r.first_period if r.first_period == r.last_period
                             else f"{r.first_period} → {r.last_period}", axis=1),
)[["label", "period", "n_periods", "n_states", "unit", "status", "national_benchmark", "source", "source_file"]]
inv_view.columns = ["Indicator", "Period", "Years", "States/UTs with data", "Unit", "Status",
                    "National benchmark", "Source", "File"]
st.dataframe(inv_view, hide_index=True, use_container_width=True)
callout(
    "<b>Two NSDP current-price vintages.</b> The RBI table (2011-12 → 2024-25) and the older "
    "<code>state_gsdp_nsdp_percapita.csv</code> disagree by ~1-2% for about 20 states in "
    "2023-24 and 2024-25 — consistent with two different release vintages. Both are shown as "
    "separate indicators so the disagreement stays visible. <b>Delhi and Puducherry</b> are "
    "missing from the RBI current-price table (their rows were transcribed with 13 of 14 "
    "values and kept unmerged). The constant-price series is a <b>splice</b> of the 2004-05 "
    "and 2011-12 base years. Urban MPCE is <b>consumption, not income</b>.",
    kind="warn",
)
st.caption(
    "Map view: no India state-boundary file (GeoJSON) exists in this repository, so there is "
    "no choropleth here. A map is a possible future addition once a boundary file with its own "
    "documented source is added."
)

with st.expander("Which files were checked, and which were left out"):
    st.markdown(
        "Every file in `data/raw/` was checked for state-level data.\n\n"
        "- **Used:** the eight indicators above, from five files.\n"
        "- **Not used as a separate indicator:** "
        "`percapita_nsdp_constant_prices_2004_05_to_2022_23.csv` (the as-published RBI Table 26). "
        "From 2011-12 on it is identical to the spliced series; before that it is the unlinked "
        "2004-05-base values, which are not comparable with later years without the link factor. "
        "It reports Jammu & Kashmir under two territorial definitions (incl. Ladakh to 2018-19; "
        "UT from 2019-20), which is why J&K has no constant-price series here. "
        f"{S.JK_TERRITORY_NOTE}\n"
        "- **Not used:** `nsdp_current_prices_delhi_puducherry_UNALIGNED.csv` (13 values for 14 "
        "years — which year is missing is unknown); `nsdp_splice_link_factors.csv` (method "
        "audit, not an indicator).\n"
        "- **Not state-level:** institutional-sector gross capital formation (national, by "
        "sector), real per-capita NNI, GDP CAGR, the HPI/NNI summary, RESIDEX (city-level), "
        "bank earnings."
    )

st.subheader("What each indicator measures")
g1, g2 = st.columns(2)
for i, (key, meta) in enumerate(S.INDICATORS.items()):
    with (g1 if i % 2 == 0 else g2):
        indicator_note(meta.label, meta.explainer)

st.markdown("---")

# ---------- A. State lookup -------------------------------------------------
st.header("A · State lookup")
default_state = ALL_STATES.index("Kerala") if "Kerala" in ALL_STATES else 0
state = st.selectbox("State or union territory", ALL_STATES, index=default_state, key="lookup_state")
profile = S.state_profile(panel, state, benchmarks)
n_with = int(profile["value"].notna().sum())
st.caption(
    f"{state}: data in {n_with} of {len(IND_KEYS)} indicators. Each card shows the state's most "
    "recent non-blank value; its rank is among the states/UTs that report that same year "
    "(1 = highest value — for unemployment that means the highest rate)."
)

cols = st.columns(2)
for i, r in enumerate(profile.itertuples(index=False)):
    with cols[i % 2]:
        if pd.isna(r.value):
            sub = (f"<b>no data</b> — {r.missing_reason}<br>"
                   f"{badge(r.status)}<br><span>Source: {r.source}</span>")
            value_html = "no data"
        else:
            if pd.notna(r.benchmark):
                diff = (r.value / r.benchmark - 1) * 100
                bm_line = (f"National ({r.period}, from source): {fmt(r.benchmark, r.unit)} "
                           f"— state is {abs(diff):.0f}% {'above' if diff >= 0 else 'below'}")
            else:
                bm_line = S.NO_BENCHMARK
            note = f"<br><i>{r.note}</i>" if r.note else ""
            sub = (f"{r.period} · {UNIT_TEXT.get(r.unit, r.unit)}<br>"
                   f"Rank <b>{int(r.rank)}</b> of {int(r.n_reporting)} states/UTs reporting {r.period}<br>"
                   f"{bm_line}<br>{badge(r.status)}{note}<br><span>Source: {r.source}</span>")
            value_html = fmt(r.value, r.unit)
        st.markdown(
            f"<div class='stat' style='margin-bottom:.8rem'><div class='label'>{r.label}</div>"
            f"<div class='value'>{value_html}</div><div class='sub'>{sub}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ---------- B. Compare states -----------------------------------------------
st.header("B · Compare states side by side")
default_cmp = [s for s in ["Bihar", "Delhi", "Kerala", "Maharashtra"] if s in ALL_STATES]
b1, b2 = st.columns([1.3, 1])
with b1:
    cmp_states = st.multiselect("States/UTs to compare (2 or more)", ALL_STATES, default=default_cmp,
                                key="cmp_states")
with b2:
    cmp_inds = st.multiselect("Indicators", IND_KEYS, default=IND_KEYS, format_func=LABEL.get,
                              key="cmp_inds")
basis = st.radio(
    "Which year to compare",
    ["common", "own_latest"],
    format_func={"common": "Same year for all (latest year any selected state reports)",
                 "own_latest": "Each state's own latest year (years may differ)"}.get,
    horizontal=True, key="cmp_basis",
)
indicator_note(
    "the comparison year setting", "**Same year for all** compares like with like: for each "
    "indicator it takes the latest year in which at least one selected state has a value and "
    "shows every state for that year, so a state whose figure for that year is not yet "
    "published shows **no data** rather than an older number. **Each state's own latest** "
    "fills that gap with the state's most recent value — useful for a quick profile, but the "
    "period column then differs between states, and values from different years should not "
    "be read as a ranking.", kind="method",
)

if len(cmp_states) < 2:
    st.warning("Select at least two states/UTs to compare.")
elif not cmp_inds:
    st.warning("Select at least one indicator.")
else:
    cmp = S.compare_states(panel, cmp_states, cmp_inds, basis=basis)
    cmp["shown"] = [
        (fmt(v, u) + f" ({p})") if pd.notna(v) else "no data"
        for v, u, p in zip(cmp["value"], cmp["unit"], cmp["period"])
    ]
    wide = cmp.pivot(index="label", columns="state", values="shown").reindex(
        index=[LABEL[k] for k in cmp_inds], columns=cmp_states)
    wide.index.name = "Indicator"
    st.dataframe(wide, use_container_width=True)
    gaps = cmp[cmp["value"].isna()]
    if not gaps.empty:
        st.caption("No data: " + "; ".join(
            f"{r.state} — {r.label}: {r.note.removeprefix('no data: ')}" for r in gaps.itertuples()))

    export = cmp.assign(availability=cmp["value"].map(lambda v: "reported" if pd.notna(v) else "no data"))
    export = export[["state", "indicator", "label", "period", "value", "unit", "availability", "status",
                     "source", "note"]]
    st.download_button(
        "Download this comparison (CSV)",
        export.to_csv(index=False).encode("utf-8"),
        file_name="state_comparison.csv", mime="text/csv", key="cmp_download",
    )

    tabs = st.tabs([LABEL[k] for k in cmp_inds])
    for tab, key in zip(tabs, cmp_inds):
        meta = S.INDICATORS[key]
        sub = cmp[cmp["indicator"] == key]
        with tab:
            periods_used = sorted({p for p in sub["period"] if isinstance(p, str)}, key=S.fiscal_year_start)
            bm = S.benchmark_for(benchmarks, key, periods_used[0]) if len(periods_used) == 1 else None
            fig = bar_with_gaps(
                list(sub["state"]), list(sub["value"]), meta.unit, benchmark=bm,
                benchmark_label=f"National (source): {fmt(bm, meta.unit)}" if bm is not None else "",
                title=f"{meta.label} — {', '.join(periods_used) if periods_used else 'no data'}",
            )
            if key in MULTI_YEAR:
                c_bar, c_line = st.columns(2)
            else:
                c_bar, c_line = st.container(), None
            with c_bar:
                st.plotly_chart(fig, use_container_width=True, key=f"cmp_bar_{key}")
                if bm is None:
                    st.caption(S.NO_BENCHMARK if not any(benchmarks["indicator"] == key)
                               else "National figure not drawn: states shown are from different years.")
            if c_line is not None:
                all_periods = S.periods_for(panel, key)
                series = panel[(panel["indicator"] == key) & panel["state"].isin(cmp_states)]
                lf = go.Figure()
                absent = []
                for s in cmp_states:
                    ss = series[series["state"] == s].set_index("period")["value"].reindex(all_periods)
                    if ss.notna().any():
                        lf.add_trace(go.Scatter(x=all_periods, y=ss.tolist(), mode="lines+markers", name=s,
                                                connectgaps=False))
                    else:
                        absent.append(s)
                nat = benchmarks[benchmarks["indicator"] == key].set_index("period")["value"].reindex(all_periods)
                if nat.notna().any():
                    lf.add_trace(go.Scatter(x=all_periods, y=nat.tolist(), mode="lines+markers",
                                            name="National (source)", line=dict(dash="dash", color=GOLD)))
                lf.update_layout(title=f"{meta.label} over time", height=380, yaxis_title=meta.unit,
                                 xaxis_title="Financial year")
                with c_line:
                    st.plotly_chart(lf, use_container_width=True, key=f"cmp_line_{key}")
                    if absent:
                        st.caption("Not in this series (no line drawn): " + ", ".join(
                            f"{s} — {S.missing_reason(panel, s, key)}" for s in absent))
                    st.caption("Gaps in a line are blank cells in the source, not zeros.")

st.markdown("---")

# ---------- C. Rank all states ----------------------------------------------
st.header("C · Rank every state by one indicator")
c1, c2, c3 = st.columns([1.6, 1, 1])
with c1:
    rank_ind = st.selectbox("Indicator", IND_KEYS, format_func=LABEL.get, key="rank_ind")
rank_periods = S.periods_for(panel, rank_ind)
with c2:
    rank_period = st.selectbox("Year", rank_periods, index=len(rank_periods) - 1, key="rank_period")
with c3:
    order = st.radio("Order", ["Highest first", "Lowest first"], key="rank_order")
meta = S.INDICATORS[rank_ind]
ranked = S.rank_states(panel, rank_ind, rank_period, ascending=(order == "Lowest first"), states=ALL_STATES)
n_rep = int(ranked["n_reporting"].iloc[0])
bm = S.benchmark_for(benchmarks, rank_ind, rank_period)
st.caption(
    f"{n_rep} of {len(ALL_STATES)} states/UTs report {meta.label.lower()} for {rank_period}; the "
    f"other {len(ALL_STATES) - n_rep} are listed at the bottom with the reason. "
    f"{state} (from section A) is highlighted. "
    + (f"National figure from the source: {fmt(bm, meta.unit)}." if bm is not None else S.NO_BENCHMARK + ".")
)
rank_fig = bar_with_gaps(
    list(ranked["state"]), list(ranked["value"]), meta.unit, highlight=state, horizontal=True,
    benchmark=bm, benchmark_label=f"National (source): {fmt(bm, meta.unit)}" if bm is not None else "",
    title=f"{meta.label}, {rank_period}", height=max(420, 24 * len(ranked) + 120),
)
st.plotly_chart(rank_fig, use_container_width=True, key="rank_chart")
rank_view = pd.DataFrame({
    "Rank": ranked["rank"].map(lambda r: "—" if pd.isna(r) else str(int(r))),
    "State/UT": ranked["state"],
    "Value": [fmt(v, meta.unit) for v in ranked["value"]],
    "Status": ranked["status"],
    "Note": ranked["note"],
})
st.dataframe(rank_view, hide_index=True, use_container_width=True)

st.markdown("---")

# ---------- D. Change over time ---------------------------------------------
st.header("D · Change over time — first vs latest observation")
st.markdown(
    "For indicators with more than one year: each state's first and latest value inside the "
    "window you choose, the change between them, and the **compound annual growth rate** "
    "(CAGR = (latest ÷ first)^(1 ÷ years) − 1). CAGR is shown only where it is defined — both "
    "values positive and at least one year apart."
)
d1, d2 = st.columns([1.4, 1.6])
with d1:
    hist_ind = st.selectbox("Indicator", MULTI_YEAR, format_func=LABEL.get, key="hist_ind")
hist_periods = S.periods_for(panel, hist_ind)
with d2:
    window = st.select_slider("Window", options=hist_periods, value=(hist_periods[0], hist_periods[-1]),
                              key="hist_window")
d3, d4 = st.columns([1.4, 1.6])
with d3:
    strict = st.checkbox(
        "Require values at both window ends (otherwise use each state's own first/latest inside it)",
        value=False, key="hist_strict")
with d4:
    hist_sort = st.radio("Sort by", ["CAGR (highest first)", "State name"], horizontal=True, key="hist_sort")
hist_states = st.multiselect("States/UTs", ALL_STATES, default=ALL_STATES, key="hist_states")
hmeta = S.INDICATORS[hist_ind]

if hmeta.price_basis == "current":
    callout("Current-price series: growth here is <b>nominal</b> — it includes inflation, so it "
            "overstates real growth in output per person.", kind="note")
elif hmeta.price_basis == "constant":
    callout("Constant-price series: growth here is <b>real</b> (inflation removed).", kind="note")
if hist_ind == "nsdp_pc_constant_spliced" and S.fiscal_year_start(min(window, key=S.fiscal_year_start)) < 2011:
    callout("This window starts before 2011-12, so its early values are 2004-05-base figures "
            "multiplied by each state's link factor (see DATA_REGISTRY.md). The growth rate depends "
            "on that factor.", kind="warn")

if not hist_states:
    st.warning("Select at least one state/UT.")
elif window[0] == window[1]:
    st.warning("Choose a window spanning at least two different years.")
else:
    hc = S.historical_change(panel, hist_ind, hist_states, window[0], window[1], strict=strict)
    if hist_sort.startswith("CAGR"):
        hc = pd.concat([hc[hc["cagr_pct"].notna()].sort_values("cagr_pct", ascending=False),
                        hc[hc["cagr_pct"].isna()].sort_values("state")])
    else:
        hc = hc.sort_values("state")
    n_valid = int(hc["cagr_pct"].notna().sum())
    st.caption(f"CAGR computable for {n_valid} of {len(hc)} selected states/UTs in {window[0]} → {window[1]}.")
    hfig = bar_with_gaps(
        list(hc["state"]), list(hc["cagr_pct"]), "%", horizontal=True, highlight=state,
        title=f"CAGR of {hmeta.label}, {window[0]} → {window[1]}", height=max(380, 24 * len(hc) + 120),
    )
    hfig.update_layout(xaxis_title="% per year")
    st.plotly_chart(hfig, use_container_width=True, key="hist_chart")
    hist_view = pd.DataFrame({
        "State/UT": hc["state"],
        "First": [f"{fmt(v, hmeta.unit)} ({p})" if pd.notna(v) else "no data"
                  for v, p in zip(hc["first_value"], hc["first_period"])],
        "Latest": [f"{fmt(v, hmeta.unit)} ({p})" if pd.notna(v) else "no data"
                   for v, p in zip(hc["last_value"], hc["last_period"])],
        "Years": hc["years"].map(lambda y: "—" if pd.isna(y) else str(int(y))),
        "Change": [fmt(v, hmeta.unit) if pd.notna(v) else "—" for v in hc["change"]],
        "% change": hc["pct_change"].map(lambda v: "—" if pd.isna(v) else f"{v:+.1f}%"),
        "CAGR": hc["cagr_pct"].map(lambda v: "—" if pd.isna(v) else f"{v:+.2f}% / yr"),
        "Note": hc["note"],
    })
    st.dataframe(hist_view, hide_index=True, use_container_width=True)

indicator_note(
    "CAGR", "**What it is.** The constant yearly growth rate that would take the first value "
    "to the latest value over the number of years between them. It smooths over every "
    "year in between — a state that fell sharply and then recovered can have the same CAGR as "
    "one that grew steadily.\n\n**When it is not shown.** If either value is missing, zero or "
    "negative, or both fall in the same year, CAGR is undefined and the table says so instead "
    "of showing a number.\n\n**Caveat.** With the default setting, states can have different "
    "first or latest years (e.g. Kerala's 2022-23 constant-price value is blank, so its latest "
    "is 2021-22); tick *Require values at both window ends* for a strictly like-for-like "
    "window.", kind="method",
)

st.markdown("---")
footnote(
    "Sources: RBI Handbook of Statistics on Indian States (Table 26) and DBIE; PLFS 2023-24; MoSPI "
    "HCES 2023-24 Statement 7; state_gsdp_nsdp_percapita.csv (source unconfirmed). Ranks, "
    "differences from the national figure, percentage changes and CAGRs are computed on this page "
    "from those values; nothing is estimated or interpolated. See DATA_REGISTRY.md for provenance."
)
