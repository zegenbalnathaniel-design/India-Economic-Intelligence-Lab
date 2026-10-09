"""Tests for analysis/inequality.py and the WIL tables in data/raw/wil/.

Expected values are read off the printed tables of WIL Working Paper
2024/09 (Table 2 and 3 on p. 40, B.1 on pp. 70-71, C.1 on p. 76, C.2 on
p. 77).
"""
from __future__ import annotations

import pandas as pd
import pytest

from analysis import inequality as I
from data_sources import loaders as L


@pytest.fixture(scope="module")
def table():
    return I.group_table(L.load_wil_income_2022(), L.load_wil_wealth_2022())


def row(table, group):
    return table.set_index("group").loc[group]


# --- extracted tables match the printed paper --------------------------------
def test_table2_and_3_spot_values():
    inc = L.load_wil_income_2022().set_index("group")
    assert inc.loc["Average", "avg_income_inr"] == 234551
    assert inc.loc["Middle 40%", "avg_income_inr"] == 165273
    assert inc.loc["Top 0.001%", "ratio_to_average"] == 2068.6
    w = L.load_wil_wealth_2022().set_index("group")
    assert (w.loc["Top 10%", "wealth_share_pct"], w.loc["Middle 40%", "wealth_share_pct"]) == (65.0, 28.6)
    assert w.loc["Top 0.1%", "wealth_share_pct"] == 29.7
    assert w.loc["Bottom 50%", "threshold_inr"] == -41000000  # the AIDIS debt outlier the paper notes


def test_series_cover_the_printed_years():
    b1, c1, c2 = L.load_wil_income_shares(), L.load_wil_wealth_shares(), L.load_wil_vhnwi()
    assert b1["year"].tolist() == list(range(1951, 2023))
    assert c1["year"].tolist() == [1961, 1971, 1981, 1991] + list(range(2002, 2024))
    assert c2["year"].tolist() == list(range(1988, 2023))
    assert b1.set_index("year").loc[1983].tolist() == [21.8, 43.0, 35.3, 10.3, 2.9]
    assert c1.set_index("year").loc[2023, "tentative"] and not c1.set_index("year").loc[2022, "tentative"]
    assert pd.isna(c2.set_index("year").loc[2015, "hurun_count"])  # '*' in the paper stays missing


def test_partitions_and_nesting_hold_every_year():
    for df in (L.load_wil_income_shares(), L.load_wil_wealth_shares()):
        total = df[["bottom_50", "middle_40", "top_10"]].sum(axis=1)
        assert total.between(99.85, 100.15).all()  # one-decimal rounding only
        assert (df["top_0_1"] <= df["top_1"]).all() and (df["top_1"] <= df["top_10"]).all()


def test_2022_row_of_each_series_matches_tables_2_and_3():
    b = L.load_wil_income_shares().set_index("year").loc[2022]
    c = L.load_wil_wealth_shares().set_index("year").loc[2022]
    assert b["middle_40"] == 27.3 and b["top_0_1"] == 9.6
    assert (c["top_10"], c["middle_40"], c["top_0_1"]) == (65.0, 28.6, 29.7)


# --- group table ---------------------------------------------------------------
def test_group_order_and_statuses(table):
    assert table["group"].tolist() == I.GROUPS
    for g in ("Bottom 10%", "Lower middle"):
        r = row(table, g)
        assert pd.isna(r.income_share) and pd.isna(r.wealth_share) and pd.isna(r.avg_income)
        assert r.income_share_status == r.wealth_share_status == I.REQUIRED
    assert row(table, "Top 0.1%").income_share == 9.6
    assert row(table, "Top 0.1%").income_share_status == I.VERIFIED


def test_upper_middle_is_top10_minus_top1(table):
    u = row(table, "Upper middle")
    assert u.income_share == pytest.approx(57.7 - 22.6) and u.income_share_status == I.DERIVED
    assert u.wealth_share == pytest.approx(65.0 - 40.1)
    assert u.avg_income == pytest.approx((10 * 1352985 - 5300549) / 9)
    assert u.avg_wealth == pytest.approx((10 * 8770132 - 54141525) / 9)


def test_partition_sums(table):
    sums = I.partition_sums(table)
    assert sums["income_share"] == pytest.approx(100.0)
    assert sums["wealth_share"] == pytest.approx(100.0)


def test_consistency_gaps(table):
    c = I.consistency_check(table, L.load_wil_income_2022()).set_index("group")
    for g in ("Bottom 50%", "Top 10%", "Top 1%", "Top 0.1%"):
        assert abs(c.loc[g, "gap_pp"]) < 0.25
    # In the paper itself: 40% x 165,273 / 234,551 = 28.2%, printed 27.3%.
    assert c.loc["Middle 40%", "gap_pp"] == pytest.approx(0.886, abs=0.01)


def test_change_between():
    ch = I.change_between(L.load_wil_income_shares(), 1980, 2022).set_index("group")
    assert ch.loc["Top 10%", "change_pp"] == pytest.approx(57.7 - 31.5)
    assert ch.loc["Top 1%", "change_rel_pct"] == pytest.approx((22.6 / 7.3 - 1) * 100)
    with pytest.raises(KeyError):
        I.change_between(L.load_wil_wealth_shares(), 1965, 2022)  # not a survey year


def test_riffle_captions(table):
    caps = I.riffle_captions(table)
    assert len(caps) == 8 and "DATA REQUIRED" in caps[0]
    assert "28.6% of wealth" in caps[3] and "*" not in caps[3]
    assert "35.1% of income*" in caps[4]


def test_fmt_inr():
    assert I.fmt_inr(71163) == "₹71,163"
    assert I.fmt_inr(165273) == "₹1.65 lakh"
    assert I.fmt_inr(22458442) == "₹2.25 crore"
    assert I.fmt_inr(-41000000) == "−₹4.10 crore"
    assert I.fmt_inr(None) == "no data"
