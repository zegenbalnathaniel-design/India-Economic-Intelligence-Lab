"""AppTest smoke tests for the State Economy Lab page: every new control is
exercised and the page must run without an exception each time."""
from __future__ import annotations

from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = st_testing.AppTest

PAGE = str(Path(__file__).resolve().parents[1] / "app" / "pages" / "3_State_Economy_Lab.py")
TIMEOUT = 180


def _run(at):
    at.run(timeout=TIMEOUT)
    assert not at.exception, [e.value for e in at.exception]
    return at


def _by_label(widgets, label):
    hits = [w for w in widgets if w.label == label]
    assert hits, f"no widget labelled {label!r}"
    return hits[0]


@pytest.fixture(scope="module")
def page():
    return _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))


def test_page_renders_all_sections(page):
    headers = [h.value for h in page.header]
    for prefix in ("Convergence window", "A · Sigma", "B · Beta", "Research notes", "I · Schematic tile map",
                   "J · State comparison workbench", "C · State ranking", "E · State lookup", "H · Change"):
        assert any(h.startswith(prefix) for h in headers), prefix
    md = " ".join(m.value for m in page.markdown)
    for text in ("Observed facts", "Statistical results", "Interpretation (cautious, non-causal)",
                 "Questions for further research", "DATA REQUIRED", "Data definitions"):
        assert text in md
    assert any("Schematic tile map — tiles are not to scale and do not depict boundaries." == c.value
               for c in page.caption)
    # default sigma panel is balanced, and the excluded states are listed
    assert _by_label(page.radio, "States counted each year").value == "balanced"
    assert any(c.value.startswith("Excluded from the balanced panel") for c in page.caption)


def test_sigma_measures_and_panel_modes():
    at = _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))
    for measure in ["sd_log", "cv", "gini", "max_min", "p90_p10"]:
        _by_label(at.selectbox, "Dispersion measure").set_value(measure)
        _run(at)
        _by_label(at.radio, "States counted each year").set_value("unbalanced")
        _run(at)
        assert any("Unbalanced" in w.value for w in at.warning)
        _by_label(at.radio, "States counted each year").set_value("balanced")
        _run(at)


def test_series_window_and_robust_se():
    at = _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))
    _by_label(at.checkbox, "Heteroskedasticity-robust standard errors (HC1)").check()
    _run(at)
    assert any("HC1" in m.value for m in at.markdown)
    for series in ["pub_2004", "pub_2011", "spliced"]:
        _by_label(at.radio, "Real per-capita NSDP series (constant prices)").set_value(series)
        _run(at)
    start = _by_label(at.selectbox, "Initial year")
    start.set_value(start.options[3])
    _run(at)
    length = _by_label(at.select_slider, "Window length (years)")
    length.set_value(int(length.options[2]))
    _run(at)


def test_scope_extremes_report_insufficient_data():
    at = _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))
    at.multiselect(key="scope_states").set_value(["Bihar", "Kerala", "Goa"])
    _run(at)
    assert any("Insufficient data" in w.value for w in at.warning)
    at.multiselect(key="scope_states").set_value([])
    _run(at)
    at.multiselect(key="scope_states").set_value(sorted(at.multiselect(key="scope_states").options))
    at.select_slider(key="scope_years").set_value(("2010-11", "2010-11"))
    _run(at)


def test_tile_map_every_indicator_and_year():
    at = _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))
    from analysis import states as S

    for ind in S.INDICATORS:
        at.selectbox(key="tile_ind").set_value(ind)
        _run(at)
        year_box = [s for s in at.selectbox if (s.key or "").startswith("tile_period_")][0]
        for per in year_box.options[:2] + year_box.options[-1:]:
            year_box.set_value(per)
            _run(at)
            year_box = [s for s in at.selectbox if (s.key or "").startswith("tile_period_")][0]
        assert any(c.value.startswith("Name check: every state/UT name") for c in at.caption)


def test_workbench_controls_and_download():
    at = _run(AppTest.from_file(PAGE, default_timeout=TIMEOUT))
    at.multiselect(key="wb_states").set_value(["Kerala"])
    _run(at)
    assert any("at least two" in w.value for w in at.warning)
    at.multiselect(key="wb_states").set_value(["Kerala", "Jammu & Kashmir", "Delhi", "Ladakh", "Sikkim"])
    _run(at)
    for base in ["2004-05", "2022-23"]:
        at.selectbox(key="wb_base").set_value(base)
        _run(at)
    at.radio(key="wb_growth_view").set_value("Lines")
    _run(at)
    assert any("No index line" in c.value for c in at.caption)
