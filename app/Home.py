"""India Economic Intelligence Lab — entry point.

Launch with `streamlit run app/Home.py` from the repository root. This file
only sets up the grouped sidebar navigation (app/components/navigation.py)
and runs the selected page; the home page itself is app/home_page.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `analysis.*` and `data_sources.*` imports when running `streamlit run app/Home.py`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.components import navigation  # noqa: E402

st.navigation(navigation.sections(), expanded=True).run()
