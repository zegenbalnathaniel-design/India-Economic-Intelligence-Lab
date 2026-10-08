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
