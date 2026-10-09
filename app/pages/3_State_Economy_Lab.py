"""State Economy Lab.

One page for everything state-level in this repository.

Research question: are Indian states converging economically or becoming
more divergent? (sigma and beta convergence on the spliced per-capita NSDP
series, plus the latest-year ranking and the PLFS unemployment snapshot.)

Alongside it, an explorer for every real state-level indicator: a per-state
profile, side-by-side comparison, a full ranking by any indicator, and
first-vs-latest change for the series that have more than one year. Those
values come from analysis/states.py, which reads data/raw/ through
data_sources/loaders.py -- nothing on this page is estimated, filled or
typed in, and a missing value is shown as "no data", never as 0.
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

from analysis import regional
from analysis import states as S
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote, GOLD, LEAF, MUTED,
)
from app.components.glossary import indicator_note
from app.components import hairline_display
from data_sources import loaders

setup("State Economy Lab", accent=LEAF)

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
    st.markdown("## State Economy Lab")
    st.caption("Sections")
    st.markdown(
        "- Branches · fastest growers vs. richest states\n"
        "- Scope (convergence & income ranking)\n"
        "- **Convergence (σ & β)** tab\n"
        "  - A · Sigma convergence\n"
        "  - B · Beta convergence\n"
        "- **Income ranking & unemployment** tab\n"
        "  - C · State ranking, latest year\n"
        "  - D · Unemployment snapshot\n"
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
    "range re-runs them on a sub-period you choose (e.g. only the years "
    "since 2015-16) instead of the full 2004-05→2022-23 window. The ranking "
    "table in section C also respects both: it shows the latest year "
    "*within your chosen range*, for only the states you selected.\n\n"
    "**Why this is useful.** The headline sigma/beta results on the full "
    "panel can mask sub-period or sub-group patterns — a sub-period "
    "slider lets you check, say, whether convergence looks different "
    "before vs. after a particular year, and a state subset lets you ask "
    "the question for a specific group of states rather than all of "
    "India at once.\n\n"
    "**Caveat.** Sigma convergence needs at least 5 states reporting in a "
    "year to compute a coefficient of variation for that year, and beta "
    "convergence needs at least 5 states with valid first/last values "
    "overall — pick too few states or too narrow a year range and the "
    "page will honestly report 'insufficient data' rather than a "
    "fabricated result.",
)

scope_ok = bool(selected_states)
i0, i1 = years_list.index(year_range[0]), years_list.index(year_range[1])
years_in_scope = set(years_list[i0:i1 + 1])
nsdp_scoped = nsdp[nsdp["state"].isin(selected_states) & nsdp["financial_year"].isin(years_in_scope)]

st.markdown("---")

(tab_conv, tab_income, tab_lookup, tab_rank, tab_change, tab_inv) = st.tabs([
    "Convergence (σ & β)",
    "Income ranking & unemployment",
    "State lookup & compare",
    "Rank any indicator",
    "Change over time",
    "Indicator inventory & sources",
])

# =========================================================================
# Tab 1 — Convergence
# =========================================================================
with tab_conv:
    # ---------- A. Sigma convergence ------------------------------------
    st.header("A · Sigma (σ) convergence — is dispersion falling?")
    st.markdown(
        "**Sigma convergence** asks whether the *spread* of state incomes is shrinking over "
        "time, measured by the cross-sectional **coefficient of variation** (CV = population "
        "std / mean, as a %) of per-capita NSDP each year. A falling CV means states are "
        "converging toward each other; a rising CV means they're spreading apart."
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
        "says 'converging' and beta also says 'converging', that is a "
        "consistent, mutually reinforcing picture. If they disagree — as the "
        "callout further down discusses for this dataset — it means the "
        "convergence story is more complicated than 'states are/aren't "
        "converging': look at which specific states are driving each test "
        "(the beta scatter plot) before drawing a single headline conclusion.\n\n"
        "**Caveat.** Both are purely descriptive statistics about this income "
        "series over this period. Neither test, by itself, identifies *why* "
        "any convergence or divergence occurs (trade, migration, policy, "
        "technology diffusion are all candidate explanations in the growth "
        "literature, and none is tested here).",
    )

    sigma = regional.sigma_convergence(nsdp_scoped) if scope_ok else None
    if not scope_ok:
        st.warning("Select at least one state in the scope controls above.")
    elif sigma.by_year.empty or sigma.by_year["cv_pct"].notna().sum() < 2:
        st.warning(
            "Insufficient data for sigma convergence with this state/year selection "
            "(needs at least 5 reporting states in at least 2 years). Widen the "
            "scope above."
        )
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            stat_card("Direction (selected scope)", sigma.direction.upper())
        with c2:
            stat_card("Trend", f"{sigma.trend_slope_pct_per_year:+.3f} pp CV / year")
        with c3:
            first_cv = sigma.by_year.iloc[0]["cv_pct"]
            last_cv = sigma.by_year.iloc[-1]["cv_pct"]
            stat_card(f"{sigma.by_year.iloc[0]['financial_year']} → {sigma.by_year.iloc[-1]['financial_year']}", f"{first_cv:.1f}% → {last_cv:.1f}%")

        fig_sigma = go.Figure()
        fig_sigma.add_trace(go.Scatter(x=sigma.by_year["financial_year"], y=sigma.by_year["cv_pct"], mode="lines+markers", name="CV (%)"))
        fig_sigma.update_layout(title=f"Cross-state coefficient of variation of per-capita NSDP ({len(selected_states)} state(s) selected)", xaxis_title="Financial year",
                                 yaxis_title="CV (%)", height=420)
        st.plotly_chart(fig_sigma, use_container_width=True, key="sigma_chart")

    callout(
        "Read this carefully: the trend is mild and non-monotonic (dispersion rises and falls "
        "within the period, not a clean line). A small negative slope over ~18 years is weak "
        "evidence, not proof of strong convergence.",
        kind="note",
    )

    st.markdown("---")

    # ---------- B. Beta convergence --------------------------------------
    st.header("B · Beta (β) convergence — do poorer states grow faster?")
    st.markdown(
        "**Beta convergence** asks whether states with *lower* initial income grew *faster* "
        "over the period — the mechanism that would produce sigma convergence if it holds "
        "strongly enough. This is the simplest possible specification: each state's average "
        "annual growth rate, regressed against its log initial income, with **no control "
        "variables**. A negative slope is consistent with (unconditional) convergence."
    )

    beta = regional.beta_convergence(nsdp_scoped) if scope_ok else None
    if not scope_ok:
        st.warning("Select at least one state in the scope controls above.")
    elif beta.direction == "insufficient data" or beta.per_state.empty:
        st.warning(
            "Insufficient data for beta convergence with this state/year selection "
            "(needs at least 5 states with valid first/last values). Widen the "
            "scope above."
        )
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            stat_card("Direction", beta.direction.upper())
        with c2:
            stat_card("Slope", f"{beta.slope:+.3f}")
        with c3:
            stat_card("R²", f"{beta.r_squared:.3f}")

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
        y_fit = beta.slope * np.log(x_range) + beta.intercept
        fig_beta.add_trace(go.Scatter(x=x_range, y=y_fit, mode="lines", name="OLS fit", line=dict(dash="dash")))
        fig_beta.update_layout(title=f"Average annual growth vs. initial per-capita income, log scale ({len(selected_states)} state(s) selected)", xaxis_title="Initial per-capita NSDP (₹, log scale)",
                                xaxis_type="log", yaxis_title="Average annual growth (%)", height=460)
        st.plotly_chart(fig_beta, use_container_width=True, key="beta_chart")

        if beta.direction != sigma.direction.replace("ing", "ing") and "insufficient" not in (beta.direction, sigma.direction):
            callout(
                f"**Sigma says '{sigma.direction}', beta says '{beta.direction}'** — and that's not a "
                "contradiction in the method. Beta convergence is a *necessary but not sufficient* "
                "condition for sigma convergence: a few fast-growing poor states and a few slow "
                "rich states can coexist with the *overall* dispersion barely moving, especially "
                f"with an R² this low ({beta.r_squared:.2f} — most of the variation in growth "
                "rates is *not* explained by initial income level). Treat both results as weak, "
                "and don't average them into one verdict.",
                kind="warn",
            )

    st.markdown("---")
    with st.expander("Methodology & limitations"):
        st.markdown(
            """
**Sigma convergence formula**: `CV_t = std(income_i,t) / mean(income_i,t) × 100`, across all states `i` with data in year `t`. Years with fewer than 5 reporting states are dropped.

**Beta convergence formula**: `growth_i = (ln(income_i,T) − ln(income_i,0)) / (T − 0)`, regressed via OLS against `ln(income_i,0)`. Unconditional — no controls for human capital, investment rate, institutions, etc., all of which the literature shows matter.

**Data**: per-capita NSDP is a **spliced** series — two RBI Handbook base-year series (2004-05 base, 2011-12 base) linked via an overlap-year factor. See `DATA_REGISTRY.md` for the exact method and per-state link factors. This is a legitimate standard technique, but it is still a derived series, not a single official publication.

**Limitations**:
- State GDP/NSDP figures are themselves estimates with known measurement issues (informal-sector coverage, price deflators, revisions).
- Unconditional beta convergence, as shown here, is a weak test — the growth-economics literature generally finds *conditional* convergence (controlling for savings rates, education, institutions) is a better description of the data than unconditional convergence.
- 21-22 years is a short window for growth convergence, which theory suggests plays out over multiple decades.
- Small states/UTs with volatile, low-base economies (Sikkim, Chandigarh) can dominate growth-rate rankings — a result driven by one or two small economies isn't the same as a broad-based pattern.
"""
        )

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
        st.caption(
            f"Per-capita NSDP (constant prices, spliced series), {latest_year} — "
            f"{len(selected_states)} of {len(all_states)} state(s) shown per the scope controls above. "
            "To rank by any other state indicator (current prices, unemployment, urban MPCE) "
            "or any single year, use the **Rank any indicator** tab."
        )
        st.dataframe(ranked, use_container_width=True, hide_index=True)

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
    st.plotly_chart(fig_u, use_container_width=True, key="unemp_chart")

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
                    st.plotly_chart(fig, use_container_width=True, key=f"cmp_bar_{key}")
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
                        st.plotly_chart(lf, use_container_width=True, key=f"cmp_line_{key}")
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
    st.plotly_chart(rank_fig, use_container_width=True, key="rank_chart")
    rank_view = pd.DataFrame({
        "Rank": ranked_ind["rank"].map(lambda r: "—" if pd.isna(r) else str(int(r))),
        "State/UT": ranked_ind["state"],
        "Value": [fmt(v, rmeta.unit) for v in ranked_ind["value"]],
        "Status": ranked_ind["status"],
        "Note": ranked_ind["note"],
    })
    st.dataframe(rank_view, hide_index=True, use_container_width=True)

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
    for i, (key, imeta) in enumerate(S.INDICATORS.items()):
        with (g1 if i % 2 == 0 else g2):
            indicator_note(imeta.label, imeta.explainer)

st.markdown("---")
footnote(
    "Sigma/beta convergence are standard growth-economics techniques (Barro & Sala-i-Martin), applied here "
    "to real RBI data. Results are descriptive statistics of this specific dataset and period, not causal claims "
    "about why states converge or diverge."
)
footnote(
    "Sources: RBI Handbook of Statistics on Indian States (Table 26) and DBIE; PLFS 2023-24; MoSPI "
    "HCES 2023-24 Statement 7; state_gsdp_nsdp_percapita.csv (source unconfirmed). Ranks, "
    "differences from the national figure, percentage changes and CAGRs are computed on this page "
    "from those values; nothing is estimated or interpolated. See DATA_REGISTRY.md for provenance."
)
