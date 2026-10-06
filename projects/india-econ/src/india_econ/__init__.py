"""india_econ: a small, honestly-scoped Python package for Indian economic indicators.

Each public function (``gdp``, ``inflation``, ``unemployment``, ``trade``,
``exchange_rate``, ``interest_rates``, ``government_finance``,
``household_finance``) tries a live fetch from the World Bank's open,
unauthenticated API first, and falls back to a clearly-labelled
deterministic synthetic series if that fails or is disabled. Every
returned :class:`~india_econ.core.IndicatorResult` exposes
``.metadata["status"]`` (also ``.source``) so callers can check,
programmatically, whether they got live or synthetic data.

This package covers a deliberately small, illustrative set of indicator
categories -- it is not a comprehensive Indian economic data platform.
See the README for scope and limitations.
"""

from .core import IndicatorResult
from .exceptions import (
    DataFetchError,
    IndiaEconError,
    InvalidDateRangeError,
    UnknownIndicatorError,
)
from .indicators import (
    exchange_rate,
    gdp,
    get_metadata,
    government_finance,
    household_finance,
    inflation,
    interest_rates,
    trade,
    unemployment,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "IndicatorResult",
    "IndiaEconError",
    "UnknownIndicatorError",
    "InvalidDateRangeError",
    "DataFetchError",
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
