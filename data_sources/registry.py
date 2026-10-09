"""Evidence ledger: one metadata record per dataset used anywhere on the site.

Each record answers: what it is, who published it, where it came from,
which period and units it covers, how this project transformed it, how
missing values are treated, and what its known limitations are. Pages
show the relevant records through `app.components.provenance`, and the
Data page lists all of them with the validation report from
`data_sources.validation`.

Status vocabulary (DATA_REGISTRY.md): VERIFIED, PARTIAL, ESTIMATED,
DERIVED, SPLICED, ILLUSTRATIVE, LIVE (fetched at run time), DATA REQUIRED.

Other modules may add records by defining `DATASETS` in a module named
`data_sources/meta_<area>.py`; `all_datasets()` collects them.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("VERIFIED", "PARTIAL", "ESTIMATED", "DERIVED", "SPLICED", "ILLUSTRATIVE", "LIVE", "DATA REQUIRED")


@dataclass(frozen=True)
class Dataset:
    id: str
    name: str
    publisher: str
    url: str                      # "" when no stable public URL is known
    status: str
    period: str
    units: str
    coverage: str                 # geography / entities
    frequency: str
    files: tuple[str, ...] = ()   # repo-relative; empty for live sources
    publication: str = ""         # publication / release date or edition
    added: str = ""               # date the file entered this project (git)
    transformations: str = "None — loaded as supplied."
    missing: str = "Missing cells stay missing (NaN); never replaced with zero."
    methodology: str = ""
    limitations: str = ""
    used_on: tuple[str, ...] = field(default_factory=tuple)


DATASETS: list[Dataset] = [
    Dataset(
        id="rbi_nsdp_constant",
        name="Per-capita NSDP, constant prices (RBI Handbook Table 26)",
        publisher="Reserve Bank of India — Handbook of Statistics on Indian States",
        url="https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States",
        status="VERIFIED",
        period="2004-05 to 2022-23 (two base years: 2004-05 and 2011-12)",
        units="₹ per person per year, constant prices of the base year",
        coverage="37 states/UTs (as published)", frequency="Annual (Indian financial year, April–March)",
        files=("data/raw/rbi_handbook/percapita_nsdp_constant_prices_2004_05_to_2022_23.csv",),
        added="2026-10-08",
        transformations="Four workbook sheets reshaped wide→long (data_sources/ingest_uploaded_sources.py); '-' cells set to missing.",
        methodology="Source table self-identifies (sheets T_26(i)–(iv)).",
        limitations="The two base-year blocks are not comparable without linking; J&K appears under two territorial definitions.",
        used_on=("State Economy Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="rbi_nsdp_spliced",
        name="Per-capita NSDP, constant prices — spliced 2004-05→2022-23",
        publisher="Derived in this project from RBI Handbook Table 26",
        url="", status="SPLICED",
        period="2004-05 to 2022-23", units="₹ per person per year, 2011-12 prices",
        coverage="States with both base-year blocks", frequency="Annual (financial year)",
        files=("data/raw/rbi_handbook/percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv",
               "data/raw/rbi_handbook/nsdp_splice_link_factors.csv"),
        added="2026-10-08",
        transformations="Old-base values × state-specific link factor (overlap-year ratio) — factors stored alongside.",
        methodology="Ratio splicing at the overlap; documented in DATA_REGISTRY.md.",
        limitations="Splicing assumes the base-year revision is a level shift; growth before 2011-12 inherits old-base methodology.",
        used_on=("State Economy Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="rbi_nsdp_current",
        name="Per-capita NSDP, current prices (RBI Handbook / DBIE)",
        publisher="Reserve Bank of India — Handbook of Statistics on Indian States (DBIE)",
        url="https://data.rbi.org.in/", status="PARTIAL",
        period="2011-12 to 2024-25", units="₹ per person per year, current prices",
        coverage="32 states/UTs (Delhi and Puducherry held separately, unaligned)", frequency="Annual (financial year)",
        files=("data/raw/rbi_handbook/nsdp_current_prices_by_state_2011_12_to_2024_25.csv",
               "data/raw/rbi_handbook/nsdp_current_prices_delhi_puducherry_UNALIGNED.csv"),
        added="2026-10-08",
        transformations="Transcribed from supplied screenshots of the DBIE table.",
        limitations="Nominal values — not comparable over time without a deflator; transcription from images.",
        used_on=("State Economy Lab", "Housing Intelligence Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="state_gsdp_nsdp_pc",
        name="Per-capita GSDP and NSDP, current and constant prices, 2023-24 and 2024-25",
        publisher="Reserve Bank of India — Handbook of Statistics on Indian States (DBIE)",
        url="https://data.rbi.org.in/", status="PARTIAL",
        period="2023-24, 2024-25", units="₹ per person per year",
        coverage="~33 states/UTs plus India", frequency="Annual (financial year)",
        files=("data/raw/state_gsdp_nsdp_percapita.csv",), added="2026-10-08",
        limitations="Older release vintage than the current-price series (values differ ~1–2%); Delhi row blank; Ladakh row misaligned and excluded.",
        used_on=("State Economy Lab",),
    ),
    Dataset(
        id="rbi_gcf_sector",
        name="Gross capital formation by institutional sector",
        publisher="Reserve Bank of India — Handbook of Statistics on Indian Economy",
        url="https://data.rbi.org.in/", status="PARTIAL",
        period="2011-12 to 2023-24", units="₹ crore, current prices",
        coverage="All-India, by institutional sector", frequency="Annual (financial year)",
        files=("data/raw/rbi_handbook/institutional_sector_gross_capital_formation_2011_12_to_2023_24.csv",),
        added="2026-10-08", transformations="Transcribed from supplied screenshots.",
        limitations="Nominal values; transcription from images.",
        used_on=("Economic Relationships Lab",),
    ),
    Dataset(
        id="plfs_unemployment",
        name="Unemployment rate by state, usual status, age 15+ (PLFS 2023-24)",
        publisher="Ministry of Statistics and Programme Implementation (NSO) — Periodic Labour Force Survey",
        url="https://www.mospi.gov.in/", status="PARTIAL",
        period="July 2023–June 2024 (PLFS 2023-24)", units="% of labour force",
        coverage="28 states + All-India", frequency="Single cross-section",
        files=("data/raw/plfs_unemployment_rate_by_state_2023_24.csv",), added="2026-10-08",
        limitations="One year only; exact report table not yet confirmed; survey sampling error not reported here.",
        used_on=("State Economy Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="hces_mpce",
        name="Urban monthly per-capita consumption expenditure by state/UT (HCES 2023-24)",
        publisher="Ministry of Statistics and Programme Implementation — Household Consumption Expenditure Survey",
        url="https://www.mospi.gov.in/", status="VERIFIED",
        period="2023-24", units="₹ per person per month", coverage="36 states/UTs (urban)",
        frequency="Single cross-section", files=("data/raw/hces/state_ut_urban_mpce_2023_24.csv",),
        publication="HCES 2023-24, Statement 7", added="2026-10-08",
        limitations="Consumption, not income; urban only; survey estimates.",
        used_on=("Housing Intelligence Lab", "State Economy Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="nhb_residex",
        name="NHB RESIDEX city housing price index and price levels",
        publisher="National Housing Bank — RESIDEX",
        url="https://residex.nhbonline.org.in/", status="PARTIAL",
        period="Jun-2013 to Sep-2024 (index and price levels); Jun-2025 to Jun-2026 (index)",
        units="Composite index (base not stated in file); price levels in ₹ per sq. m.",
        coverage="50 cities", frequency="Quarterly",
        files=("data/raw/nhb_residex/city_composite_index_2013_2024.csv",
               "data/raw/nhb_residex/city_composite_index_2025_2026.csv",
               "data/raw/nhb_residex/city_price_levels_by_unit_size_2013_2024.csv",
               "data/raw/nhb_residex/assessment_price_usable_records_quarterly.csv"),
        added="2026-10-08",
        transformations="HTML-in-.xls parsed, duplicate table removed, wide→long reshape.",
        limitations="Index base year not confirmed from the file; assessment prices (not transactions); gap Oct-2024–Mar-2025.",
        used_on=("Housing Intelligence Lab", "Economic Relationships Lab"),
    ),
    Dataset(
        id="real_pc_nni",
        name="Real per-capita Net National Income, selected years",
        publisher="Likely MoSPI National Accounts Statistics (not confirmed)",
        url="", status="PARTIAL",
        period="2011-12, 2014-15, 2019-20, 2020-21, 2022-23, 2023-24, 2024-25",
        units="₹, constant prices", coverage="All-India", frequency="Selected years only",
        files=("data/raw/real_percapita_nni_timeseries.csv", "data/raw/indicator_summary_hpi_nni.csv"),
        added="2026-10-08", transformations="'₹', commas and dashes stripped on load.",
        limitations="Source inferred, not confirmed; not a continuous annual series.",
        used_on=("Economic Relationships Lab",),
    ),
    Dataset(
        id="gdp_cagr_worldeconomics",
        name="India real GDP CAGR over trailing windows",
        publisher="World Economics (private provider — non-official)",
        url="https://www.worldeconomics.com/", status="VERIFIED",
        period="Trailing 10, 5 and 3 years (end year not stated)", units="% per year",
        coverage="All-India", frequency="Point estimates", files=("data/raw/india_gdp_growth_cagr.csv",),
        added="2026-10-08",
        limitations="Non-official source; end year of windows not stated.",
    ),
    Dataset(
        id="wil_india",
        name="Income and wealth inequality in India, 1922-2023 (Tables 2, 3, B.1, C.1, C.2)",
        publisher="World Inequality Lab — Bharti, Chancel, Piketty & Somanchi, Working Paper 2024/09",
        url="https://wid.world/www-site/uploads/2024/03/WorldInequalityLab_WP2024_09_Income-and-Wealth-Inequality-in-India-1922-2023_Final.pdf",
        status="VERIFIED",
        period="Income shares 1951-2022; wealth shares 1961-2023 (survey years before 2002); billionaires 1988-2022",
        units="% of pre-tax national income / net wealth; ₹ (2022 prices) for averages",
        coverage="All-India adults (UN WPP population)", frequency="Annual (wealth: survey years to 1991)",
        files=("data/raw/wil/table2_income_2022_23.csv", "data/raw/wil/table3_wealth_2022_23.csv",
               "data/raw/wil/tableB1_income_shares_1951_2022.csv", "data/raw/wil/tableC1_wealth_shares_1961_2023.csv",
               "data/raw/wil/tableC2_vhnwi_1988_2022.csv", "data/raw/wil/long_run_facts.csv"),
        publication="18 March 2024", added="2026-10-09",
        transformations="Parsed from the PDF text layer by scripts/extract_wil_tables.py (no retyping); Tables 2–3 checked against the printed page.",
        methodology="Distributional national accounts: national accounts + tax tabulations + surveys + rich lists.",
        limitations="Authors call results a lower bound; no comparable consumption survey after 2011-12; 2023 wealth tentative; pre-1991 wealth from surveys only.",
        used_on=("Wealth & Inequality Lab", "Economic Relationships Lab", "Inequality & Financialisation Lab"),
    ),
    Dataset(
        id="paper_a",
        name="Author's Paper A — Table 1 asset returns and Figure 2",
        publisher="Site author (paper); returns from Wahengbam (2023, CSEP); asset shares from RBI (2017)",
        url="app/static/papers/Income_Wealth_Inequality_India.pdf", status="VERIFIED",
        period="Returns 1991-2021; shares as of RBI (2017)", units="% nominal return per year; % of household assets",
        coverage="All-India households", frequency="Long-run averages",
        files=("data/raw/author_paper/paperA_table1_asset_returns.csv", "data/raw/author_paper/paperA_figure2_endpoints.csv"),
        added="2026-10-09",
        transformations="Transcribed from the paper; deposits 6.5% is the midpoint of the stated 6–7%.",
        limitations="Secondary averages; no volatility, costs or taxes.",
        used_on=("Wealth & Inequality Lab", "Inequality & Financialisation Lab"),
    ),
    Dataset(
        id="macro_monthly",
        name="Latest monthly releases: CPI, IIP, RBI household inflation expectations",
        publisher="MoSPI (CPI, IIP) and Reserve Bank of India (survey)",
        url="https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2310058", status="PARTIAL",
        period="Jul–Sep 2026 reference periods", units="% y/y; index (CPI base 2024=100; IIP base 2022-23=100); survey medians",
        coverage="All-India", frequency="Monthly / survey rounds",
        files=("data/raw/macro_monthly/india_macro_monthly.csv", "data/raw/macro_monthly/release_calendar.csv"),
        added="2026-10-09",
        transformations="Entered by hand from releases, cross-checked against press coverage; per-row status (CPI VERIFIED, others PARTIAL).",
        limitations="Provisional / quick estimates are revised; not fetched live.",
        used_on=("India Macro & World", "Banking & Monetary Policy Lab"),
    ),
    Dataset(
        id="rbi_policy_decisions",
        name="RBI policy repo rate decisions",
        publisher="Reserve Bank of India — Monetary Policy Committee",
        url="https://www.rbi.org.in/", status="PARTIAL",
        period="7 Oct 2026 (one decision loaded)", units="% per year", coverage="India",
        frequency="Per MPC decision", files=("data/raw/macro_monthly/rbi_policy_decisions.csv",), added="2026-10-09",
        transformations="Daily and monthly tables built from decisions in analysis/macro_monthly.py; no back-filling.",
        limitations="Only one decision loaded; earlier history is DATA REQUIRED.",
        used_on=("India Macro & World", "Banking & Monetary Policy Lab"),
    ),
    Dataset(
        id="bank_panel_illustrative",
        name="Five-bank quarterly panel and repo-rate series (iBFPI demonstration)",
        publisher="Generated in this project (data_sources/build_illustrative_data.py)",
        url="", status="ILLUSTRATIVE",
        period="2018-Q2 to 2024-Q3", units="Ratios / % (synthetic)", coverage="SBI, HDFC, ICICI, Axis, Kotak (names only)",
        frequency="Quarterly", files=("data/processed/bank_panel.csv", "data/processed/repo_rate.csv"), added="2026-09-23",
        methodology="Synthetic generator built to demonstrate the BFPI method end to end.",
        limitations="Not real bank data — no result from it is a finding about real banks.",
        used_on=("Banking & Monetary Policy Lab",),
    ),
    Dataset(
        id="bank_earnings",
        name="Bank quarterly results (reported) and an ESTIMATED quarterly split",
        publisher="Bank disclosures (reported file); project estimate (estimated file)",
        url="", status="PARTIAL",
        period="Reported: Q2 FY25–Q2 FY26; estimated: 2019-Q1–2025-Q1", units="₹ crore; %",
        coverage="HDFC Bank, ICICI Bank, SBI, Axis Bank", frequency="Quarterly",
        files=("data/raw/bank_earnings/bank_earnings_reported_q2fy25_to_q2fy26.csv",
               "data/raw/bank_earnings/bank_earnings_ESTIMATED_2019q1_2025q1.csv"),
        added="2026-10-08",
        limitations="The ESTIMATED file distributes annual figures across quarters and must never be shown as reported data.",
    ),
    Dataset(
        id="worldbank_wdi",
        name="World Development Indicators (live API)",
        publisher="World Bank", url="https://data.worldbank.org/", status="LIVE",
        period="As returned by the API at run time", units="Per indicator (WDI metadata)",
        coverage="India and selected peers", frequency="Annual", added="",
        transformations="None; API 'lastupdated' and retrieval time shown with the data.",
        missing="API nulls stay missing; any failed request shows DATA UNAVAILABLE, never stale values.",
        limitations="Harmonised series can differ from MoSPI/RBI headline figures; not reachable from the build sandbox, so verified only on the deployed app.",
        used_on=("India Macro & World", "Structural Transformation Lab", "Inequality & Financialisation Lab"),
    ),
]


def _extra_datasets() -> list[Dataset]:
    out: list[Dataset] = []
    pkg_dir = Path(__file__).resolve().parent
    for mod in pkgutil.iter_modules([str(pkg_dir)]):
        if mod.name.startswith("meta_"):
            m = importlib.import_module(f"data_sources.{mod.name}")
            out.extend(getattr(m, "DATASETS", []))
    return out


def all_datasets() -> list[Dataset]:
    seen, out = set(), []
    for d in DATASETS + _extra_datasets():
        if d.id not in seen:
            seen.add(d.id)
            out.append(d)
    return out


def get(dataset_id: str) -> Dataset:
    for d in all_datasets():
        if d.id == dataset_id:
            return d
    raise KeyError(f"no dataset with id {dataset_id!r} in the registry")


def as_frame() -> pd.DataFrame:
    rows = []
    for d in all_datasets():
        r = asdict(d)
        r["files"] = "; ".join(d.files)
        r["used_on"] = "; ".join(d.used_on)
        rows.append(r)
    return pd.DataFrame(rows)


def registry_problems() -> list[str]:
    """Structural checks on the registry itself (run in tests and on the Data page)."""
    problems = []
    ids = [d.id for d in all_datasets()]
    if len(ids) != len(set(ids)):
        problems.append("duplicate dataset ids")
    for d in all_datasets():
        if d.status not in STATUSES:
            problems.append(f"{d.id}: unknown status {d.status!r}")
        for f in d.files:
            if not (ROOT / f).exists():
                problems.append(f"{d.id}: file missing: {f}")
        if not d.limitations:
            problems.append(f"{d.id}: no limitations recorded")
    covered = {f for d in all_datasets() for f in d.files}
    for p in sorted((ROOT / "data").rglob("*.csv")):
        rel = str(p.relative_to(ROOT))
        if rel not in covered:
            problems.append(f"data file not in the registry: {rel}")
    return problems
