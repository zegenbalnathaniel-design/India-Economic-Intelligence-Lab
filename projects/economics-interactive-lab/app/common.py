"""Shared page-rendering helper for module pages.

Every page under app/pages/ is a thin wrapper: look up one (or a couple
of related) ``EconModule`` by key from the registry, then call
``render_module_page(module)``. This keeps the concept -> equation ->
controls -> visualization -> experiment -> explanation -> limitations
ordering identical across every module page, defined once here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

import econ_lab.modules  # noqa: F401  (registers every built-in module)
from econ_lab.registry import EconModule


def render_module_page(module: EconModule) -> None:
    st.set_page_config(page_title=module.title, page_icon="📈", layout="wide")
    st.title(module.title)
    st.caption(module.domain)

    st.markdown("### Concept")
    st.markdown(module.concept)

    st.markdown("### Equation")
    st.latex(module.equation)

    st.markdown("### Try it")
    inputs = module.render_controls()

    try:
        results = module.compute(**inputs)
    except ValueError as exc:
        st.error(f"Invalid inputs for this illustrative model: {exc}")
        return

    st.markdown("### Visualization")
    module.render_visualization(inputs, results)

    st.markdown("### Experiment")
    st.info(module.experiment)

    st.markdown("### Explanation")
    st.markdown(module.explanation)

    st.markdown("### Limitations")
    st.warning(module.limitations)
