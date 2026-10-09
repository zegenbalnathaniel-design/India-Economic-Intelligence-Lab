"""Data page — sources, dates, units and provenance for every number used."""
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

from data_sources.loaders import load_bank_panel, load_repo_rate
from app.components.theme import setup, kicker, callout, source_badge, footnote, stat_card
from app.components.provenance import sources_panel
from data_sources import registry, validation


setup("Data")


with st.sidebar:
    st.markdown("## Data")
    st.caption("Source registry & sample previews")


kicker("Data transparency")
st.title("Sources, dates, units, provenance")
st.markdown(
    "Every number on this site comes from one of the datasets below. Each has a status, a "
    "publisher and link, the period and units it covers, when it was added, how this project "
    "transformed it, how missing values are treated, and its known limitations."
)

# ---------- Evidence ledger --------------------------------------------------
st.header("Evidence ledger")
ledger = registry.as_frame()
status_counts = ledger["status"].value_counts()
lc = st.columns(min(len(status_counts), 6))
for col, (stt, n) in zip(lc, status_counts.items()):
    with col:
        stat_card(stt, f"{n}", "dataset(s)")
show_cols = {"name": "Dataset", "publisher": "Publisher", "status": "Status", "period": "Period",
             "units": "Units", "frequency": "Frequency", "added": "Added", "used_on": "Used on"}
st.dataframe(ledger[list(show_cols)].rename(columns=show_cols), hide_index=True, use_container_width=True)
pick = st.selectbox("Full record for", ledger["id"], format_func=lambda i: registry.get(i).name, key="ledger_pick")
sources_panel(pick, title="Selected dataset — full record")
st.download_button("Download the evidence ledger (CSV)", ledger.to_csv(index=False).encode("utf-8"),
                   file_name="ieil_evidence_ledger.csv", mime="text/csv", key="dl_ledger")
problems = registry.registry_problems()
if problems:
    st.error("Ledger problems: " + "; ".join(problems))
else:
    st.caption("Ledger check: every data file in the repository has a record, every record has a known "
               "status and stated limitations, and every listed file exists.")

# ---------- Validation report -------------------------------------------------
st.header("Validation report")
st.markdown(
    "Automatic checks on every file: duplicate rows and keys, missing cells, period labels that "
    "are not valid years / financial years / quarters / months, names with stray spaces or "
    "inconsistent spellings, impossible values (negative prices or levels, shares above 100%) and "
    "suspicious period-on-period jumps. **Checks never change the data** — findings are listed for "
    "review."
)


@st.cache_data(show_spinner="Running checks on every data file…")
def _validation():
    return validation.validate_all()


report = _validation()
sev = report["severity"].value_counts()
vc = st.columns(4)
for col, k, sub in zip(vc, ["ERROR", "WARN", "INFO", "OK"],
                       ["unreadable files", "need a look", "noted, by design", "files with no findings"]):
    with col:
        stat_card(k, f"{int(sev.get(k, 0))}", sub)
level = st.multiselect("Show", ["ERROR", "WARN", "INFO", "OK"], default=["ERROR", "WARN", "INFO"], key="val_levels")
st.dataframe(report[report["severity"].isin(level)], hide_index=True, use_container_width=True)
st.download_button("Download the validation report (CSV)", report.to_csv(index=False).encode("utf-8"),
                   file_name="ieil_validation_report.csv", mime="text/csv", key="dl_validation")
callout(
    "Two flags worth knowing about, both kept as published: Sikkim's per-capita NSDP rises 72% in "
    "2009-10 in the RBI table, and Bhiwadi's RESIDEX price level rises 36% in the Sep-2023 quarter.",
    kind="note",
)

st.header("Sources to replace the illustrative bank panel")
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
    "- **Frequency**: quarterly; an indicator disclosed only half-yearly stays "
    "half-yearly — quarters without a disclosure are left missing, never interpolated."
)

footnote(
    "See <code>data_dictionary.md</code> at the repository root for the "
    "authoritative field-by-field spec."
)
