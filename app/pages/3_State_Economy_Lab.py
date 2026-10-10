"""State Economy Lab.

One page for everything state-level in this repository.

Research question: are Indian states converging economically or becoming
more divergent? Sigma (σ) convergence with a choice of dispersion measure
on a balanced panel by default, beta (β) convergence over a chosen window
with classical or HC1 standard errors and the implied half-life, and
research notes generated deterministically from those results -- all on
real per-capita NSDP at constant prices (spliced, or either RBI base-year
block as published).

Alongside it: a schematic tile map of any state indicator, a 2-5 state
comparison workbench, and an explorer for every real state-level indicator
(per-state profile, side-by-side comparison, a full ranking by any
indicator, first-vs-latest change). Calculations live in
analysis/convergence.py, analysis/regional.py and analysis/states.py, which
read data/raw/ through data_sources/loaders.py -- nothing on this page is
estimated, filled or typed in, and a missing value is shown as "no data",
never as 0.
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
from plotly.colors import sample_colorscale
import streamlit as st

from analysis import regional
from analysis import convergence as C
from analysis import states as S
from app.components.theme import (
    setup, set_chart_source, chart_source, kicker, callout, source_badge, stat_card, footnote, GOLD, LEAF, MUTED,
    COBALT, INK, WARM_WHITE, SERIES,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel
from app.components import hairline_display
from data_sources import loaders

setup("State Economy Lab", accent=LEAF)
set_chart_source("RBI Handbook of Statistics on Indian States; PLFS 2023-24; MoSPI HCES 2023-24; calculations on this site")

UNIT_TEXT = {
    "₹": "₹ per person, per year",
    "₹/month": "₹ per person, per month",
    "%": "% of labour force",
}

PRICE_BASIS_TEXT = {
    "constant": "real (constant prices)",
    "current": "nominal (current prices)",
    "n/a": "rate (no price basis)",
}

# Sequential scale for the tile map, built from theme colours only:
# cobalt (dark) -> leaf -> gold (light), luminance rising monotonically.
TILE_SCALE = [[0.0, COBALT], [0.5, LEAF], [1.0, GOLD]]


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



def _short_value(value, unit: str) -> str:
    """Compact tile label: lakh for ₹/year, thousands for ₹/month."""
    if value is None or pd.isna(value):
        return "no data"
    if unit == "%":
        return f"{value:.1f}%"
    if unit == "₹/month":
        return f"₹{value / 1e3:.1f}k"
    return f"₹{value / 1e5:.2f}L"


def _luminance(rgb: str) -> float:
    r, g, b = (int(float(v)) / 255 for v in rgb[rgb.index("(") + 1:rgb.index(")")].split(","))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def tile_map_figure(tf: pd.DataFrame, label: str, unit: str, period: str) -> go.Figure:
    """Equal-size square tiles (a Heatmap on an integer grid) coloured by
    value; no-data tiles drawn grey and hatched with their own hover."""
    nrows, ncols = int(tf["row"].max()) + 1, int(tf["col"].max()) + 1
    z = np.full((nrows, ncols), np.nan)
    hover = np.full((nrows, ncols), "", dtype=object)
    has = tf["value"].notna()
    vmin = float(tf.loc[has, "value"].min()) if has.any() else 0.0
    vmax = float(tf.loc[has, "value"].max()) if has.any() else 1.0
    span = (vmax - vmin) or 1.0
    fig = go.Figure()
    annotations, shapes = [], []
    nd_x, nd_y, nd_text = [], [], []
    g = 0.06
    for r in tf.itertuples(index=False):
        note = f"<br><i>{r.note}</i>" if isinstance(r.note, str) and r.note else ""
        if pd.notna(r.value):
            z[r.row, r.col] = r.value
            hover[r.row, r.col] = (
                f"<b>{r.state}</b><br>{label}, {period}<br>Value: {S.format_value(r.value, unit)}"
                f"<br>Rank {int(r.rank)} of {int(r.n_reporting)} reporting (1 = highest)"
                f"<br>Status: {r.status}{note}"
            )
            fill = sample_colorscale(TILE_SCALE, [(r.value - vmin) / span])[0]
            colour = INK if _luminance(fill) > 0.28 else WARM_WHITE
            annotations.append(dict(x=r.col, y=r.row, text=f"<b>{r.abbr}</b><br>{_short_value(r.value, unit)}",
                                    showarrow=False, font=dict(size=10, color=colour)))
        else:
            x0, x1, y0, y1 = r.col - 0.5 + g, r.col + 0.5 - g, r.row - 0.5 + g, r.row + 0.5 - g
            shapes.append(dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color=MUTED, width=1),
                               fillcolor="rgba(139,141,153,0.18)", layer="below"))
            s = x1 - x0
            for d in (-s / 2, 0.0, s / 2):
                shapes.append(dict(type="line", x0=x0 + max(0.0, -d), y0=y0 + max(0.0, d),
                                   x1=x1 - max(0.0, d), y1=y1 - max(0.0, -d),
                                   line=dict(color=MUTED, width=1), layer="below"))
            annotations.append(dict(x=r.col, y=r.row, text=f"<b>{r.abbr}</b><br>no data", showarrow=False,
                                    font=dict(size=10, color=WARM_WHITE)))
            nd_x.append(r.col)
            nd_y.append(r.row)
            nd_text.append(f"<b>{r.state}</b><br>{label}, {period}<br><b>no data</b>{note}"
                           f"<br>Status of series: {r.status}")
    fig.add_trace(go.Heatmap(
        z=z, x=list(range(ncols)), y=list(range(nrows)), customdata=hover,
        hovertemplate="%{customdata}<extra></extra>", hoverongaps=False,
        colorscale=TILE_SCALE, zmin=vmin, zmax=vmax, xgap=6, ygap=6, showscale=bool(has.any()),
        colorbar=dict(title=dict(text=UNIT_TEXT.get(unit, unit), side="right"), thickness=14, len=0.75),
        name="value",
    ))
    if nd_x:
        fig.add_trace(go.Scatter(x=nd_x, y=nd_y, mode="markers", hovertext=nd_text, hoverinfo="text",
                                 marker=dict(symbol="square", size=34, color="rgba(0,0,0,0)"),
                                 showlegend=False, name="no data"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="no data (grey, hatched)",
                                 marker=dict(symbol="square-x-open", size=14, color=MUTED), showlegend=True,
                                 hoverinfo="skip"))
    fig.update_layout(
        title=f"{label}, {period} — schematic tile map", height=640, shapes=shapes, annotations=annotations,
        xaxis=dict(visible=False, range=[-0.6, ncols - 0.4], constrain="domain"),
        yaxis=dict(visible=False, autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain"),
        legend=dict(orientation="h", y=-0.02, x=0.0), margin=dict(l=10, r=10, t=60, b=30),
    )
    return fig


CONV_SERIES = {
    "spliced": "Spliced 2004-05 → 2022-23 (derived: two RBI base years linked)",
    "pub_2004": "As published, 2004-05 base block (2004-05 → 2014-15)",
    "pub_2011": "As published, 2011-12 base block (2011-12 → 2022-23)",
}


@st.cache_data(show_spinner=False)
def _conv_source(choice: str):
    if choice == "spliced":
        return loaders.load_nsdp_spliced()[["state", "financial_year", C.VALUE_COL, "method"]].copy(), []
    base = "2004-05" if choice == "pub_2004" else "2011-12"
    return C.as_published_block(loaders.load_nsdp_constant_as_published(), base)


# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## State Economy Lab")
    st.caption("Sections")
    st.markdown(
        "- Branches · fastest growers vs. richest states\n"
        "- Scope (convergence & income ranking)\n"
        "- Data definitions (read first)\n"
        "- **Convergence (σ & β)** tab\n"
        "  - Window & series\n"
        "  - A · Sigma convergence (5 measures)\n"
        "  - B · Beta convergence, SEs, half-life\n"
        "  - Research notes (auto-generated)\n"
        "- **Tile map** tab — I · schematic tile map\n"
        "- **Income ranking & unemployment** tab\n"
        "  - C · State ranking, latest year\n"
        "  - D · Unemployment snapshot\n"
        "- **Comparison workbench** tab — J\n"
        "- **State lookup & compare** tab\n"
        "  - E · State lookup\n"
        "  - F · Compare states side by side\n"
        "- **Rank any indicator** tab — G\n"
        "- **Change over time** tab — H · first vs latest, CAGR\n"
        "- **Indicator inventory & sources** tab"
    )
    st.markdown("---")
    st.caption(
        "Status labels follow DATA_REGISTRY.md: VERIFIED (source confirmed), PARTIAL "
        "(real, source or coverage not fully confirmed), SPLICED (two real base-year "
        "series linked by a documented factor). Real data throughout — see the badges."
    )

kicker("STATE ECONOMY LAB · INDIA")
st.title("Are Indian states converging or diverging?")
st.markdown(
    "Per-capita income across Indian states, 2004-05 to 2022-23 — real data from the "
    "RBI Handbook of Statistics on Indian States, with two standard convergence tests "
    "from the growth-economics literature (Barro & Sala-i-Martin)."
)
st.markdown(
    f"Alongside the convergence tests: look up any of **{len(ALL_STATES)} states and union "
    f"territories** across the **{len(IND_KEYS)} state-level indicators** this repository "
    "holds — output per person, unemployment and urban consumption — then compare, rank and "
    "track them. Every number is read straight from a file in `data/raw/`. Where a source has "
    "no value, the page says **no data** and why; it never shows a zero in its place."
)
source_badge("RBI Handbook of Statistics on Indian States, Table 26", "RBI DBIE", "PLFS 2023-24",
             "MoSPI HCES 2023-24", "VERIFIED / PARTIAL / SPLICED — see Data page")

st.markdown("---")

nsdp = loaders.load_nsdp_spliced()

# Hero: computed on the full series (all states, all years), so it does not
# move with the scope controls below.
_main_states = regional.rank_states_latest(nsdp).sort_values("rank")["state"].head(8).tolist()
_feature_states = (
    regional.beta_convergence(nsdp).per_state
    .sort_values("avg_annual_growth_pct", ascending=False)["state"].head(3).tolist()
)
fig_col, text_col = st.columns([5, 4], vertical_alignment="center")
with fig_col:
    hairline_display.render(
        "branches", hero=True, accent=LEAF,
        main=json.dumps(_main_states), feature=json.dumps(_feature_states),
    )
with text_col:
    st.markdown(
        "### Economies do not follow one path\n"
        "The main line is the **8 states with the highest latest per-capita "
        "NSDP**; the branch is the **3 states that grew fastest on average** "
        f"over {nsdp['financial_year'].min()} → {nsdp['financial_year'].max()}. "
        "**Hover a commit** to see which state it is. Every name is a real "
        "rank from the RBI Handbook series used throughout this page, across "
        "all states and years (the scope controls below don't change it)."
    )

st.markdown("---")

# ---------- Scope controls: states + year range --------------------------
st.subheader("Scope — convergence & income ranking")
st.caption(
    "These two controls re-run the real sigma/beta convergence tests and the "
    "per-capita NSDP ranking table on whichever states and years you choose — not a "
    "cosmetic filter. They apply to the **Convergence (σ & β)** and **Income ranking & "
    "unemployment** tabs only; the explorer tabs have their own state and year pickers. "
    "Defaults are every state and the full available window."
)
all_states = sorted(nsdp["state"].unique())
years_list = sorted(nsdp["financial_year"].unique())

scope_c1, scope_c2 = st.columns([1.4, 1])
with scope_c1:
    selected_states = st.multiselect(
        "States included (sigma/beta convergence & ranking)",
        all_states, default=all_states, key="scope_states",
    )
with scope_c2:
    year_range = st.select_slider(
        "Financial year range (sigma/beta convergence & ranking)",
        options=years_list, value=(years_list[0], years_list[-1]), key="scope_years",
    )

indicator_note(
    "the state and year-range scope controls",
    "**What they change.** Sigma and beta convergence are both computed "
    "directly from whichever rows are handed to them — they don't assume "
    "one fixed panel of states or one fixed window of years. Narrowing the "
    "state list re-runs both tests on only that subset (e.g. just the "
    "southern states, or just the largest economies); narrowing the year "
    "range limits the years the convergence window (chosen at the top of the "
    "Convergence tab) can use. The ranking table in section C also respects "
    "both: it shows the latest year *within your chosen range*, for only the "
    "states you selected.\n\n"
    "**Why this is useful.** The headline sigma/beta results on the full "
    "panel can mask sub-period or sub-group patterns — you can check, say, "
    "whether convergence looks different before vs. after a particular year, "
    "or ask the question for a specific group of states rather than all of "
    "India at once.\n\n"
    "**Caveat.** Sigma convergence is computed on a **balanced panel** by "
    "default — only states with a value in every year of the window — and "
    "needs at least 5 of them; beta convergence needs at least 5 states with "
    "values at both ends of the window. Pick too few states or too narrow a "
    "window and the page reports 'insufficient data' rather than a fabricated "
    "result.",
)

scope_ok = bool(selected_states)
i0, i1 = years_list.index(year_range[0]), years_list.index(year_range[1])
years_in_scope = set(years_list[i0:i1 + 1])
nsdp_scoped = nsdp[nsdp["state"].isin(selected_states) & nsdp["financial_year"].isin(years_in_scope)]

# ---------- F. Data-definition guardrails --------------------------------
_n_last = int(nsdp.loc[nsdp["financial_year"] == years_list[-1], C.VALUE_COL].notna().sum())
with st.container(border=True):
    st.markdown("#### Data definitions — read before interpreting anything on this page")
    st.markdown(
        "- **Real vs nominal.** *Constant-price* series (2011-12 prices) are **real** — inflation removed. "
        "*Current-price* series are **nominal** and mix real growth with price rises. Convergence (σ, β), "
        "the research notes and the workbench index use **real** per-capita NSDP only; current-price levels "
        "are labelled nominal wherever they appear.\n"
        "- **Per-capita vs total.** Every NSDP/GSDP figure here is **per person** (state output ÷ population), "
        "not the size of the state economy. **NSDP** is net of depreciation; **GSDP** is gross. Output produced "
        "in a state is not income received by its residents.\n"
        "- **Financial year vs calendar year.** '2022-23' is the Indian **financial year** 1 April 2022 – 31 March "
        "2023. PLFS and HCES '2023-24' are **survey rounds**, not financial-year accounts.\n"
        "- **Official vs derived.** RBI Table 26 is published in two base-year blocks (2004-05 and 2011-12). "
        "The **spliced** 2004-05 → 2022-23 series is **derived** in this project (old-base values × a per-state "
        "link factor before 2011-12); the Convergence tab can also run on either block **as published**. "
        "Growth rates, ranks, dispersion statistics, regressions and indices are **calculations on this site**.\n"
        "- **Missing vs zero.** A blank in a source is shown as **no data** — never as 0, never interpolated. "
        f"In {years_list[-1]} only {_n_last} of {len(all_states)} states have a constant-price value; states "
        "missing a year are listed wherever they are excluded.\n"
        "- **Unweighted across states.** Each state counts once — Sikkim as much as Uttar Pradesh. "
        "Population-weighted versions are **DATA REQUIRED** (a state population series for every year is "
        "not in this repository)."
    )

st.markdown("---")

(tab_conv, tab_tile, tab_income, tab_wb, tab_lookup, tab_rank, tab_change, tab_inv) = st.tabs([
    "Convergence (σ & β)",
    "Tile map",
    "Income ranking & unemployment",
    "Comparison workbench",
    "State lookup & compare",
    "Rank any indicator",
    "Change over time",
    "Indicator inventory & sources",
])

# =========================================================================
# Tab 1 — Convergence
# =========================================================================
with tab_conv:
    # ---------- Window & series ------------------------------------------
    st.header("Convergence window & series")
    st.markdown(
        "Choose the income series and the **initial year** and **window length**. Sigma convergence, beta "
        "convergence and the research notes below all use this one window, restricted to the states and "
        "year range in the scope controls above."
    )
    series_choice = st.radio("Real per-capita NSDP series (constant prices)", list(CONV_SERIES),
                             format_func=CONV_SERIES.get, key="conv_series")
    conv_src_all, conv_series_notes = _conv_source(series_choice)
    conv_src = conv_src_all[conv_src_all["state"].isin(selected_states)]
    conv_years = sorted(
        conv_src.loc[conv_src[C.VALUE_COL].notna() & conv_src["financial_year"].isin(years_in_scope),
                     "financial_year"].unique(),
        key=S.fiscal_year_start,
    )
    for _note in conv_series_notes:
        st.caption(_note)
    if series_choice != "spliced":
        st.caption("As-published values are exactly RBI Table 26 for one base year — no link factor, so no "
                   "splice assumption, but only windows inside that block are possible.")

    conv_ok = scope_ok and len(conv_years) >= 2
    if not scope_ok:
        st.warning("Select at least one state in the scope controls above.")
    elif not conv_ok:
        st.warning("The scope year range and this series share fewer than two financial years. Widen the "
                   "scope year range or pick another series.")
    else:
        wc1, wc2, wc3 = st.columns([1, 1.4, 1])
        with wc1:
            conv_start = st.selectbox("Initial year", conv_years[:-1], index=0,
                                      key=f"conv_start_{series_choice}_{conv_years[0]}_{conv_years[-1]}")
        _later = [y for y in conv_years if S.fiscal_year_start(y) > S.fiscal_year_start(conv_start)]
        _lengths = [S.fiscal_year_start(y) - S.fiscal_year_start(conv_start) for y in _later]
        with wc2:
            if len(_lengths) > 1:
                conv_len = st.select_slider("Window length (years)", options=_lengths, value=_lengths[-1],
                                            key=f"conv_len_{series_choice}_{conv_start}_{_lengths[-1]}")
            else:
                conv_len = _lengths[0]
                st.markdown(f"Window length: **{conv_len} year**")
        conv_end = _later[_lengths.index(conv_len)]
        with wc3:
            stat_card("Window", f"{conv_start} → {conv_end}", f"{conv_len} financial year(s) apart")

    st.markdown("---")

    # ---------- A. Sigma convergence ------------------------------------
    st.header("A · Sigma (σ) convergence — is the spread across states narrowing?")
    st.markdown(
        "**Sigma convergence** asks whether the *spread* of state per-capita incomes shrinks over time. "
        "Pick how to measure the spread; the default, the **standard deviation of log income**, is the "
        "classic Barro & Sala-i-Martin σ. A falling measure is σ-convergence; a rising one is σ-divergence."
    )

    indicator_note(
        "sigma convergence vs. beta convergence",
        "**Two different questions, both called 'convergence'.** Sigma (σ) "
        "convergence asks a question about the *group as a whole*: is the "
        "spread of incomes across all states shrinking over time? Beta (β) "
        "convergence asks a different question about *individual states*: do "
        "the states that started poorer tend to grow faster than the states "
        "that started richer? These sound similar but are not interchangeable "
        "— one describes the shape of the whole distribution at each point in "
        "time, the other describes a pattern in each state's own growth rate "
        "relative to where it started.\n\n"
        "**Why you need both.** Beta convergence (poorer states growing "
        "faster) is a *necessary but not sufficient* condition for sigma "
        "convergence (the overall spread shrinking). It is possible for a few "
        "poor states to grow quickly and a few rich states to grow slowly — "
        "satisfying beta convergence — while the dispersion of the *whole* "
        "distribution barely moves, because other states in the middle are "
        "pulling apart, or the fast-growing poor states were too few to move "
        "the aggregate statistic. Seeing one without the other is a normal, "
        "informative outcome, not a contradiction to be explained away — it "
        "tells you *where* in the distribution the action (or inaction) is "
        "concentrated.\n\n"
        "**How to read the two findings together on this page.** If sigma "
        "says 'falling' and beta also points to convergence, that is a "
        "consistent, mutually reinforcing picture. If they disagree, the "
        "convergence story is more complicated than 'states are/aren't "
        "converging': look at which specific states are driving each test "
        "(the beta scatter plot) before drawing a single headline conclusion.\n\n"
        "**Caveat.** Both are purely descriptive statistics about this income "
        "series over this period. Neither test, by itself, identifies *why* "
        "any convergence or divergence occurs (trade, migration, policy, "
        "technology diffusion are all candidate explanations in the growth "
        "literature, and none is tested here).",
    )

    sig = None
    if conv_ok:
        sc1, sc2 = st.columns([1.2, 1.4])
        with sc1:
            sigma_measure = st.selectbox("Dispersion measure", list(C.MEASURES),
                                         format_func=lambda k: C.MEASURES[k].label, key="sigma_measure")
        with sc2:
            sigma_panel = st.radio(
                "States counted each year", ["balanced", "unbalanced"],
                format_func={"balanced": "Balanced panel — the same states every year (default)",
                             "unbalanced": "All available states (unbalanced — composition changes)"}.get,
                key="sigma_panel",
            )
        mdef = C.MEASURES[sigma_measure]
        sig = C.sigma_dispersion(conv_src, conv_start, conv_end, sigma_measure,
                                 balanced=(sigma_panel == "balanced"), states=selected_states)
        if sigma_panel == "unbalanced":
            n_range = (f"{int(sig.by_year['n_states'].min())}–{int(sig.by_year['n_states'].max())}"
                       if len(sig.by_year) else "0")
            st.warning(
                f"Unbalanced: each year uses whichever states report it ({n_range} states per year here). "
                "When the set of states changes, the measure moves for reasons that have nothing to do with "
                "incomes — e.g. if several high-income states have no 2022-23 value yet, the spread *looks* "
                "narrower in 2022-23. The verdict below can be an artefact; use the balanced panel for "
                "conclusions."
            )
        if sig.verdict == "insufficient data":
            st.warning(
                "Insufficient data for sigma convergence with this selection (needs at least 5 states in "
                "at least 2 years of the window"
                + (", all with values in every year — see the excluded list below" if sig.balanced else "")
                + "). Widen the scope or shorten the window."
            )
        else:
            label = {"falling": "FALLING · σ-convergence", "rising": "RISING · σ-divergence",
                     "stable": "STABLE · no clear trend"}[sig.verdict]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                stat_card("Verdict (rule below)", label)
            with c2:
                stat_card("Trend change over window", f"{sig.trend_change_pct_of_mean:+.1f}% of mean",
                          f"slope {sig.slope_per_year:+.4f} {mdef.unit}/yr")
            with c3:
                stat_card(f"{sig.by_year['financial_year'].iloc[0]} → {sig.by_year['financial_year'].iloc[-1]}",
                          f"{C.fmt_measure(sig.first_value, sigma_measure)} → "
                          f"{C.fmt_measure(sig.last_value, sigma_measure)}")
            with c4:
                n_txt = (f"{len(sig.included_states)}" if sig.balanced
                         else f"{int(sig.by_year['n_states'].min())}–{int(sig.by_year['n_states'].max())}")
                stat_card("States in each year", n_txt, "balanced panel" if sig.balanced else "unbalanced")

            fig_sigma = go.Figure()
            fig_sigma.add_trace(go.Scatter(
                x=sig.by_year["financial_year"], y=sig.by_year["value"], mode="lines+markers", name=mdef.label,
                customdata=sig.by_year["n_states"],
                hovertemplate="%{x}: %{y:.4f}<br>%{customdata} states<extra></extra>",
            ))
            t_years = np.array([S.fiscal_year_start(y) for y in sig.by_year["financial_year"]], dtype=float)
            fit_line = C.ols(t_years, sig.by_year["value"].to_numpy(dtype=float))
            fig_sigma.add_trace(go.Scatter(
                x=sig.by_year["financial_year"], y=fit_line.intercept + fit_line.slope * t_years, mode="lines",
                name="OLS trend", line=dict(dash="dash", color=GOLD), hoverinfo="skip",
            ))
            fig_sigma.update_layout(
                title=(f"{mdef.label} of real per-capita NSDP across states, {conv_start} → {conv_end} "
                       f"({'balanced panel, ' + str(len(sig.included_states)) + ' states' if sig.balanced else 'unbalanced'})"),
                xaxis_title="Financial year", yaxis_title=f"{mdef.label} ({mdef.unit})", height=430,
                legend=dict(orientation="h", y=1.02, yanchor="bottom"),
            )
            st.plotly_chart(fig_sigma, width="stretch", key="sigma_chart")

            with st.container(border=True):
                st.markdown(f"**How the verdict is decided.** {C.sigma_rule_text(sig.threshold_pct)}")
                span_years = int(t_years.max() - t_years.min())
                st.markdown(
                    f"Here: slope {sig.slope_per_year:+.5f} {mdef.unit}/year × {span_years} years = "
                    f"{sig.trend_change:+.5f} {mdef.unit}; mean level over the window "
                    f"{float(sig.by_year['value'].mean()):.5f} → trend change **{sig.trend_change_pct_of_mean:+.1f}%** "
                    f"of the mean → **{sig.verdict}**. Trend-slope SE {sig.slope_se:.5f}, {C.fmt_p(sig.slope_p)} "
                    "(consecutive years are serially correlated, so this p-value is indicative only)."
                )
                st.caption(f"Formula: {mdef.formula}. {mdef.reading}")
        if sig.balanced and len(sig.excluded):
            st.caption(
                f"Excluded from the balanced panel ({len(sig.excluded)}): "
                + "; ".join(f"{r.state} — {r.reason}" for r in sig.excluded.itertuples())
                + ". Not filled or interpolated; switch to 'All available states' to include them year by year "
                "(with the composition warning)."
            )
        callout(C.POPULATION_WEIGHTING_CAVEAT, kind="note")

    st.markdown("---")

    # ---------- B. Beta convergence --------------------------------------
    st.header("B · Beta (β) convergence — did poorer states grow faster?")
    st.markdown(
        "**Beta convergence** asks whether states with *lower* initial income grew *faster* over the "
        "window. Each state's **average annual growth** of real per-capita NSDP, "
        "100 × (ln y<sub>end</sub> − ln y<sub>start</sub>) ÷ T, is regressed by OLS on its **log initial "
        "real per-capita NSDP**, with **no control variables** (unconditional β-convergence). States need a "
        "value at *both* ends of the window — no nearby year is substituted.",
        unsafe_allow_html=True,
    )

    beta = None
    if conv_ok:
        beta_robust = st.checkbox("Heteroskedasticity-robust standard errors (HC1)", value=False,
                                  key="beta_robust",
                                  help="HC1 = White's sandwich estimator scaled by n/(n−2). Inference uses "
                                       "Student's t with n−2 degrees of freedom either way.")
        beta = C.beta_window(conv_src, conv_start, conv_end, robust=beta_robust, states=selected_states)
        if not beta.ok:
            st.warning(
                "Insufficient data for beta convergence with this selection (needs at least 5 states with "
                "values at both ends of the window). Widen the scope or change the window."
            )
        else:
            f = beta.fit
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                stat_card("Slope b", f"{f.slope:+.3f}", f"pp of annual growth per log point · {f.se_type} SE {f.se:.3f}")
            with c2:
                stat_card("95% CI for b", f"[{f.ci_low:+.2f}, {f.ci_high:+.2f}]", f"t = {f.t:+.2f}, {C.fmt_p(f.p)}")
            with c3:
                stat_card("n · R²", f"{f.n} · {f.r_squared:.3f}", f"{f.df_resid} residual df")
            with c4:
                if pd.notna(beta.speed):
                    stat_card("Speed λ · half-life", f"{beta.speed * 100:.2f}%/yr · {beta.half_life:.1f} yrs",
                              "implied by the slope (formula below)")
                else:
                    stat_card("Speed λ · half-life", "not defined", beta.speed_note)

            sig_txt = "significant" if pd.notna(f.p) and f.p < 0.05 else "not significant"
            if f.slope < 0:
                callout(
                    f"**Negative slope ({f.slope:+.3f}, {sig_txt} at 5%)**: states that started poorer grew "
                    "faster on average — a pattern *consistent with* unconditional β-convergence. It is a "
                    "description of this sample, not a causal finding: it does not say *why* poorer states grew "
                    "faster, and with no controls it cannot separate catch-up from differences in structure, "
                    "policy or measurement.", kind="note")
            else:
                callout(
                    f"**Non-negative slope ({f.slope:+.3f}, {sig_txt} at 5%)**: no tendency for initially "
                    "poorer states to grow faster in this window — no evidence of unconditional β-convergence. "
                    "A positive slope would describe richer states pulling ahead; either way this is "
                    "descriptive, not causal.", kind="note")

            fig_beta = go.Figure()
            # Clusters of near-identical states (e.g. Tamil Nadu/Uttarakhand/
            # Telangana) made labels overprint; place each label at the first of
            # top/bottom/right/left whose rough box doesn't hit one already placed
            # (in normalised log-x / y space). Hover always gives exact values.
            pts = beta.per_state.sort_values("avg_annual_growth_pct", ascending=False).reset_index(drop=True)
            lx = np.log(pts["initial_value"].to_numpy(dtype=float))
            gy = pts["avg_annual_growth_pct"].to_numpy(dtype=float)
            nx = (lx - lx.min()) / max(np.ptp(lx), 1e-9)
            ny = (gy - gy.min()) / max(np.ptp(gy), 1e-9)
            h = 0.055
            offsets = {"top center": (0, h), "bottom center": (0, -h), "middle right": (1, 0), "middle left": (-1, 0)}
            placed, label_pos = [], []
            for i, name in enumerate(pts["state"]):
                w = 0.0095 * len(str(name))
                best = "top center"
                for pos, (dx, dy) in offsets.items():
                    cx = nx[i] + dx * (w / 2 + 0.012)
                    cy = ny[i] + dy
                    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                    if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in placed):
                        best = pos
                        break
                dx, dy = offsets[best]
                cx, cy = nx[i] + dx * (w / 2 + 0.012), ny[i] + dy
                placed.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
                label_pos.append(best)
            fig_beta.add_trace(go.Scatter(
                x=pts["initial_value"], y=pts["avg_annual_growth_pct"],
                mode="markers+text", text=pts["state"], textposition=label_pos,
                name="States", marker=dict(size=9),
                hovertemplate="%{text}<br>Initial: ₹%{x:,.0f}<br>Avg growth: %{y:.2f}%<extra></extra>",
            ))
            x_range = np.linspace(beta.per_state["initial_value"].min(), beta.per_state["initial_value"].max(), 50)
            y_fit = f.slope * np.log(x_range) + f.intercept
            fig_beta.add_trace(go.Scatter(x=x_range, y=y_fit, mode="lines", name="OLS fit", line=dict(dash="dash")))
            fig_beta.update_layout(
                title=(f"Average annual real growth {conv_start} → {conv_end} vs. initial real per-capita NSDP "
                       f"({f.n} states, log scale)"),
                xaxis_title=f"Initial real per-capita NSDP, {conv_start} (₹ at 2011-12 prices, log scale)",
                xaxis_type="log", yaxis_title="Average annual growth (% a year)", height=480)
            st.plotly_chart(fig_beta, width="stretch", key="beta_chart")

            with st.expander("Regression details & formulas"):
                st.markdown(
                    f"- **Model:** growth_i = a + b · ln(y_i,{conv_start}) + e_i, with growth_i = 100 · "
                    f"(ln y_i,{conv_end} − ln y_i,{conv_start}) ÷ {beta.years}.\n"
                    f"- **Estimates:** a = {f.intercept:+.3f} (SE {f.se_intercept:.3f}); b = {f.slope:+.4f} "
                    f"(SE {f.se:.4f}, {f.se_type}); t = {f.t:+.3f}; {C.fmt_p(f.p)}; 95% CI [{f.ci_low:+.4f}, "
                    f"{f.ci_high:+.4f}] (t with {f.df_resid} df); R² = {f.r_squared:.4f}; n = {f.n}.\n"
                    f"- **Speed of convergence & half-life:** {C.SPEED_FORMULA}. "
                    + (f"Here b = {f.slope / 100:+.5f}, T = {beta.years}: λ = {beta.speed:.5f} a year, half-life = "
                       f"{beta.half_life:.1f} years." if pd.notna(beta.speed) else f"Not computed: {beta.speed_note}.")
                    + "\n- **Validation:** slope, SE, p, CI and R² are tested against statsmodels OLS "
                    "(classical and `cov_type='HC1'`, `use_t=True`) in `tests/test_convergence.py`."
                )
                st.dataframe(
                    beta.per_state.assign(
                        initial_value=lambda d: d["initial_value"].round(0),
                        final_value=lambda d: d["final_value"].round(0),
                        log_initial=lambda d: d["log_initial"].round(4),
                        avg_annual_growth_pct=lambda d: d["avg_annual_growth_pct"].round(3),
                    ).rename(columns={"initial_value": f"₹ {conv_start}", "final_value": f"₹ {conv_end}",
                                      "log_initial": "ln initial", "avg_annual_growth_pct": "avg growth % / yr"}),
                    hide_index=True, width="stretch",
                )
            if len(beta.excluded):
                st.caption(
                    f"Not in the regression ({len(beta.excluded)}): "
                    + "; ".join(f"{r.state} — {r.reason}" for r in beta.excluded.itertuples()) + "."
                )

            if sig is not None and sig.verdict != "insufficient data":
                beta_conv = f.slope < 0 and pd.notna(f.p) and f.p < 0.05
                if beta_conv and sig.verdict != "falling":
                    callout(
                        f"**β points to catch-up but σ is '{sig.verdict}'** — not a contradiction. β-convergence is "
                        "*necessary but not sufficient* for σ-convergence: a few fast-growing poor states and slow "
                        "rich states can coexist with an overall spread that does not narrow, especially with an "
                        f"R² of {f.r_squared:.2f}. Don't average them into one verdict.", kind="warn")
                elif not beta_conv and sig.verdict == "falling":
                    callout(
                        "**σ is falling but β shows no significant catch-up** — the spread narrowed without a clear "
                        "link between initial income and growth (e.g. through changes in the middle of the "
                        "distribution). Treat both as weak evidence.", kind="warn")

    st.markdown("---")

    # ---------- Research notes ------------------------------------------
    st.header("Research notes — generated from the results above")
    if conv_ok and sig is not None and beta is not None:
        st.caption(
            f"Series: {CONV_SERIES[series_choice]} · window {conv_start} → {conv_end} · "
            f"{len(selected_states)} state(s) in scope · σ measure: {C.MEASURES[sigma_measure].label} "
            f"({'balanced' if sig.balanced else 'unbalanced'}) · {beta.fit.se_type if beta.ok else 'classical'} SE. "
            "Every sentence is assembled by `analysis.convergence.research_notes` from the numbers computed "
            "for this selection — change a control and the notes are rewritten. Nothing here is hand-written "
            "for a particular result."
        )
        conv_ranks = C.rank_changes(conv_src, conv_start, conv_end, states=selected_states)
        notes = C.research_notes(beta, sig, conv_ranks)
        nc1, nc2 = st.columns(2)
        for col, key, title in [(nc1, "observed", "Observed facts"), (nc1, "statistical", "Statistical results"),
                                (nc2, "interpretation", "Interpretation (cautious, non-causal)"),
                                (nc2, "questions", "Questions for further research")]:
            with col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.markdown("\n".join(f"- {line}" for line in notes[key]) or "- (none for this selection)")
        if len(conv_ranks):
            with st.expander(f"Rank changes {conv_start} → {conv_end} ({int(conv_ranks['n_compared'].iloc[0])} states with both years)"):
                st.dataframe(conv_ranks.rename(columns={
                    "rank_start": f"Rank {conv_start}", "rank_end": f"Rank {conv_end}",
                    "places": "Places gained (+) / lost (−)", "n_compared": "States compared"}),
                    hide_index=True, width="stretch")
    else:
        st.info("Research notes appear once the window above has enough data.")

    st.markdown("---")
    with st.expander("Methodology & limitations"):
        st.markdown(
            """
**Sigma convergence**: the chosen dispersion measure is computed across states for every financial year in the window; years with fewer than 5 states are dropped. **Balanced panel (default)**: only states with a value in every year of the window, so the same states are compared each year. Measures — SD of log income (population SD), coefficient of variation (population SD ÷ mean × 100), Gini across states (unweighted: Σ|yᵢ−yⱼ| ÷ 2n²ȳ), max/min, P90/P10 (numpy linear percentiles). Verdict: OLS trend of the measure on the year; trend change over the window as a % of the window mean; |change| < 5% = stable.

**Beta convergence**: `growth_i = 100 · (ln y_i,T − ln y_i,0) / T`, regressed by OLS on `ln y_i,0`; classical or HC1 standard errors, t-distribution (n − 2 df) for p-values and the 95% CI. Unconditional — no controls for human capital, investment rate, sector mix or institutions, all of which the literature shows matter. Speed of convergence λ = −ln(1 + bT)/T with b = slope/100; half-life = ln 2/λ.

**Data**: per-capita NSDP at constant (2011-12) prices. The default is a **spliced** series — the two RBI Handbook base-year blocks (2004-05 base, 2011-12 base) linked via per-state overlap factors (see `DATA_REGISTRY.md`). Either block can be used **as published** instead, which avoids the splice but limits the window.

**Limitations**:
- State NSDP figures are estimates with known measurement issues (informal-sector coverage, price deflators, revisions).
- Unconditional β-convergence is a weak test; the literature generally finds *conditional* convergence a better description of the data.
- Measurement error in initial income biases β toward finding convergence (the same value appears on both sides).
- ~18 years is a short window for growth convergence, which theory suggests plays out over decades.
- Small states/UTs with volatile, low-base economies can dominate growth-rate rankings.
- Every statistic is unweighted across states; population weighting is DATA REQUIRED.
"""
        )

# =========================================================================
# Tab — Schematic tile map
# =========================================================================
with tab_tile:
    st.header("I · Schematic tile map")
    st.markdown(
        "Every state and union territory as one **equal-size square**, placed on a grid that roughly follows "
        "its position on the map of India, coloured by the indicator and year you choose. Equal tiles stop "
        "large states from visually dominating — Goa and Rajasthan get the same weight. Hover a tile for its "
        "value, rank and data status; **grey hatched tiles have no data** for that indicator and year."
    )
    tc1, tc2 = st.columns([1.6, 1])
    with tc1:
        tile_ind = st.selectbox("Indicator", IND_KEYS, format_func=LABEL.get, key="tile_ind")
    tile_periods = S.periods_for(panel, tile_ind)
    # Default: the latest year with the widest coverage (e.g. 2021-22 for the
    # spliced series, where 2022-23 has only 21 of 32 states).
    _cov = panel[(panel["indicator"] == tile_ind) & panel["value"].notna()].groupby("period")["state"].nunique()
    _default_period = max(tile_periods, key=lambda p: (_cov.get(p, 0), S.fiscal_year_start(p)))
    with tc2:
        tile_period = st.selectbox("Year", tile_periods, index=tile_periods.index(_default_period),
                                   key=f"tile_period_{tile_ind}",
                                   help="Defaults to the latest year with the most states reporting.")
    tmeta = S.INDICATORS[tile_ind]
    tile_rank = S.rank_states(panel, tile_ind, tile_period, states=list(C.TILE_GRID))
    _matched, tile_unmatched = C.tile_coverage(panel.loc[panel["indicator"] == tile_ind, "state"].unique())
    tile_extra = {r.state: {"status": r.status, "note": r.note} for r in tile_rank.itertuples()}
    tf = C.tile_frame(dict(zip(tile_rank["state"], tile_rank["value"])), extra=tile_extra)
    st.caption(
        f"{tmeta.label} — {PRICE_BASIS_TEXT[tmeta.price_basis]}, {UNIT_TEXT.get(tmeta.unit, tmeta.unit)}, "
        f"{tile_period}. Status: {tmeta.status}. Colour runs from cobalt (lowest reporting value) through leaf to "
        "gold (highest); rank 1 = highest value"
        + (" — for unemployment that means the highest rate." if tile_ind == "plfs_unemployment" else ".")
    )
    st.plotly_chart(tile_map_figure(tf, tmeta.label, tmeta.unit, tile_period), width="stretch",
                    key="tile_chart")
    st.caption(C.TILE_CAPTION)
    n_tile_data = int(tf["value"].notna().sum())
    if tile_unmatched:
        st.error("State names in this indicator with no tile (not drawn): " + ", ".join(tile_unmatched))
    else:
        st.caption(
            f"Name check: every state/UT name in this indicator's data maps to a tile "
            f"({n_tile_data} of {len(tf)} tiles have a {tile_period} value)."
        )
    nd = tf[tf["value"].isna()]
    if len(nd):
        with st.expander(f"No data in {tile_period} ({len(nd)} tiles) — why"):
            st.markdown("\n".join(f"- **{r.state}** — {r.note or 'no value in source'}" for r in nd.itertuples()))
    indicator_note(
        "the tile layout", "**A design layout, not data.** Each tile's row and column were placed by hand so "
        "that neighbouring states stay roughly adjacent (north at the top, west on the left); they are not "
        "computed from coordinates. Tiles are not to scale, island UTs (Lakshadweep, Andaman & Nicobar) are "
        "set beside the mainland, and nothing on the map depicts a boundary. A geographic choropleth was not "
        "used because no verified official state-boundary file exists in this repository. The two-letter "
        "labels are this page's own short forms. The grid lives in `analysis/convergence.py` (`TILE_GRID`) "
        "and a test checks that every state name in the data has exactly one tile.", kind="method",
    )

# =========================================================================
# Tab — State comparison workbench
# =========================================================================
with tab_wb:
    st.header("J · State comparison workbench")
    st.markdown(
        "Pick **2 to 5** states/UTs to compare real per-capita NSDP **indexed to a base year (= 100)**, "
        "**year-on-year real growth**, and **nominal** per-capita NSDP levels. Gaps are gaps — a missing year "
        "breaks a line rather than being bridged."
    )
    _wb_default = [s for s in ["Bihar", "Gujarat", "Karnataka", "Uttar Pradesh"] if s in ALL_STATES]
    wb1, wb2, wb3 = st.columns([1.8, 1, 1])
    with wb1:
        wb_states = st.multiselect("States/UTs (2–5)", ALL_STATES, default=_wb_default, max_selections=5,
                                   key="wb_states")
    _wb_years = sorted(nsdp["financial_year"].unique(), key=S.fiscal_year_start)
    with wb2:
        wb_base = st.selectbox("Index base year (= 100)", _wb_years,
                               index=_wb_years.index("2011-12") if "2011-12" in _wb_years else 0, key="wb_base")
    with wb3:
        wb_growth_view = st.radio("Growth chart", ["Bars", "Lines"], horizontal=True, key="wb_growth_view")

    if len(wb_states) < 2:
        st.warning("Select at least two states/UTs (up to five).")
    else:
        real_wide = C.wide_panel(nsdp[nsdp["state"].isin(wb_states)]).reindex(wb_states)
        idx_wide, idx_reasons = C.index_to_base(real_wide, wb_base)
        growth_wide = C.annual_growth(real_wide)
        cur_rows = panel[(panel["indicator"] == "nsdp_pc_current_rbi") & panel["state"].isin(wb_states)]
        cur_periods = S.periods_for(panel, "nsdp_pc_current_rbi")
        cur_wide = pd.DataFrame(np.nan, index=wb_states, columns=cur_periods)
        for r in cur_rows.dropna(subset=["value"]).itertuples(index=False):
            if r.period in cur_wide.columns:
                cur_wide.at[r.state, r.period] = float(r.value)
        colours = {s: SERIES[i % len(SERIES)] for i, s in enumerate(wb_states)}

        # Indexed real per-capita NSDP
        fig_idx = go.Figure()
        for s in wb_states:
            row = idx_wide.loc[s] if s in idx_wide.index else pd.Series(dtype=float)
            if row.notna().any():
                fig_idx.add_trace(go.Scatter(x=_wb_years, y=row.reindex(_wb_years).tolist(), mode="lines+markers",
                                             name=s, line=dict(color=colours[s]), connectgaps=False,
                                             hovertemplate=f"{s}<br>%{{x}}: %{{y:.1f}}<extra></extra>"))
        fig_idx.add_hline(y=100, line_dash="dot", line_color=MUTED)
        fig_idx.update_layout(title=f"Real per-capita NSDP, index {wb_base} = 100 (constant 2011-12 prices, spliced)",
                              xaxis_title="Financial year", yaxis_title=f"Index ({wb_base} = 100)", height=420)
        st.plotly_chart(fig_idx, width="stretch", key="wb_index_chart")
        no_idx = {s: idx_reasons.get(s) or S.missing_reason(panel, s, "nsdp_pc_constant_spliced") or "no data"
                  for s in wb_states if s not in idx_wide.index or idx_wide.loc[s].isna().all()}
        if no_idx:
            st.caption("No index line: " + "; ".join(f"{s} — {r}" for s, r in no_idx.items()))
        if S.fiscal_year_start(wb_base) >= 2011:
            st.caption("Values before 2011-12 are 2004-05-base figures × a per-state link factor (spliced); "
                       "from 2011-12 they are as published.")
        else:
            st.caption("The base year is before 2011-12, so the index base itself is a spliced (derived) value.")

        # Year-on-year growth
        fig_g = go.Figure()
        for s in wb_states:
            row = growth_wide.loc[s].reindex(_wb_years) if s in growth_wide.index else pd.Series(index=_wb_years, dtype=float)
            if not row.notna().any():
                continue
            if wb_growth_view == "Bars":
                fig_g.add_trace(go.Bar(x=_wb_years, y=row.tolist(), name=s, marker_color=colours[s],
                                       hovertemplate=f"{s}<br>%{{x}}: %{{y:.2f}}%<extra></extra>"))
            else:
                fig_g.add_trace(go.Scatter(x=_wb_years, y=row.tolist(), name=s, mode="lines+markers",
                                           line=dict(color=colours[s]), connectgaps=False,
                                           hovertemplate=f"{s}<br>%{{x}}: %{{y:.2f}}%<extra></extra>"))
        fig_g.update_layout(title="Annual real growth of per-capita NSDP, % change on previous financial year",
                            xaxis_title="Financial year", yaxis_title="% a year", height=420, barmode="group")
        st.plotly_chart(fig_g, width="stretch", key="wb_growth_chart")
        st.caption("Growth into 2011-12 compares a 2011-12-base value with a linked 2004-05-base value, so it "
                   "depends on the link factor. A blank year means one of the two years has no value.")

        # Nominal levels
        fig_c = go.Figure()
        cur_absent = []
        for s in wb_states:
            row = cur_wide.loc[s] if s in cur_wide.index else pd.Series(dtype=float)
            if row.notna().any():
                fig_c.add_trace(go.Scatter(x=cur_periods, y=row.tolist(), mode="lines+markers", name=s,
                                           line=dict(color=colours[s]), connectgaps=False,
                                           hovertemplate=f"{s}<br>%{{x}}: ₹%{{y:,.0f}}<extra></extra>"))
            else:
                cur_absent.append(s)
        fig_c.update_layout(title="Per-capita NSDP at current prices (nominal ₹, RBI newer vintage)",
                            xaxis_title="Financial year", yaxis_title="₹ per person, per year (nominal)", height=420)
        st.plotly_chart(fig_c, width="stretch", key="wb_current_chart")
        if cur_absent:
            st.caption("Not in the current-price table: " + "; ".join(
                f"{s} — {S.missing_reason(panel, s, 'nsdp_pc_current_rbi')}" for s in cur_absent))
        st.caption("Nominal levels include inflation — do not compare them with the real index above. "
                   "Source status PARTIAL (screenshot transcription).")

        # CSV with settings
        def _stack(wide: pd.DataFrame, series: str, unit: str, basis: str, method: str) -> pd.DataFrame:
            # melt keeps blank cells as NaN rows ("no data"), unlike stack().
            long = (wide.rename_axis(index="state").rename_axis(columns=None).reset_index()
                    .melt(id_vars="state", var_name="financial_year", value_name="value"))
            return long.assign(series=series, unit=unit, price_basis=basis, method=method)

        wb_export = pd.concat([
            _stack(real_wide, "real per-capita NSDP", "₹ per person per year, 2011-12 prices", "real (constant)",
                   "spliced RBI Table 26 (old base × link factor before 2011-12)"),
            _stack(idx_wide, f"real per-capita NSDP index ({wb_base} = 100)", "index", "real (constant)",
                   "value ÷ base-year value × 100"),
            _stack(growth_wide, "real per-capita NSDP growth, y/y", "% a year", "real (constant)",
                   "(y_t ÷ y_t−1 − 1) × 100, consecutive years only"),
            _stack(cur_wide, "nominal per-capita NSDP", "₹ per person per year, current prices", "nominal (current)",
                   "RBI DBIE screenshot transcription (PARTIAL)"),
        ], ignore_index=True)
        wb_export["availability"] = np.where(wb_export["value"].notna(), "reported", "no data")
        wb_export["setting_states"] = " | ".join(wb_states)
        wb_export["setting_index_base_year"] = wb_base
        wb_export["financial_year_note"] = "Indian financial year, April–March"
        wb_export = wb_export[["state", "financial_year", "series", "value", "unit", "price_basis", "availability",
                               "method", "setting_states", "setting_index_base_year", "financial_year_note"]]
        st.download_button("Download workbench data with settings (CSV)", wb_export.to_csv(index=False).encode("utf-8"),
                           file_name=f"state_workbench_base_{wb_base}.csv", mime="text/csv", key="wb_download")

    st.subheader("Not available yet — DATA REQUIRED")
    st.caption("These comparisons need datasets this repository does not hold. Nothing is drawn for them.")
    _req = [
        ("Sectoral GVA (agriculture / industry / services)",
         "RBI **Handbook of Statistics on Indian States** — Gross State Value Added at constant prices by "
         "industry of origin, by state and year."),
        ("Labour productivity (GVA per worker, by sector)",
         "State GVA by sector (above) **plus** **PLFS** state-level employment by industry (NIC sections, usual "
         "status) to supply the worker counts — both are required."),
        ("Fiscal position (revenue, capital outlay, deficits, debt)",
         "RBI **State Finances: A Study of Budgets** — state-wise revenue receipts, own tax revenue, capital "
         "outlay, gross fiscal deficit and outstanding liabilities."),
        ("Human development",
         "**UNDP / Global Data Lab Subnational Human Development Index** (SHDI and its health, education and "
         "income components) for Indian states."),
    ]
    rc1, rc2 = st.columns(2)
    for i, (title, need) in enumerate(_req):
        with (rc1 if i % 2 == 0 else rc2):
            with st.container(border=True):
                st.markdown(f"**{title} — DATA REQUIRED**\n\nWould be enabled by: {need}")

# =========================================================================
# Tab 2 — Income ranking & unemployment
# =========================================================================
with tab_income:
    # ---------- C. State ranking -----------------------------------------
    st.header("C · State ranking — latest year")

    indicator_note(
        "per-capita NSDP as a welfare measure",
        "**What it measures.** Net State Domestic Product (NSDP) per capita "
        "divides a state's total economic output (minus depreciation) by its "
        "population. It is a measure of *average output per person in the "
        "state economy* — the standard, officially published way to compare "
        "the size of state economies on a population-adjusted basis.\n\n"
        "**How to read a high vs. low value.** A higher per-capita NSDP means "
        "a state produces more economic output per resident, on average. It "
        "is the state-level analogue of national per-capita GDP, and carries "
        "the same broad interpretation: a rough, aggregate indicator of "
        "economic scale relative to population, not a precise welfare score.\n\n"
        "**What it is NOT.** Per-capita NSDP is **not household income** — "
        "output produced within a state's borders is not the same as income "
        "received by its residents (profits can flow to shareholders "
        "elsewhere; migrant workers can send output home to other states). It "
        "also says nothing about **how that output is distributed within the "
        "state** — a state can have a high average and still have most of its "
        "population living far below that average, if income is concentrated "
        "in a small share of residents or a few urban centres. Averages by "
        "construction hide distribution.\n\n"
        "**Caveat.** State output estimates carry their own measurement "
        "issues — informal-sector activity is harder to capture than formal-"
        "sector activity, and price deflators and population estimates used "
        "to convert raw output into real, per-capita terms are themselves "
        "estimates subject to revision (see the splice-method note in "
        "`DATA_REGISTRY.md` for exactly how this series' two base-year "
        "vintages were linked).",
    )

    if not scope_ok:
        st.warning("Select at least one state in the scope controls above.")
    elif nsdp_scoped.empty:
        st.warning("No data for this state/year selection. Widen the scope above.")
    else:
        ranked = regional.rank_states_latest(nsdp_scoped)
        latest_year = nsdp_scoped["financial_year"].max()
        _not_reporting = sorted(set(selected_states) - set(ranked["state"]))
        st.caption(
            f"Real per-capita NSDP (constant 2011-12 prices, spliced series, ₹ per person per year), "
            f"{latest_year} — {len(ranked)} of the {len(selected_states)} state(s) in scope report this year"
            + (f"; no {latest_year} value (not ranked, not zero): {', '.join(_not_reporting)}" if _not_reporting else "")
            + ". To rank by any other state indicator (current prices, unemployment, urban MPCE) "
            "or any single year, use the **Rank any indicator** tab."
        )
        st.dataframe(ranked, width="stretch", hide_index=True)

    st.markdown("---")

    # ---------- D. Unemployment snapshot ---------------------------------
    st.header("D · Unemployment — 2023-24 snapshot")
    st.markdown(
        "**Single cross-section only** — PLFS reports one year here, so this is a snapshot, "
        "not a trend. It cannot itself answer the convergence/divergence question; it's shown "
        "alongside income for context."
    )

    indicator_note(
        "the PLFS unemployment rate",
        "**What it measures.** This is the **usual status** unemployment "
        "rate for persons aged 15 and above, from the government's Periodic "
        "Labour Force Survey (PLFS) — the share of the labour force (people "
        "working or seeking work) who did not have work for a relatively long "
        "reference period (the preceding 365 days under the 'usual status' "
        "definition) but were available for it.\n\n"
        "**What 'unemployed' means here, precisely.** PLFS classifies someone "
        "as unemployed only if they are *actively seeking or available for* "
        "work and currently have none — this excludes people not seeking work "
        "at all (students, those engaged solely in unpaid domestic duties, "
        "retirees), who are counted as 'out of the labour force' rather than "
        "unemployed. It also does not distinguish someone working one hour a "
        "week from someone working full-time — both count as 'employed' under "
        "usual status, which is a known limitation of this kind of headline "
        "unemployment measure, not specific to PLFS or to India.\n\n"
        "**How to read a high vs. a low value.** A higher rate means a larger "
        "share of that state's labour force is both seeking work and not "
        "finding it over the reference period — but a *low* unemployment rate "
        "in a state with widespread informal, low-paid or underemployed work "
        "does not necessarily mean that state's workforce is well off; it can "
        "simply mean very few people can afford to be formally jobless.\n\n"
        "**Why this is a snapshot, not a trend.** Only the 2023-24 PLFS year "
        "is available in this project, so the chart above shows one point in "
        "time for each state — it cannot show whether any state's "
        "unemployment rate is rising, falling, or stable, and should not be "
        "read as doing so.",
    )

    unemp = loaders.load_unemployment_by_state()
    unemp_sorted = unemp[unemp["state"] != "India"].sort_values("unemployment_rate_usual_status_15plus_2023_24", ascending=False)
    fig_u = go.Figure(go.Bar(x=unemp_sorted["state"], y=unemp_sorted["unemployment_rate_usual_status_15plus_2023_24"]))
    fig_u.update_layout(title="Unemployment rate by state, 2023-24 (usual status, 15+)", xaxis_title="", yaxis_title="%", height=450)
    st.plotly_chart(fig_u, width="stretch", key="unemp_chart")

# =========================================================================
# Tab 3 — State lookup & compare
# =========================================================================
with tab_lookup:
    # ---------- E. State lookup ------------------------------------------
    st.header("E · State lookup")
    default_state = ALL_STATES.index("Kerala") if "Kerala" in ALL_STATES else 0
    state = st.selectbox("State or union territory", ALL_STATES, index=default_state, key="lookup_state")
    profile = S.state_profile(panel, state, benchmarks)
    n_with = int(profile["value"].notna().sum())
    st.caption(
        f"{state}: data in {n_with} of {len(IND_KEYS)} indicators. Each card shows the state's most "
        "recent non-blank value; its rank is among the states/UTs that report that same year "
        "(1 = highest value — for unemployment that means the highest rate). This state is also "
        "highlighted on the **Rank any indicator** and **Change over time** tabs."
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

    # ---------- F. Compare states ----------------------------------------
    st.header("F · Compare states side by side")
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
        st.dataframe(wide, width="stretch")
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

        cmp_tabs = st.tabs([LABEL[k] for k in cmp_inds])
        for cmp_tab, key in zip(cmp_tabs, cmp_inds):
            cmeta = S.INDICATORS[key]
            csub = cmp[cmp["indicator"] == key]
            with cmp_tab:
                periods_used = sorted({p for p in csub["period"] if isinstance(p, str)}, key=S.fiscal_year_start)
                cbm = S.benchmark_for(benchmarks, key, periods_used[0]) if len(periods_used) == 1 else None
                fig = bar_with_gaps(
                    list(csub["state"]), list(csub["value"]), cmeta.unit, benchmark=cbm,
                    benchmark_label=f"National (source): {fmt(cbm, cmeta.unit)}" if cbm is not None else "",
                    title=f"{cmeta.label} — {', '.join(periods_used) if periods_used else 'no data'}",
                )
                if key in MULTI_YEAR:
                    c_bar, c_line = st.columns(2)
                else:
                    c_bar, c_line = st.container(), None
                with c_bar:
                    st.plotly_chart(fig, width="stretch", key=f"cmp_bar_{key}")
                    if cbm is None:
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
                    lf.update_layout(title=f"{cmeta.label} over time", height=380, yaxis_title=cmeta.unit,
                                     xaxis_title="Financial year")
                    with c_line:
                        st.plotly_chart(lf, width="stretch", key=f"cmp_line_{key}")
                        if absent:
                            st.caption("Not in this series (no line drawn): " + ", ".join(
                                f"{s} — {S.missing_reason(panel, s, key)}" for s in absent))
                        st.caption("Gaps in a line are blank cells in the source, not zeros.")

# =========================================================================
# Tab 4 — Rank any indicator
# =========================================================================
with tab_rank:
    st.header("G · Rank every state by one indicator")
    r1, r2, r3 = st.columns([1.6, 1, 1])
    with r1:
        rank_ind = st.selectbox("Indicator", IND_KEYS, format_func=LABEL.get, key="rank_ind")
    rank_periods = S.periods_for(panel, rank_ind)
    with r2:
        rank_period = st.selectbox("Year", rank_periods, index=len(rank_periods) - 1, key="rank_period")
    with r3:
        order = st.radio("Order", ["Highest first", "Lowest first"], key="rank_order")
    rmeta = S.INDICATORS[rank_ind]
    ranked_ind = S.rank_states(panel, rank_ind, rank_period, ascending=(order == "Lowest first"), states=ALL_STATES)
    n_rep = int(ranked_ind["n_reporting"].iloc[0])
    rbm = S.benchmark_for(benchmarks, rank_ind, rank_period)
    st.caption(
        f"{n_rep} of {len(ALL_STATES)} states/UTs report {rmeta.label.lower()} for {rank_period}; the "
        f"other {len(ALL_STATES) - n_rep} are listed at the bottom with the reason. "
        f"{state} (from the State lookup tab) is highlighted. "
        + (f"National figure from the source: {fmt(rbm, rmeta.unit)}." if rbm is not None else S.NO_BENCHMARK + ".")
    )
    rank_fig = bar_with_gaps(
        list(ranked_ind["state"]), list(ranked_ind["value"]), rmeta.unit, highlight=state, horizontal=True,
        benchmark=rbm, benchmark_label=f"National (source): {fmt(rbm, rmeta.unit)}" if rbm is not None else "",
        title=f"{rmeta.label}, {rank_period}", height=max(420, 24 * len(ranked_ind) + 120),
    )
    st.plotly_chart(rank_fig, width="stretch", key="rank_chart")
    rank_view = pd.DataFrame({
        "Rank": ranked_ind["rank"].map(lambda r: "—" if pd.isna(r) else str(int(r))),
        "State/UT": ranked_ind["state"],
        "Value": [fmt(v, rmeta.unit) for v in ranked_ind["value"]],
        "Status": ranked_ind["status"],
        "Note": ranked_ind["note"],
    })
    st.dataframe(rank_view, hide_index=True, width="stretch")

# =========================================================================
# Tab 5 — Change over time
# =========================================================================
with tab_change:
    st.header("H · Change over time — first vs latest observation")
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
        st.caption(f"CAGR computable for {n_valid} of {len(hc)} selected states/UTs in {window[0]} → {window[1]}. "
                   f"{state} (from the State lookup tab) is highlighted.")
        hfig = bar_with_gaps(
            list(hc["state"]), list(hc["cagr_pct"]), "%", horizontal=True, highlight=state,
            title=f"CAGR of {hmeta.label}, {window[0]} → {window[1]}", height=max(380, 24 * len(hc) + 120),
        )
        hfig.update_layout(xaxis_title="% per year")
        st.plotly_chart(hfig, width="stretch", key="hist_chart")
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
        st.dataframe(hist_view, hide_index=True, width="stretch")

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

# =========================================================================
# Tab 6 — Indicator inventory & sources
# =========================================================================
with tab_inv:
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
    st.dataframe(inv_view, hide_index=True, width="stretch")
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
        "Map view: no verified India state-boundary file (GeoJSON) exists in this repository, so there is "
        "no geographic choropleth. The **Tile map** tab shows every indicator on a schematic tile grid "
        "instead — tiles are not to scale and do not depict boundaries."
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
    for i, (key, imeta) in enumerate(S.INDICATORS.items()):
        with (g1 if i % 2 == 0 else g2):
            indicator_note(imeta.label, imeta.explainer)

st.markdown("---")
footnote(
    "Sigma/beta convergence are standard growth-economics techniques (Barro & Sala-i-Martin), applied here "
    "to real RBI data. Results are descriptive statistics of this specific dataset and period, not causal claims "
    "about why states converge or diverge. Sigma convergence uses a balanced panel by default; all cross-state "
    "statistics are unweighted (population weighting is DATA REQUIRED)."
)
footnote(
    "Sources: RBI Handbook of Statistics on Indian States (Table 26) and DBIE; PLFS 2023-24; MoSPI "
    "HCES 2023-24 Statement 7; state_gsdp_nsdp_percapita.csv (source unconfirmed). Ranks, "
    "differences from the national figure, percentage changes and CAGRs are computed on this page "
    "from those values; nothing is estimated or interpolated. See DATA_REGISTRY.md for provenance."
)

sources_panel("rbi_nsdp_constant", "rbi_nsdp_spliced", "rbi_nsdp_current", "state_gsdp_nsdp_pc", "plfs_unemployment", "hces_mpce")
