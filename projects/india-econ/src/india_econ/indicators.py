"""Public indicator functions.

Every function here follows the same contract: try a live fetch from the
World Bank's open API first, fall back to a clearly-labelled synthetic
series if that fails (or if ``allow_live=False``), and return an
:class:`~india_econ.core.IndicatorResult` whose ``.metadata["status"]``
(also available as ``.source``) says honestly which one happened.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._registry import metadata_dict as _metadata_dict
from .core import IndicatorResult, get_indicator

__all__ = [
    "gdp",
    "inflation",
    "unemployment",
    "trade",
    "exchange_rate",
    "interest_rates",
    "government_finance",
    "household_finance",
    "get_metadata",
]


def gdp(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's GDP level (current US$) and derived year-over-year growth rate.

    Returns a DataFrame with columns ``gdp_current_usd`` and
    ``gdp_growth_pct``, indexed by year.
    """
    return get_indicator("gdp", start, end, allow_live)


def inflation(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's consumer price inflation, annual % change.

    Returns a Series named ``cpi_inflation_pct``, indexed by year.
    """
    return get_indicator("inflation", start, end, allow_live)


def unemployment(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's unemployment rate (ILO modeled estimate), % of labor force.

    Returns a Series named ``unemployment_rate_pct``, indexed by year.
    """
    return get_indicator("unemployment", start, end, allow_live)


def trade(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's exports and imports of goods and services, current US$.

    Returns a DataFrame with columns ``exports_usd`` and ``imports_usd``,
    indexed by year.
    """
    return get_indicator("trade", start, end, allow_live)


def exchange_rate(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's official INR/USD exchange rate, period average.

    Returns a Series named ``inr_per_usd``, indexed by year.
    """
    return get_indicator("exchange_rate", start, end, allow_live)


def interest_rates(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """A policy-adjacent interest rate series (commercial lending rate proxy).

    The World Bank's open API does not publish the RBI's repo rate
    directly; see ``docs/DATA_SOURCES.md`` for why the lending rate is
    used here instead.

    Returns a Series named ``lending_rate_pct``, indexed by year.
    """
    return get_indicator("interest_rates", start, end, allow_live)


def government_finance(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """India's fiscal balance and government debt, both % of GDP.

    Returns a DataFrame with columns ``fiscal_balance_pct_gdp`` (negative
    = deficit) and ``government_debt_pct_gdp``, indexed by year.
    """
    return get_indicator("government_finance", start, end, allow_live)


def household_finance(
    start: Optional[int] = None, end: Optional[int] = None, allow_live: bool = True
) -> IndicatorResult:
    """Economy-wide savings and private-credit proxies for household finance.

    There is no household-level survey series in the World Bank's open
    API, so this uses gross domestic savings and domestic credit to the
    private sector (both % of GDP) as the closest available proxies; see
    ``docs/DATA_SOURCES.md``.

    Returns a DataFrame with columns ``gross_savings_pct_gdp`` and
    ``domestic_credit_private_pct_gdp``, indexed by year.
    """
    return get_indicator("household_finance", start, end, allow_live)


def get_metadata(indicator_name: str) -> Dict[str, Any]:
    """Return the static metadata dict for a named indicator.

    This does not fetch anything -- it's the provider/URL/definition/
    unit/frequency description from the registry, usable without a
    network call. For the live-vs-synthetic status of an *actual* fetch,
    check ``result.metadata["status"]`` (or ``result.source``) on the
    object a function like :func:`gdp` returns.

    Raises :class:`~india_econ.exceptions.UnknownIndicatorError` for an
    unrecognized name.
    """
    return _metadata_dict(indicator_name)
