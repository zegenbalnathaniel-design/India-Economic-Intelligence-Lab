"""Research Library — investigations computed live from the project's data.

Each investigation (analysis/research_library.py) is laid out in the same
eight parts: research question, economic motivation, data sources (from the
evidence ledger), methodology, results, interpretation, limitations and
further questions. Findings are kept in four separate blocks — observed
facts, statistical results, interpretation, hypotheses — and every number in
them is computed from the files listed, when the page runs. Each
investigation downloads as a self-contained HTML research brief, the result
tables as CSV and the settings as JSON.
"""
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

import json

import plotly.graph_objects as go
import streamlit as st

from analysis import research_library as lib
from app.components.briefs import brief_html, tables_csv
from app.components.provenance import sources_panel
from app.components.theme import (
    setup, set_chart_source, prepare_figure_for_export, kicker, callout, footnote,
    TURQUOISE, COBALT, VERMILLION, GOLD, LEAF,
)

setup("Research Library", accent=TURQUOISE)
set_chart_source("data files in this project (listed under Data sources); calculations on this site")

SERIES_COLOURS = [COBALT, VERMILLION, GOLD, LEAF, TURQUOISE]
LABELS = {
    "convergence": "Interstate economic convergence",
    "concentration": "Income and wealth concentration since independence",
    "composition": "Composition effect and return heterogeneity",
    "housing": "Housing price pressure across cities",
    "financialisation": "Financialisation and household wealth",
}

with st.sidebar:
    st.markdown("## Research Library")
    st.caption("Investigations computed from this project's data")


@st.cache_data(show_spinner="Running the investigation…")
def run(key: str, **kwargs) -> lib.Investigation:
    return lib.INVESTIGATIONS[key](**kwargs)


def build_chart(inv: lib.Investigation, spec: dict) -> go.Figure:
    df = inv.tables[spec["table"]]
    ys = spec["y"] if isinstance(spec["y"], list) else [spec["y"]]
    fig = go.Figure()
    if spec["kind"] == "bar":
        d = df.dropna(subset=ys).sort_values(ys[0], ascending=False)
        fig.add_bar(x=d[spec["x"]], y=d[ys[0]], marker_color=COBALT, name=ys[0])
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
    else:
        for i, y in enumerate(ys):
            d = df.dropna(subset=[y])  # gaps stay gaps: no interpolation across missing years
            fig.add_scatter(x=d[spec["x"]], y=d[y], mode="lines+markers", name=y,
                            line=dict(color=SERIES_COLOURS[i % len(SERIES_COLOURS)], width=2),
                            marker=dict(size=4))
    fig.update_layout(title=spec["title"], height=440, margin=dict(l=10, r=10, b=10),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def bullets(items: list[str]) -> None:
    st.markdown("\n".join(f"- {i}" for i in items) if items else "_None._")


kicker("Research Library")
st.title("Investigations, computed from the data")
st.markdown(
    "Each investigation asks one question and answers it only with data already in this project. "
    "The numbers below are calculated when the page runs — change a file and the findings change. "
    "Facts, statistical results, interpretation and hypotheses are kept apart, and nothing here "
    "claims cause and effect."
)

key = st.selectbox("Investigation", list(lib.INVESTIGATIONS), format_func=lambda k: LABELS.get(k, k))
kwargs: dict = {}
if key == "composition":
    c1, c2 = st.columns(2)
    kwargs["inflation"] = c1.slider("Inflation π (%)", 2.0, 10.0, 6.5, 0.1) / 100
    kwargs["g_real"] = c2.slider("Real income growth g (%)", 2.0, 9.0, 6.5, 0.1) / 100
    st.caption("Starting values 6.5% / 6.5% are round settings for illustration, not estimates — "
               "move them to test the reading.")
inv = run(key, **kwargs)

st.header(inv.title)
st.subheader("1 · Research question")
st.markdown(inv.question)
st.subheader("2 · Economic motivation")
st.markdown(inv.motivation)
st.subheader("3 · Data sources")
st.markdown(f"Evidence-ledger records: {', '.join(f'`{d}`' for d in inv.data)}")
sources_panel(*inv.data, title="Full records for these sources")
st.subheader("4 · Methodology")
st.markdown(inv.method)

st.subheader("5 · Results")
figures = []
for spec in inv.charts:
    fig = build_chart(inv, spec)
    st.plotly_chart(fig, use_container_width=True)
    figures.append(prepare_figure_for_export(fig)[0])
for name, df in inv.tables.items():
    with st.expander(f"Table: {name} ({len(df)} rows)"):
        st.dataframe(df, use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Observed facts**")
    bullets(inv.facts)
with c2:
    st.markdown("**Statistical results**")
    bullets(inv.statistics)

st.subheader("6 · Interpretation")
bullets(inv.interpretation)
footnote("Descriptive and correlational only — no causal claim is made.")
st.markdown("**Hypotheses requiring further testing**")
bullets(inv.hypotheses)

st.subheader("7 · Limitations")
bullets(inv.limitations)
st.subheader("8 · Further research questions")
bullets(inv.further_questions)

st.subheader("Downloads")
d1, d2, d3 = st.columns(3)
d1.download_button("Research brief (HTML)", brief_html(inv, figures).encode("utf-8"),
                   file_name=f"ieil-brief-{inv.id}.html", mime="text/html")
d2.download_button("Result tables (CSV)", tables_csv(inv), file_name=f"ieil-{inv.id}-tables.csv",
                   mime="text/csv")
d3.download_button("Settings (JSON)", json.dumps({"investigation": inv.id, **inv.settings}, indent=2,
                                                 default=str).encode("utf-8"),
                   file_name=f"ieil-{inv.id}-settings.json", mime="application/json")
st.caption("The brief contains all eight parts, the charts, the tables, the sources with their limitations, "
           "the settings and the time it was generated. Charts in the brief load plotly.js from its CDN.")

st.divider()
st.header("Not yet possible with the data in this project")
callout("These investigations are part of the research programme but would need data the project does not "
        "hold. They are listed rather than approximated.", kind="note")
for title, need in lib.NOT_YET_POSSIBLE:
    st.markdown(f"- **{title}** — DATA REQUIRED: {need}")
