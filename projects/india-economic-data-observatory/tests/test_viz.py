import plotly.graph_objects as go

from data_observatory import loaders, viz


def test_line_chart_returns_figure_with_caption_annotation():
    frame, meta = loaders.load("gdp", "2000-01-01", "2010-01-01", allow_live=False)
    fig = viz.line_chart(frame, meta)
    assert isinstance(fig, go.Figure)
    assert len(fig.layout.annotations) >= 1
    caption_text = fig.layout.annotations[0].text
    assert meta.provider in caption_text
    assert "SYNTHETIC" in caption_text.upper()


def test_line_chart_marks_imputed_points_as_separate_trace():
    frame, meta = loaders.load("unemployment_rate", "2000-01-01", "2010-01-01", allow_live=False)
    frame = frame.copy()
    frame.loc[frame.index[2], "imputed"] = True
    fig = viz.line_chart(frame, meta)
    trace_names = [t.name for t in fig.data]
    assert "forward-filled (imputed)" in trace_names


def test_comparison_chart_uses_dual_axes_and_both_captions():
    frame_a, meta_a = loaders.load("gdp", "2000-01-01", "2010-01-01", allow_live=False)
    frame_b, meta_b = loaders.load("cpi", "2000-01-01", "2010-01-01", allow_live=False)
    fig = viz.comparison_chart(frame_a, meta_a, frame_b, meta_b)
    assert len(fig.data) == 2
    assert fig.data[0].yaxis in ("y", "y1", None)
    assert fig.data[1].yaxis == "y2"
    annotations_text = " ".join(a.text for a in fig.layout.annotations)
    assert meta_a.provider in annotations_text
    assert meta_b.provider in annotations_text


def test_status_badge_text_differs_official_vs_synthetic():
    from data_observatory.metadata import DataStatus, with_status

    _, meta_synthetic = loaders.load("gdp", "2000-01-01", "2005-01-01", allow_live=False)
    meta_official = with_status(meta_synthetic, DataStatus.OFFICIAL)
    assert "LIVE" in viz.status_badge_text(meta_official)
    assert "SYNTHETIC" in viz.status_badge_text(meta_synthetic)
