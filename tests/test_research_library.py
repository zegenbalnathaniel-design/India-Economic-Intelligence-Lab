"""Research Library: every investigation runs on the project's data, its
findings carry computed numbers, and the brief contains all eight parts."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from analysis import research_library as lib
from app.components.briefs import brief_html, tables_csv
from data_sources import loaders, registry


@pytest.fixture(scope="module", params=list(lib.INVESTIGATIONS))
def inv(request):
    return lib.INVESTIGATIONS[request.param]()


def test_investigation_complete(inv):
    for part in ("question", "motivation", "method"):
        assert getattr(inv, part).strip()
    for part in ("facts", "statistics", "interpretation", "limitations", "further_questions"):
        assert getattr(inv, part), part
    for d in inv.data:
        registry.get(d)  # every source is in the evidence ledger
    for spec in inv.charts:
        df = inv.tables[spec["table"]]
        ys = spec["y"] if isinstance(spec["y"], list) else [spec["y"]]
        assert {spec["x"], *ys} <= set(df.columns)


def test_findings_carry_numbers(inv):
    # Facts and statistics are generated from computed values, not prose.
    for line in inv.facts + inv.statistics:
        assert re.search(r"\d", line), line


def test_brief_has_all_parts(inv):
    doc = brief_html(inv, [])
    for h in ("1. Research question", "2. Economic motivation", "3. Data sources", "4. Methodology",
              "5. Results", "6. Interpretation", "7. Limitations", "8. Further research questions",
              "Reproducibility"):
        assert h in doc
    csv = tables_csv(inv).decode()
    for name in inv.tables:
        assert f"# table: {name}" in csv


def test_balanced_sigma_is_like_for_like():
    nsdp = loaders.load_nsdp_spliced()
    col = "percapita_nsdp_constant_prices_inr_SPLICED"
    bal = lib.balanced_sigma(nsdp, col)
    assert bal["table"]["n_states"].nunique() == 1
    wide = nsdp.pivot_table(index="financial_year", columns="state", values=col)
    assert bal["n_states"] == wide.dropna(axis=1).shape[1]


def test_rg_reading_classifies():
    rmg = pd.DataFrame({"asset": ["A", "B", "C"], "r_minus_g": [0.02, 0.001, -0.03]})
    text = lib._rg_reading(rmg)
    assert "above g: A" in text and "about equal to g (within ±0.5 pts): B" in text and "below g: C" in text


def test_composition_settings_flow_through():
    inv = lib.composition_effect(inflation=0.05, g_real=0.06)
    assert inv.settings["inflation"] == 0.05 and inv.settings["g_real"] == 0.06
    assert "5.0%" in inv.method


def test_page_runs():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/pages/16_Research_Library.py"), default_timeout=120).run()
    assert not at.exception, at.exception
    for k in lib.INVESTIGATIONS:
        at.selectbox[0].set_value(k).run()
        assert not at.exception, (k, at.exception)


def test_sigma_robustness_two_panels():
    from analysis import convergence as conv
    rob = conv.sigma_robustness(loaders.load_nsdp_spliced())
    assert set(rob["panel"].str.split(",").str[0]) == {"full span", "all states"}
    full = rob[rob["panel"].str.startswith("full")]
    alt = rob[rob["panel"].str.startswith("all states")]
    assert alt["n_states"].iloc[0] >= full["n_states"].iloc[0]
    assert set(full["measure"]) == set(conv.ROBUSTNESS_MEASURES)


def test_convergence_all_states_line_is_unbalanced():
    inv = lib.convergence()
    line = next(f for f in inv.facts if f.startswith("All available states"))
    counts = [int(n) for n in re.findall(r"\((\d+) states", line)]
    assert counts[0] != counts[1]  # the unbalanced series really changes composition
