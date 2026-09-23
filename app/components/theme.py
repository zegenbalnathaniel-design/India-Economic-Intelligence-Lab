"""Shared visual theme: colours, typography, chart defaults.

Design intent: academic paper x financial terminal x modern data lab.
Restrained palette, high whitespace, no gradients or gaming UI.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

INK = "#0E1116"
INK_SOFT = "#3A3F47"
MUTED = "#6B7280"
RULE = "#E5E7EB"
PAPER = "#FBFBF9"
ACCENT = "#0A4D68"
ACCENT_ALT = "#B45309"
POS = "#0F766E"
NEG = "#9F1239"

SERIES = ["#0A4D68", "#B45309", "#4B5563", "#0F766E", "#7C3AED", "#9F1239"]


def apply_page_config(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} — India Economic Intelligence Lab",
        page_icon="◧",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        html, body, [class*="css"]  {
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Helvetica Neue", Arial, sans-serif;
        }
        .block-container { padding-top: 2.2rem; max-width: 1180px; }
        h1, h2, h3, h4 { letter-spacing: -0.01em; color: #0E1116; }
        h1 { font-weight: 600; }
        h2 { font-weight: 600; margin-top: 1.4rem; border-bottom: 1px solid #E5E7EB; padding-bottom: .35rem; }
        h3 { font-weight: 600; color: #1F2937; }
        .stMarkdown p { color: #1F2937; line-height: 1.55; }
        .source-badge {
            display: inline-block; font-size: 11px; padding: 2px 8px; margin-right: 6px;
            border: 1px solid #D1D5DB; border-radius: 999px; color: #374151; background: #F9FAFB;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }
        .kicker {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .16em; color: #6B7280; text-transform: uppercase;
        }
        .callout {
            border-left: 3px solid #0A4D68; background: #F3F6F9;
            padding: .7rem 1rem; margin: .8rem 0; border-radius: 2px; color: #1F2937;
        }
        .callout.warn { border-left-color: #B45309; background: #FBF6EE; }
        .callout.note { border-left-color: #6B7280; background: #F9FAFB; }
        .stat {
            border: 1px solid #E5E7EB; padding: .8rem 1rem; border-radius: 4px; background: #FFFFFF;
        }
        .stat .label { font-size: 11px; letter-spacing: .12em; color: #6B7280; text-transform: uppercase; }
        .stat .value { font-size: 1.35rem; font-weight: 600; color: #0E1116; margin-top: .15rem; }
        .stat .sub { font-size: 12px; color: #6B7280; margin-top: .1rem; }
        section[data-testid="stSidebar"] { background: #F7F7F4; border-right: 1px solid #E5E7EB; }
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 14px; letter-spacing: .12em; text-transform: uppercase; color: #6B7280; border: none; }
        .footnote { color: #6B7280; font-size: 12px; margin-top: 1rem; border-top: 1px solid #E5E7EB; padding-top: .6rem; }
        table { font-size: 13px; }
        .flowbox {
            display: inline-block; padding: .6rem 1rem; border: 1px solid #D1D5DB; border-radius: 2px;
            background: #FFFFFF; font-weight: 500; color: #0E1116; min-width: 200px; text-align: center;
        }
        .flowarrow { color: #9CA3AF; font-size: 20px; margin: .1rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def register_plotly_template() -> None:
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, Helvetica Neue, Arial", color=INK, size=13),
        colorway=SERIES,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=False, ticks="outside", tickcolor=RULE, linecolor=RULE, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=RULE, zeroline=False, ticks="outside", tickcolor=RULE, linecolor=RULE),
        margin=dict(l=48, r=24, t=48, b=48),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        title=dict(font=dict(size=15, color=INK), x=0.0),
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
