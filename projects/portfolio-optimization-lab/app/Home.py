"""Open Portfolio Optimization Laboratory — Streamlit entry point."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Open Portfolio Optimization Laboratory", page_icon="📈", layout="wide")

st.title("📈 Open Portfolio Optimization Laboratory")
st.markdown(
    """
An educational, from-scratch implementation of **Modern Portfolio Theory**:
expected return, covariance, the Sharpe ratio, the minimum-variance and
maximum-Sharpe portfolios (both derived via **Lagrange multipliers** — see
the Methodology page for the full algebra), and the efficient frontier —
over a configurable universe spanning **six exchange groups**: the US
(NYSE & Nasdaq), India (NSE & BSE), the London Stock Exchange, the Japan
Exchange Group, the Shanghai Stock Exchange and Hong Kong Exchanges.

**Use the sidebar pages:**

1. **Portfolio Builder** — pick your stocks, your initial investment, and
   your constraints (long-only, max weight per asset); see the resulting
   minimum-variance and maximum-Sharpe allocations.
2. **Efficient Frontier (3D)** — the frontier in return/volatility/Sharpe
   space, against a cloud of random portfolios.
3. **Correlation Network (3D)** — an interactive, physically-meaningful 3D
   layout (classical multidimensional scaling) of how your chosen assets
   move together.
4. **Methodology** — every formula, every derivation, every assumption.

> ⚠️ **Educational tool — not investment advice.** Live price data is
> fetched via `yfinance` when the network allows it; wherever a ticker
> can't be fetched live (including every ticker in this exact hosted demo
> environment, whose network policy blocks the request), a clearly-labelled
> **synthetic** price series is substituted instead and flagged in the app.
> See the Data Status panel on the Portfolio Builder page before reading
> any number as real.
"""
)

st.info(
    "Part of a nine-project open-source portfolio exploring economics, "
    "finance and Indian economic data. See the root README for the full set."
)
