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
# Economy Explorer, analysis/states.py). Both return the file exactly as
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
# Real data: World Inequality Lab (WIL) distributional estimates for India,
# as supplied by the author (a summary of Bharti, Chancel, Piketty &
# Somanchi, "Income and Wealth Inequality in India, 1922-2023: The Rise of
# the Billionaire Raj", WIL Working Paper 2024/09). Status: PARTIAL -- the
# values are transcribed from that summary and have not yet been checked
# against the paper's own tables. Approximate statements ("about 29%") are
# kept as notes, never as numbers. Derived values live in
# analysis/inequality.py.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_wil_distribution() -> pd.DataFrame:
    """Income and wealth by group, 2022-23 (Bottom 50% ... Top 0.1%)."""
    return pd.read_csv(RAW_DIR / "wil" / "distribution_2022_23.csv")


@lru_cache(maxsize=8)
def load_wil_wealth_shares() -> pd.DataFrame:
    """Wealth shares by group, 1961 vs 2022-23."""
    return pd.read_csv(RAW_DIR / "wil" / "wealth_shares_1961_2022_23.csv")


@lru_cache(maxsize=8)
def load_wil_facts() -> pd.DataFrame:
    """Long-run headline figures (growth, wealth-income ratio, billionaires).
    `qualifier` is "stated", "approximate" or "upper bound"."""
    return pd.read_csv(RAW_DIR / "wil" / "long_run_facts.csv")


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
