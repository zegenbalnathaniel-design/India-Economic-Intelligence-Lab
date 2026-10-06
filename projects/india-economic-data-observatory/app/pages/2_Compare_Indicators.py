"""Compare Indicators — overlay any two indicators on one chart, each
carrying its own live/synthetic status and metadata caption."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from data_observatory import loaders, viz  # noqa: E402
from data_observatory.metadata import DataStatus  # noqa: E402

st.set_page_config(page_title="Compare Indicators — India Economic Data Observatory", page_icon="📊", layout="wide")
st.title("Compare Indicators")
st.caption("Overlay two indicators on dual y-axes. Units usually differ — read each axis by its color.")

all_keys = list(loaders.INDICATORS.keys())
label = lambda k: f"{loaders.INDICATORS[k].category} — {loaders.INDICATORS[k].name}"  # noqa: E731

col_a, col_b = st.columns(2)
with col_a:
    key_a = st.selectbox("Indicator A", all_keys, index=all_keys.index("gdp"), format_func=label)
with col_b:
    default_b = "cpi" if "cpi" in all_keys else all_keys[1]
    key_b = st.selectbox("Indicator B", all_keys, index=all_keys.index(default_b), format_func=label)

start = st.sidebar.date_input("Start date", date(2000, 1, 1))
end = st.sidebar.date_input("End date", date(2023, 1, 1))
allow_live = st.sidebar.toggle("Attempt live fetch first", value=True)

if start >= end:
    st.error("Start date must be before end date.")
    st.stop()

with st.spinner("Loading..."):
    frame_a, meta_a = loaders.load(key_a, str(start), str(end), allow_live=allow_live)
    frame_b, meta_b = loaders.load(key_b, str(start), str(end), allow_live=allow_live)

badge_cols = st.columns(2)
for col, meta in zip(badge_cols, (meta_a, meta_b)):
    with col:
        if meta.status is DataStatus.OFFICIAL:
            st.success(viz.status_badge_text(meta))
        else:
            st.warning(viz.status_badge_text(meta))

fig = viz.comparison_chart(frame_a, meta_a, frame_b, meta_b)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Metadata — Indicator A"):
    st.text(meta_a.long_description())
with st.expander("Metadata — Indicator B"):
    st.text(meta_b.long_description())
