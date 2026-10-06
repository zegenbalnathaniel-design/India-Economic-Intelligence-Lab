"""India Economic Policy Simulator — Streamlit entry point."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

st.set_page_config(page_title="India Economic Policy Simulator", page_icon="🏛️", layout="wide")

st.title("🏛️ India Economic Policy Simulator")
st.markdown(
    """
A small, open-source computational model for exploring **Indian fiscal and
monetary policy trade-offs** — built to make textbook transmission
mechanisms explorable, not to forecast the Indian economy.

**Use the sidebar pages:**

1. **Scenario Builder** — set fiscal/monetary/external inputs, compare a
   baseline path against a shock, and see the transmission mechanism play
   out across GDP, inflation, unemployment, the fiscal deficit, public debt
   and the exchange rate.
2. **Monetary Transmission (Empirical)** — the iBFPI: an *empirical*
   bank-performance index compared against the actual RBI repo-rate path,
   kept deliberately separate from the theoretical simulator above.
3. **Methodology & Limitations** — every equation, every assumption, and
   what this model cannot tell you.

> ⚠️ **This is a teaching model.** Its parameters are illustrative
> calibrations loosely consistent with publicly reported aggregate ratios —
> not an econometric estimate, and not a forecast of the Indian economy.
"""
)

st.info(
    "Part of a nine-project open-source portfolio exploring economics, "
    "finance and Indian economic data. See the root README for the full set."
)
