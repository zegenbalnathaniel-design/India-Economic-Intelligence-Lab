#!/usr/bin/env python3
"""Standalone demo of every public india_econ function.

Run with:

    python examples/demo.py

Each call tries a live World Bank fetch first and falls back to a
labelled synthetic series if that fails -- the printed ``status`` line
tells you, honestly, which one you got.
"""

from __future__ import annotations

import india_econ as ie


def show(label: str, result: ie.IndicatorResult) -> None:
    print(f"\n=== {label} ===")
    print(f"status:     {result.source}")
    print(f"provider:   {result.metadata['provider']}")
    print(f"definition: {result.metadata['definition']}")
    print(result.data.tail(5))


def main() -> None:
    show("GDP (level + growth)", ie.gdp(start=2010, end=2023))
    show("Inflation (CPI, % per year)", ie.inflation(start=2010, end=2023))
    show("Unemployment rate (%)", ie.unemployment(start=2010, end=2023))
    show("Trade (exports/imports, US$)", ie.trade(start=2010, end=2023))
    show("Exchange rate (INR per USD)", ie.exchange_rate(start=2010, end=2023))
    show("Interest rates (lending rate proxy, %)", ie.interest_rates(start=2010, end=2023))
    show("Government finance (% of GDP)", ie.government_finance(start=2010, end=2023))
    show("Household finance proxies (% of GDP)", ie.household_finance(start=2010, end=2023))

    print("\n=== get_metadata() without fetching anything ===")
    print(ie.get_metadata("gdp"))

    print("\n=== Error handling ===")
    try:
        ie.get_metadata("not_a_real_indicator")
    except ie.UnknownIndicatorError as exc:
        print(f"UnknownIndicatorError (as expected): {exc}")

    try:
        ie.gdp(start=2020, end=2010)
    except ie.InvalidDateRangeError as exc:
        print(f"InvalidDateRangeError (as expected): {exc}")

    print("\n=== Forcing the synthetic path on purpose ===")
    forced = ie.inflation(allow_live=False)
    print(f"status: {forced.source} (allow_live=False forces this)")


if __name__ == "__main__":
    main()
