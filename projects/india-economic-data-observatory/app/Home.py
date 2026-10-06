"""India Economic Data Observatory — Streamlit entry point."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_observatory import loaders  # noqa: E402

st.set_page_config(page_title="India Economic Data Observatory", page_icon="📊", layout="wide")

st.title("📊 India Economic Data Observatory")
st.markdown(
    """
A data ingestion, cleaning and validation **platform** for Indian economic
indicators — GDP and growth, prices, the labour market, government
finances, the external sector and the financial system — each one loaded
through the same pipeline: **attempt a real official source first, fall
back to a clearly-labelled synthetic series only if that fails, validate
and clean either way, and never let the two be confused.**

**Use the sidebar pages:**

1. **Browse Indicators** — pick a category and an indicator, see the chart
   with its full source metadata, and see at a glance whether you're
   looking at live official data or a synthetic stand-in.
2. **Compare Indicators** — overlay any two indicators on one chart.
3. **Methodology & Sources** — the full source table, the validation
   rules, and this environment's actual live-fetch probe result.
"""
)

st.divider()

live_count = 0
synthetic_count = 0
for key in loaders.INDICATORS:
    spec = loaders.INDICATORS[key]
    if spec.wb_code is not None:
        live_count += 1
    else:
        synthetic_count += 1

st.warning(
    f"**Live/synthetic status, architecture-wide:** {live_count} of "
    f"{len(loaders.INDICATORS)} indicators are wired to a real, unauthenticated "
    f"World Bank API endpoint and are attempted live on every load; the "
    f"remaining {synthetic_count} (WPI, the RBI policy rate) have no plain "
    f"REST endpoint at their official source and are illustrative-only today. "
    f"**Whether the World Bank attempts actually succeed depends on this "
    f"specific runtime's network policy — see the Methodology & Sources page "
    f"for the measured result in this environment.** Every chart below "
    f"states its own live-vs-synthetic status explicitly; never assume."
)

st.subheader("Indicator categories")
cols = st.columns(3)
for i, (category, keys) in enumerate(loaders.list_categories().items()):
    with cols[i % 3]:
        st.markdown(f"**{category}**")
        for k in keys:
            st.markdown(f"- {loaders.INDICATORS[k].name}")
