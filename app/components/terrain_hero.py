"""Embeds the pre-built Hairline "Terrain" hero (see
app/assets/terrain_hero/) as a bidirectional Streamlit custom component.

The JS bundle is built offline with esbuild (see
app/assets/terrain_hero/build.mjs) because Streamlit Cloud runs Python
only — this module just points declare_component() at the already-built
dist/ directory. There is no economic data in this component; it is pure
navigation chrome to the site's own Lab pages. A click sends the target
page's slug back to Python (Streamlit's own postMessage protocol), and
render() returns that slug so the caller can st.switch_page() — the
frontend never navigates the browser directly.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_DIST_DIR = Path(__file__).resolve().parents[1] / "assets" / "terrain_hero" / "dist"

# href slug (sent by the frontend) -> the page file st.switch_page() expects.
PAGE_FOR_SLUG = {
    "Wealth_Inequality_Lab": "pages/1_Wealth_Inequality_Lab.py",
    "Banking_Monetary_Policy_Lab": "pages/2_Banking_Monetary_Policy_Lab.py",
    "State_Economic_Divergence_Lab": "pages/3_State_Economic_Divergence_Lab.py",
    "Housing_Intelligence_Lab": "pages/4_Housing_Intelligence_Lab.py",
}

_component = None
if _DIST_DIR.exists():
    _component = components.declare_component("terrain_hero", path=str(_DIST_DIR))


def render(key: str = "terrain_hero") -> None:
    """Render the terrain hero and switch pages if a region was clicked.

    Silently does nothing if the bundle hasn't been built (keeps the app
    usable without the Node toolchain).

    Streamlit custom components keep returning their last value on every
    rerun, not just the rerun right after the click -- without the "already
    consumed" guard below, navigating back to Home after visiting a Lab
    would immediately bounce you right back to that same Lab.
    """
    if _component is None:
        return
    slug = _component(key=key, default=None)
    last_slug_key = f"_{key}_last_slug"
    if slug and slug != st.session_state.get(last_slug_key):
        st.session_state[last_slug_key] = slug
        target = PAGE_FOR_SLUG.get(slug)
        if target:
            st.switch_page(target)
