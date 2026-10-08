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


def _split_quarter_label(quarter_str: str) -> tuple[str, int]:
    """Shared parsing step for the RESIDEX quarter label: returns
    (3-letter lowercase month key, calendar year). Raises ValueError on
    anything that isn't recognisably '<month> <year>' in some separator
    style (the source tables mix 'Jun-2013', 'JUN-2018', 'DEC 2018', ...)."""
    s = str(quarter_str).strip().replace("-", " ").replace("_", " ")
    parts = [p for p in s.split() if p]
    if len(parts) != 2:
        raise ValueError(f"Unrecognised RESIDEX quarter label: {quarter_str!r}")
    month_raw, year_raw = parts
    month_key = month_raw.strip().lower()[:3]
    if month_key not in _MONTH_TO_Q:
        raise ValueError(f"Unrecognised month in RESIDEX quarter label: {quarter_str!r}")
    return month_key, int(year_raw)


def parse_residex_quarter(quarter_str: str) -> pd.Period:
    """Parse the NHB RESIDEX quarter label into a proper, sortable
    `pandas.Period`. The source tables format this label inconsistently
    across years (e.g. 'Jun-2013', 'JUN-2018', 'DEC 2018', 'Mar 2019' all
    appear in the same column) — this normalises all of them rather than
    relying on string sort, which gets the chronological order wrong
    (alphabetically, 'Dec' < 'Jun' < 'Mar' < 'Sep').
    """
    month_key, year = _split_quarter_label(quarter_str)
    return pd.Period(year=year, quarter=_MONTH_TO_Q[month_key], freq="Q-MAR")


def financial_year_of_quarter(quarter_str: str) -> str:
    """Map a RESIDEX quarter label to the Indian financial year (April to
    March) it falls in, formatted the same way as the NSDP tables
    ('YYYY-YY'), e.g.:

    - 'Mar-2018' (Jan-Mar 2018, the last quarter of FY2017-18) -> '2017-18'
    - 'Jun-2018' (Apr-Jun 2018, the first quarter of FY2018-19) -> '2018-19'
    - 'Dec-2018' (Oct-Dec 2018, still FY2018-19) -> '2018-19'

    This is a plain calendar mapping (no estimation), used to align the
    quarterly RESIDEX composite index with the annual NSDP income series
    for `relative_price_income_pressure`.
    """
    month_key, year = _split_quarter_label(quarter_str)
    start_year = year - 1 if month_key == "mar" else year
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


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


# Income-proxy caveats, carried verbatim (or near-verbatim, crediting the
# exact source wording) into every result that uses them, and into the UI.
# Neither proxy is true city-level household income -- see DATA_REGISTRY.md.
INCOME_PROXY_CAVEATS: Dict[str, str] = {
    "nsdp": (
        "State per-capita NSDP (current prices) used as a city-income proxy — no "
        "city-level household income exists in any source available to this project. "
        "Systematically overstates affordability in cities priced above their state average."
    ),
    "mpce": (
        "Use only as an urban state/UT consumption proxy; do not label as city household "
        "income. (Verbatim notes-column caveat, MoSPI HCES 2023-24 Statement 7 — this is "
        "average monthly per-capita CONSUMPTION EXPENDITURE, not income, and state/UT-level, "
        "not city-level.)"
    ),
}


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
    income_source: str = "nsdp"         # "nsdp" (per-capita NSDP) or "mpce" (urban MPCE)
    income_caveat: str = ""             # the exact caveat for income_source, see INCOME_PROXY_CAVEATS


def city_affordability(
    price_levels: pd.DataFrame,
    nsdp_current: pd.DataFrame,
    city: str,
    quarter: Optional[str] = None,
    unit_size_sqm: float = DEFAULT_UNIT_SIZE_SQM,
    down_payment_pct: float = 0.20,
    annual_interest_rate: float = 0.085,
    loan_years: float = 20.0,
    income_source: str = "nsdp",
    mpce_urban: Optional[pd.DataFrame] = None,
) -> CityAffordability:
    """Compute affordability for one city using real RESIDEX prices and
    one of two explicit, documented income proxies (see module docstring
    and INCOME_PROXY_CAVEATS) -- neither is true city-level household
    income, since none exists in any source available to this project:

    - income_source='nsdp' (default, backward-compatible): state per-capita
      NSDP, current prices, from `nsdp_current`.
    - income_source='mpce': state/UT urban per-capita MPCE (MoSPI HCES
      2023-24), annualised (monthly x 12), from `mpce_urban`
      (data_sources.loaders.load_hces_urban_mpce()). This is a single
      cross-section (2023-24 only) and is CONSUMPTION, not income.
    """
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

    if income_source == "nsdp":
        income_row = nsdp_current[(nsdp_current["state"] == state)].dropna(subset=["percapita_nsdp_current_prices_inr"])
        if income_row.empty:
            raise ValueError(f"No per-capita NSDP data for {state!r} (proxy for {city!r}).")
        income_row = income_row.sort_values("financial_year").iloc[-1]
        annual_income_proxy = float(income_row["percapita_nsdp_current_prices_inr"])
    elif income_source == "mpce":
        if mpce_urban is None:
            raise ValueError(
                "income_source='mpce' requires the mpce_urban DataFrame "
                "(data_sources.loaders.load_hces_urban_mpce())."
            )
        mpce_row = mpce_urban[mpce_urban["state_ut"] == state]
        if mpce_row.empty:
            raise ValueError(f"No HCES urban MPCE data for {state!r} (proxy for {city!r}).")
        monthly_mpce = float(mpce_row["average_monthly_per_capita_consumption_expenditure_inr"].iloc[0])
        annual_income_proxy = monthly_mpce * 12.0
    else:
        raise ValueError(f"Unknown income_source: {income_source!r}. Must be 'nsdp' or 'mpce'.")

    loan_amount = unit_price * (1 - down_payment_pct)
    emi_monthly = emi(loan_amount, annual_interest_rate, loan_years)
    pi = price_to_income_ratio(unit_price, annual_income_proxy)
    emi_pct = mortgage_payment_to_income_ratio(emi_monthly, annual_income_proxy / 12.0) * 100.0

    return CityAffordability(
        city=city, state=state, quarter=str(quarter), price_per_sqm=price_per_sqm, unit_price=unit_price,
        annual_income_proxy=annual_income_proxy, price_to_income=pi, emi_monthly=emi_monthly, emi_to_income_pct=emi_pct,
        income_source=income_source, income_caveat=INCOME_PROXY_CAVEATS[income_source],
    )


def affordability_across_cities(
    price_levels: pd.DataFrame,
    nsdp_current: pd.DataFrame,
    mpce_urban: Optional[pd.DataFrame] = None,
    **kwargs,
) -> pd.DataFrame:
    """city_affordability() for every city with both price and income
    data available, as a tidy DataFrame sorted by price-to-income descending.

    `mpce_urban` and an `income_source='mpce'` kwarg select the alternative
    MoSPI HCES urban-MPCE income proxy instead of the default state-NSDP
    proxy (see `city_affordability`); omitting both keeps the original
    NSDP-only behaviour."""
    rows = []
    for city in price_levels["city"].unique():
        state = CITY_TO_STATE.get(city)
        if state is None:
            continue
        try:
            result = city_affordability(price_levels, nsdp_current, city, mpce_urban=mpce_urban, **kwargs)
            rows.append(vars(result))
        except (KeyError, ValueError):
            continue
    df = pd.DataFrame(rows)
    return df.sort_values("price_to_income", ascending=False).reset_index(drop=True) if not df.empty else df


# ---------------------------------------------------------------------------
# RPIPI -- Relative Price-to-Income Pressure Index (real time series)
# ---------------------------------------------------------------------------

@dataclass
class RpipiResult:
    """Result of `relative_price_income_pressure` for one city.

    `series` has columns: financial_year, price_index, income_proxy, rpipi
    — one row per financial year in the overlap window between the
    RESIDEX composite index and the income series, in chronological order.
    `rpipi` is exactly 100.0 at `base_financial_year` by construction.
    """
    city: str
    state: str
    base_financial_year: str
    series: pd.DataFrame
    latest_financial_year: str
    latest_rpipi: float
    status: str  # "ok" or "insufficient data (<2 overlapping years)"


def relative_price_income_pressure(
    residex_index: pd.DataFrame,
    income_annual: pd.DataFrame,
    city: str,
    income_value_col: str = "percapita_nsdp_current_prices_inr",
) -> RpipiResult:
    """Relative Price-to-Income Pressure Index (RPIPI): a fallback to the
    full ICHASI methodology that is **fully computable from real data
    already in this repository** -- the real NHB RESIDEX composite price
    index (`data_sources.loaders.load_residex_index()`, 2013-2024) and the
    real state per-capita NSDP time series (`load_nsdp_current()` or
    `load_nsdp_spliced()`, via `CITY_TO_STATE`), with no invented benchmark
    price level or mortgage-rate history.

        RPIPI_c,t = 100 * (HPI_c,t / HPI_c,0) / (Y_c,t / Y_c,0)

    where `HPI_c,t` is the city's composite index value at financial year
    `t`, `Y_c,t` is its state's per-capita income (NSDP or, if you pass
    `load_nsdp_spliced()`, the constant-price spliced series) at `t`, and
    `0` denotes the **base period = the earliest financial year both
    series cover for this city** (not a fixed calendar year -- different
    cities can have different overlap windows depending on data coverage).

    Reading the result:
    - **100** = price and income have grown by exactly the same proportion
      since the base period.
    - **>100** = housing price has outpaced income since the base period
      (affordability pressure has increased).
    - **<100** = income has outpaced housing price since the base period
      (affordability pressure has eased).

    The RESIDEX composite index is published quarterly; it is averaged
    across the (up to four) quarters observed in each financial year to
    align it with the annual NSDP series. This averaging is a transparent,
    documented calculation over real data (not an estimate standing in for
    a missing value) -- see `financial_year_of_quarter` for the exact
    calendar mapping used.
    """
    if city not in CITY_TO_STATE:
        raise KeyError(f"Unknown city: {city!r}. Not in the NHB RESIDEX city list.")
    state = CITY_TO_STATE[city]

    city_col = "City" if "City" in residex_index.columns else "city"
    quarter_col = "quarter_raw" if "quarter_raw" in residex_index.columns else "quarter"
    city_idx = residex_index[residex_index[city_col] == city].copy()
    if city_idx.empty:
        raise ValueError(f"No RESIDEX composite-index data for {city!r}.")

    city_idx["financial_year"] = city_idx[quarter_col].map(financial_year_of_quarter)
    price_annual = (
        city_idx.groupby("financial_year")["composite_index"]
        .mean()
        .rename("price_index")
        .reset_index()
    )

    income_state = income_annual[income_annual["state"] == state].dropna(subset=[income_value_col])
    income_state = income_state[["financial_year", income_value_col]].rename(
        columns={income_value_col: "income_proxy"}
    )

    merged = price_annual.merge(income_state, on="financial_year", how="inner")
    if merged.empty:
        raise ValueError(
            f"No overlapping financial years between the RESIDEX composite index for {city!r} "
            f"and the income series for {state!r}."
        )
    merged = merged.sort_values("financial_year").reset_index(drop=True)

    base_price = float(merged["price_index"].iloc[0])
    base_income = float(merged["income_proxy"].iloc[0])
    merged["rpipi"] = 100.0 * (merged["price_index"] / base_price) / (merged["income_proxy"] / base_income)

    status = "ok" if len(merged) >= 2 else "insufficient data (<2 overlapping years)"

    return RpipiResult(
        city=city,
        state=state,
        base_financial_year=str(merged["financial_year"].iloc[0]),
        series=merged[["financial_year", "price_index", "income_proxy", "rpipi"]],
        latest_financial_year=str(merged["financial_year"].iloc[-1]),
        latest_rpipi=float(merged["rpipi"].iloc[-1]),
        status=status,
    )


# ---------------------------------------------------------------------------
# ICHASI cross-section fallback -- percentile-clipped affordability stress
# ---------------------------------------------------------------------------

# No real mortgage-rate-HISTORY dataset exists in this project (see
# DATA_REGISTRY.md, "Still specifically needed" -- a proper version needs a
# fixed lender panel observed over time, not one assumed number). Rather
# than invent one, this cross-section uses the single, user-selected rate
# already exposed as sliders on the Housing Lab page, applied uniformly to
# every city -- an explicit, disclosed simplification, not a disguised
# fabrication of a rate history that was never collected.
RATE_DISCLOSURE = (
    "Stress scores use ONE representative, currently-selected mortgage rate, loan "
    "tenure and down-payment -- the same controls used elsewhere on this page -- "
    "applied uniformly to every city. This is NOT an observed historical, "
    "cross-lender mortgage-rate panel; no such dataset exists yet in this project "
    "(see DATA_REGISTRY.md, 'Still specifically needed')."
)


@dataclass
class StressIndexResult:
    """Result of `stress_index_cross_section`: a percentile-clipped 0-100
    affordability stress score across cities at a single quarter.

    `scores` has columns: city, state, quarter, price_to_income,
    pti_clipped, stress_score_0_100 -- sorted by stress_score_0_100
    descending.
    """
    quarter: str
    annual_interest_rate: float
    loan_years: float
    down_payment_pct: float
    clip_low_pctile: float
    clip_high_pctile: float
    scores: pd.DataFrame
    rate_disclosure: str = RATE_DISCLOSURE


def stress_index_cross_section(
    price_levels: pd.DataFrame,
    nsdp_current: pd.DataFrame,
    quarter: Optional[str] = None,
    unit_size_sqm: float = DEFAULT_UNIT_SIZE_SQM,
    down_payment_pct: float = 0.20,
    annual_interest_rate: float = 0.085,
    loan_years: float = 20.0,
    low_pctile: float = 5.0,
    high_pctile: float = 95.0,
    income_source: str = "nsdp",
    mpce_urban: Optional[pd.DataFrame] = None,
) -> StressIndexResult:
    """A percentile-clipped, 0-100 affordability-stress score across cities
    at a SINGLE quarter (cross-section, not a time series -- for the time
    series see `relative_price_income_pressure`).

    This is the part of the ICHASI ("India City Housing Affordability
    Stress Index") spec that can be honestly built from data already in
    this repository: real RESIDEX price levels, a real state-income proxy,
    and the standard EMI/price-to-income machinery already used elsewhere
    in this module (`city_affordability`, `price_to_income_ratio`). It does
    **not** reconstruct a city benchmark price level or a mortgage-rate
    history -- see RATE_DISCLOSURE and the module-level comment above this
    function for exactly why not.

    Method:
    1. Compute each city's price-to-income (PTI) ratio at the given
       quarter via `affordability_across_cities` (same quarter for every
       city, so cities are genuinely comparable).
    2. Clip each city's PTI to the [`low_pctile`, `high_pctile`] percentile
       range of the comparison set (default 5th-95th), so one extreme
       outlier city cannot compress every other city's score toward zero.
    3. Rescale the clipped PTI linearly onto 0-100:
       `score = (clipped_PTI - p_low) / (p_high - p_low) * 100`.

    A city at or below the low percentile scores 0; at or above the high
    percentile, 100 -- by construction, no city's *displayed* score can
    exceed 100 regardless of how extreme its raw PTI is, while its raw
    (unclipped) `price_to_income` is still reported in `scores` for
    transparency.
    """
    if quarter is None:
        quarter = sort_quarters(price_levels.drop_duplicates(subset=["quarter"]))["quarter"].iloc[-1]

    aff = affordability_across_cities(
        price_levels, nsdp_current, mpce_urban=mpce_urban, quarter=quarter,
        unit_size_sqm=unit_size_sqm, down_payment_pct=down_payment_pct,
        annual_interest_rate=annual_interest_rate, loan_years=loan_years,
        income_source=income_source,
    )
    if len(aff) < 3:
        raise ValueError(
            "Need at least 3 cities with both price and income data at this quarter "
            "to compute a cross-sectional stress index (percentile clipping is "
            "meaningless with fewer)."
        )

    pti = aff["price_to_income"].astype(float)
    lo = float(np.percentile(pti, low_pctile))
    hi = float(np.percentile(pti, high_pctile))
    if hi <= lo:
        # Degenerate case: all PTI values (anywhere outside the clip range)
        # are identical, so percentile clipping alone can't form a range.
        hi = lo + 1e-9

    clipped = pti.clip(lower=lo, upper=hi)
    score = (clipped - lo) / (hi - lo) * 100.0

    scores = aff[["city", "state", "quarter", "price_to_income"]].copy()
    scores["pti_clipped"] = clipped
    scores["stress_score_0_100"] = score
    scores = scores.sort_values("stress_score_0_100", ascending=False).reset_index(drop=True)

    return StressIndexResult(
        quarter=str(quarter),
        annual_interest_rate=annual_interest_rate,
        loan_years=loan_years,
        down_payment_pct=down_payment_pct,
        clip_low_pctile=low_pctile,
        clip_high_pctile=high_pctile,
        scores=scores,
    )
