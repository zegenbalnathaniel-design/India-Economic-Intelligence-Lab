"""Loader for the bundled SYNTHETIC per-city housing baseline.

See `examples/generate_synthetic_city_housing.py` for how the CSV this
module reads was produced, and `docs/DATA_SOURCES.md` for where real data
could be sourced instead. Nothing returned by this module should ever be
presented as a real statistic about Indian housing markets.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic_city_housing_baseline.csv"

CITY_NAMES: list[str] = [
    "Mumbai",
    "Delhi NCR",
    "Bengaluru",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Kolkata",
    "Ahmedabad",
]


def load_synthetic_city_baseline(path: str | Path | None = None) -> pd.DataFrame:
    """Load the synthetic per-city baseline CSV into a DataFrame.

    Args:
        path: Optional override path. Defaults to
            `data/synthetic_city_housing_baseline.csv` relative to the
            project root.

    Returns:
        DataFrame with one row per city: city, synthetic_annual_household
        _income_inr, synthetic_house_price_inr,
        illustrative_price_to_income_anchor, data_status,
        synthetic_price_to_income_ratio.

    Raises:
        FileNotFoundError: If the CSV does not exist at the resolved path
            (run `examples/generate_synthetic_city_housing.py` first).
    """
    resolved = Path(path) if path is not None else DEFAULT_DATA_PATH
    if not resolved.exists():
        raise FileNotFoundError(
            f"Synthetic city baseline not found at {resolved}. Run "
            "`python examples/generate_synthetic_city_housing.py` to generate it."
        )
    return pd.read_csv(resolved)


def city_baseline(city: str, path: str | Path | None = None) -> dict:
    """Look up one city's synthetic baseline row as a plain dict.

    Args:
        city: City name, must match a value in `CITY_NAMES` exactly.
        path: Optional override path, forwarded to
            `load_synthetic_city_baseline`.

    Returns:
        Dict with keys matching the CSV columns for that city's row.

    Raises:
        ValueError: If `city` is not found in the loaded baseline.
    """
    df = load_synthetic_city_baseline(path)
    matches = df[df["city"] == city]
    if matches.empty:
        raise ValueError(f"Unknown city {city!r}; expected one of {CITY_NAMES}.")
    return matches.iloc[0].to_dict()
