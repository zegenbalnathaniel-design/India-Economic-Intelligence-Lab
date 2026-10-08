"""State Economic Divergence Lab.

Research question: are Indian states converging economically or becoming
more divergent?
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from analysis import regional
from app.components.theme import setup, kicker, callout, source_badge, stat_card, footnote, LEAF
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

# ---------- A. Sigma convergence ----------------------------------------
st.header("A · Sigma (σ) convergence — is dispersion falling?")
st.markdown(
    "**Sigma convergence** asks whether the *spread* of state incomes is shrinking over "
    "time, measured by the cross-sectional **coefficient of variation** (CV = population "
    "std / mean, as a %) of per-capita NSDP each year. A falling CV means states are "
    "converging toward each other; a rising CV means they're spreading apart."
)

sigma = regional.sigma_convergence(nsdp)
c1, c2, c3 = st.columns(3)
with c1:
    stat_card("Direction (whole period)", sigma.direction.upper())
with c2:
    stat_card("Trend", f"{sigma.trend_slope_pct_per_year:+.3f} pp CV / year")
with c3:
    first_cv = sigma.by_year.iloc[0]["cv_pct"]
    last_cv = sigma.by_year.iloc[-1]["cv_pct"]
    stat_card(f"{sigma.by_year.iloc[0]['financial_year']} → {sigma.by_year.iloc[-1]['financial_year']}", f"{first_cv:.1f}% → {last_cv:.1f}%")

fig_sigma = go.Figure()
fig_sigma.add_trace(go.Scatter(x=sigma.by_year["financial_year"], y=sigma.by_year["cv_pct"], mode="lines+markers", name="CV (%)"))
fig_sigma.update_layout(title="Cross-state coefficient of variation of per-capita NSDP", xaxis_title="Financial year",
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

beta = regional.beta_convergence(nsdp)
c1, c2, c3 = st.columns(3)
with c1:
    stat_card("Direction", beta.direction.upper())
with c2:
    stat_card("Slope", f"{beta.slope:+.3f}")
with c3:
    stat_card("R²", f"{beta.r_squared:.3f}")

fig_beta = go.Figure()
fig_beta.add_trace(go.Scatter(
    x=beta.per_state["initial_value"], y=beta.per_state["avg_annual_growth_pct"],
    mode="markers+text", text=beta.per_state["state"], textposition="top center",
    marker=dict(size=9),
))
import numpy as np
x_range = np.linspace(beta.per_state["initial_value"].min(), beta.per_state["initial_value"].max(), 50)
y_fit = beta.slope * np.log(x_range) + beta.intercept
fig_beta.add_trace(go.Scatter(x=x_range, y=y_fit, mode="lines", name="OLS fit", line=dict(dash="dash")))
fig_beta.update_layout(title="Average annual growth vs. initial per-capita income (log scale)", xaxis_title="Initial per-capita NSDP (₹, log scale)",
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
ranked = regional.rank_states_latest(nsdp)
latest_year = nsdp["financial_year"].max()
st.caption(f"Per-capita NSDP (constant prices, spliced series), {latest_year}")
st.dataframe(ranked, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------- D. Unemployment snapshot --------------------------------------
st.header("D · Unemployment — 2023-24 snapshot")
st.markdown(
    "**Single cross-section only** — PLFS reports one year here, so this is a snapshot, "
    "not a trend. It cannot itself answer the convergence/divergence question; it's shown "
    "alongside income for context."
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
