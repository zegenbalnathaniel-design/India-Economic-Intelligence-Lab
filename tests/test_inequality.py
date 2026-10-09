"""Tests for analysis/inequality.py against the WIL files in data/raw/wil/."""
from __future__ import annotations

import pandas as pd
import pytest

from analysis import inequality as I
from data_sources import loaders as L


@pytest.fixture(scope="module")
def table():
    return I.group_table(L.load_wil_distribution(), L.load_wil_facts())


def row(table, group):
    return table.set_index("group").loc[group]


def test_groups_bottom_to_top(table):
    assert table["group"].tolist() == [
        "Bottom 10%", "Lower middle", "Bottom 50%", "Middle 40%",
        "Upper middle", "Top 10%", "Top 1%", "Top 0.1%",
    ]


def test_stated_values_pass_through_unchanged(table):
    b = row(table, "Bottom 50%")
    assert (b.income_share_pct, b.wealth_share_pct, b.avg_income_inr) == (15.0, 6.4, 71163)
    assert b.income_share_status == b.wealth_share_status == I.STATED
    t = row(table, "Top 1%")
    assert (t.income_share_pct, t.wealth_share_pct) == (22.6, 40.1)


def test_missing_tiers_are_data_required_not_zero(table):
    for g in ("Bottom 10%", "Lower middle"):
        r = row(table, g)
        assert pd.isna(r.income_share_pct) and pd.isna(r.wealth_share_pct) and pd.isna(r.avg_income_inr)
        assert r.income_share_status == r.wealth_share_status == I.REQUIRED


def test_middle_40_derived_as_remainder(table):
    m = row(table, "Middle 40%")
    assert m.income_share_pct == pytest.approx(27.3) and m.income_share_status == I.DERIVED
    assert m.wealth_share_pct == pytest.approx(29.0) and m.wealth_share_status == I.DERIVED
    assert "100 −" in m.income_share_formula


def test_upper_middle_is_top10_minus_top1(table):
    u = row(table, "Upper middle")
    assert u.income_share_pct == pytest.approx(57.7 - 22.6)
    assert u.wealth_share_pct == pytest.approx(64.6 - 40.1)
    assert u.avg_income_inr == pytest.approx((10 * 1353000 - 5300000) / 9)
    assert u.avg_income_status == I.DERIVED


def test_partitions_sum_to_100(table):
    sums = I.partition_sums(table)
    assert sums["income_share_pct"] == pytest.approx(100.0)
    assert sums["wealth_share_pct"] == pytest.approx(100.0)


def test_multiples_of_average(table):
    assert row(table, "Bottom 50%").multiple_of_average == pytest.approx(71163 / 235000)
    assert row(table, "Top 1%").multiple_of_average == pytest.approx(53e5 / 235000)


def test_consistency_gaps_are_small_for_stated_shares(table):
    c = I.consistency_check(table, L.load_wil_facts()).set_index("group")
    for g in ("Bottom 50%", "Top 10%", "Top 1%"):
        assert abs(c.loc[g, "gap_pp"]) < 0.25
    # Known: the Middle 40% average (Rs 1,65,273 per coverage of the paper's
    # table) implies ~28.1%, not the paper's 27.3% -- surfaced on the page.
    assert 0.5 < c.loc["Middle 40%", "gap_pp"] < 1.0


def test_wealth_change_1961_to_2022(  ):
    w = I.wealth_change(L.load_wil_wealth_shares()).set_index("group")
    assert w.loc["Top 10%", "change_pp"] == pytest.approx(19.7)
    assert w.loc["Top 0.1%", "ratio"] == pytest.approx(29.0 / 3.2)
    assert w.loc["Middle 40%", "share_1961_pct"] == pytest.approx(43.7)
    assert w.loc["Middle 40%", "status_1961"] == I.DERIVED
    assert pd.isna(w.loc["Top 1%", "share_1961_pct"]) and w.loc["Top 1%", "status_1961"] == I.REQUIRED


def test_riffle_captions_one_per_card(table):
    caps = I.riffle_captions(table)
    assert len(caps) == 8
    assert "DATA REQUIRED" in caps[0] and "DATA REQUIRED" in caps[1]
    assert "15.0% of income" in caps[2] and "*" not in caps[2]
    assert "27.3% of income*" in caps[3]  # derived values are starred


def test_fmt_inr():
    assert I.fmt_inr(71163) == "₹71,163"
    assert I.fmt_inr(165000) == "₹1.65 lakh"
    assert I.fmt_inr(22500000) == "₹2.25 crore"
    assert I.fmt_inr(None) == "no data"
