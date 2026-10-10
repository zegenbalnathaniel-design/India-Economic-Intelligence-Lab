"""Site navigation: every page, its sidebar section and its URL.

app/Home.py (the entry point) passes `sections()` to st.navigation. URL
paths are set explicitly to the ones Streamlit derived from the file names
before navigation was grouped, so existing links and bookmarks keep working.
Page files stay where they are, so st.page_link / st.switch_page targets
such as "pages/3_State_Economy_Lab.py" are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PageSpec:
    path: str        # relative to app/
    title: str
    url_path: str    # "" for the home page


SECTIONS: dict[str, list[PageSpec]] = {
    "": [PageSpec("home_page.py", "Home", "")],
    "Labs": [
        PageSpec("pages/1_Wealth_Inequality_Lab.py", "Wealth & Inequality Lab", "Wealth_Inequality_Lab"),
        PageSpec("pages/14_Inequality_Financialisation_Lab.py", "Inequality & Financialisation Lab",
                 "Inequality_Financialisation_Lab"),
        PageSpec("pages/2_Banking_Monetary_Policy_Lab.py", "Banking & Monetary Policy Lab",
                 "Banking_Monetary_Policy_Lab"),
        PageSpec("pages/3_State_Economy_Lab.py", "State Economy Lab", "State_Economy_Lab"),
        PageSpec("pages/4_Housing_Intelligence_Lab.py", "Housing Intelligence Lab", "Housing_Intelligence_Lab"),
        PageSpec("pages/13_Structural_Transformation_Lab.py", "Structural Transformation Lab",
                 "Structural_Transformation_Lab"),
        PageSpec("pages/10_Economic_Relationships_Lab.py", "Economic Relationships Lab",
                 "Economic_Relationships_Lab"),
    ],
    "Models & tools": [
        PageSpec("pages/15_Macro_Transmission_Simulator.py", "Macro Transmission Simulator",
                 "Macro_Transmission_Simulator"),
        PageSpec("pages/12_Macro_and_World.py", "India Macro & World", "Macro_and_World"),
    ],
    "Research": [
        PageSpec("pages/16_Research_Library.py", "Research Library", "Research_Library"),
        PageSpec("pages/5_Research.py", "The Papers", "Research"),
        PageSpec("pages/6_Methodology.py", "Methodology", "Methodology"),
    ],
    "About": [
        PageSpec("pages/7_Data.py", "Data & Evidence Ledger", "Data"),
        PageSpec("pages/8_About.py", "About", "About"),
        PageSpec("pages/9_Limitations.py", "Limitations", "Limitations"),
    ],
}


def all_pages() -> list[PageSpec]:
    return [p for specs in SECTIONS.values() for p in specs]


def sections() -> dict:
    """{section: [st.Page, ...]} for st.navigation."""
    import streamlit as st

    return {
        name: [st.Page(str(APP_DIR / p.path), title=p.title, url_path=p.url_path or None,
                       default=not p.url_path)
               for p in specs]
        for name, specs in SECTIONS.items()
    }
