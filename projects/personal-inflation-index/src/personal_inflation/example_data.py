"""Clearly-labeled ILLUSTRATIVE example data.

Nothing in this file is an official MoSPI CPI number. The weights below
are a plausible, round-number illustration of how expenditure shares
*might* be split across broad categories, used only so that this
project's demo, tests, and Streamlit app have something sensible to show
before a user enters their own numbers. Treat every value here as a
placeholder.

For where to find the real, official CPI combined weights and sub-group
weights, see ``docs/DATA_SOURCES.md`` -- they must be obtained from
MoSPI's published CPI documentation (mospi.gov.in) and should be
independently verified against the current base-year publication before
being used for anything beyond demonstration.
"""

from __future__ import annotations

# Example weights, NOT official MoSPI figures. Rounded for illustration
# only; sums to 1.0. A user of the basket builder is expected to override
# every single one of these with their own actual expenditure shares.
EXAMPLE_ILLUSTRATIVE_WEIGHTS: dict[str, float] = {
    "food": 0.35,
    "housing": 0.20,
    "transport": 0.10,
    "education": 0.08,
    "healthcare": 0.07,
    "communication": 0.04,
    "recreation": 0.05,
    "clothing": 0.05,
    "other": 0.06,
}

assert abs(sum(EXAMPLE_ILLUSTRATIVE_WEIGHTS.values()) - 1.0) < 1e-9
