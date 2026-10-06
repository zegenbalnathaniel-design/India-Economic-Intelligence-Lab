#!/usr/bin/env python3
"""Quickstart example: load three indicators across categories, print their
metadata, and report the live/synthetic split — exactly what a new user
should run first.

Run from the project root:
    python3 examples/quickstart.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_observatory import loaders
from data_observatory.metadata import DataStatus


def main() -> None:
    start, end = "2000-01-01", "2023-01-01"
    keys = ["gdp", "unemployment_rate", "exchange_rate"]

    print(f"Loading {len(keys)} indicators for India, {start} to {end}...\n")

    live, synthetic = [], []
    for key in keys:
        frame, meta = loaders.load(key, start, end, allow_live=True)
        print(meta.caption())
        print(f"  rows: {len(frame)}  |  last value: {frame['value'].iloc[-1]:,.4f}")
        print(f"  imputed points: {int(frame['imputed'].sum())}")
        print()
        (live if meta.status is DataStatus.OFFICIAL else synthetic).append(meta.indicator)

    print("--- Live/synthetic split for this run ---")
    print(f"Live/official: {live or 'none'}")
    print(f"Synthetic/illustrative: {synthetic or 'none'}")
    print(
        "\nIf every series above is synthetic, your network either blocked the "
        "World Bank API call or allow_live was False — this is expected behavior "
        "in a restricted sandbox, not a bug. See docs/DATA_SOURCES.md."
    )


if __name__ == "__main__":
    main()
