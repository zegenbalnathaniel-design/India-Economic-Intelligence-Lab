"""About / GitHub page."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    "├── app/                    # Streamlit UI\n"
    "│   ├── Home.py\n"
    "│   ├── components/         # theme / shared UI\n"
    "│   └── pages/              # multi-page app: 1..6\n"
    "│\n"
    "├── analysis/               # domain logic\n"
    "│   ├── wealth.py           # composition effect, r - g\n"
    "│   └── banking.py          # iBFPI robust z-score, Spearman, regime split\n"
    "│\n"
    "├── data/\n"
    "│   ├── raw/                # (empty — user-supplied)\n"
    "│   ├── processed/          # bank_panel.csv, repo_rate.csv\n"
    "│   └── cache/              # (empty — for future API-cached pulls)\n"
    "│\n"
    "├── data_sources/           # loaders + illustrative-panel builder\n"
    "├── models/                 # (reserved for future extensions)\n"
    "├── tests/                  # unit tests for analysis modules\n"
    "├── docs/                   # figure notes, methodology pdfs\n"
    "│\n"
    "├── README.md\n"
    "├── methodology.md\n"
    "├── data_dictionary.md\n"
    "├── requirements.txt\n"
    "├── .env.example\n"
    "└── LICENSE\n",
    language="text",
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
    "Version 0.1 (MVP). Future work: real-data ingestion, event studies "
    "around FOMC / RBI MPC decisions, bank-fixed-effects panel regression, "
    "sensitivity analysis for the composition-effect module."
)
