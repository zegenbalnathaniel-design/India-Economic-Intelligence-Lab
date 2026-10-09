"""Tests for analysis/macro_monthly.py and the monthly release files."""
from __future__ import annotations

import pandas as pd
import pytest

from analysis import macro_monthly as M
from data_sources import loaders as L


def decisions(rows):
    return pd.DataFrame(rows, columns=["effective_date", "policy_repo_rate_pct"]).assign(
        effective_date=lambda d: pd.to_datetime(d["effective_date"]))


def test_daily_rate_steps_and_no_backfill():
    d = decisions([("2026-10-07", 5.50)])
    s = M.daily_policy_rate(d, "2026-10-01", "2026-10-09")
    assert s.loc["2026-10-01":"2026-10-06"].isna().all()
    assert (s.loc["2026-10-07":] == 5.50).all()


def test_daily_rate_uses_latest_effective_decision():
    d = decisions([("2026-01-01", 5.25), ("2026-10-07", 5.50)])
    s = M.daily_policy_rate(d, "2026-10-05", "2026-10-08")
    assert s.tolist() == [5.25, 5.25, 5.50, 5.50]


def test_monthly_only_for_complete_known_months():
    d = decisions([("2026-01-01", 5.25), ("2026-10-07", 5.50)])
    daily = M.daily_policy_rate(d, "2026-09-01", "2026-10-31")
    m = M.monthly_policy_rate(daily, as_of="2026-10-09").set_index("month")
    assert m.loc["2026-09", "month_end_rate_pct"] == 5.25
    assert m.loc["2026-09", "monthly_avg_rate_pct"] == pytest.approx(5.25)
    assert pd.isna(m.loc["2026-10", "monthly_avg_rate_pct"]) and "not yet ended" in m.loc["2026-10", "note"]
    later = M.monthly_policy_rate(daily, as_of="2026-11-15").set_index("month")
    assert later.loc["2026-10", "monthly_avg_rate_pct"] == pytest.approx((6 * 5.25 + 25 * 5.50) / 31)


def test_partial_month_without_earlier_decisions_is_not_averaged():
    daily = M.daily_policy_rate(decisions([("2026-10-07", 5.50)]), "2026-10-01", "2026-10-31")
    m = M.monthly_policy_rate(daily, as_of="2026-11-30")
    assert pd.isna(m.iloc[0]["monthly_avg_rate_pct"]) and "not loaded" in m.iloc[0]["note"]


def test_loaded_files_are_consistent():
    df = L.load_macro_monthly()
    assert not df.duplicated(["indicator", "reference_period"]).any()
    assert set(df["status"]) <= {"VERIFIED", "PARTIAL"}
    # IIP: the two index levels imply the published 8.0% y/y (to rounding).
    yoy = M.implied_yoy(M.value(df, "IIP_GENERAL_INDEX", "2026-08"), M.value(df, "IIP_GENERAL_INDEX", "2025-08"))
    assert yoy == pytest.approx(M.value(df, "IIP_GENERAL_YOY", "2026-08"), abs=0.1)
    assert set(df.loc[df["indicator"].str.startswith("IIP"), "base"]) == {"2022-23=100"}
    dec = M.latest_decision(L.load_rbi_policy_decisions())
    assert dec["policy_repo_rate_pct"] - dec["previous_rate_pct"] == pytest.approx(dec["change_bp"] / 100)


def test_calendar_never_becomes_an_observation():
    cal = M.calendar_status(L.load_release_calendar(), "2026-10-09")
    assert cal.iloc[0]["status"] == "scheduled"
    assert M.value(L.load_macro_monthly(), "CPI_COMBINED_YOY", "2026-09") is None
    assert M.calendar_status(L.load_release_calendar(), "2026-10-13").iloc[0]["status"].startswith("due")
