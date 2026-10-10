"""Latest monthly macro prints and the RBI policy rate.

The policy rate is stored as dated *decisions* (data/raw/macro_monthly/
rbi_policy_decisions.csv). The daily and monthly tables are built from
them here, never typed in:

* daily -- the rate in force on each day: the most recent decision whose
  effective date is on or before that day. Days before the earliest
  loaded decision are missing (NaN), not back-filled.
* monthly -- month-end rate and monthly average, reported only for months
  that have ended and whose every day is known.
"""
from __future__ import annotations

import pandas as pd


def value(df: pd.DataFrame, indicator: str, period: str) -> float | None:
    row = df[(df["indicator"] == indicator) & (df["reference_period"] == period)]
    return None if row.empty else float(row["value"].iloc[0])


def row(df: pd.DataFrame, indicator: str, period: str) -> pd.Series | None:
    r = df[(df["indicator"] == indicator) & (df["reference_period"] == period)]
    return None if r.empty else r.iloc[0]


def implied_yoy(current_index: float, year_ago_index: float) -> float:
    """Year-on-year % change implied by two index levels."""
    return (current_index / year_ago_index - 1.0) * 100.0


def latest_decision(decisions: pd.DataFrame) -> pd.Series:
    return decisions.sort_values("effective_date").iloc[-1]


def daily_policy_rate(decisions: pd.DataFrame, start, end) -> pd.Series:
    days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    d = decisions.sort_values("effective_date")
    steps = pd.Series(d["policy_repo_rate_pct"].to_numpy(dtype=float),
                      index=pd.DatetimeIndex(d["effective_date"]))
    steps = steps[~steps.index.duplicated(keep="last")]
    return steps.reindex(steps.index.union(days)).ffill().reindex(days).rename("policy_repo_rate_pct")


def quarter_end_policy_rate(decisions: pd.DataFrame, quarter_ends) -> pd.DataFrame:
    """Repo rate in force at each quarter end, from the decision table.
    A quarter end before the first loaded decision is left blank."""
    q = pd.DatetimeIndex(pd.to_datetime(quarter_ends))
    first = pd.Timestamp(decisions["effective_date"].min())
    daily = daily_policy_rate(decisions, min(first, q.min()), q.max())
    rate = daily.reindex(q)
    rate[q < first] = float("nan")
    return pd.DataFrame({"period": q, "repo_rate": rate.to_numpy()})


def monthly_policy_rate(daily: pd.Series, as_of) -> pd.DataFrame:
    as_of = pd.Timestamp(as_of)
    out = []
    for period, s in daily.groupby(daily.index.to_period("M")):
        month_end = period.to_timestamp(how="end").normalize()
        full_month = len(s) == period.days_in_month
        complete = month_end <= as_of and full_month and s.notna().all()
        out.append({
            "month": str(period),
            "month_end_rate_pct": float(s.iloc[-1]) if complete else None,
            "monthly_avg_rate_pct": float(s.mean()) if complete else None,
            "note": "" if complete else (
                "month not yet ended" if month_end > as_of
                else "earlier decisions not loaded -- some days unknown"),
        })
    return pd.DataFrame(out)


def calendar_status(calendar: pd.DataFrame, today) -> pd.DataFrame:
    today = pd.Timestamp(today).normalize()
    c = calendar.copy()
    c["status"] = ["scheduled" if d > today else "due — enter the value once released"
                   for d in c["scheduled_release_date"]]
    return c
