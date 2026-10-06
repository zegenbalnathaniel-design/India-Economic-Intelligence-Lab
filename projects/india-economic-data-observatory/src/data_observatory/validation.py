"""Validation and cleaning layer applied to every series before it is
returned to a caller, regardless of whether it came from a live fetch or
the synthetic fallback.

Checks performed:
  1. Index is sorted (monotonically increasing dates).
  2. No duplicate periods (if present, the last observation wins — this is
     the common convention for revised statistical releases superseding an
     earlier one for the same period).
  3. No impossible values for the indicator's documented domain (e.g. a
     negative unemployment rate, a negative price index). Out-of-domain
     points are treated as missing (NaN) rather than silently kept.
  4. Missing-data handling: gaps are forward-filled, but every imputed
     point is flagged in an explicit boolean `imputed` column — this
     project never silently imputes without flagging it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    """Summary of what the validation/cleaning pass did to one series."""

    indicator: str
    n_input_rows: int
    n_duplicates_removed: int
    n_out_of_domain: int
    n_imputed: int
    was_monotonic_on_input: bool
    issues: List[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True only if nothing needed fixing at all."""
        return (
            self.n_duplicates_removed == 0
            and self.n_out_of_domain == 0
            and self.n_imputed == 0
            and self.was_monotonic_on_input
        )

    def summary(self) -> str:
        bits = [f"{self.indicator}: {self.n_input_rows} input rows"]
        if not self.was_monotonic_on_input:
            bits.append("index was not sorted (sorted)")
        if self.n_duplicates_removed:
            bits.append(f"{self.n_duplicates_removed} duplicate period(s) resolved")
        if self.n_out_of_domain:
            bits.append(f"{self.n_out_of_domain} out-of-domain value(s) dropped")
        if self.n_imputed:
            bits.append(f"{self.n_imputed} value(s) forward-filled (flagged)")
        if self.is_clean:
            bits.append("no issues found")
        return "; ".join(bits)


def validate_and_clean_series(
    series: pd.Series,
    indicator: str,
    value_bounds: Optional[Tuple[float, float]] = None,
) -> Tuple[pd.DataFrame, ValidationReport]:
    """Validate and clean one time-indexed series.

    Returns a `(frame, report)` tuple where `frame` has columns:
      - `value`: the cleaned value (after dropping out-of-domain points and
        forward-filling gaps on the series' own observed frequency).
      - `imputed`: `True` for any row whose value was forward-filled rather
        than observed.

    `value_bounds`, if given, is an inclusive `(lower, upper)` range; any
    observed value outside it is treated as an impossible/invalid reading
    for this indicator (e.g. a negative unemployment rate) and converted to
    NaN before the imputation step, so it gets forward-filled and flagged
    like any other gap rather than silently kept.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError(f"{indicator}: series must have a DatetimeIndex.")

    n_input = len(series)
    was_monotonic = bool(series.index.is_monotonic_increasing)
    issues: List[str] = []

    s = series.sort_index()

    # 1. De-duplicate periods: keep the last observation per date (treated
    # as a later revision superseding an earlier figure for that period).
    n_dupes = int(s.index.duplicated(keep="last").sum())
    if n_dupes:
        issues.append(f"{n_dupes} duplicate period(s) found; kept latest value per period.")
        s = s[~s.index.duplicated(keep="last")]

    # 2. Domain / impossible-value check.
    n_out_of_domain = 0
    if value_bounds is not None:
        lower, upper = value_bounds
        out_of_domain = (s < lower) | (s > upper)
        n_out_of_domain = int(out_of_domain.sum())
        if n_out_of_domain:
            issues.append(
                f"{n_out_of_domain} value(s) outside documented domain "
                f"[{lower}, {upper}]; treated as missing."
            )
            s = s.mask(out_of_domain)

    # 3. Missing-data handling: forward-fill, with an explicit flag.
    imputed_flag = s.isna()
    s_filled = s.ffill()
    # Any still-NaN at the start (nothing to forward-fill from) is left as
    # NaN — we never backfill, since that would use future information.
    still_missing = s_filled.isna()
    n_imputed = int((imputed_flag & ~still_missing).sum())
    if n_imputed:
        issues.append(f"{n_imputed} missing period(s) forward-filled from the prior observation.")
    if still_missing.any():
        issues.append(
            f"{int(still_missing.sum())} leading period(s) have no prior value to forward-fill from; left missing."
        )

    frame = pd.DataFrame({"value": s_filled, "imputed": imputed_flag & ~still_missing})

    report = ValidationReport(
        indicator=indicator,
        n_input_rows=n_input,
        n_duplicates_removed=n_dupes,
        n_out_of_domain=n_out_of_domain,
        n_imputed=n_imputed,
        was_monotonic_on_input=was_monotonic,
        issues=issues,
    )
    return frame, report


def check_no_duplicate_periods(index: pd.DatetimeIndex) -> bool:
    """Standalone check used directly by tests: True iff `index` has no
    duplicate timestamps."""
    return not bool(pd.Index(index).duplicated().any())


def check_monotonic_increasing(index: pd.DatetimeIndex) -> bool:
    """Standalone check used directly by tests."""
    return bool(pd.Index(index).is_monotonic_increasing)
