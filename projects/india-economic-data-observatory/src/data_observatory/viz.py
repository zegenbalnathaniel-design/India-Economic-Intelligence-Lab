"""Reusable visualization helpers where Metadata always travels with the
chart: every figure this module builds carries its source, unit, frequency
and live/synthetic status as a visible annotation, not just as a return
value the caller might forget to display.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from .metadata import DataStatus, Metadata

# A restrained, "sophisticated" palette: deep slate/ink for official data,
# a dashed warm amber for synthetic, consistent across the whole app.
COLOR_OFFICIAL = "#1f3a5f"
COLOR_SYNTHETIC = "#b5651d"
COLOR_GRID = "rgba(0,0,0,0.08)"
COLOR_CAPTION = "#555555"


def status_badge_text(meta: Metadata) -> str:
    return "● LIVE / OFFICIAL" if meta.status.is_official else "◆ SYNTHETIC / ILLUSTRATIVE"


def _trace_style(meta: Metadata) -> dict:
    if meta.status.is_official:
        return dict(color=COLOR_OFFICIAL, dash="solid")
    return dict(color=COLOR_SYNTHETIC, dash="dash")


def line_chart(frame: pd.DataFrame, meta: Metadata, title: Optional[str] = None) -> go.Figure:
    """Single-indicator time-series line chart with the Metadata caption
    rendered as a chart annotation, and imputed points marked.

    `frame` must have a DatetimeIndex and a `value` column (and, if
    present, a boolean `imputed` column from `validation.py`).
    """
    style = _trace_style(meta)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame.index, y=frame["value"],
            mode="lines", name=meta.indicator,
            line=dict(color=style["color"], width=2.4, dash=style["dash"]),
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
        )
    )
    if "imputed" in frame.columns and frame["imputed"].any():
        imputed_points = frame[frame["imputed"]]
        fig.add_trace(
            go.Scatter(
                x=imputed_points.index, y=imputed_points["value"],
                mode="markers", name="forward-filled (imputed)",
                marker=dict(color=style["color"], size=7, symbol="circle-open", line=dict(width=2)),
                hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f} (imputed)<extra></extra>",
            )
        )

    fig.update_layout(
        title=title or f"{meta.indicator}  —  {status_badge_text(meta)}",
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Georgia, 'Times New Roman', serif", size=13, color="#1a1a1a"),
        xaxis=dict(title="", gridcolor=COLOR_GRID, showline=True, linecolor="#ccc"),
        yaxis=dict(title=meta.unit, gridcolor=COLOR_GRID, showline=True, linecolor="#ccc"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=60, r=30, t=70, b=90),
        annotations=[
            dict(
                text=meta.caption(),
                xref="paper", yref="paper", x=0, y=-0.22,
                showarrow=False, align="left",
                font=dict(size=11, color=COLOR_CAPTION),
            )
        ],
    )
    return fig


def comparison_chart(
    frame_a: pd.DataFrame, meta_a: Metadata,
    frame_b: pd.DataFrame, meta_b: Metadata,
    title: Optional[str] = None,
) -> go.Figure:
    """Two-indicator comparison on dual y-axes (units typically differ),
    each line carrying its own live/synthetic styling, with both series'
    metadata captions stacked underneath."""
    fig = go.Figure()
    style_a, style_b = _trace_style(meta_a), _trace_style(meta_b)

    fig.add_trace(
        go.Scatter(
            x=frame_a.index, y=frame_a["value"], name=meta_a.indicator,
            mode="lines", line=dict(color=style_a["color"], width=2.4, dash=style_a["dash"]),
            yaxis="y1",
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra>" + meta_a.indicator + "</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame_b.index, y=frame_b["value"], name=meta_b.indicator,
            mode="lines", line=dict(color=style_b["color"], width=2.4, dash=style_b["dash"]),
            yaxis="y2",
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra>" + meta_b.indicator + "</extra>",
        )
    )

    fig.update_layout(
        title=title or f"{meta_a.indicator}  vs.  {meta_b.indicator}",
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Georgia, 'Times New Roman', serif", size=13, color="#1a1a1a"),
        xaxis=dict(title="", gridcolor=COLOR_GRID, showline=True, linecolor="#ccc"),
        yaxis=dict(title=dict(text=meta_a.unit, font=dict(color=style_a["color"])),
                    gridcolor=COLOR_GRID, showline=True, linecolor="#ccc",
                    tickfont=dict(color=style_a["color"])),
        yaxis2=dict(title=dict(text=meta_b.unit, font=dict(color=style_b["color"])),
                     overlaying="y", side="right", showgrid=False,
                     tickfont=dict(color=style_b["color"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=60, r=60, t=70, b=120),
        annotations=[
            dict(text=f"A — {meta_a.caption()}", xref="paper", yref="paper", x=0, y=-0.24,
                 showarrow=False, align="left", font=dict(size=11, color=COLOR_CAPTION)),
            dict(text=f"B — {meta_b.caption()}", xref="paper", yref="paper", x=0, y=-0.32,
                 showarrow=False, align="left", font=dict(size=11, color=COLOR_CAPTION)),
        ],
    )
    return fig
