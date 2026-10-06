"""Basket Builder page: set weights, supply prices, see your personal index."""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from personal_inflation.example_data import EXAMPLE_ILLUSTRATIVE_WEIGHTS
from personal_inflation.index import (
    DEFAULT_CATEGORIES,
    compare_to_reference,
    laspeyres_index,
    normalize_weights,
    personal_index_time_series,
)

st.set_page_config(page_title="Basket Builder | Personal Inflation Index", page_icon="chart", layout="wide")

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
SERIES_BLUE = "#2a78d6"   # personal index
SERIES_ORANGE = "#eb6834"  # reference / illustrative comparison index

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {SURFACE}; }}
    h1, h2, h3 {{ color: {PRIMARY_INK}; font-weight: 650; }}
    .banner {{
        background: #fff6e8; border: 1px solid #eda100; border-radius: 8px;
        padding: 0.75rem 1rem; color: #6b4a00; font-size: 0.92rem; margin-bottom: 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Basket Builder")
st.markdown(
    """
    <div class="banner">
    ⚠️ <b>Example weights / synthetic data.</b> The sliders below default to
    illustrative example weights (not official MoSPI figures), and the
    bundled comparison series is a deterministic synthetic demo, not real
    CPI data. Replace the weights and prices with your own for a
    meaningful personal estimate. See <code>docs/DATA_SOURCES.md</code>.
    </div>
    """,
    unsafe_allow_html=True,
)

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic_category_price_index.csv"

# ---------------------------------------------------------------------------
# Step 1: weights
# ---------------------------------------------------------------------------
st.header("1. Set your category weights")
st.caption(
    "Move the sliders to match your own household's spending shares. "
    "They do not need to add to 100 -- the app renormalizes automatically "
    "(see the live total below) and shows you the normalized shares it "
    "actually uses."
)

if "raw_weights" not in st.session_state:
    # seed sliders from the illustrative example -- clearly labeled, user overrides freely
    st.session_state.raw_weights = {
        cat: round(EXAMPLE_ILLUSTRATIVE_WEIGHTS.get(cat, 0.0) * 100, 1)
        for cat in DEFAULT_CATEGORIES
    }

cols = st.columns(3)
raw_weights: dict[str, float] = {}
for i, cat in enumerate(DEFAULT_CATEGORIES):
    with cols[i % 3]:
        raw_weights[cat] = st.slider(
            cat.capitalize(),
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.raw_weights.get(cat, 0.0)),
            step=0.5,
            key=f"weight_{cat}",
        )
st.session_state.raw_weights = raw_weights

raw_total = sum(raw_weights.values())
try:
    normalized_weights = normalize_weights(raw_weights)
except ValueError as e:
    st.error(f"Cannot normalize weights: {e}")
    st.stop()

weight_table = pd.DataFrame(
    {
        "category": list(normalized_weights.keys()),
        "raw input": [raw_weights[c] for c in normalized_weights],
        "normalized share": [f"{100 * normalized_weights[c]:.1f}%" for c in normalized_weights],
    }
)
st.caption(f"Raw slider total: {raw_total:.1f} -- normalized to 100% below.")
st.dataframe(weight_table, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Step 2: prices
# ---------------------------------------------------------------------------
st.header("2. Supply category prices")
mode = st.radio(
    "Choose how to supply prices",
    ["Use the bundled synthetic example series", "Upload my own CSV of category prices over time"],
    horizontal=False,
)

if mode == "Upload my own CSV of category prices over time":
    st.caption(
        "CSV format: one column named like a period (or just a row index), "
        "one column per category (matching the names above), values = prices "
        "in that category for that period. First row is treated as the base period."
    )
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded is None:
        st.info("Upload a CSV to continue, or switch to the bundled synthetic example above.")
        st.stop()
    price_df = pd.read_csv(uploaded, index_col=0)
    reference_series = None
else:
    if not DATA_PATH.exists():
        st.error(
            f"Synthetic example data not found at {DATA_PATH}. Run "
            "`python examples/generate_synthetic_data.py` first."
        )
        st.stop()
    full_df = pd.read_csv(DATA_PATH, index_col="period")
    reference_series = full_df["official_cpi_reference"]
    price_df = full_df.drop(columns=["official_cpi_reference"])

missing_cols = [c for c in normalized_weights if c not in price_df.columns]
if missing_cols:
    st.error(
        f"Your price data is missing columns for weighted categories: {missing_cols}. "
        "Either supply a price column for every category you weighted, or zero out "
        "that category's slider above."
    )
    st.stop()

active_weights = {c: w for c, w in normalized_weights.items() if w > 0}
if not active_weights:
    st.warning("Set at least one category weight above zero to compute an index.")
    st.stop()

try:
    personal_series = personal_index_time_series(price_df, active_weights)
except ValueError as e:
    st.error(f"Could not compute the personal index: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Step 3: results
# ---------------------------------------------------------------------------
st.header("3. Your personal index vs. the comparison series")

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=list(personal_series.index),
        y=list(personal_series.values),
        mode="lines",
        name="Your personal index",
        line=dict(color=SERIES_BLUE, width=2),
    )
)

if reference_series is not None:
    common_idx = [p for p in personal_series.index if p in reference_series.index]
    fig.add_trace(
        go.Scatter(
            x=common_idx,
            y=[reference_series.loc[p] for p in common_idx],
            mode="lines",
            name="Illustrative comparison index (synthetic)",
            line=dict(color=SERIES_ORANGE, width=2, dash="dash"),
        )
    )

fig.update_layout(
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    font=dict(color=PRIMARY_INK, family="system-ui, -apple-system, Segoe UI, sans-serif"),
    xaxis=dict(showgrid=False, color=MUTED_INK, linecolor=GRIDLINE, title="Period"),
    yaxis=dict(showgrid=True, gridcolor=GRIDLINE, color=MUTED_INK, title="Index (base = 100)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

if reference_series is not None:
    comparison = compare_to_reference(personal_series, reference_series)
    latest = comparison.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Your personal index (latest)", f"{latest['personal_index']:.1f}")
    c2.metric("Comparison index (latest)", f"{latest['reference_index']:.1f}")
    c3.metric("Gap (points)", f"{latest['gap_points']:+.1f}", f"{latest['gap_pct']:+.1f}%")

    with st.expander("Show full comparison table"):
        st.dataframe(comparison.round(2), use_container_width=True)

st.divider()
st.caption(
    "Formula: I_t = 100 * sum_i( w_i * (P_i,t / P_i,0) ). "
    "See docs/METHODOLOGY.md for the full derivation and economic reasoning, "
    "and docs/DATA_SOURCES.md for where to get real MoSPI CPI data."
)
