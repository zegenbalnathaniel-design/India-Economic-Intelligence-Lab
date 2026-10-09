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

import re

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


_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)([^*]+?)(?<!\s)\*(?![*\w])")


def callout(text: str, kind: str = "note") -> None:
    """Boxed note. The box is raw HTML, where Markdown is not rendered, so
    **bold** and *italic* are converted here rather than shown literally."""
    html = _ITALIC.sub(r"<i>\1</i>", _BOLD.sub(r"<b>\1</b>", text))
    st.markdown(f"<div class='callout {kind}'>{html}</div>", unsafe_allow_html=True)


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


# ---------------------------------------------------------------------------
# Chart export: every st.plotly_chart gets a high-resolution PNG download
# (the chart's camera button) and, when the chart has a title, a "Source: …"
# subtitle so an exported image always carries its source. Pages set a
# default with set_chart_source(); a single chart can override it with
# chart_source(fig, "…"). Patched once per process from setup().
# ---------------------------------------------------------------------------
_FALLBACK_DEFAULTS = {"source": None, "page": "chart"}  # outside a Streamlit run (tests)


def _chart_defaults() -> dict:
    """Per-session store, so two visitors on different pages never share a
    source line; falls back to a module dict outside a Streamlit run."""
    try:
        return st.session_state.setdefault("_ieil_chart_defaults", {"source": None, "page": "chart"})
    except Exception:
        return _FALLBACK_DEFAULTS


def set_chart_source(text: str) -> None:
    """Default source line for every titled chart on the current page."""
    _chart_defaults()["source"] = text


def chart_source(fig: go.Figure, text: str) -> go.Figure:
    """Source line for this one chart (overrides the page default)."""
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    fig.update_layout(meta={**meta, "source": text})
    return fig


def _slug(text: str) -> str:
    keep = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    return "-".join(p for p in keep.split("-") if p)[:60] or "chart"


_FY = re.compile(r"^\d{4}-\d{2}$")


def _fix_financial_year_axis(fig: go.Figure) -> None:
    """Plotly reads Indian financial-year labels such as "2004-05" as dates
    (May 2004), misplacing points and silently dropping "2012-13" onwards
    (no 13th month). Any x axis carrying such labels becomes a category
    axis in chronological order unless a type was set explicitly."""
    for tr in fig.data:
        xs = getattr(tr, "x", None)
        if xs is None or len(xs) == 0:
            continue
        sample = [v for v in list(xs)[:50] if v is not None]
        if sample and all(isinstance(v, str) and _FY.match(v) for v in sample):
            axis = getattr(tr, "xaxis", None) or "x"
            name = "xaxis" if axis == "x" else f"xaxis{axis[1:]}"
            ax = fig.layout[name]
            if ax is None or ax.type in (None, "-"):
                cfg = dict(type="category", categoryorder="category ascending", automargin=True)
                if len(set(xs)) > 8 and (ax is None or ax.tickangle is None):
                    cfg["tickangle"] = -45
                fig.update_layout({name: cfg})


def prepare_figure_for_export(fig: go.Figure) -> tuple[go.Figure, str]:
    """Fix financial-year axes, add the source subtitle (if the chart has a
    title and no subtitle) and return the figure plus a PNG file name."""
    _fix_financial_year_axis(fig)
    title = fig.layout.title.text or ""
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    defaults = _chart_defaults()
    source = meta.get("source") or defaults["source"]
    if title and source:
        try:
            if not fig.layout.title.subtitle.text:
                fig.update_layout(title_subtitle_text=f"Source: {source}",
                                  title_subtitle_font=dict(size=11, color=MUTED))
                top = fig.layout.margin.t if fig.layout.margin.t is not None else 48
                fig.update_layout(margin_t=max(top, 78))
        except (AttributeError, ValueError):  # Plotly < 5.24 has no title.subtitle
            pass
    return fig, f"ieil-{_slug(defaults['page'])}-{_slug(title)}"


def _install_chart_export() -> None:
    if getattr(st.plotly_chart, "_ieil_export", False):
        return
    original = st.plotly_chart

    def plotly_chart(figure_or_data, *args, **kwargs):
        if isinstance(figure_or_data, go.Figure):
            figure_or_data, filename = prepare_figure_for_export(figure_or_data)
            config = dict(kwargs.get("config") or {})
            config.setdefault("displaylogo", False)
            config.setdefault("toImageButtonOptions", {"format": "png", "scale": 3, "filename": filename})
            kwargs["config"] = config
        return original(figure_or_data, *args, **kwargs)

    plotly_chart._ieil_export = True
    st.plotly_chart = plotly_chart


def setup(page_title: str, accent: str | None = None) -> None:
    apply_page_config(page_title)
    register_plotly_template(accent)
    inject_css()
    if accent is not None:
        inject_accent_override(accent)
    _chart_defaults().update(source=None, page=page_title)
    _install_chart_export()
