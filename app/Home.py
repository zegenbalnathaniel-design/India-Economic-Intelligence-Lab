"""India Economic Intelligence Lab — Home.

Streamlit entry point. Launch with `streamlit run app/Home.py` from the
repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `analysis.*` and `data_sources.*` imports when running `streamlit run app/Home.py`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.theme import setup, kicker, callout, footnote


setup("Home")

with st.sidebar:
    st.markdown("## India Economic Intelligence Lab")
    st.caption("Computational economics research portfolio")
    st.markdown(
        "- **Home**\n"
        "- Wealth & Inequality Lab\n"
        "- Banking & Monetary Policy Lab\n"
        "- Research\n"
        "- Methodology\n"
        "- Data\n"
        "- About\n"
        "- Limitations"
    )
    st.markdown("---")
    st.caption("Author: Nathaniel Zegenbal")
    st.caption("Version: 0.1 (MVP)")

kicker("Computational Economics Research")
st.title("India Economic Intelligence Lab")
st.markdown(
    "**An interactive computational economics research portfolio.**  \n"
    "An exploration of how economic theory can be translated into quantitative "
    "models, simulations and empirical analysis using Indian economic and "
    "financial data."
)

st.markdown("---")

col1, col2, col3 = st.columns(3, gap="large")
with col1:
    kicker("Theme 01 · Wealth")
    st.markdown("### Income → Saving → Ownership → Asset Accumulation")
    st.markdown(
        "How income, ownership, asset composition and returns on capital "
        "shape wealth accumulation and economic mobility in India."
    )
    st.page_link("pages/1_Wealth_Inequality_Lab.py", label="Open the Wealth Lab →")

with col2:
    kicker("Theme 02 · Banking")
    st.markdown("### Interest Rates → Financial Conditions → Bank Performance")
    st.markdown(
        "Adapting the BFPI robust z-score methodology from my JP Morgan "
        "research to a five-bank Indian panel — the iBFPI."
    )
    st.page_link("pages/2_Banking_Monetary_Policy_Lab.py", label="Open the Banking Lab →")

with col3:
    kicker("Theme 03 · Method")
    st.markdown("### Economics + Mathematics + Statistics + Python")
    st.markdown(
        "Every figure is generated from code with the underlying data, "
        "assumptions and formulae documented in-line."
    )
    st.page_link("pages/4_Methodology.py", label="Read the Methodology →")

st.markdown("---")

st.header("Why I built this")
st.markdown(
    "This site is a **computational extension of my research papers**, not a "
    "dashboard. It exists so that readers can interact with the models and "
    "the evidence — modify assumptions, re-run the composition-effect "
    "simulation, swap allocations, split the sample by rate regime — instead "
    "of reading a static figure and moving on.\n\n"
    "Two research questions drive the interactive components:"
)

st.markdown(
    "1. **How do income, ownership, asset composition and returns on capital "
    "influence wealth accumulation and economic mobility in India?**\n"
    "2. **To what extent did changes in policy interest rates influence bank "
    "financial performance during 2018-2024?** — adapted from my JP Morgan / "
    "Federal Reserve study to Indian scheduled commercial banks (the iBFPI)."
)

callout(
    "This is a research portfolio, not financial advice. Every quantitative "
    "output on this site is a simulation under user-editable assumptions. "
    "Historical returns are not forecasts.",
    kind="warn",
)

st.header("What is (and isn't) inside")
c1, c2 = st.columns(2)
with c1:
    st.markdown(
        "**Inside the MVP**\n"
        "- Composition-effect simulator (30-year default)\n"
        "- Asset-allocation comparison\n"
        "- r − g explorer\n"
        "- iBFPI construction from a 5-bank panel\n"
        "- RBI repo rate × iBFPI comparison, with regime split\n"
        "- Research paper page, methodology, data provenance"
    )
with c2:
    st.markdown(
        "**Not inside the MVP (by design)**\n"
        "- Personalised financial advice\n"
        "- A commercial data terminal\n"
        "- A prediction engine\n"
        "- Any claim of causal identification without stated design\n"
        "- Real-time market data feeds"
    )

footnote(
    "The iBFPI is my adaptation of the BFPI methodology developed in my "
    "JP Morgan / Fed-rate research paper. It is not a published or "
    "industry-standard index."
)
