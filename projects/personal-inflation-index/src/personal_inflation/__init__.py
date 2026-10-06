"""Personal Inflation Index.

A small toolkit for computing a Laspeyres-style personal (household-level)
inflation index from user-supplied expenditure weights and category price
series, and comparing it against an illustrative "official CPI" style
series.

See ``docs/METHODOLOGY.md`` in the project root for the formula, the
economic reasoning behind the project, and a full account of exactly which
numbers in this package are real (none of the default weights are) versus
synthetic demonstration data.
"""

from personal_inflation.index import (
    DEFAULT_CATEGORIES,
    compare_to_reference,
    laspeyres_index,
    normalize_weights,
    personal_index_time_series,
)

__all__ = [
    "DEFAULT_CATEGORIES",
    "laspeyres_index",
    "normalize_weights",
    "personal_index_time_series",
    "compare_to_reference",
]

__version__ = "0.1.0"
