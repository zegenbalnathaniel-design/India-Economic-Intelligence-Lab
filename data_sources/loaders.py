"""Data loaders for the interactive labs.

The MVP ships with an *illustrative* quarterly panel for five Indian banks
and the RBI repo rate. Every value is clearly labelled as ILLUSTRATIVE in
the accompanying metadata and rendered with a source badge in the UI.

The intent is to let a visitor exercise the methodology end-to-end without
requiring API keys or a bulk data download. To reproduce with real values
each visitor can replace `data/processed/bank_panel.csv` and
`data/processed/repo_rate.csv` with values sourced from bank annual reports,
RBI's DBIE (https://dbie.rbi.org.in) and RBI's Basel III disclosures.
See data_dictionary.md for exact provenance conventions.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


@lru_cache(maxsize=8)
def load_bank_panel() -> pd.DataFrame:
    """Bank x quarter panel with the five iBFPI indicators."""
    df = pd.read_csv(DATA_DIR / "bank_panel.csv", parse_dates=["period"])
    return df


@lru_cache(maxsize=8)
def load_repo_rate() -> pd.DataFrame:
    """RBI repo rate at quarter end (%)."""
    df = pd.read_csv(DATA_DIR / "repo_rate.csv", parse_dates=["period"])
    return df


def bank_names() -> list[str]:
    return sorted(load_bank_panel()["bank"].unique().tolist())


def joined_panel() -> pd.DataFrame:
    """Bank panel merged with the repo rate for that quarter."""
    return load_bank_panel().merge(load_repo_rate(), on="period", how="left")


# ---------------------------------------------------------------------------
# Real data: state economic indicators (RBI Handbook of Statistics on
# Indian States, PLFS). See DATA_REGISTRY.md for full provenance of every
# file loaded here.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_nsdp_spliced() -> pd.DataFrame:
    """Per-capita NSDP, constant prices, one continuous series 2004-05 to
    2022-23 (two base-year series linked via overlap-year factors — see
    DATA_REGISTRY.md and analysis/regional.py for the method)."""
    return pd.read_csv(RAW_DIR / "rbi_handbook" / "percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv")


@lru_cache(maxsize=8)
def load_nsdp_current() -> pd.DataFrame:
    """Per-capita NSDP, current prices, 2011-12 to 2024-25 (transcribed
    from a dbie.rbihub.in screenshot — PARTIAL status, see registry)."""
    return pd.read_csv(RAW_DIR / "rbi_handbook" / "nsdp_current_prices_by_state_2011_12_to_2024_25.csv")


@lru_cache(maxsize=8)
def load_unemployment_by_state() -> pd.DataFrame:
    """PLFS 2023-24 unemployment rate by state (single cross-section)."""
    return pd.read_csv(RAW_DIR / "plfs_unemployment_rate_by_state_2023_24.csv")


@lru_cache(maxsize=8)
def load_real_percapita_nni() -> pd.DataFrame:
    """All-India real per-capita NNI (₹, constant prices) for the seven
    financial years in `real_percapita_nni_timeseries.csv` (2011-12,
    2014-15, 2019-20, 2020-21, 2022-23, 2023-24, 2024-25 -- not a
    continuous annual series). Status PARTIAL (source inferred as MoSPI
    National Accounts, not confirmed; see DATA_REGISTRY.md).

    The only processing is parsing the display formatting: the en dash in
    the year label becomes '-' ('2011–12' -> '2011-12', the convention of
    the NSDP tables) and '₹63,462' becomes 63462.0. The cells as published
    are kept in `financial_year_as_published` / `value_as_published`.
    Missing years stay missing -- nothing is interpolated."""
    raw = pd.read_csv(RAW_DIR / "real_percapita_nni_timeseries.csv", dtype=str)
    out = pd.DataFrame({
        "financial_year": raw["Financial year"].str.strip().str.replace("–", "-", regex=False),
        "real_percapita_nni_inr": pd.to_numeric(
            raw["Real per-capita NNI"].str.replace("₹", "", regex=False).str.replace(",", "", regex=False).str.strip(),
            errors="raise",
        ),
        "financial_year_as_published": raw["Financial year"],
        "value_as_published": raw["Real per-capita NNI"],
    })
    return out


@lru_cache(maxsize=8)
def load_gross_capital_formation() -> pd.DataFrame:
    """Institutional-sector-wise gross capital formation, current prices,
    2011-12 to 2023-24."""
    return pd.read_csv(RAW_DIR / "rbi_handbook" / "institutional_sector_gross_capital_formation_2011_12_to_2023_24.csv")


# ---------------------------------------------------------------------------
# Real data: NHB RESIDEX housing prices.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_residex_price_levels() -> pd.DataFrame:
    """Actual price levels (INR/sqm) by city, quarter and unit-size tier,
    50 cities, Jun-2013 to Sep-2024."""
    return pd.read_csv(RAW_DIR / "nhb_residex" / "city_price_levels_by_unit_size_2013_2024.csv")


@lru_cache(maxsize=8)
def load_residex_index() -> pd.DataFrame:
    """Composite housing price index by city/quarter, 2013-2024. Base
    quarter Mar-2018=100, inferred empirically from the data itself."""
    return pd.read_csv(RAW_DIR / "nhb_residex" / "city_composite_index_2013_2024.csv")


def residex_cities() -> list[str]:
    return sorted(load_residex_price_levels()["city"].unique().tolist())


@lru_cache(maxsize=8)
def load_residex_usable_records() -> pd.DataFrame:
    """NHB RESIDEX data-quality coverage: how many phase-1 city residential
    apartment records existed each quarter (Jun-2017 to Jun-2026) vs. how
    many were "usable" for the Assessment Prices HPI (68-93% of records).

    This is **data-quality coverage of the underlying RESIDEX series**, not
    a city HPI index or price value — the source file states this verbatim
    on every row: "This is data-quality coverage, not city HPI index
    values." See DATA_REGISTRY.md. Status: VERIFIED (directly supplied
    primary statistic)."""
    return pd.read_csv(RAW_DIR / "nhb_residex" / "assessment_price_usable_records_quarterly.csv")


@lru_cache(maxsize=8)
def load_hces_urban_mpce() -> pd.DataFrame:
    """MoSPI HCES 2023-24 Statement 7: average monthly per-capita
    consumption expenditure (MPCE), urban sector, by state/UT — a single
    cross-section for survey year 2023-24.

    This is **consumption expenditure, not income**, and **state/UT-level,
    not city-level** — the source file states this verbatim on every row:
    "Use only as an urban state/UT consumption proxy; do not label as city
    household income." See DATA_REGISTRY.md and analysis/housing.py (the
    `income_source='mpce'` path on `city_affordability`). Status: VERIFIED
    (directly supplied primary statistic)."""
    return pd.read_csv(RAW_DIR / "hces" / "state_ut_urban_mpce_2023_24.csv")


# ---------------------------------------------------------------------------
# Real data: state-level files that had no loader yet (added for the State
# Economy Lab explorer tabs, analysis/states.py). Both return the file exactly as
# read -- no cleaning, realignment or renaming happens here.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_state_gsdp_nsdp_percapita() -> pd.DataFrame:
    """Per-capita GSDP and NSDP, current and constant prices, 2023-24 and
    2024-25, ~33 states/UTs plus an "India" row (the original, earlier
    upload; source not confirmed -- PARTIAL, see DATA_REGISTRY.md).

    Read as strings with no NA conversion so the caller sees the cells
    exactly as stored. Known issues, carried as-is (not repaired here):
    this is an **older release vintage** than `load_nsdp_current()`
    (values differ by ~1-2% for ~20 states); the Delhi row is blanked;
    the Ladakh row has one field fewer than the header, so its values
    cannot be placed in the right columns with certainty
    (analysis/states.py excludes it rather than realigning it); some blank
    cells contain a single space."""
    return pd.read_csv(RAW_DIR / "state_gsdp_nsdp_percapita.csv", dtype=str, keep_default_na=False)


@lru_cache(maxsize=8)
def load_nsdp_constant_as_published() -> pd.DataFrame:
    """Per-capita NSDP, constant prices, RBI Handbook Table 26 exactly as
    published in its two base-year blocks (2004-05 base: 2004-05 to
    2014-15; 2011-12 base: 2011-12 to 2022-23). The spliced series in
    `load_nsdp_spliced()` is built from this file. Includes the table's
    two footnote rows and Jammu & Kashmir under two different territorial
    definitions ("Jammu & Kashmir*" incl. Ladakh, "Jammu & Kashmir-U.T.")."""
    return pd.read_csv(RAW_DIR / "rbi_handbook" / "percapita_nsdp_constant_prices_2004_05_to_2022_23.csv")


# ---------------------------------------------------------------------------
# Real data: World Inequality Lab (WIL) estimates for India, extracted from
# Bharti, Chancel, Piketty & Somanchi (2024), "Income and Wealth Inequality
# in India, 1922-2023: The Rise of the Billionaire Raj", WIL Working Paper
# 2024/09, by scripts/extract_wil_tables.py (no number retyped by hand).
# Status: VERIFIED (transcribed from the paper's own tables).
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_wil_income_2022() -> pd.DataFrame:
    """Table 2: income by group, 2022-23 (Average ... Top 0.001%)."""
    return pd.read_csv(RAW_DIR / "wil" / "table2_income_2022_23.csv")


@lru_cache(maxsize=8)
def load_wil_wealth_2022() -> pd.DataFrame:
    """Table 3: wealth by group, 2022-23 (Average ... Top 0.001%)."""
    return pd.read_csv(RAW_DIR / "wil" / "table3_wealth_2022_23.csv")


@lru_cache(maxsize=8)
def load_wil_income_shares() -> pd.DataFrame:
    """Table B.1: pre-tax national income shares (%), annual 1951-2022."""
    return pd.read_csv(RAW_DIR / "wil" / "tableB1_income_shares_1951_2022.csv")


@lru_cache(maxsize=8)
def load_wil_wealth_shares() -> pd.DataFrame:
    """Table C.1: national wealth shares (%), 1961-2023. Survey years only
    before 2002 (1961, 1971, 1981, 1991); 2023 is flagged tentative by the
    authors (`tentative` column)."""
    return pd.read_csv(RAW_DIR / "wil" / "tableC1_wealth_shares_1961_2023.csv")


@lru_cache(maxsize=8)
def load_wil_vhnwi() -> pd.DataFrame:
    """Table C.2: Forbes billionaires and Hurun rich-list counts and net
    wealth as % of NNI, 1988-2022 (blank where the list was not published)."""
    return pd.read_csv(RAW_DIR / "wil" / "tableC2_vhnwi_1988_2022.csv")


@lru_cache(maxsize=8)
def load_wil_facts() -> pd.DataFrame:
    """Figures stated in the paper's text (growth rates, wealth-income
    ratio, pre-1951 top shares). `qualifier`: stated / approximate / lower
    bound; `source` gives the section."""
    return pd.read_csv(RAW_DIR / "wil" / "long_run_facts.csv")


@lru_cache(maxsize=2)
def load_aidis_debt_headline() -> pd.DataFrame:
    """Headline household-debt figures from the NSS 77th round AIDIS
    (reference date 30 June 2018): incidence and average amount of debt,
    rural and urban, and the highest/lowest states. Per-row status."""
    return pd.read_csv(RAW_DIR / "aidis" / "aidis77_debt_headline.csv")


# ---------------------------------------------------------------------------
# Real data: latest monthly releases (MoSPI CPI and IIP, RBI policy rate and
# household inflation-expectations survey), entered by hand from official
# releases and cross-checked against press coverage. Each row carries its
# own status, base year and release type -- see DATA_REGISTRY.md.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_macro_monthly() -> pd.DataFrame:
    """One row per (indicator, reference_period); `reference_period` is a
    string ("2026-08", or a labelled range for cumulative figures)."""
    return pd.read_csv(RAW_DIR / "macro_monthly" / "india_macro_monthly.csv", dtype={"reference_period": str})


@lru_cache(maxsize=8)
def load_rbi_policy_decisions() -> pd.DataFrame:
    """Dated RBI policy-repo-rate decisions (one row per decision)."""
    return pd.read_csv(RAW_DIR / "macro_monthly" / "rbi_policy_decisions.csv",
                       parse_dates=["decision_date", "effective_date"])


@lru_cache(maxsize=8)
def load_release_calendar() -> pd.DataFrame:
    """Scheduled future releases -- never observed values."""
    return pd.read_csv(RAW_DIR / "macro_monthly" / "release_calendar.csv",
                       parse_dates=["scheduled_release_date"])


# ---------------------------------------------------------------------------
# The author's Paper A (Income & wealth inequality in India): Table 1 asset
# returns and Figure 2 end values, transcribed from
# app/static/papers/Income_Wealth_Inequality_India.pdf. Returns are the
# paper's 1991-2021 nominal averages (Wahengbam 2023, CSEP); shares RBI 2017.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_paper_a_returns() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "author_paper" / "paperA_table1_asset_returns.csv")


@lru_cache(maxsize=8)
def load_paper_a_figure2() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "author_paper" / "paperA_figure2_endpoints.csv")
