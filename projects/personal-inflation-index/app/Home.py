"""Personal Inflation Index -- Streamlit app entry point.

Run with:
    streamlit run app/Home.py
"""

import _pathfix  # noqa: F401  (adds ../src to sys.path)
import streamlit as st

st.set_page_config(
    page_title="Personal Inflation Index",
    page_icon="chart",
    layout="wide",
)

PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
SURFACE = "#fcfcfb"
SERIES_BLUE = "#2a78d6"
SERIES_ORANGE = "#eb6834"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {SURFACE}; }}
    h1, h2, h3 {{ color: {PRIMARY_INK}; font-weight: 650; }}
    p, li {{ color: {SECONDARY_INK}; }}
    .caption-muted {{ color: {MUTED_INK}; font-size: 0.85rem; }}
    .banner {{
        background: #fff6e8;
        border: 1px solid #eda100;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: #6b4a00;
        font-size: 0.92rem;
        margin-bottom: 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Personal Inflation Index")
st.markdown(
    "A Laspeyres-style calculator that lets you build **your own** household "
    "spending basket and see how your personal inflation rate can diverge "
    "from a national-average CPI figure."
)

st.markdown(
    """
    <div class="banner">
    ⚠️ <b>Every weight and price series in this app is either something you
    entered yourself, or a clearly labeled illustrative / synthetic example.</b>
    Nothing here is official MoSPI CPI data. See the Data page notes and
    <code>docs/DATA_SOURCES.md</code> for exactly where to get the real,
    official series.
    </div>
    """,
    unsafe_allow_html=True,
)

st.header("Research question")
st.markdown(
    "**Why can the inflation experienced by an individual household differ "
    "from official CPI inflation?** Official CPI numbers are a weighted "
    "average built from one national basket. No single household is "
    "average -- its own budget shares and the prices it actually faces can "
    "differ sharply from the national aggregate. This tool makes that gap "
    "concrete and explorable."
)

st.header("What's in this app")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Basket Builder")
    st.markdown(
        "Use the sliders in the **Basket Builder** page (left sidebar) to "
        "set your own category expenditure weights -- they visibly "
        "renormalize to 100% as you move them -- then either type in "
        "price changes per category or upload a CSV of category prices "
        "over multiple periods. The app computes your personal Laspeyres "
        "index and plots it next to an illustrative comparison index."
    )
with col2:
    st.subheader("Under the hood")
    st.markdown(
        "The math is the textbook fixed-basket **Laspeyres index**: "
        r"$I_t = 100 \times \sum_i w_i \cdot (P_{i,t} / P_{i,0})$. "
        "See `docs/METHODOLOGY.md` for the full derivation, its "
        "substitution-bias assumption, and the economic reasoning behind "
        "why personal and official inflation can diverge."
    )

st.divider()
st.markdown(
    '<p class="caption-muted">Source code, tests, and documentation: '
    "see this project's README.md and docs/ folder.</p>",
    unsafe_allow_html=True,
)
