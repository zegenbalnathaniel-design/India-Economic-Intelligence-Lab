"""Data loaders for the monetary-transmission (empirical) module.

The repo ships an *illustrative* quarterly panel for five Indian banks and
the RBI repo rate. Every value is clearly labelled ILLUSTRATIVE — see
`docs/DATA_SOURCES.md`. To reproduce with real values, replace
`data/processed/bank_panel.csv` and `data/processed/repo_rate.csv` with
values sourced from bank annual reports and RBI's DBIE
(https://dbie.rbi.org.in).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


@lru_cache(maxsize=8)
def load_bank_panel() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "bank_panel.csv", parse_dates=["period"])


@lru_cache(maxsize=8)
def load_repo_rate() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "repo_rate.csv", parse_dates=["period"])


def bank_names() -> list[str]:
    return sorted(load_bank_panel()["bank"].unique().tolist())


def joined_panel() -> pd.DataFrame:
    return load_bank_panel().merge(load_repo_rate(), on="period", how="left")
