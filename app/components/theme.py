"""Shared visual theme: colours, typography, chart defaults.

Design intent: a vibrant, confident computational-economics laboratory on
a near-black base -- contemporary, not vintage, not a generic SaaS
dashboard, not monochrome. Palette is fixed to seven colours (two
neutrals, five vibrant -- no pink or purple); every other tone here
(muted text, rules, chart tints) is a derived shade of one of the seven,
not a new hue.

Each Lab page gets its own accent colour (matching its colour on the
homepage's Research Index) via `setup(title, accent=...)`, layered on top
of this shared base rather than one flat colour for the whole site.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Fixed 7-colour set. Nothing on this site uses a colour outside this list.
INK = "#11131A"         # page background (deep ink)
WARM_WHITE = "#F5F0E6"  # primary text
COBALT = "#3155D9"
VERMILLION = "#F04A32"
GOLD = "#F3C542"
LEAF = "#5B963F"
TURQUOISE = "#24A6A1"

PARCHMENT = WARM_WHITE          # back-compat alias
VOID = INK                      # back-compat alias
PAPER = INK                     # back-compat alias
CRIMSON = VERMILLION            # back-compat alias (old secondary accent)
ESPRESSO = "#181B26"            # card / sidebar background
INK_SOFT = "#C9C5BA"            # warm white, dimmed -- secondary text
MUTED = "#8B8D99"               # cool-dimmed -- captions/labels
RULE = "#2A2E3C"                # espresso, lightened -- dividers/borders

ACCENT = COBALT
ACCENT_ALT = VERMILLION
POS = LEAF
NEG = VERMILLION

SERIES = [COBALT, VERMILLION, GOLD, LEAF, TURQUOISE, WARM_WHITE]

# One accent per Lab, matching its colour on the homepage Research Index.
LAB_ACCENTS = {
    "wealth": VERMILLION,
    "banking": COBALT,
    "regional": LEAF,
    "housing": GOLD,
}


def apply_page_config(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} — India Economic Intelligence Lab",
        page_icon="◧",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{ --accent: {ACCENT}; }}
        html, body, [class*="css"]  {{
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Helvetica Neue", Arial, sans-serif;
            background: {INK};
        }}
        .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
        h1, h2, h3, h4 {{
            letter-spacing: -0.01em; color: {WARM_WHITE};
            font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-weight: 800;
        }}
        h1 {{ font-weight: 800; }}
        h2 {{ font-weight: 700; margin-top: 1.4rem; border-bottom: 1px solid {RULE}; padding-bottom: .35rem; }}
        h3 {{ font-weight: 700; color: {INK_SOFT}; }}
        .stMarkdown p {{ color: {INK_SOFT}; line-height: 1.55; }}
        a, .stMarkdown a {{ color: var(--accent); }}
        .source-badge {{
            display: inline-block; font-size: 11px; padding: 2px 8px; margin-right: 6px;
            border: 1px solid {RULE}; border-radius: 999px; color: {MUTED}; background: {ESPRESSO};
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }}
        .kicker {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .16em; color: var(--accent); text-transform: uppercase;
        }}
        .callout {{
            border-left: 3px solid var(--accent); background: {ESPRESSO};
            padding: .7rem 1rem; margin: .8rem 0; border-radius: 2px; color: {INK_SOFT};
        }}
        .callout.warn {{ border-left-color: {VERMILLION}; background: #2A1414; }}
        .callout.note {{ border-left-color: {MUTED}; background: {ESPRESSO}; }}
        .stat {{
            border: 1px solid {RULE}; padding: .8rem 1rem; border-radius: 4px; background: {ESPRESSO};
        }}
        .stat .label {{ font-size: 11px; letter-spacing: .12em; color: {MUTED}; text-transform: uppercase; }}
        .stat .value {{ font-size: 1.35rem; font-weight: 700; color: var(--accent); margin-top: .15rem; }}
        .stat .sub {{ font-size: 12px; color: {MUTED}; margin-top: .1rem; }}
        section[data-testid="stSidebar"] {{ background: {ESPRESSO}; border-right: 1px solid {RULE}; }}
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2 {{
            font-size: 14px; letter-spacing: .12em; text-transform: uppercase; color: {MUTED};
            border: none; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }}
        .footnote {{ color: {MUTED}; font-size: 12px; margin-top: 1rem; border-top: 1px solid {RULE}; padding-top: .6rem; }}
        table {{ font-size: 13px; }}
        .flowbox {{
            display: inline-block; padding: .6rem 1rem; border: 1px solid {RULE}; border-radius: 2px;
            background: {ESPRESSO}; font-weight: 500; color: {WARM_WHITE}; min-width: 200px; text-align: center;
        }}
        .flowarrow {{ color: {MUTED}; font-size: 20px; margin: .1rem 0; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_accent_override(accent: str) -> None:
    """Overrides --accent for the current page only -- each Lab gets its
    own colour (matching its homepage Research Index entry) layered on
    top of the shared theme, instead of one flat colour site-wide."""
    st.markdown(f"<style>:root {{ --accent: {accent} !important; }}</style>", unsafe_allow_html=True)


def register_plotly_template(accent: str | None = None) -> None:
    colorway = SERIES if accent is None else [accent] + [c for c in SERIES if c != accent]
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, Helvetica Neue, Arial", color=WARM_WHITE, size=13),
        colorway=colorway,
        paper_bgcolor=ESPRESSO,
        plot_bgcolor=ESPRESSO,
        xaxis=dict(showgrid=False, ticks="outside", tickcolor=RULE, linecolor=RULE, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=RULE, zeroline=False, ticks="outside", tickcolor=RULE, linecolor=RULE),
        margin=dict(l=48, r=24, t=48, b=48),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        title=dict(font=dict(size=15, color=WARM_WHITE), x=0.0),
    )
    pio.templates["iiel"] = tmpl
    pio.templates.default = "iiel"


def kicker(text: str) -> None:
    st.markdown(f"<div class='kicker'>{text}</div>", unsafe_allow_html=True)


def callout(text: str, kind: str = "note") -> None:
    st.markdown(f"<div class='callout {kind}'>{text}</div>", unsafe_allow_html=True)


def source_badge(*labels: str) -> None:
    html = " ".join(f"<span class='source-badge'>{label}</span>" for label in labels)
    st.markdown(html, unsafe_allow_html=True)


def stat_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"<div class='stat'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>"
        f"<div class='sub'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def footnote(text: str) -> None:
    st.markdown(f"<div class='footnote'>{text}</div>", unsafe_allow_html=True)


def setup(page_title: str, accent: str | None = None) -> None:
    apply_page_config(page_title)
    register_plotly_template(accent)
    inject_css()
    if accent is not None:
        inject_accent_override(accent)
