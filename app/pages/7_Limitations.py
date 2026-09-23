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

import pandas as pd
import streamlit as st

from app.components.theme import setup, kicker, callout, footnote


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
    {"Limitation": "Monte Carlo assumes independent normal returns",
     "Where it bites": "Underestimates joint downside; ignores fat tails",
     "Mitigation in the MVP": "Called out inline; band is a lower bound on dispersion"},
    {"Limitation": "No fees, taxes, or transaction costs",
     "Where it bites": "Final wealth is over-stated relative to net-of-costs reality",
     "Mitigation in the MVP": "Documented; parameterisation is a natural extension"},
    {"Limitation": "Single-household simulation, no distribution",
     "Where it bites": "The module says nothing about *inequality between* households",
     "Mitigation in the MVP": "r − g explorer discusses this; distributional Gini is future work"},
    {"Limitation": "Top-tail wealth undercoverage in Indian survey data",
     "Where it bites": "Any Gini or share-of-top-1 statistic from surveys",
     "Mitigation in the MVP": "The MVP does not compute a survey-based Gini"},
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
    {"Limitation": "Autocorrelation not corrected in Spearman p-values",
     "Where it bites": "Nominal p-values understate uncertainty on serially correlated series",
     "Mitigation in the MVP": "Documented; Newey-West on a linear regression is a natural extension"},
    {"Limitation": "Cross-bank accounting differences",
     "Where it bites": "IND-AS vs prior AS transitions create structural breaks in the raw series",
     "Mitigation in the MVP": "Per-bank standardisation absorbs level differences but not slope breaks"},
    {"Limitation": "Composite-index subjectivity",
     "Where it bites": "Equal weights and fixed direction coefficients are choices",
     "Mitigation in the MVP": "Both are documented; weights can be re-tuned in code"},
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
st.markdown(
    "1. Real bank filings replacing the illustrative panel.\n"
    "2. Bank fixed-effects panel regression of iBFPI on repo rate with "
    "macro controls.\n"
    "3. FOMC / RBI MPC event studies (window returns / iBFPI moves).\n"
    "4. Joint-covariance Monte Carlo for the wealth module.\n"
    "5. AIDIS / NSS-seeded distributional Gini simulation.\n"
    "6. Sensitivity analysis over composite weights and direction coefficients."
)

footnote(
    "This is a research showcase. If a claim looks stronger than the "
    "evidence should permit, please flag it — a research portfolio should "
    "surface uncertainty, not hide it."
)
