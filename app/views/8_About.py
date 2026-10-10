"""About / GitHub page."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import streamlit as st

from app.components.theme import setup, kicker, callout, footnote


setup("About")


kicker("About")
st.title("Project, technology, reproducibility")

st.header("What this is")
st.markdown(
    "An interactive computational supplement to two research papers. "
    "Built as a demonstration of computational economics — how theory can "
    "be translated into code, quantitative models, and interactive "
    "simulations that a reader can re-run under their own assumptions."
)

st.header("Technology")
st.markdown(
    "- **Python** — analysis, modelling and app runtime\n"
    "- **pandas / NumPy** — data handling and numerical operations\n"
    "- **SciPy / statsmodels** — statistics (Spearman ρ, correlation tests)\n"
    "- **Plotly** — interactive visualisation\n"
    "- **Streamlit** — the app framework itself\n"
    "- **No external services** for the MVP — everything runs locally"
)

st.header("Reproducibility")
st.markdown(
    "```\n"
    "git clone <this repo>\n"
    "cd india-economic-intelligence-lab\n"
    "python -m venv .venv && source .venv/bin/activate\n"
    "pip install -r requirements.txt\n"
    "python -m data_sources.build_illustrative_data\n"
    "streamlit run app/Home.py\n"
    "```"
)

st.header("Repository structure")
st.code(
    "india-economic-intelligence-lab/\n"
    "│\n"
    "├── app/                    Streamlit UI\n"
    "│   ├── Home.py             entry point: grouped sidebar navigation (st.navigation)\n"
    "│   ├── home_page.py        the home page\n"
    "│   ├── components/         theme, chart export, navigation, sources panel, 3D figures, briefs\n"
    "│   ├── assets/             built JS bundles for the 3D figures (terrain, turntable, hairlines)\n"
    "│   └── views/              the 15 page scripts (registered in components/navigation.py)\n"
    "│\n"
    "├── analysis/               domain logic (pure functions, tested)\n"
    "│   ├── wealth.py, inequality.py, financialisation.py\n"
    "│   ├── banking.py          iBFPI, robustness, fixed-effects regression\n"
    "│   ├── regional.py, convergence.py, states.py\n"
    "│   ├── housing.py, structural.py, transmission.py, macro_monthly.py\n"
    "│   ├── relationships.py, hypotheses.py, econometrics.py, workbench_catalogue.py\n"
    "│   └── research_library.py investigations behind the Research Library\n"
    "│\n"
    "├── data/\n"
    "│   ├── raw/                source files (RBI, NHB, PLFS, HCES, WIL, author papers, ...)\n"
    "│   └── processed/          bank_panel.csv (ILLUSTRATIVE), repo_rate.csv (DERIVED)\n"
    "│\n"
    "├── data_sources/           loaders, evidence ledger (registry.py, meta_*.py),\n"
    "│                           validation checks, World Bank client\n"
    "├── tests/                  pytest suite (analysis, data, ledger, pages, navigation)\n"
    "│\n"
    "├── README.md, methodology.md, data_dictionary.md, DATA_REGISTRY.md\n"
    "├── requirements.txt\n"
    "└── LICENSE",
    language=None,
)

st.header("About the author")
st.markdown(
    "Nathaniel Zegenbal — economics and computational research. This site "
    "is a computational extension of my written research papers, built "
    "for a university-portfolio audience. Contact / discussion invited "
    "via the GitHub repository."
)

st.header("License & citation")
st.markdown(
    "MIT-licensed code. Please cite the underlying research papers when "
    "referring to the methodologies; cite this repository when referring "
    "to any specific interactive result."
)

callout(
    "This is a research showcase. It is not a financial-advice platform. "
    "It does not sell, recommend or execute anything.",
    kind="warn",
)

footnote(
    "Still to do: real bank filings to replace the illustrative panel, event "
    "studies around RBI MPC decisions (needs the decision history), and macro "
    "controls for the fixed-effects regression. Done: bank fixed-effects and "
    "Newey–West regression, iBFPI sensitivity analysis, correlated / fat-tailed "
    "Monte Carlo, and a distributional Gini from the WIL shares. See Limitations."
)
