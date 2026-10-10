"""Limitations — explicit, categorised, cross-referenced to modules.

Intellectual honesty is more important than making the results look
impressive. This page exists so limitations are visible, not buried in
tooltips or the README.
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
import streamlit as st

from app.components.theme import setup, kicker, callout, footnote
from app.components import hairline_display
from analysis import convergence
from data_sources import loaders


setup("Limitations")


with st.sidebar:
    st.markdown("## Limitations")
    st.caption("Categorised by module")


kicker("Limitations")
st.title("What this site can and cannot say")
st.markdown(
    "Every research project has boundaries. Below they are stated "
    "explicitly, categorised, and mapped to the module where they bite."
)

fig_col, text_col = st.columns([2, 3])
with fig_col:
    hairline_display.render("vault")
with text_col:
    st.markdown(
        "**Six kinds of limits, not one.** Turn the dial — then read them "
        "stated plainly below, by category, not buried in a tooltip:"
    )
    st.markdown(
        "- **Data** — what's missing, proxied, or a single cross-section\n"
        "- **Measurement** — what a number is actually counting\n"
        "- **Causality** — what a correlation cannot tell you\n"
        "- **Assumptions** — what a user-set slider is standing in for\n"
        "- **External validity** — what a result does and doesn't generalise to\n"
        "- **Time** — what's current, what's dated, what's a single snapshot"
    )
    st.caption("A model is not reality. It is a way of asking questions about reality.")

st.markdown("---")

st.header("Cross-cutting")
callout(
    "Correlation is not causation. No coefficient on this site — Spearman ρ, "
    "regime-conditional ρ, or otherwise — is a causal estimate. Causal "
    "claims require an identification strategy this MVP does not implement.",
    kind="warn",
)


st.header("Wealth & inequality module")
wealth_lim = pd.DataFrame([
    {"Limitation": "Historical returns are not future returns",
     "Where it bites": "Composition effect, asset allocation comparison",
     "Mitigation": "Every return is user-editable; Monte Carlo overlay shows dispersion"},
    {"Limitation": "Deterministic returns (default view)",
     "Where it bites": "Point estimate of final wealth is a central tendency, not a forecast",
     "Mitigation": "Monte Carlo module renders the 5-95% band"},
    {"Limitation": "Correlations and tail heaviness are assumptions, not estimates",
     "Where it bites": "Monte Carlo band width depends on the correlation matrix and t degrees of freedom you set",
     "Mitigation": "Correlated and fat-tailed (Student-t) draws are available and checked for "
                              "consistency; estimating the correlations needs Indian asset-return history"},
    {"Limitation": "No fees, taxes, or transaction costs",
     "Where it bites": "Final wealth is over-stated relative to net-of-costs reality",
     "Mitigation": "Documented; parameterisation is a natural extension"},
    {"Limitation": "Gini is a lower bound",
     "Where it bites": "Built from five published group shares, so inequality within each group is ignored",
     "Mitigation": "Labelled as a lower bound; a full Gini needs AIDIS / NSS household microdata"},
    {"Limitation": "No figures for the Bottom 10% or P10–P50",
     "Where it bites": "The two lowest Riffle cards and table rows",
     "Mitigation": "Shown as DATA REQUIRED; WID.world downloads for p0p10 and p10p50 would fill them"},
    {"Limitation": "Top-tail wealth undercoverage in Indian survey data",
     "Where it bites": "Any Gini or top-share statistic",
     "Mitigation": "WIL combines AIDIS with Forbes rich lists for the top tail; the authors still "
                              "describe their results as a lower bound"},
    {"Limitation": "Asset-valuation uncertainty (property, gold)",
     "Where it bites": "Real-world household wealth is measured with error",
     "Mitigation": "Model uses target values, not marked-to-market"},
])
st.dataframe(wealth_lim, hide_index=True, width="stretch")


st.header("Banking & monetary policy module")
banking_lim = pd.DataFrame([
    {"Limitation": "Illustrative panel in the MVP",
     "Where it bites": "iBFPI levels and the ρ estimate reflect the synthetic generator",
     "Mitigation": "Panel is CSV-replaceable; loader has no hard-coded values"},
    {"Limitation": "Small sample (n ≈ 26 quarters)",
     "Where it bites": "Regime-conditional ρ has n well below rules-of-thumb",
     "Mitigation": "n reported alongside every ρ; p-values shown"},
    {"Limitation": "Autocorrelation in quarterly series",
     "Where it bites": "Spearman p-values understate uncertainty on serially correlated series",
     "Mitigation": "Newey–West (HAC) errors in the Robustness regression; the Spearman p-values "
                              "themselves are unadjusted"},
    {"Limitation": "No macro controls in the fixed-effects regression",
     "Where it bites": "The repo-rate slope may pick up the business cycle",
     "Mitigation": "Stated next to the table; needs quarterly GDP growth and CPI series"},
    {"Limitation": "Cross-bank accounting differences",
     "Where it bites": "IND-AS vs prior AS transitions create structural breaks in the raw series",
     "Mitigation": "Per-bank standardisation absorbs level differences but not slope breaks"},
    {"Limitation": "Regime threshold (±25bp on 3-quarter change) is a modelling choice",
     "Where it bites": "Alternative thresholds re-label periods and change ρ per regime",
     "Mitigation": "Documented; parameter can be exposed if useful"},
    {"Limitation": "Survivorship bias in the bank subset",
     "Where it bites": "Only extant large private/public banks are in the panel — small/failed banks are absent",
     "Mitigation": "Documented; scope is stated as five specific banks"},
])
st.dataframe(banking_lim, hide_index=True, width="stretch")


def _robustness_text() -> str:
    rob = convergence.sigma_robustness(loaders.load_nsdp_spliced())
    full = rob[rob["panel"].str.startswith("full")]
    alt = rob[rob["panel"].str.startswith("all states")]
    if full.empty or alt.empty:
        return "Balanced panel by default; the all-states comparison is shown in the State Economy Lab"
    n_all, n_bal = int(alt["n_states"].iloc[0]), int(full["n_states"].iloc[0])
    rising = int((alt["verdict"] == "rising").sum())
    cv = alt.set_index("measure").loc["cv", "verdict"]
    return (f"Headline uses the balanced panel ({n_bal} states with data in every year to {full['end'].iloc[0]}); "
            f"{n_all - n_bal} states are dropped for missing the last year. Keeping all {n_all} states to "
            f"{alt['end'].iloc[0]}, {rising} of {len(alt)} dispersion measures rise and the CV is {cv} — "
            "both comparisons are shown")


st.header("States, housing and structural change")
regional_lim = pd.DataFrame([
    {"Limitation": "The convergence verdict depends on which states are compared",
     "Where it bites": "σ-convergence headline (Home, State Lab, Research Library)",
     "Mitigation": _robustness_text()},
    {"Limitation": "Unweighted across states",
     "Where it bites": "σ and β treat a small state the same as Uttar Pradesh",
     "Mitigation": "Stated on the page; population-weighted dispersion needs a state population series "
                   "(DATA REQUIRED)"},
    {"Limitation": "Spliced constant-price series",
     "Where it bites": "Real per-capita NSDP across the 2004-05 and 2011-12 bases",
     "Mitigation": "Splice method documented; the as-published base-year blocks can be used instead"},
    {"Limitation": "β regression is a small cross-section with no controls",
     "Where it bites": "β slope, speed of convergence, half-life",
     "Mitigation": "n, SE (classical or HC1), CI and p shown; no half-life when the slope is not significant"},
    {"Limitation": "City household income is an average, for 28 of the 50 RESIDEX cities",
     "Where it bites": "Price-to-income and EMI-to-income in the Housing Lab",
     "Mitigation": "Averages are pulled up by high earners, so ratios understate a typical household's burden; "
                   "other cities can only use the per-person state proxies. RESIDEX prices are assessment "
                   "prices (₹ per sq. ft of carpet area), not transactions"},
    {"Limitation": "Employment shares are ILO modelled estimates, not PLFS",
     "Where it bites": "Structural Transformation Lab: relative labour productivity, sector gaps",
     "Mitigation": "Labelled ILO modelled; value-added shares are of GDP at market prices, so sectors sum "
                   "to less than 100 and the residual is shown"},
    {"Limitation": "Live World Bank series",
     "Where it bites": "Structural Transformation, Inequality & Financialisation, India Macro & World",
     "Mitigation": "If the API cannot be reached the page says DATA UNAVAILABLE; no cached or invented values"},
])
st.dataframe(regional_lim, hide_index=True, width="stretch")


st.header("Financialisation, the simulator and the regression workbench")
tools_lim = pd.DataFrame([
    {"Limitation": "No household-group breakdown of financial assets",
     "Where it bites": "Whether financial gains are broad-based",
     "Mitigation": "AIDIS by wealth group, AMFI folios/SIPs and NSDL/CDSL demat data are DATA REQUIRED; "
                   "folios and demat accounts are not unique investors"},
    {"Limitation": "Billionaire lists and WIL top shares are not independent",
     "Where it bites": "Correlation of Forbes wealth with the Top 0.1% share",
     "Mitigation": "Stated next to the result; WIL uses rich lists for the top tail"},
    {"Limitation": "Simulator parameters come from different studies, periods and methods",
     "Where it bites": "Every Macro Transmission Simulator output",
     "Mitigation": "Labelled HYPOTHETICAL; links are added up linearly with no general-equilibrium "
                   "consistency; some defaults are single-episode ratios, not general elasticities"},
    {"Limitation": "Simulator citations were checked through search results, not the source documents",
     "Where it bites": "All cited defaults",
     "Mitigation": "Each row records the quote and how it was checked; values that could not be confirmed "
                   "were removed and trade elasticities are left blank (DATA REQUIRED)"},
    {"Limitation": "Regression workbench is OLS on short samples",
     "Where it bites": "Coefficients, p-values, R²",
     "Mitigation": "Robust (HC1, Newey–West) errors, diagnostics, a spurious-regression check for trending "
                   "series; no causal or panel methods"},
    {"Limitation": "Research Library text is generated by fixed rules",
     "Where it bites": "Findings and interpretation in each investigation",
     "Mitigation": "Every sentence is built from computed values; facts, statistics, interpretation and "
                   "hypotheses are kept apart; nothing claims cause and effect"},
])
st.dataframe(tools_lim, hide_index=True, width="stretch")


st.header("What the site does not claim")
st.markdown(
    "- It does **not** claim to identify the causal effect of monetary "
    "policy on bank performance.\n"
    "- It does **not** claim that any specific asset is universally better.\n"
    "- It does **not** claim r > g mechanically produces individual "
    "inequality.\n"
    "- It does **not** provide personalised financial advice.\n"
    "- It does **not** present iBFPI as an established or industry-standard "
    "index.\n"
    "- It does **not** forecast: the Macro Transmission Simulator shows "
    "hypothetical shocks with cited sensitivities, not predictions."
)


footnote(
    "This is a research showcase. If a claim looks stronger than the "
    "evidence should permit, please flag it — a research portfolio should "
    "surface uncertainty, not hide it."
)
