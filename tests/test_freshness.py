"""app/components/freshness.py: stale project modules are reloaded in place."""
from __future__ import annotations

import os
import sys
import time

from app.components import freshness
from data_sources import loaders


def test_missing_function_restored_after_redeploy_like_state():
    freshness.reload_stale_modules()          # mark everything as current
    del loaders.load_macro_monthly            # simulate the old in-memory module
    os.utime(loaders.__file__)                # ...and a newer file on disk
    time.sleep(0.01)
    reloaded = freshness.reload_stale_modules()
    assert "data_sources.loaders" in reloaded
    assert hasattr(sys.modules["data_sources.loaders"], "load_macro_monthly")
    assert loaders.load_macro_monthly is sys.modules["data_sources.loaders"].load_macro_monthly  # in place


def test_unchanged_modules_are_not_reloaded_again():
    freshness.reload_stale_modules()
    assert "data_sources.loaders" not in freshness.reload_stale_modules()


def test_financial_year_axis_becomes_category():
    import plotly.graph_objects as go
    from app.components import theme
    fys = [f"{y}-{(y + 1) % 100:02d}" for y in range(2004, 2023)]
    f = go.Figure(go.Scatter(x=fys, y=list(range(len(fys)))))
    theme.prepare_figure_for_export(f)
    assert f.layout.xaxis.type == "category" and f.layout.xaxis.tickangle == -45
    g = go.Figure(go.Scatter(x=[2004, 2005], y=[1, 2]))
    theme.prepare_figure_for_export(g)
    assert g.layout.xaxis.type is None


def test_source_subtitle_only_on_titled_charts():
    import plotly.graph_objects as go
    from app.components import theme
    theme.set_chart_source("Test source")
    f, name = theme.prepare_figure_for_export(go.Figure().update_layout(title="My chart"))
    assert f.layout.title.subtitle.text == "Source: Test source" and name.endswith("my-chart")
    o, _ = theme.prepare_figure_for_export(theme.chart_source(go.Figure().update_layout(title="T"), "Override"))
    assert o.layout.title.subtitle.text == "Source: Override"
    n, _ = theme.prepare_figure_for_export(go.Figure())
    assert not n.layout.title.subtitle.text
