"""Homepage-only visual system: vibrant editorial identity for the Home
page hero, numbers strip, research index and process diagram.

Deliberately separate from app/components/theme.py, which stays in force
on every Lab/Research/Methodology/etc. page. Scope, per the brief this
was built from: redesign the HOME PAGE's visual identity; do not touch
the Labs' existing dark/gold theme, routes, data or methodology.

The base stays the site's existing near-black (already functionally
"Deep Ink") and parchment text -- this module only adds the vibrant
accent system and large-type hero/index layout on top of it, rather
than re-deriving a whole second base palette.
"""
from __future__ import annotations

import streamlit as st

# Fixed 7-colour set (2 neutrals + 5 vibrant). Pink and purple are excluded
# by explicit instruction -- every colour used on the home page comes from
# this list, nothing invented ad hoc.
INK = "#11131A"
WARM_WHITE = "#F5F0E6"
COBALT = "#3155D9"
VERMILLION = "#F04A32"
GOLD = "#F3C542"
LEAF = "#5B963F"
TURQUOISE = "#24A6A1"

# Per-lab colour direction (2-3 colours each, all from the set above).
LAB_COLORS = {
    "wealth": {"primary": VERMILLION, "secondary": GOLD},
    "banking": {"primary": COBALT, "secondary": TURQUOISE},
    "regional": {"primary": LEAF, "secondary": VERMILLION},
    "housing": {"primary": GOLD, "secondary": COBALT},
}


def inject_home_css() -> None:
    st.markdown(
        f"""
        <style>
        .ieil-micro {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
            color: #8C8779; display: flex; gap: 1.5rem; flex-wrap: wrap;
            margin-bottom: .6rem;
        }}
        .ieil-hero-title {{
            font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-weight: 800; letter-spacing: -0.02em; line-height: 0.95;
            font-size: clamp(3.2rem, 9vw, 7.2rem); color: #F5F0E6;
            margin: 0;
        }}
        .ieil-hero-title .accent {{ color: {VERMILLION}; }}
        .ieil-hero-sub {{
            max-width: 560px; font-size: 1.05rem; color: #B6AF9E; line-height: 1.5;
            margin-top: .6rem;
        }}
        .ieil-numbers {{
            display: flex; flex-wrap: wrap; gap: 3rem; margin: 1rem 0 .5rem;
        }}
        .ieil-number .n {{
            font-weight: 800; font-size: clamp(2.6rem, 6vw, 4.2rem); line-height: 1;
            letter-spacing: -0.02em;
        }}
        .ieil-number .l {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
            color: #8C8779; margin-top: .35rem;
        }}
        .ieil-index-row {{
            display: flex; align-items: baseline; gap: 1.4rem;
            padding: 1.3rem 0; border-top: 1px solid #2A2420;
        }}
        .ieil-index-row:last-child {{ border-bottom: 1px solid #2A2420; }}
        .ieil-index-num {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 13px; color: #8C8779; min-width: 1.8rem;
        }}
        .ieil-index-headline {{
            font-weight: 800; font-size: clamp(1.4rem, 3vw, 2.1rem);
            letter-spacing: -0.01em; line-height: 1.05; margin: 0;
        }}
        .ieil-index-meta {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
            color: #8C8779; margin-top: .3rem;
        }}
        .ieil-index-desc {{ color: #B6AF9E; font-size: .92rem; margin-top: .25rem; max-width: 460px; }}
        .ieil-flow {{ display: flex; align-items: center; gap: .9rem; flex-wrap: wrap; margin: 1rem 0; }}
        .ieil-flow-step {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
            padding: .55rem 1rem; border: 1px solid #3A3026; border-radius: 2px;
            color: #F5F0E6;
        }}
        .ieil-flow-arrow {{ color: #8C8779; font-size: 16px; }}
        .ieil-secondary-links {{
            display: flex; flex-wrap: wrap; gap: 1.4rem; margin-top: .4rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_micro(items: list[str]) -> None:
    html = '<div class="ieil-micro">' + "".join(f"<span>{i}</span>" for i in items) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def hero_title(lines: list[tuple[str, bool]]) -> None:
    """lines: list of (text, is_accent) rendered one per line."""
    inner = "".join(
        f'<div class="{"accent" if accent else ""}">{text}</div>' for text, accent in lines
    )
    st.markdown(f'<div class="ieil-hero-title">{inner}</div>', unsafe_allow_html=True)


def number_stat(value: str, label: str, color: str) -> None:
    st.markdown(
        f'<div class="ieil-number"><div class="n" style="color:{color}">{value}</div>'
        f'<div class="l">{label}</div></div>',
        unsafe_allow_html=True,
    )


def index_row_header(num: str, headline: str, meta: str, desc: str, color: str) -> None:
    st.markdown(
        f"""
        <div class="ieil-index-row">
          <div class="ieil-index-num">{num}</div>
          <div>
            <div class="ieil-index-headline" style="color:{color}">{headline}</div>
            <div class="ieil-index-meta">{meta}</div>
            <div class="ieil-index-desc">{desc}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def flow(steps: list[str]) -> None:
    parts = []
    for i, s in enumerate(steps):
        if i:
            parts.append('<span class="ieil-flow-arrow">→</span>')
        parts.append(f'<span class="ieil-flow-step">{s}</span>')
    st.markdown(f'<div class="ieil-flow">{"".join(parts)}</div>', unsafe_allow_html=True)
