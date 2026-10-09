"""Embeds the pre-built Hairline "Turntable" ("four ways of looking at this
site") as a second, bidirectional homepage navigation device, alongside
the terrain hero. Same pattern as app/components/terrain_hero.py: a click
sends the chosen page's slug back to Python over Streamlit's own
postMessage protocol, and render() calls st.switch_page() -- the
frontend never navigates the browser directly (confirmed, while building
the terrain hero, that a components.v1.html()/declare_component iframe's
sandbox silently refuses a direct top-level navigation).
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_DIST_DIR = Path(__file__).resolve().parents[1] / "assets" / "turntable_home" / "dist"

PAGE_FOR_SLUG = {
    "Banking_Monetary_Policy_Lab": "pages/2_Banking_Monetary_Policy_Lab.py",
    "Wealth_Inequality_Lab": "pages/1_Wealth_Inequality_Lab.py",
    # Slug kept from the built JS bundle (page was renamed to State Economy Lab
    # when the State Economy Explorer was merged into it); only the target changed.
    "State_Economic_Divergence_Lab": "pages/3_State_Economy_Lab.py",
    "Data": "pages/7_Data.py",
}

_component = None
if _DIST_DIR.exists():
    _component = components.declare_component("turntable_home", path=str(_DIST_DIR))


def render(key: str = "turntable_home") -> None:
    """Render the turntable and switch pages if a face was chosen.

    Silently does nothing if the bundle hasn't been built. Uses the same
    "already consumed" session-state guard as the terrain hero, so
    navigating back to Home doesn't immediately bounce you to the same
    page again.
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
