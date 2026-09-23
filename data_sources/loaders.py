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
