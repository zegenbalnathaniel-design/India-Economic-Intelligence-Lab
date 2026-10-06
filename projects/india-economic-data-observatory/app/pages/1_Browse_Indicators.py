"""Browse Indicators — pick a category and an indicator, see its chart and
full metadata, with an explicit live/synthetic status badge."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from data_observatory import loaders, viz  # noqa: E402
from data_observatory.metadata import DataStatus  # noqa: E402

st.set_page_config(page_title="Browse Indicators — India Economic Data Observatory", page_icon="📊", layout="wide")
st.title("Browse Indicators")

categories = loaders.list_categories()
category = st.sidebar.selectbox("Category", list(categories.keys()))
indicator_key = st.sidebar.selectbox(
    "Indicator",
    categories[category],
    format_func=lambda k: loaders.INDICATORS[k].name,
)

start = st.sidebar.date_input("Start date", date(2000, 1, 1))
end = st.sidebar.date_input("End date", date(2023, 1, 1))
allow_live = st.sidebar.toggle("Attempt live fetch first", value=True)

if start >= end:
    st.error("Start date must be before end date.")
    st.stop()

with st.spinner("Loading..."):
    frame, meta = loaders.load(indicator_key, str(start), str(end), allow_live=allow_live)

if meta.status is DataStatus.OFFICIAL:
    st.success(f"**{viz.status_badge_text(meta)}** — fetched live from {meta.provider}.")
else:
    st.warning(
        f"**{viz.status_badge_text(meta)}** — {meta.provider} could not be reached live "
        f"(or live fetch was turned off above). The chart below is a deterministic, "
        f"clearly-labelled stand-in series, **not real data**. See the caption and the "
        f"Methodology & Sources page for exactly why."
    )

fig = viz.line_chart(frame, meta)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Full metadata for this series"):
    st.text(meta.long_description())

with st.expander("Underlying data table"):
    st.dataframe(frame, use_container_width=True)

st.caption(
    "Imputed (forward-filled) points — where the source had a gap or an out-of-domain "
    "value that was treated as missing — are marked with an open circle on the chart "
    "and flagged `True` in the `imputed` column above."
)
