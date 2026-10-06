"""Standardized metadata schema that travels with every indicator series.

The central research-integrity rule of this project is simple to state and
easy to violate by accident: a chart, a table, or a dataframe must never let
a synthetic fallback series be mistaken for a real, officially-sourced one.
The mechanism this module provides is a small, immutable `Metadata` record
that every loader in `loaders.py` is required to return alongside its data,
and that `viz.py` is required to render next to every chart. Nothing else in
this codebase is allowed to show a series without it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class DataStatus(str, Enum):
    """Whether a series came from a real, live, cited source or is a
    deterministic stand-in generated because the live fetch failed (or
    `allow_live=False` was passed)."""

    OFFICIAL = "official"
    SYNTHETIC = "illustrative_synthetic"

    @property
    def is_official(self) -> bool:
        return self is DataStatus.OFFICIAL

    @property
    def badge_label(self) -> str:
        return "LIVE / OFFICIAL" if self.is_official else "SYNTHETIC / ILLUSTRATIVE"


@dataclass(frozen=True)
class Metadata:
    """Provenance and definitional record for one indicator series.

    Every field is required and deliberately verbose: the point of this
    object is that a consumer (a chart, a table, a notebook cell) never has
    to go hunting for what a number means or where it came from.
    """

    indicator: str                 # human-readable indicator name, e.g. "GDP (current US$)"
    source: str                    # specific dataset/series name at the provider
    provider: str                  # organization, e.g. "World Bank", "RBI DBIE", "MoSPI"
    url: str                       # canonical URL for the dataset or API endpoint
    definition: str                # what the number actually measures
    unit: str                      # e.g. "current US$", "%", "index (2010=100)"
    frequency: str                 # "annual", "monthly", "quarterly"
    date_coverage: str             # requested/returned date range, e.g. "2000-01-01 to 2023-12-31"
    transformations: Tuple[str, ...]  # pipeline steps applied after the raw fetch
    limitations: str               # known caveats a reader should keep in mind
    status: DataStatus             # OFFICIAL or SYNTHETIC — never implied, always explicit

    def __post_init__(self) -> None:
        if not isinstance(self.transformations, tuple):
            object.__setattr__(self, "transformations", tuple(self.transformations))

    def caption(self) -> str:
        """One-line, human-readable string meant to sit directly under a
        chart or table: "metadata travels with the chart"."""
        tag = self.status.badge_label
        return (
            f"[{tag}] {self.indicator} — {self.provider} ({self.source}) · "
            f"{self.unit} · {self.frequency} · {self.date_coverage}"
        )

    def long_description(self) -> str:
        lines = [
            f"Indicator: {self.indicator}",
            f"Status: {self.status.badge_label}",
            f"Provider / source: {self.provider} — {self.source}",
            f"URL: {self.url}",
            f"Definition: {self.definition}",
            f"Unit: {self.unit}",
            f"Frequency: {self.frequency}",
            f"Date coverage: {self.date_coverage}",
            f"Transformations applied: {', '.join(self.transformations) if self.transformations else 'none'}",
            f"Limitations: {self.limitations}",
        ]
        return "\n".join(lines)

    def as_dict(self) -> dict:
        d = {
            "indicator": self.indicator,
            "source": self.source,
            "provider": self.provider,
            "url": self.url,
            "definition": self.definition,
            "unit": self.unit,
            "frequency": self.frequency,
            "date_coverage": self.date_coverage,
            "transformations": list(self.transformations),
            "limitations": self.limitations,
            "status": self.status.value,
        }
        return d


def with_date_coverage(meta: Metadata, start: str, end: str) -> Metadata:
    """Return a copy of `meta` with `date_coverage` filled in. Loaders build
    a template Metadata before they know the actual requested range, then
    call this once the range is known."""
    from dataclasses import replace

    return replace(meta, date_coverage=f"{start} to {end}")


def with_status(meta: Metadata, status: DataStatus, extra_limitation: str = "") -> Metadata:
    """Return a copy of `meta` with `status` set, optionally appending a
    note (e.g. explaining *why* the live fetch failed) to `limitations`."""
    from dataclasses import replace

    limitations = meta.limitations
    if extra_limitation:
        limitations = f"{limitations} {extra_limitation}".strip()
    return replace(meta, status=status, limitations=limitations)
