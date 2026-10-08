"""Shared visual theme: colours, typography, chart defaults.

Design intent: a cinematic, dark computational-economics laboratory --
near-black with gold instrumentation and a deep red secondary accent, not
a generic light SaaS dashboard. Palette is fixed to five colours; every
other tone here (muted text, rules, chart tints) is a derived shade of
one of the five, not a new hue.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

VOID = "#0A0908"       # page background
ESPRESSO = "#221C16"   # card / sidebar background
GOLD = "#D4AF37"        # primary accent
CRIMSON = "#8E2424"     # secondary accent
PARCHMENT = "#EAEAE0"   # primary text

INK = PARCHMENT
INK_SOFT = "#B6AF9E"    # parchment, dimmed -- secondary text
MUTED = "#8C8779"       # parchment, further dimmed -- captions/labels
RULE = "#3A3026"        # espresso, lightened -- dividers/borders
PAPER = VOID
ACCENT = GOLD
ACCENT_ALT = CRIMSON
POS = GOLD
NEG = CRIMSON

SERIES = [GOLD, CRIMSON, PARCHMENT, "#8C8779", "#C9972A", "#5C2323"]


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
        html, body, [class*="css"]  {{
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Helvetica Neue", Arial, sans-serif;
            background: {VOID};
        }}
        .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
        h1, h2, h3, h4 {{
            letter-spacing: -0.01em; color: {PARCHMENT};
            font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
        }}
        h1 {{ font-weight: 600; }}
        h2 {{ font-weight: 600; margin-top: 1.4rem; border-bottom: 1px solid {RULE}; padding-bottom: .35rem; }}
        h3 {{ font-weight: 600; color: {INK_SOFT}; }}
        .stMarkdown p {{ color: {INK_SOFT}; line-height: 1.55; }}
        a, .stMarkdown a {{ color: {GOLD}; }}
        .source-badge {{
            display: inline-block; font-size: 11px; padding: 2px 8px; margin-right: 6px;
            border: 1px solid {RULE}; border-radius: 999px; color: {MUTED}; background: {ESPRESSO};
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }}
        .kicker {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .16em; color: {GOLD}; text-transform: uppercase;
        }}
        .callout {{
            border-left: 3px solid {GOLD}; background: {ESPRESSO};
            padding: .7rem 1rem; margin: .8rem 0; border-radius: 2px; color: {INK_SOFT};
        }}
        .callout.warn {{ border-left-color: {CRIMSON}; background: #2A1414; }}
        .callout.note {{ border-left-color: {MUTED}; background: {ESPRESSO}; }}
        .stat {{
            border: 1px solid {RULE}; padding: .8rem 1rem; border-radius: 4px; background: {ESPRESSO};
        }}
        .stat .label {{ font-size: 11px; letter-spacing: .12em; color: {MUTED}; text-transform: uppercase; }}
        .stat .value {{ font-size: 1.35rem; font-weight: 600; color: {GOLD}; margin-top: .15rem; }}
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
            background: {ESPRESSO}; font-weight: 500; color: {PARCHMENT}; min-width: 200px; text-align: center;
        }}
        .flowarrow {{ color: {MUTED}; font-size: 20px; margin: .1rem 0; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def register_plotly_template() -> None:
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, Helvetica Neue, Arial", color=INK, size=13),
        colorway=SERIES,
        paper_bgcolor=ESPRESSO,
        plot_bgcolor=ESPRESSO,
        xaxis=dict(showgrid=False, ticks="outside", tickcolor=RULE, linecolor=RULE, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=RULE, zeroline=False, ticks="outside", tickcolor=RULE, linecolor=RULE),
        margin=dict(l=48, r=24, t=48, b=48),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        title=dict(font=dict(size=15, color=PARCHMENT), x=0.0),
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


def setup(page_title: str) -> None:
    apply_page_config(page_title)
    register_plotly_template()
    inject_css()
