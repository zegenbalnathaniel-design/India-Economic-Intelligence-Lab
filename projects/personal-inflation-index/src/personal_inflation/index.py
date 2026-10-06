"""Core Laspeyres-index logic for the Personal Inflation Index project.

WHAT THIS MODULE DOES NOT DO
-----------------------------
It does not ship, embed, or claim to use any official MoSPI CPI number.
Every category weight and every price series that is not explicitly
supplied by the caller at runtime is, at best, a clearly labeled
*illustrative example* meant to demonstrate the arithmetic. See
``docs/DATA_SOURCES.md`` for where to find the real, official series.

CONVENTIONS USED THROUGHOUT THIS MODULE
----------------------------------------
* The index is expressed on a base of 100 (not 1.0): a basket whose prices
  are unchanged from the base period scores exactly 100.0.
* Weights are always *normalized to sum to 1* before being used. If the
  weights handed in do not sum to 1 (e.g. they were given as percentages
  summing to 100, or as a partial/rounded set), they are rescaled
  proportionally. This is a deliberate, documented choice (see
  ``normalize_weights``) rather than an error, because in interactive use
  (e.g. basket-builder sliders) it is far more useful to silently keep
  relative proportions correct than to force the user to hit exactly
  1.000000 by hand. The one exception is an all-zero weight vector, which
  cannot be normalized and raises ``ValueError``.
* A category that appears in the weights dict but has no matching price
  observation is treated as a *hard error* (``ValueError``), never silently
  imputed or dropped. Silent imputation of a missing household expenditure
  category would quietly change the economic meaning of the index, which
  this project treats as unacceptable. If the caller genuinely wants to
  drop a category, they must remove it from the weights dict themselves
  (an explicit choice), not rely on this code to guess.
* Negative prices are economically meaningless and always raise
  ``ValueError``. A price of exactly 0 is also rejected (division by zero
  in the price-relative, and no real good is free) except where it appears
  only in a period that is not used as the base.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
# A starting checklist of household spending categories loosely modeled on
# the broad groups MoSPI's CPI publishes (Food and beverages, Housing,
# Transport and communication, Education, Health, Recreation, Clothing and
# footwear, Miscellaneous/other). This list is a convenience default for
# the basket builder, NOT a reproduction of the official CPI category
# structure or its sub-items -- users are free (and encouraged) to edit,
# rename, split, or extend it to match their own actual spending.
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "food",
    "housing",
    "transport",
    "education",
    "healthcare",
    "communication",
    "recreation",
    "clothing",
    "other",
)


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Rescale a dict of category weights so that they sum to exactly 1.0.

    This project's documented convention (see module docstring) is to
    *normalize* rather than reject weights that do not already sum to 1 --
    e.g. weights entered as percentages (summing to 100), or a slider UI
    that is off by a rounding error. Relative proportions between
    categories are preserved exactly; only the overall scale changes.

    Parameters
    ----------
    weights:
        Mapping of category name -> non-negative weight. Weights do not
        need to sum to 1; they will be rescaled.

    Returns
    -------
    dict[str, float]
        A new dict with the same keys, rescaled to sum to 1.0.

    Raises
    ------
    ValueError
        If ``weights`` is empty, contains a negative weight, or sums to
        (approximately) zero, since such a vector cannot be rescaled into
        a valid set of expenditure shares.
    """
    if not weights:
        raise ValueError("weights must be a non-empty mapping of category -> weight")

    for category, w in weights.items():
        if w < 0:
            raise ValueError(
                f"weight for category '{category}' is negative ({w!r}); "
                "expenditure weights must be non-negative"
            )

    total = float(sum(weights.values()))
    if np.isclose(total, 0.0):
        raise ValueError(
            "weights sum to zero; cannot normalize an all-zero weight vector "
            "into expenditure shares"
        )

    return {category: float(w) / total for category, w in weights.items()}


def _validate_prices(prices: Mapping[str, float], *, label: str) -> None:
    """Raise ValueError if any price in ``prices`` is negative or zero."""
    for category, price in prices.items():
        if price < 0:
            raise ValueError(
                f"{label} price for category '{category}' is negative ({price!r}); "
                "prices cannot be negative"
            )
        if price == 0:
            raise ValueError(
                f"{label} price for category '{category}' is zero; a price of "
                "zero is not economically meaningful here and would produce a "
                "division by zero or an undefined price relative"
            )


def _require_price(
    prices: Mapping[str, float], category: str, *, label: str
) -> float:
    """Fetch ``prices[category]``, raising a clear error if it is missing.

    This project never silently imputes a missing category price (see
    module docstring): a weighted category with no matching price
    observation is always a hard error that the caller must resolve
    explicitly (e.g. by supplying a price, or by removing that category
    from the weights).
    """
    if category not in prices:
        raise ValueError(
            f"missing {label} price for category '{category}': every category "
            "present in `weights` must have a matching entry in both the base "
            "and current price dicts. This function does not perform implicit "
            "imputation -- either supply a price for this category or remove "
            "it from the weights."
        )
    return prices[category]


def laspeyres_index(
    base_prices: Mapping[str, float],
    current_prices: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Compute a fixed-basket Laspeyres price index on a base of 100.

    Formula
    -------
    ``I_t = 100 * sum_i( w_i * (P_i,t / P_i,0) )``

    where ``w_i`` are the (normalized) base-period expenditure weights,
    ``P_i,0`` is each category's base-period price, and ``P_i,t`` is each
    category's current-period price. This is the textbook Laspeyres
    fixed-basket index: quantities (equivalently, expenditure shares) are
    frozen at the base period, and only prices move. See
    ``docs/METHODOLOGY.md`` for the full derivation and its key assumption
    (no substitution between categories as relative prices change --
    "substitution bias").

    Parameters
    ----------
    base_prices:
        Category -> price in the base period.
    current_prices:
        Category -> price in the current period.
    weights:
        Category -> base-period expenditure weight. Does not need to sum
        to 1; it will be normalized (see ``normalize_weights``).

    Returns
    -------
    float
        The index value, on a base of 100.0 (i.e. an unchanged basket
        returns exactly 100.0; a basket that is on average 12% more
        expensive returns 112.0).

    Raises
    ------
    ValueError
        If weights are empty/negative/all-zero, if any price is negative
        or zero, or if any weighted category is missing a base or current
        price (see module docstring for why missing prices are never
        auto-imputed).
    """
    norm_weights = normalize_weights(weights)

    _validate_prices(base_prices, label="base")
    _validate_prices(current_prices, label="current")

    index_value = 0.0
    for category, w in norm_weights.items():
        p0 = _require_price(base_prices, category, label="base")
        pt = _require_price(current_prices, category, label="current")
        index_value += w * (pt / p0)

    return 100.0 * index_value


def personal_index_time_series(
    price_df: pd.DataFrame,
    weights: Mapping[str, float],
    base_period: object | None = None,
) -> pd.Series:
    """Compute a Laspeyres personal index across every period in a price panel.

    Parameters
    ----------
    price_df:
        A DataFrame indexed by period (e.g. month labels, or a
        ``DatetimeIndex``), with one column per spending category and
        values equal to that category's price level in that period.
        Every column named in ``weights`` must be present.
    weights:
        Category -> base-period expenditure weight (normalized internally;
        need not sum to 1).
    base_period:
        The index label to treat as the base period (its row will read
        exactly 100.0 in the result). Defaults to the first row of
        ``price_df`` (in its existing order) when not given.

    Returns
    -------
    pandas.Series
        The personal index value for every period in ``price_df``, indexed
        the same way, with ``name="personal_index"``.

    Raises
    ------
    ValueError
        If ``price_df`` is empty, if a weighted category has no matching
        column, if ``base_period`` is not present in the index, or if any
        price is negative or zero (propagated from ``laspeyres_index``).
    """
    if price_df.empty:
        raise ValueError("price_df must contain at least one period (row)")

    norm_weights = normalize_weights(weights)
    missing_cols = [c for c in norm_weights if c not in price_df.columns]
    if missing_cols:
        raise ValueError(
            f"price_df is missing a column for weighted categories: {missing_cols}"
        )

    if base_period is None:
        base_period = price_df.index[0]
    elif base_period not in price_df.index:
        raise ValueError(f"base_period {base_period!r} is not present in price_df.index")

    base_prices = price_df.loc[base_period, list(norm_weights)].to_dict()

    values = []
    for period in price_df.index:
        current_prices = price_df.loc[period, list(norm_weights)].to_dict()
        values.append(laspeyres_index(base_prices, current_prices, norm_weights))

    return pd.Series(values, index=price_df.index, name="personal_index")


def compare_to_reference(
    personal_index: pd.Series,
    reference_index: pd.Series,
) -> pd.DataFrame:
    """Compare a personal index series against a reference (e.g. "official CPI") series.

    IMPORTANT: this function performs no economic claim of its own. Any
    "official CPI" series passed in must come from the caller -- this
    project ships only a clearly-labeled illustrative example reference
    series built from example weights (see
    ``data/synthetic_category_price_index.csv`` and
    ``docs/DATA_SOURCES.md``), never a real published CPI number. The gap
    this function computes is only ever as meaningful as the two series
    fed into it.

    Parameters
    ----------
    personal_index:
        A period-indexed Series of personal index values (as returned by
        ``personal_index_time_series``).
    reference_index:
        A period-indexed Series of reference/comparison index values,
        sharing at least some periods with ``personal_index``.

    Returns
    -------
    pandas.DataFrame
        Indexed on the intersection of both series' periods, with columns
        ``personal_index``, ``reference_index``, ``gap_points`` (personal
        minus reference, in index points) and ``gap_pct`` (the gap
        expressed as a percentage of the reference index).

    Raises
    ------
    ValueError
        If the two series share no common periods.
    """
    common = personal_index.index.intersection(reference_index.index)
    if len(common) == 0:
        raise ValueError("personal_index and reference_index share no common periods")

    common = common.sort_values()
    out = pd.DataFrame(
        {
            "personal_index": personal_index.loc[common],
            "reference_index": reference_index.loc[common],
        }
    )
    out["gap_points"] = out["personal_index"] - out["reference_index"]
    out["gap_pct"] = 100.0 * out["gap_points"] / out["reference_index"]
    return out
