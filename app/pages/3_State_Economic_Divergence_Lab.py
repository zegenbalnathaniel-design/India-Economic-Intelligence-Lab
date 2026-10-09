"""State Economic Divergence Lab.

Research question: are Indian states converging economically or becoming
more divergent?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from analysis import regional
from app.components.theme import setup, kicker, callout, source_badge, stat_card, footnote, LEAF
from app.components.glossary import indicator_note
from app.components import hairline_display
from data_sources import loaders

setup("State Economic Divergence Lab", accent=LEAF)

with st.sidebar:
    st.markdown("## State Divergence Lab")
    st.caption("Sections")
    st.markdown(
        "- A · Sigma convergence\n"
        "- B · Beta convergence\n"
        "- C · State ranking\n"
        "- D · Unemployment snapshot"
    )
    st.markdown("---")
    st.caption("Status: real data, see badges below")

kicker("STATE DIVERGENCE · INDIA")
st.title("Are Indian states converging or diverging?")
st.markdown(
    "Per-capita income across Indian states, 2004-05 to 2022-23 — real data from the "
    "RBI Handbook of Statistics on Indian States, with two standard convergence tests "
    "from the growth-economics literature (Barro & Sala-i-Martin)."
)
source_badge("RBI Handbook of Statistics on Indian States, Table 26", "PLFS 2023-24", "VERIFIED / PARTIAL — see Data page")

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
st.subheader("Scope")
st.caption(
    "These two controls re-run the real sigma/beta convergence tests and the "
    "ranking table below on whichever states and years you choose — not a "
    "cosmetic filter. Defaults are every state and the full available window "
    "(unchanged from the page's original behaviour)."
)
all_states = sorted(nsdp["state"].unique())
years_list = sorted(nsdp["financial_year"].unique())

scope_c1, scope_c2 = st.columns([1.4, 1])
with scope_c1:
    selected_states = st.multiselect(
        "States included (sigma/beta convergence & ranking)",
        all_states, default=all_states,
    )
with scope_c2:
    year_range = st.select_slider(
        "Financial year range (sigma/beta convergence & ranking)",
        options=years_list, value=(years_list[0], years_list[-1]),
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

if not selected_states:
    st.warning("Select at least one state.")
    st.stop()

i0, i1 = years_list.index(year_range[0]), years_list.index(year_range[1])
years_in_scope = set(years_list[i0:i1 + 1])
nsdp_scoped = nsdp[nsdp["state"].isin(selected_states) & nsdp["financial_year"].isin(years_in_scope)]

st.markdown("---")

# ---------- A. Sigma convergence ----------------------------------------
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

sigma = regional.sigma_convergence(nsdp_scoped)
if sigma.by_year.empty or sigma.by_year["cv_pct"].notna().sum() < 2:
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
    st.plotly_chart(fig_sigma, use_container_width=True)

callout(
    "Read this carefully: the trend is mild and non-monotonic (dispersion rises and falls "
    "within the period, not a clean line). A small negative slope over ~18 years is weak "
    "evidence, not proof of strong convergence.",
    kind="note",
)

st.markdown("---")

# ---------- B. Beta convergence ------------------------------------------
st.header("B · Beta (β) convergence — do poorer states grow faster?")
st.markdown(
    "**Beta convergence** asks whether states with *lower* initial income grew *faster* "
    "over the period — the mechanism that would produce sigma convergence if it holds "
    "strongly enough. This is the simplest possible specification: each state's average "
    "annual growth rate, regressed against its log initial income, with **no control "
    "variables**. A negative slope is consistent with (unconditional) convergence."
)

import numpy as np

beta = regional.beta_convergence(nsdp_scoped)
if beta.direction == "insufficient data" or beta.per_state.empty:
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
    st.plotly_chart(fig_beta, use_container_width=True)

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

# ---------- C. State ranking ----------------------------------------------
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

if nsdp_scoped.empty:
    st.warning("No data for this state/year selection. Widen the scope above.")
else:
    ranked = regional.rank_states_latest(nsdp_scoped)
    latest_year = nsdp_scoped["financial_year"].max()
    st.caption(
        f"Per-capita NSDP (constant prices, spliced series), {latest_year} — "
        f"{len(selected_states)} of {len(all_states)} state(s) shown per the scope controls above."
    )
    st.dataframe(ranked, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------- D. Unemployment snapshot --------------------------------------
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
st.plotly_chart(fig_u, use_container_width=True)

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

footnote(
    "Sigma/beta convergence are standard growth-economics techniques (Barro & Sala-i-Martin), applied here "
    "to real RBI data. Results are descriptive statistics of this specific dataset and period, not causal claims "
    "about why states converge or diverge."
)
