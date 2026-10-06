"""Custom exception types for india-econ.

All exceptions raised deliberately by this package inherit from
:class:`IndiaEconError`, so callers can catch a single base class if they
don't care about the precise failure mode.
"""

from __future__ import annotations

__all__ = [
    "IndiaEconError",
    "UnknownIndicatorError",
    "InvalidDateRangeError",
    "DataFetchError",
]


class IndiaEconError(Exception):
    """Base class for all exceptions raised intentionally by india_econ."""


class UnknownIndicatorError(IndiaEconError):
    """Raised when a caller asks for an indicator name that doesn't exist.

    Example
    -------
    >>> from india_econ import get_metadata
    >>> get_metadata("not_a_real_indicator")
    Traceback (most recent call last):
        ...
    india_econ.exceptions.UnknownIndicatorError: Unknown indicator 'not_a_real_indicator'. ...
    """


class InvalidDateRangeError(IndiaEconError):
    """Raised when ``start``/``end`` arguments are malformed or inverted."""


class DataFetchError(IndiaEconError):
    """Raised internally when a live fetch fails.

    Public API functions catch this and fall back to synthetic data rather
    than letting it propagate, so callers normally will not see this
    exception directly -- it exists mainly so the fallback logic has a
    single, specific thing to catch instead of a bare ``except Exception``.
    """
