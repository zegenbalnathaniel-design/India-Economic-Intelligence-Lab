"""India's income and wealth distribution by group (World Inequality Lab).

Works only from the three WIL files in data/raw/wil/ (see
data_sources.loaders). Every value this module returns carries a status:

* STATED        -- a number given exactly in the source summary.
* DERIVED       -- arithmetic on STATED numbers only, with the formula
                   recorded alongside (e.g. Middle 40% income share =
                   100 - Bottom 50% - Top 10%).
* DATA REQUIRED -- the source gives no number; nothing is filled in.

Approximate statements in the source ("about 29%") are never turned into
numbers here.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

STATED, DERIVED, REQUIRED = "STATED", "DERIVED", "DATA REQUIRED"

# The overall average the group multiples are measured against.
AVG_INCOME_METRIC = ("Average adult income", "2022-23")


@dataclass(frozen=True)
class Cell:
    value: float | None
    status: str
    formula: str = ""


def _num(x) -> float | None:
    return None if pd.isna(x) else float(x)


def average_income(facts: pd.DataFrame) -> float:
    row = facts[(facts["metric"] == AVG_INCOME_METRIC[0]) & (facts["period"] == AVG_INCOME_METRIC[1])]
    if row.empty:
        raise ValueError("average adult income for 2022-23 is missing from long_run_facts.csv")
    return float(row["value"].iloc[0])


def group_table(dist: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    """One row per group, bottom to top, with value/status for each measure.

    Adds the user-defined tiers the source does not report directly:
    Bottom 10% and Lower middle (DATA REQUIRED) and Upper middle, P90-P99
    (DERIVED as Top 10% minus Top 1%).
    """
    d = dist.set_index("group")
    avg = average_income(facts)

    def stated(group: str, col: str) -> Cell:
        v = _num(d.loc[group, col]) if group in d.index else None
        return Cell(v, STATED) if v is not None else Cell(None, REQUIRED)

    b50, t10, t1 = "Bottom 50%", "Top 10%", "Top 1%"
    rows: dict[str, dict[str, Cell]] = {}
    for g in ("Bottom 10%", "Lower middle"):
        rows[g] = {k: Cell(None, REQUIRED) for k in ("avg_income", "income_share", "wealth_share")}

    rows[b50] = {k: stated(b50, c) for k, c in
                 (("avg_income", "avg_annual_income_inr"), ("income_share", "income_share_pct"),
                  ("wealth_share", "wealth_share_pct"))}

    m40 = {"avg_income": stated("Middle 40%", "avg_annual_income_inr")}
    for key, col in (("income_share", "income_share_pct"), ("wealth_share", "wealth_share_pct")):
        direct = stated("Middle 40%", col)
        if direct.value is not None:
            m40[key] = direct
            continue
        a, b = stated(b50, col).value, stated(t10, col).value
        m40[key] = (Cell(round(100 - a - b, 1), DERIVED, f"100 − Bottom 50% ({a}) − Top 10% ({b})")
                    if a is not None and b is not None else Cell(None, REQUIRED))
    rows["Middle 40%"] = m40

    up = {}
    for key, col in (("income_share", "income_share_pct"), ("wealth_share", "wealth_share_pct")):
        a, b = stated(t10, col).value, stated(t1, col).value
        up[key] = (Cell(round(a - b, 1), DERIVED, f"Top 10% ({a}) − Top 1% ({b})")
                   if a is not None and b is not None else Cell(None, REQUIRED))
    a, b = stated(t10, "avg_annual_income_inr").value, stated(t1, "avg_annual_income_inr").value
    up["avg_income"] = (Cell((10 * a - 1 * b) / 9, DERIVED, "(10 × Top 10% avg − 1 × Top 1% avg) ÷ 9")
                        if a is not None and b is not None else Cell(None, REQUIRED))
    rows["Upper middle"] = up

    for g in (t10, t1, "Top 0.1%"):
        rows[g] = {k: stated(g, c) for k, c in
                   (("avg_income", "avg_annual_income_inr"), ("income_share", "income_share_pct"),
                    ("wealth_share", "wealth_share_pct"))}
    t01 = rows["Top 0.1%"]
    if t01["income_share"].value is None and t01["avg_income"].value is not None:
        t01["income_share"] = Cell(round(0.1 * t01["avg_income"].value / avg, 1), DERIVED,
                                   "0.1% × (Top 0.1% avg ÷ overall avg) — from rounded averages, ±0.2 pp")

    ranges = {"Bottom 10%": "P0–P10", "Lower middle": "P10–P50", "Bottom 50%": "P0–P50",
              "Middle 40%": "P50–P90", "Upper middle": "P90–P99", "Top 10%": "P90–P100",
              "Top 1%": "P99–P100", "Top 0.1%": "P99.9–P100"}
    pops = {"Bottom 10%": 10, "Lower middle": 40, "Bottom 50%": 50, "Middle 40%": 40,
            "Upper middle": 9, "Top 10%": 10, "Top 1%": 1, "Top 0.1%": 0.1}
    out = []
    for g, cells in rows.items():
        inc = cells["avg_income"].value
        out.append({
            "group": g, "percentile_range": ranges[g], "population_share_pct": pops[g],
            "avg_income_inr": inc, "avg_income_status": cells["avg_income"].status,
            "avg_income_formula": cells["avg_income"].formula,
            "multiple_of_average": None if inc is None else inc / avg,
            "income_share_pct": cells["income_share"].value,
            "income_share_status": cells["income_share"].status,
            "income_share_formula": cells["income_share"].formula,
            "wealth_share_pct": cells["wealth_share"].value,
            "wealth_share_status": cells["wealth_share"].status,
            "wealth_share_formula": cells["wealth_share"].formula,
        })
    return pd.DataFrame(out)


def consistency_check(table: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    """Income share implied by (population share × group avg ÷ overall avg)
    vs the stated/derived share. Small gaps come from rounded averages;
    a large gap would mean a transcription error."""
    avg = average_income(facts)
    t = table.dropna(subset=["avg_income_inr", "income_share_pct"]).copy()
    t["implied_income_share_pct"] = t["population_share_pct"] * t["avg_income_inr"] / avg
    t["gap_pp"] = t["implied_income_share_pct"] - t["income_share_pct"]
    return t[["group", "income_share_pct", "income_share_status", "implied_income_share_pct", "gap_pp"]]


def partition_sums(table: pd.DataFrame) -> dict[str, float]:
    """Bottom 50% + Middle 40% + Top 10% must add to 100 for each share."""
    part = table[table["group"].isin(["Bottom 50%", "Middle 40%", "Top 10%"])]
    return {c: float(part[c].sum()) for c in ("income_share_pct", "wealth_share_pct")}


def wealth_change(shares: pd.DataFrame) -> pd.DataFrame:
    """1961 vs 2022-23 wealth shares, with the Middle 40% derived as the
    remainder in each year when both other partition groups are stated."""
    s = shares.set_index("group")
    out = []
    for g in s.index:
        v61, v22 = _num(s.loc[g, "wealth_share_1961_pct"]), _num(s.loc[g, "wealth_share_2022_23_pct"])
        st61 = st22 = STATED
        if g == "Middle 40%":
            def rem(col):
                a, b = _num(s.loc["Bottom 50%", col]), _num(s.loc["Top 10%", col])
                return None if a is None or b is None else round(100 - a - b, 1)
            if v61 is None:
                v61, st61 = rem("wealth_share_1961_pct"), DERIVED
            if v22 is None:
                v22, st22 = rem("wealth_share_2022_23_pct"), DERIVED
        if v61 is None:
            st61 = REQUIRED
        if v22 is None:
            st22 = REQUIRED
        out.append({
            "group": g, "share_1961_pct": v61, "status_1961": st61,
            "share_2022_23_pct": v22, "status_2022_23": st22,
            "change_pp": None if v61 is None or v22 is None else round(v22 - v61, 1),
            "ratio": None if v61 is None or v22 is None or v61 == 0 else v22 / v61,
        })
    return pd.DataFrame(out)


def fmt_inr(x: float | None) -> str:
    """Indian-style short form: ₹71,163 · ₹1.65 lakh · ₹2.25 crore."""
    if x is None or pd.isna(x):
        return "no data"
    if x >= 1e7:
        return f"₹{x / 1e7:.2f} crore"
    if x >= 1e5:
        return f"₹{x / 1e5:.2f} lakh"
    return f"₹{x:,.0f}"


def riffle_captions(table: pd.DataFrame) -> list[str]:
    """Eight captions, bottom card to top, for the Wealth Lab's Riffle
    figure. Order matches the table (Bottom 10% ... Top 0.1%)."""
    caps = []
    for r in table.itertuples():
        head = f"{r.percentile_range} · {r.group}"
        if pd.isna(r.income_share_pct) and pd.isna(r.wealth_share_pct) and pd.isna(r.avg_income_inr):
            caps.append(f"{head}\nDATA REQUIRED — not in the WIL summary")
            continue
        parts = []
        for val, status, what in ((r.income_share_pct, r.income_share_status, "of income"),
                                  (r.wealth_share_pct, r.wealth_share_status, "of wealth")):
            if not pd.isna(val):
                parts.append(f"{val:.1f}% {what}" + ("*" if status == DERIVED else ""))
        if not pd.isna(r.avg_income_inr):
            parts.append(f"avg {fmt_inr(r.avg_income_inr)}/yr" + ("*" if r.avg_income_status == DERIVED else ""))
        caps.append(f"{head}\n" + " · ".join(parts))
    return caps
