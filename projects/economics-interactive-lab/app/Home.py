"""Economics Interactive Lab -- Streamlit entry point.

This file only sets page-level config and an overview/navigation page.
Each module gets its own page under app/pages/, generated from the same
registry described in econ_lab.registry -- adding a new module to the
registry and a thin page file is all a future contributor needs to do.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

import econ_lab.modules  # noqa: F401  (registers every built-in module)
from econ_lab.registry import all_modules, domains, modules_by_domain

st.set_page_config(
    page_title="Economics Interactive Lab",
    page_icon="📈",
    layout="wide",
)

st.title("Economics Interactive Lab")
st.caption(
    "A small set of interactive, mathematically correct modules for learning "
    "microeconomics, macroeconomics, and finance fundamentals by experimenting, "
    "not just by looking at a static diagram."
)

st.markdown(
    """
This is an **educational toy-model lab**, not a forecasting or empirical-research
tool. Every module below pairs:

1. A short explanation of the **concept**.
2. The governing **equation** -- always true given the model's assumptions.
3. **Interactive controls** for the specific, illustrative numbers you choose.
4. A **visualization** that updates as you move the controls.
5. A concrete **experiment** prompt -- something specific to try.
6. A plain-English **explanation** of what you're seeing.
7. Explicit **limitations** -- what the model does *not* claim.

Use the sidebar to open a module page.
"""
)

st.divider()

for domain in domains():
    st.subheader(domain)
    cols = st.columns(3)
    for i, (key, module) in enumerate(modules_by_domain(domain).items()):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{module.title}**")
                st.caption(module.concept)

st.divider()
st.markdown(
    "Source, methodology, and the full module architecture are documented in "
    "`README.md` and `docs/METHODOLOGY.md` in this project's repository folder."
)
