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

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import streamlit as st

from analysis import regional
from app.components.theme import setup, kicker, callout, footnote
from app.components import terrain_hero
from app.components import turntable_home
from app.components import home_theme
from data_sources import loaders


setup("Home")
home_theme.inject_home_css()

with st.sidebar:
    st.markdown("## India Economic Intelligence Lab")
    st.caption("Computational economics research portfolio")
    st.markdown("---")
    st.caption("Author: Nathaniel Zegenbal")
    st.caption("Version: 0.1 (MVP)")

# ---------- Hero ------------------------------------------------------------
home_theme.hero_micro(["IEIL / 2026", "COMPUTATIONAL ECONOMICS", "DATA · MODELS · SIMULATIONS"])
home_theme.hero_title([("INDIA,", False), ("MEASURED.", True)])
st.markdown(
    '<div class="ieil-hero-sub">An experimental laboratory for understanding '
    "India's economy through data, models and interactive simulations.</div>",
    unsafe_allow_html=True,
)

terrain_hero.render()
st.caption(
    "Hover or tab through the terrain — each rise is a Lab, not a data point. "
    "On a touch device, tap a rise."
)

# ---------- Numbers ----------------------------------------------------------
with st.container(key="reveal_numbers"):
    st.markdown('<div class="ieil-numbers">', unsafe_allow_html=True)
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        home_theme.number_stat("04", "Research Labs", home_theme.VERMILLION)
    with n2:
        home_theme.number_stat("06", "Data Series", home_theme.COBALT)
    with n3:
        home_theme.number_stat("07", "Models", home_theme.LEAF)
    with n4:
        home_theme.number_stat("∞", "Questions", home_theme.TURQUOISE)
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption(
        "Counts reflect what's actually wired up: 6 real data series loaded from "
        "RBI/PLFS/NHB sources, 7 named models (iBFPI, sigma & beta convergence, "
        "composition-effect, SIP Monte Carlo, r−g, EMI/affordability) — see the Data page."
    )

st.markdown("<br>", unsafe_allow_html=True)

# ---------- Research index ----------------------------------------------------
with st.container(key="reveal_index"):
    st.subheader("Research Index")
    st.caption("Drag, scroll or swipe — the cards aren't stacked, they're a carousel.")

    RESEARCH_CARDS = [
        ("01", "WHO OWNS INDIA?", "Wealth Inequality Lab · 2026",
         "How income, ownership, asset composition and returns on capital shape wealth accumulation.",
         home_theme.VERMILLION, "pages/1_Wealth_Inequality_Lab.py", "Open the Wealth Lab →"),
        ("02", "HOW DOES MONEY MOVE?", "Banking & Monetary Policy Lab · 2026",
         "The iBFPI robust z-score methodology, adapted from my JP Morgan research, applied "
         "to a five-bank Indian panel against the RBI repo rate.",
         home_theme.COBALT, "pages/2_Banking_Monetary_Policy_Lab.py", "Open the Banking Lab →"),
        ("03", "ONE COUNTRY. UNEQUAL TRAJECTORIES.", "State Economic Divergence Lab · 2026",
         "Sigma and beta convergence on real per-capita income by state, 2004-05 to 2022-23, "
         "from the RBI Handbook of Statistics on Indian States.",
         home_theme.LEAF, "pages/3_State_Economic_Divergence_Lab.py", "Open the State Divergence Lab →"),
        ("04", "WHERE DOES INDIA'S WEALTH LIVE?", "Housing Intelligence Lab · 2026",
         "Real NHB RESIDEX price data for 50 cities against a documented state-income proxy "
         "— price-to-income, EMI, and an honest caveat about what the proxy distorts.",
         home_theme.GOLD, "pages/4_Housing_Intelligence_Lab.py", "Open the Housing Lab →"),
    ]

    with st.container(key="research_carousel", horizontal=True, gap="medium"):
        for num, headline, meta, desc, color, page, link_label in RESEARCH_CARDS:
            with st.container(border=True):
                home_theme.index_card(num, headline, meta, desc, color)
                st.page_link(page, label=link_label)

    home_theme.carousel_drag_script("research_carousel")

st.markdown("<br>", unsafe_allow_html=True)

# ---------- A second way in: Turntable ---------------------------------------
with st.container(key="reveal_turntable"):
    st.subheader("Four Ways of Looking at This Site")
    tcol1, tcol2 = st.columns([1, 2])
    with tcol1:
        turntable_home.render()
    with tcol2:
        st.markdown(
            "Markets. People. Institutions. Data. Drag the turntable to a "
            "face, then open it — a second, more deliberate way into the "
            "same four real sections as the terrain above and the index "
            "below, for anyone who'd rather turn than hover."
        )

st.markdown("<br>", unsafe_allow_html=True)

# ---------- A real series, drawn on scroll -----------------------------------
with st.container(key="reveal_graph"):
    st.subheader("States Converging — Drawn, Not Just Charted")
    sigma = regional.sigma_convergence(loaders.load_nsdp_spliced())
    gcol1, gcol2 = st.columns([3, 2])
    with gcol1:
        st.markdown(
            home_theme.sigma_convergence_svg(sigma.by_year, home_theme.LEAF),
            unsafe_allow_html=True,
        )
    with gcol2:
        st.markdown(
            f"**{sigma.direction.upper()}** · {sigma.trend_slope_pct_per_year:+.3f} pp CV/year  \n"
            "Cross-state coefficient of variation of real per-capita NSDP, "
            f"{sigma.by_year['financial_year'].iloc[0]} to {sigma.by_year['financial_year'].iloc[-1]} "
            "— the same real RBI Handbook series behind the State Divergence Lab, here as a line "
            "that draws itself in as you scroll to it, not a static picture."
        )
        st.page_link(
            "pages/3_State_Economic_Divergence_Lab.py",
            label="See the full convergence analysis →",
        )

st.markdown("<br>", unsafe_allow_html=True)

# ---------- Process -----------------------------------------------------------
with st.container(key="reveal_process"):
    st.subheader("From Question to Model")
    home_theme.flow(["Question", "Data", "Model", "Simulation", "Interpretation"])
    st.caption(
        "This site doesn't just show visualisations — it shows how an economic "
        "question becomes a computational one, at each step, with the data and "
        "assumptions left visible rather than hidden behind the chart."
    )

home_theme.scroll_reveal_script()

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="ieil-secondary-links">', unsafe_allow_html=True)
sl1, sl2, sl3, sl4, sl5 = st.columns(5)
with sl1:
    st.page_link("pages/5_Research.py", label="05 Research")
with sl2:
    st.page_link("pages/6_Methodology.py", label="06 Methodology")
with sl3:
    st.page_link("pages/7_Data.py", label="07 Data")
with sl4:
    st.page_link("pages/8_About.py", label="08 About")
with sl5:
    st.page_link("pages/9_Limitations.py", label="09 Limitations")
tl1, tl2, tl3 = st.columns(3)
with tl1:
    st.page_link("pages/10_Economic_Relationships_Lab.py", label="10 Economic Relationships")
with tl2:
    st.page_link("pages/11_State_Economy_Explorer.py", label="11 State Economy Explorer")
with tl3:
    st.page_link("pages/12_Macro_and_World.py", label="12 India Macro & World")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

st.header("Why I built this")
st.markdown(
    "This site is a **computational extension of my research papers**, not a "
    "dashboard. It exists so that readers can interact with the models and "
    "the evidence — modify assumptions, re-run the composition-effect "
    "simulation, swap allocations, split the sample by rate regime — instead "
    "of reading a static figure and moving on.\n\n"
    "Four research questions drive the interactive components:"
)

st.markdown(
    "1. **How do income, ownership, asset composition and returns on capital "
    "influence wealth accumulation and economic mobility in India?**\n"
    "2. **To what extent did changes in policy interest rates influence bank "
    "financial performance during 2018-2024?** — adapted from my JP Morgan / "
    "Federal Reserve study to Indian scheduled commercial banks (the iBFPI).\n"
    "3. **Are Indian states converging economically, or becoming more "
    "divergent?** — sigma and beta convergence on real RBI state-income data.\n"
    "4. **Is Indian housing becoming less affordable relative to income?** — "
    "real NHB RESIDEX price data for 50 cities, against a documented income proxy."
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
        "- Sigma/beta convergence on real state per-capita income\n"
        "- City-level housing affordability on real NHB RESIDEX prices\n"
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
