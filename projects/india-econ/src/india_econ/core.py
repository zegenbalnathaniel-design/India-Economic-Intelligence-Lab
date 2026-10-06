"""Core orchestration: live-fetch-then-synthetic-fallback, and the result wrapper."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import pandas as pd

from ._registry import DEFAULT_SYNTHETIC_END, DEFAULT_SYNTHETIC_START, IndicatorSpec, get_spec
from ._synthetic import synthetic_series
from ._worldbank import fetch_indicator_series
from .exceptions import DataFetchError, InvalidDateRangeError

LIVE_STATUS = "live"
SYNTHETIC_STATUS = "synthetic"


class IndicatorResult:
    """Wraps a fetched indicator's data together with its metadata.

    Attributes
    ----------
    data:
        A :class:`pandas.Series` (single-column indicators) or
        :class:`pandas.DataFrame` (multi-column indicators, e.g. exports
        and imports together), indexed by year (``int``).
    metadata:
        A plain dict describing the data: ``source`` ("live" or
        "synthetic"), ``provider``, ``url``, ``definition``, ``unit``,
        ``frequency``, and ``status`` (alias of ``source``, kept for
        readers who look for either name).

    The same metadata dict is also attached to ``data.attrs``, so code
    that unwraps ``.data`` right away (e.g. for plotting) doesn't lose the
    live/synthetic status -- ``result.data.attrs["status"]`` works too.
    """

    __slots__ = ("data", "metadata")

    def __init__(self, data: Union[pd.Series, pd.DataFrame], metadata: Dict[str, Any]) -> None:
        self.data = data
        self.metadata = metadata
        try:
            data.attrs.update(metadata)
        except Exception:
            # pandas .attrs has existed since 1.0; this guard just makes
            # sure a future pandas quirk can never break data access.
            pass

    @property
    def source(self) -> str:
        """Shortcut for ``metadata["status"]``: ``"live"`` or ``"synthetic"``."""
        return self.metadata["status"]

    def is_live(self) -> bool:
        return self.source == LIVE_STATUS

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"IndicatorResult(status={self.metadata['status']!r}, "
            f"provider={self.metadata['provider']!r}, shape={getattr(self.data, 'shape', None)})"
        )


def _validate_range(start: Optional[int], end: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    def _coerce(value: Optional[int], label: str) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidDateRangeError(f"{label}={value!r} is not a valid year.") from exc

    start_year = _coerce(start, "start")
    end_year = _coerce(end, "end")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise InvalidDateRangeError(
            f"start ({start_year}) must be <= end ({end_year})."
        )
    return start_year, end_year


def _build_live_frame(spec: IndicatorSpec) -> pd.DataFrame:
    columns: Dict[str, pd.Series] = {}
    for wb_col in spec.columns:
        points = fetch_indicator_series(wb_col.code)  # may raise DataFetchError
        years, values = zip(*points)
        columns[wb_col.column] = pd.Series(values, index=pd.Index(years, name="year"))
    frame = pd.DataFrame(columns).sort_index()

    if spec.name == "gdp" and "gdp_current_usd" in frame:
        frame["gdp_growth_pct"] = (frame["gdp_current_usd"].pct_change() * 100).round(2)

    return frame


def _build_synthetic_frame(spec: IndicatorSpec, start_year: int, end_year: int) -> pd.DataFrame:
    columns: Dict[str, pd.Series] = {}
    for wb_col in spec.columns:
        series_map = synthetic_series(spec.name, wb_col.column, wb_col.synthetic, start_year, end_year)
        columns[wb_col.column] = pd.Series(series_map)
    frame = pd.DataFrame(columns).sort_index()
    frame.index.name = "year"

    if spec.name == "gdp" and "gdp_current_usd" in frame:
        frame["gdp_growth_pct"] = (frame["gdp_current_usd"].pct_change() * 100).round(2)

    return frame


def get_indicator(
    indicator_name: str,
    start: Optional[int] = None,
    end: Optional[int] = None,
    allow_live: bool = True,
) -> IndicatorResult:
    """Fetch (or synthesize) one registered indicator and wrap it.

    Parameters
    ----------
    indicator_name:
        One of the keys in ``india_econ._registry.REGISTRY``
        (e.g. ``"gdp"``, ``"inflation"``). Unknown names raise
        :class:`~india_econ.exceptions.UnknownIndicatorError`.
    start, end:
        Optional inclusive year bounds. ``None`` means "don't bound that
        side". Passing ``start > end`` raises
        :class:`~india_econ.exceptions.InvalidDateRangeError`.
    allow_live:
        If ``False``, skip the live World Bank fetch entirely and go
        straight to the synthetic fallback. Useful for tests, offline
        use, or reproducible demos.
    """
    spec = get_spec(indicator_name)  # raises UnknownIndicatorError
    start_year, end_year = _validate_range(start, end)

    status = LIVE_STATUS
    fetch_note = "Fetched live from the World Bank Open Data API."
    frame: pd.DataFrame

    if allow_live:
        try:
            frame = _build_live_frame(spec)
        except DataFetchError as exc:
            status = SYNTHETIC_STATUS
            fetch_note = f"Live fetch failed ({exc}); using synthetic fallback."
    else:
        status = SYNTHETIC_STATUS
        fetch_note = "Live fetch disabled (allow_live=False); using synthetic fallback."

    if status == SYNTHETIC_STATUS:
        synth_start = start_year if start_year is not None else DEFAULT_SYNTHETIC_START
        synth_end = end_year if end_year is not None else DEFAULT_SYNTHETIC_END
        if synth_end < synth_start:
            synth_start, synth_end = DEFAULT_SYNTHETIC_START, DEFAULT_SYNTHETIC_END
        frame = _build_synthetic_frame(spec, synth_start, synth_end)

    if start_year is not None:
        frame = frame[frame.index >= start_year]
    if end_year is not None:
        frame = frame[frame.index <= end_year]

    metadata = {
        "indicator": spec.name,
        "provider": spec.provider,
        "url": spec.url,
        "definition": spec.definition,
        "unit": spec.unit,
        "frequency": spec.frequency,
        "status": status,
        "source": status,
        "note": fetch_note,
    }

    data: Union[pd.Series, pd.DataFrame]
    if frame.shape[1] == 1:
        data = frame.iloc[:, 0].copy()
        data.name = frame.columns[0]
    else:
        data = frame.copy()

    return IndicatorResult(data, metadata)
