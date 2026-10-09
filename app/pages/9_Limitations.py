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
     "Mitigation in the MVP": "Every return is user-editable; Monte Carlo overlay shows dispersion"},
    {"Limitation": "Deterministic returns (default view)",
     "Where it bites": "Point estimate of final wealth is a central tendency, not a forecast",
     "Mitigation in the MVP": "Monte Carlo module renders the 5-95% band"},
    {"Limitation": "Correlations and tail heaviness are assumptions, not estimates",
     "Where it bites": "Monte Carlo band width depends on the correlation matrix and t degrees of freedom you set",
     "Mitigation in the MVP": "FIXED in part: correlated and fat-tailed (Student-t) draws are now available, "
                              "validated for consistency; estimating them needs Indian asset-return history"},
    {"Limitation": "No fees, taxes, or transaction costs",
     "Where it bites": "Final wealth is over-stated relative to net-of-costs reality",
     "Mitigation in the MVP": "Documented; parameterisation is a natural extension"},
    {"Limitation": "Composition simulator is one household",
     "Where it bites": "The simulator itself says nothing about inequality between households",
     "Mitigation in the MVP": "FIXED: section W shows WIL income and wealth shares 1951–2023 and a "
                              "distributional Gini with a redistribution scenario"},
    {"Limitation": "Gini is a lower bound",
     "Where it bites": "Built from five published group shares, so inequality within each group is ignored",
     "Mitigation in the MVP": "Labelled as a lower bound; a full Gini needs AIDIS / NSS household microdata"},
    {"Limitation": "No figures for the Bottom 10% or P10–P50",
     "Where it bites": "The two lowest Riffle cards and table rows",
     "Mitigation in the MVP": "Shown as DATA REQUIRED; WID.world downloads for p0p10 and p10p50 would fill them"},
    {"Limitation": "Top-tail wealth undercoverage in Indian survey data",
     "Where it bites": "Any Gini or top-share statistic",
     "Mitigation in the MVP": "WIL combines AIDIS with Forbes rich lists for the top tail; the authors still "
                              "describe their results as a lower bound"},
    {"Limitation": "Asset-valuation uncertainty (property, gold)",
     "Where it bites": "Real-world household wealth is measured with error",
     "Mitigation in the MVP": "Model uses target values, not marked-to-market"},
])
st.dataframe(wealth_lim, hide_index=True, use_container_width=True)


st.header("Banking & monetary policy module")
banking_lim = pd.DataFrame([
    {"Limitation": "Illustrative panel in the MVP",
     "Where it bites": "iBFPI levels and the ρ estimate reflect the synthetic generator",
     "Mitigation in the MVP": "Panel is CSV-replaceable; loader has no hard-coded values"},
    {"Limitation": "Small sample (n ≈ 26 quarters)",
     "Where it bites": "Regime-conditional ρ has n well below rules-of-thumb",
     "Mitigation in the MVP": "n reported alongside every ρ; p-values shown"},
    {"Limitation": "Autocorrelation in quarterly series",
     "Where it bites": "Spearman p-values understate uncertainty on serially correlated series",
     "Mitigation in the MVP": "FIXED in part: Newey–West (HAC) regression added under Robustness; the "
                              "Spearman p-values themselves are still unadjusted"},
    {"Limitation": "No macro controls in the fixed-effects regression",
     "Where it bites": "The repo-rate slope may pick up the business cycle",
     "Mitigation in the MVP": "Stated next to the table; needs quarterly GDP growth and CPI series"},
    {"Limitation": "Cross-bank accounting differences",
     "Where it bites": "IND-AS vs prior AS transitions create structural breaks in the raw series",
     "Mitigation in the MVP": "Per-bank standardisation absorbs level differences but not slope breaks"},
    {"Limitation": "Composite-index subjectivity",
     "Where it bites": "Equal weights and fixed direction coefficients are choices",
     "Mitigation in the MVP": "FIXED: sensitivity analysis (300 random weightings, drop one indicator, "
                              "reverse one direction) shows which indicators drive ρ"},
    {"Limitation": "Regime threshold (±25bp on 3-quarter change) is a modelling choice",
     "Where it bites": "Alternative thresholds re-label periods and change ρ per regime",
     "Mitigation in the MVP": "Documented; parameter can be exposed if useful"},
    {"Limitation": "Survivorship bias in the bank subset",
     "Where it bites": "Only extant large private/public banks are in the panel — small/failed banks are absent",
     "Mitigation in the MVP": "Documented; scope is stated as five specific banks"},
])
st.dataframe(banking_lim, hide_index=True, use_container_width=True)


st.header("What the site does not claim")
st.markdown(
    "- It does **not** claim to identify the causal effect of monetary "
    "policy on bank performance.\n"
    "- It does **not** claim that any specific asset is universally better.\n"
    "- It does **not** claim r > g mechanically produces individual "
    "inequality.\n"
    "- It does **not** provide personalised financial advice.\n"
    "- It does **not** present iBFPI as an established or industry-standard "
    "index."
)


st.header("What would materially strengthen the research")
st.dataframe(pd.DataFrame([
    {"Item": "Real bank filings replacing the illustrative panel", "Status": "NEEDS DATA",
     "Detail": "Quarterly PPNR, total assets, CET1, net charge-offs, LCR and unrealised bond losses for the "
               "five banks, 2018–2024 (Basel III Pillar 3 disclosures and results)"},
    {"Item": "Bank fixed-effects regression of iBFPI on the repo rate", "Status": "DONE (partly)",
     "Detail": "Banking Lab → Robustness, with clustered and Newey–West errors. Macro controls still need "
               "quarterly GDP growth and CPI"},
    {"Item": "RBI MPC event studies", "Status": "NEEDS DATA",
     "Detail": "Every MPC decision date since 2018 (only 7 Oct 2026 is loaded) and bank data more frequent "
               "than quarterly, so a decision's effect can be separated from the rest of the quarter"},
    {"Item": "Joint-covariance Monte Carlo for the wealth module", "Status": "DONE",
     "Detail": "Wealth Lab → Monte Carlo: correlation matrix and fat tails. Correlations are user "
               "assumptions until Indian return history (Nifty TRI, gold in ₹, a house-price index, a "
               "G-sec index) is added to estimate them"},
    {"Item": "Distributional Gini simulation", "Status": "DONE (from WIL shares)",
     "Detail": "Wealth Lab → section W: Gini 1951–2023 and a redistribution scenario. An AIDIS/NSS "
               "household-level version needs the microdata (registered login at microdata.gov.in)"},
    {"Item": "Sensitivity over composite weights and direction coefficients", "Status": "DONE",
     "Detail": "Banking Lab → Robustness"},
]), hide_index=True, use_container_width=True)

footnote(
    "This is a research showcase. If a claim looks stronger than the "
    "evidence should permit, please flag it — a research portfolio should "
    "surface uncertainty, not hide it."
)
