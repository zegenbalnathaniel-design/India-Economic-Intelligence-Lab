from __future__ import annotations

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Methodology", page_icon="📐", layout="wide")
st.title("📐 Methodology")

doc_path = Path(__file__).resolve().parents[2] / "docs" / "METHODOLOGY.md"
st.markdown(doc_path.read_text())
