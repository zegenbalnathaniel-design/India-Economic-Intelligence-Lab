"""Housing Intelligence — affordability metrics on real NHB RESIDEX data.

Combines NHB RESIDEX city-level housing price levels (real, see
data/raw/nhb_residex/) with state per-capita NSDP as an **explicit,
documented income proxy** (no city-level household income exists in any
source provided so far — see DATA_REGISTRY.md). Every function that uses
the proxy says so in its return value / docstring; nothing here claims to
measure true city-level household income.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


# City -> state mapping for the 50 NHB RESIDEX cities. Plain geography
# (which state each city is in), not a statistical estimate.
CITY_TO_STATE: Dict[str, str] = {
    "Ahmedabad": "Gujarat", "Bengaluru": "Karnataka", "Bhiwadi": "Rajasthan",
    "Bhopal": "Madhya Pradesh", "Bhubaneswar": "Odisha",
    "Bidhan Nagar (Excluding Rajarhat)": "West Bengal", "Chakan": "Maharashtra",
    "Chandigarh (Tricity)": "Chandigarh", "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu",
    "Dehradun": "Uttarakhand", "Delhi": "Delhi", "Faridabad": "Haryana",
    "Gandhinagar": "Gujarat", "Ghaziabad": "Uttar Pradesh", "Greater Noida": "Uttar Pradesh",
    "Gurugram": "Haryana", "Guwahati": "Assam", "Howrah": "West Bengal",
    "Hyderabad": "Telangana", "Indore": "Madhya Pradesh", "Jaipur": "Rajasthan",
    "Kalyan Dombivali": "Maharashtra", "Kanpur": "Uttar Pradesh", "Kochi": "Kerala",
    "Kolkata": "West Bengal", "Lucknow": "Uttar Pradesh", "Ludhiana": "Punjab",
    "Meerut": "Uttar Pradesh", "Mira Bhayander": "Maharashtra", "Mumbai": "Maharashtra",
    "Nagpur": "Maharashtra", "Nashik": "Maharashtra", "Navi Mumbai": "Maharashtra",
    "New Town Kolkata": "West Bengal", "Noida": "Uttar Pradesh", "Panvel": "Maharashtra",
    "Patna": "Bihar", "Pimpri Chinchwad": "Maharashtra", "Pune": "Maharashtra",
    "Raipur": "Chhattisgarh", "Rajkot": "Gujarat", "Ranchi": "Jharkhand",
    "Surat": "Gujarat", "Thane": "Maharashtra", "Thiruvananthapuram": "Kerala",
    "Vadodara": "Gujarat", "Vasai Virar": "Maharashtra", "Vijayawada": "Andhra Pradesh",
    "Vizag": "Andhra Pradesh",
}

RESIDEX_BASE_QUARTER = "Mar-2018"  # inferred empirically from the index data; see DATA_REGISTRY.md

# A representative dwelling size used to turn a per-sq.m. price into a
# total price. 70 sq.m. (~754 sq.ft) is a commonly used reference for a
# modest 2BHK apartment in Indian metros -- an explicit, overridable
# assumption, not a measured figure.
DEFAULT_UNIT_SIZE_SQM = 70.0


_MONTH_TO_Q = {"mar": 1, "jun": 2, "sep": 3, "dec": 4}


def parse_residex_quarter(quarter_str: str) -> pd.Period:
    """Parse the NHB RESIDEX quarter label into a proper, sortable
    `pandas.Period`. The source tables format this label inconsistently
    across years (e.g. 'Jun-2013', 'JUN-2018', 'DEC 2018', 'Mar 2019' all
    appear in the same column) — this normalises all of them rather than
    relying on string sort, which gets the chronological order wrong
    (alphabetically, 'Dec' < 'Jun' < 'Mar' < 'Sep').
    """
    s = str(quarter_str).strip().replace("-", " ").replace("_", " ")
    parts = [p for p in s.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Unrecognised RESIDEX quarter label: {quarter_str!r}")
    month_raw, year_raw = parts
    month_key = month_raw.strip().lower()[:3]
    if month_key not in _MONTH_TO_Q:
        raise ValueError(f"Unrecognised month in RESIDEX quarter label: {quarter_str!r}")
    year = int(year_raw)
    return pd.Period(year=year, quarter=_MONTH_TO_Q[month_key], freq="Q-MAR")


def sort_quarters(df: pd.DataFrame, quarter_col: str = "quarter") -> pd.DataFrame:
    """Return `df` sorted into true chronological order by its RESIDEX
    quarter-label column (see `parse_residex_quarter`)."""
    key = df[quarter_col].map(parse_residex_quarter)
    return df.assign(_sort_key=key).sort_values("_sort_key").drop(columns="_sort_key")


def emi(principal: float, annual_interest_rate: float, loan_years: float) -> float:
    """Standard amortising-loan EMI formula.

        EMI = P * r * (1+r)^n / ((1+r)^n - 1)

    where r is the monthly interest rate and n the number of monthly
    instalments. At r=0, reduces to P/n (no division by zero).
    """
    if principal < 0:
        raise ValueError("principal must be non-negative.")
    if loan_years <= 0:
        raise ValueError("loan_years must be positive.")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate must be non-negative.")
    n = int(round(loan_years * 12))
    if annual_interest_rate == 0:
        return principal / n
    r = annual_interest_rate / 12.0
    factor = (1 + r) ** n
    return principal * r * factor / (factor - 1)


def price_to_income_ratio(price: float, annual_income: float) -> float:
    if annual_income <= 0:
        raise ValueError("annual_income must be positive.")
    if price < 0:
        raise ValueError("price must be non-negative.")
    return price / annual_income


def mortgage_payment_to_income_ratio(emi_monthly: float, monthly_income: float) -> float:
    if monthly_income <= 0:
        raise ValueError("monthly_income must be positive.")
    if emi_monthly < 0:
        raise ValueError("emi_monthly must be non-negative.")
    return emi_monthly / monthly_income


@dataclass
class CityAffordability:
    city: str
    state: str
    quarter: str
    price_per_sqm: float
    unit_price: float
    annual_income_proxy: float
    price_to_income: float
    emi_monthly: float
    emi_to_income_pct: float
    income_is_state_proxy: bool = True  # always True until real city income exists


def city_affordability(
    price_levels: pd.DataFrame,
    nsdp_current: pd.DataFrame,
    city: str,
    quarter: Optional[str] = None,
    unit_size_sqm: float = DEFAULT_UNIT_SIZE_SQM,
    down_payment_pct: float = 0.20,
    annual_interest_rate: float = 0.085,
    loan_years: float = 20.0,
) -> CityAffordability:
    """Compute affordability for one city using real RESIDEX prices and
    the state-NSDP income proxy (see module docstring)."""
    if city not in CITY_TO_STATE:
        raise KeyError(f"Unknown city: {city!r}. Not in the NHB RESIDEX city list.")
    state = CITY_TO_STATE[city]

    city_prices = price_levels[price_levels["city"] == city].copy()
    if city_prices.empty:
        raise ValueError(f"No RESIDEX price data for {city!r}.")
    if quarter is None:
        quarter = sort_quarters(city_prices)["quarter"].iloc[-1]
    row = city_prices[city_prices["quarter"] == quarter]
    if row.empty:
        raise ValueError(f"No RESIDEX price data for {city!r} at quarter {quarter!r}.")
    price_per_sqm = float(row["composite_price_inr_per_sqm"].iloc[0])
    unit_price = price_per_sqm * unit_size_sqm

    income_row = nsdp_current[(nsdp_current["state"] == state)].dropna(subset=["percapita_nsdp_current_prices_inr"])
    if income_row.empty:
        raise ValueError(f"No per-capita NSDP data for {state!r} (proxy for {city!r}).")
    income_row = income_row.sort_values("financial_year").iloc[-1]
    annual_income_proxy = float(income_row["percapita_nsdp_current_prices_inr"])

    loan_amount = unit_price * (1 - down_payment_pct)
    emi_monthly = emi(loan_amount, annual_interest_rate, loan_years)
    pi = price_to_income_ratio(unit_price, annual_income_proxy)
    emi_pct = mortgage_payment_to_income_ratio(emi_monthly, annual_income_proxy / 12.0) * 100.0

    return CityAffordability(
        city=city, state=state, quarter=str(quarter), price_per_sqm=price_per_sqm, unit_price=unit_price,
        annual_income_proxy=annual_income_proxy, price_to_income=pi, emi_monthly=emi_monthly, emi_to_income_pct=emi_pct,
    )


def affordability_across_cities(
    price_levels: pd.DataFrame, nsdp_current: pd.DataFrame, **kwargs,
) -> pd.DataFrame:
    """city_affordability() for every city with both price and income
    data available, as a tidy DataFrame sorted by price-to-income descending."""
    rows = []
    for city in price_levels["city"].unique():
        state = CITY_TO_STATE.get(city)
        if state is None:
            continue
        if not (nsdp_current["state"] == state).any():
            continue
        try:
            result = city_affordability(price_levels, nsdp_current, city, **kwargs)
            rows.append(vars(result))
        except (KeyError, ValueError):
            continue
    df = pd.DataFrame(rows)
    return df.sort_values("price_to_income", ascending=False).reset_index(drop=True) if not df.empty else df
