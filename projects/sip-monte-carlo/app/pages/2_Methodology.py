"""Methodology page: a readable summary; see docs/METHODOLOGY.md for the
full derivations."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Methodology", page_icon="📐", layout="wide")

st.title("Methodology")

st.markdown(
    """
This page summarizes how the simulator works. The full derivations,
assumptions and limitations live in `docs/METHODOLOGY.md` in the project
repository.

### 1. This is a distribution, not a forecast

Every chart and number in this app describes **what happens across many
randomly-drawn paths under the assumptions you chose** — not a prediction
of what will actually happen to any real investment. Change the sliders
and the distribution changes; that is the point of a Monte Carlo tool.

### 2. Compound interest with growing contributions (the deterministic core)

At zero volatility, the simulator reduces exactly to the closed-form future
value of a **growing annuity**: contributions made every month, stepped up
once a year, compounding at a constant monthly rate. This equivalence is
verified by the test suite (`tests/test_engine.py`), not just asserted.

### 3. Returns are modeled as lognormal

Monthly returns are drawn from a lognormal distribution whose **annual**
mean and volatility are set to match your sliders exactly (moment
matching), decomposed into 12 independent monthly draws so the simulation
is internally consistent with the annual assumptions you entered.

### 4. Fees are a continuous drag

The annual fee/expense-ratio assumption is subtracted from the growth rate
every month — a small, continuous drag that compounds against the investor
over time, the same way a real expense ratio does.

### 5. Volatility drag (the arithmetic–geometric mean gap)

Holding the *arithmetic mean* return fixed, raising volatility lowers the
**median** (typical-path) outcome, even though it does not lower — and can
even slightly raise — the *mean*. This is because compounding is
multiplicative: the geometric growth rate that governs a typical
compounding path is approximately `mean − variance / 2`, strictly below the
arithmetic mean whenever there is any volatility at all. The simulator
demonstrates this directly — see the Home page, and `tests/test_engine.py::
test_higher_volatility_does_not_increase_median_final_value`.

### 6. Sequence-of-returns risk

Holding the *set* of annual returns fixed, the **order** in which they
occur changes the final wealth when there are ongoing contributions — see
the dedicated Sequence of Returns Risk page.

### 7. Inflation adjustment

Inflation never touches the nominal simulation. It is applied once, at the
end, purely to re-express nominal results in constant (today's) purchasing
power: `real(t) = nominal(t) / (1 + inflation) ** (t / 12)`.

### 8. Reproducibility

The same `seed` with otherwise identical inputs reproduces byte-identical
output — the simulation uses NumPy's `default_rng(seed)` and draws nothing
else from any other source of randomness.
"""
)
