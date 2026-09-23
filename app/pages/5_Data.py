"""Data page — sources, dates, units and provenance for every number used."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from data_sources.loaders import load_bank_panel, load_repo_rate
from app.components.theme import setup, kicker, callout, source_badge, footnote


setup("Data")


with st.sidebar:
    st.markdown("## Data")
    st.caption("Source registry & sample previews")


kicker("Data transparency")
st.title("Sources, dates, units, provenance")
st.markdown(
    "Every number surfaced by the labs originates from one of the "
    "following. Where a value is illustrative it is labelled as such."
)


st.header("Source registry")
registry = pd.DataFrame([
    {"Source": "RBI — Database on Indian Economy (DBIE)", "Url": "https://dbie.rbi.org.in",
     "Used for": "Repo rate, banking aggregates", "Frequency": "Daily / Monthly / Qtr", "Access": "Open (portal)"},
    {"Source": "RBI — Basel III disclosures (bank filings)", "Url": "Bank IR pages",
     "Used for": "CET1, LCR, disclosures", "Frequency": "Quarterly", "Access": "Open (PDF)"},
    {"Source": "Bank annual & quarterly reports", "Url": "Each bank’s investor page",
     "Used for": "PPNR, charge-offs, unrealised losses on AFS book", "Frequency": "Quarterly / Annual", "Access": "Open"},
    {"Source": "MOSPI — National Statistical Office", "Url": "https://mospi.gov.in",
     "Used for": "GDP, inflation, CPI (when real g is calibrated)", "Frequency": "Qtr / Monthly", "Access": "Open"},
    {"Source": "Ministry of Finance — Economic Survey", "Url": "https://www.indiabudget.gov.in/economicsurvey/",
     "Used for": "Structural context, sectoral background", "Frequency": "Annual", "Access": "Open"},
    {"Source": "SEBI, NSE / BSE", "Url": "https://www.sebi.gov.in ; www.nseindia.com ; www.bseindia.com",
     "Used for": "Equity market historical returns benchmark", "Frequency": "Daily", "Access": "Open"},
    {"Source": "World Bank / IMF / BIS", "Url": "https://data.worldbank.org ; www.imf.org ; www.bis.org",
     "Used for": "Cross-country comparators", "Frequency": "Annual", "Access": "Open"},
    {"Source": "Federal Reserve FRED", "Url": "https://fred.stlouisfed.org",
     "Used for": "US comparison (JP Morgan paper)", "Frequency": "Daily / Monthly", "Access": "Open API"},
])
st.dataframe(registry, hide_index=True, use_container_width=True)


st.header("What ships in this build")
callout(
    "The MVP ships an <b>illustrative synthetic panel</b> so the "
    "methodology can be exercised without API keys. Replace the two CSVs "
    "in <code>data/processed/</code> with values sourced from the "
    "registry above to reproduce with real data. The construction script "
    "is at <code>data_sources/build_illustrative_data.py</code>.",
    kind="warn",
)
source_badge("Illustrative", "Reproducible with `python -m data_sources.build_illustrative_data`")


c1, c2 = st.columns(2)
with c1:
    st.subheader("Bank panel (preview)")
    st.dataframe(load_bank_panel().head(12), hide_index=True, use_container_width=True)
with c2:
    st.subheader("RBI repo rate (preview)")
    st.dataframe(load_repo_rate().head(12), hide_index=True, use_container_width=True)


st.header("Units, direction, frequency")
units = pd.DataFrame([
    {"Field": "ppnr_to_assets", "Units": "Decimal fraction of total assets", "Direction": "+1 (higher = better)"},
    {"Field": "cet1_ratio", "Units": "Decimal fraction of RWA", "Direction": "+1"},
    {"Field": "nco_rate", "Units": "Decimal fraction, annualised", "Direction": "−1"},
    {"Field": "lcr", "Units": "Ratio (1.30 = 130%)", "Direction": "+1"},
    {"Field": "unrealised_loss_to_cet1", "Units": "Decimal fraction of CET1", "Direction": "−1"},
    {"Field": "repo_rate", "Units": "% (annualised)", "Direction": "— (regressor)"},
])
st.dataframe(units, hide_index=True, use_container_width=True)


st.header("Refresh & retrieval")
st.markdown(
    "- **Repo rate**: pull the RBI reference-rate series from DBIE. "
    "Quarter-end value is used.\n"
    "- **Bank indicators**: extract from the bank's own quarterly disclosures "
    "and Basel III Pillar 3 report; align to the fiscal-quarter end.\n"
    "- **Unrealised losses**: use the AFS reserve on the balance-sheet OCI "
    "line, divided by CET1 capital.\n"
    "- **Frequency**: quarterly; any indicator that is disclosed only "
    "half-yearly should be linearly interpolated with a flag."
)

footnote(
    "See <code>data_dictionary.md</code> at the repository root for the "
    "authoritative field-by-field spec."
)
