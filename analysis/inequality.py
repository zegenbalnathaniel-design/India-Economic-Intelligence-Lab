"""India's income and wealth distribution by group (World Inequality Lab).

Works only from the tables of Bharti, Chancel, Piketty & Somanchi (2024),
WIL Working Paper 2024/09, as extracted into data/raw/wil/ (see
data_sources.loaders and scripts/extract_wil_tables.py). Every value this
module returns for a group carries a status:

* VERIFIED      -- printed in the paper's tables.
* DERIVED       -- arithmetic on VERIFIED numbers only, with the formula
                   recorded alongside (e.g. Upper middle = Top 10% - Top 1%).
* DATA REQUIRED -- the paper gives no number; nothing is filled in.
"""
from __future__ import annotations

import pandas as pd

VERIFIED, DERIVED, REQUIRED = "VERIFIED", "DERIVED", "DATA REQUIRED"

# Bottom card to top card on the Wealth Lab's Riffle figure.
GROUPS = ["Bottom 10%", "Lower middle", "Bottom 50%", "Middle 40%",
          "Upper middle", "Top 10%", "Top 1%", "Top 0.1%"]
RANGES = {"Bottom 10%": "P0–P10", "Lower middle": "P10–P50", "Bottom 50%": "P0–P50",
          "Middle 40%": "P50–P90", "Upper middle": "P90–P99", "Top 10%": "P90–P100",
          "Top 1%": "P99–P100", "Top 0.1%": "P99.9–P100"}
POP = {"Bottom 10%": 10, "Lower middle": 40, "Bottom 50%": 50, "Middle 40%": 40,
       "Upper middle": 9, "Top 10%": 10, "Top 1%": 1, "Top 0.1%": 0.1}

# Table B.1 / C.1 column -> display name.
SERIES = {"bottom_50": "Bottom 50%", "middle_40": "Middle 40%", "top_10": "Top 10%",
          "top_1": "Top 1%", "top_0_1": "Top 0.1%"}


def _lookup(table: pd.DataFrame, group: str, col: str) -> float | None:
    r = table.loc[table["group"] == group, col]
    return None if r.empty or pd.isna(r.iloc[0]) else float(r.iloc[0])


def average(table: pd.DataFrame, col: str) -> float:
    v = _lookup(table, "Average", col)
    if v is None:
        raise ValueError(f"the table's 'Average' row has no {col}")
    return v


def group_table(income: pd.DataFrame, wealth: pd.DataFrame) -> pd.DataFrame:
    """One row per group in GROUPS order, from Tables 2 and 3.

    Upper middle (P90-P99) is DERIVED as Top 10% minus Top 1%; Bottom 10%
    and Lower middle (P10-P50) are DATA REQUIRED (not in the paper).
    """
    avg_inc = average(income, "avg_income_inr")
    measures = {  # key -> (table, column)
        "avg_income": (income, "avg_income_inr"),
        "income_share": (income, "income_share_pct"),
        "avg_wealth": (wealth, "avg_wealth_inr"),
        "wealth_share": (wealth, "wealth_share_pct"),
    }
    out = []
    for g in GROUPS:
        row = {"group": g, "percentile_range": RANGES[g], "population_share_pct": POP[g]}
        for key, (tbl, col) in measures.items():
            value, status, formula = None, REQUIRED, ""
            if g == "Upper middle":
                t10, t1 = _lookup(tbl, "Top 10%", col), _lookup(tbl, "Top 1%", col)
                if t10 is not None and t1 is not None:
                    if key.startswith("avg_"):
                        value, formula = (10 * t10 - 1 * t1) / 9, "(10 × Top 10% avg − 1 × Top 1% avg) ÷ 9"
                    else:
                        value, formula = round(t10 - t1, 1), f"Top 10% ({t10}) − Top 1% ({t1})"
                    status = DERIVED
            else:
                v = _lookup(tbl, g, col)
                if v is not None:
                    value, status = v, VERIFIED
            row[key] = value
            row[f"{key}_status"] = status
            row[f"{key}_formula"] = formula
        row["multiple_of_average"] = None if row["avg_income"] is None else row["avg_income"] / avg_inc
        out.append(row)
    return pd.DataFrame(out)


def consistency_check(table: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    """Income share implied by (population share × group avg ÷ overall avg)
    vs the printed share. Gaps measure how far the paper's own averages and
    shares agree."""
    avg = average(income, "avg_income_inr")
    t = table.dropna(subset=["avg_income", "income_share"]).copy()
    t["implied_income_share_pct"] = t["population_share_pct"] * t["avg_income"] / avg
    t["gap_pp"] = t["implied_income_share_pct"] - t["income_share"]
    return t[["group", "income_share", "income_share_status", "implied_income_share_pct", "gap_pp"]]


def partition_sums(table: pd.DataFrame) -> dict[str, float]:
    """Bottom 50% + Middle 40% + Top 10% should add to 100 for each share."""
    part = table[table["group"].isin(["Bottom 50%", "Middle 40%", "Top 10%"])]
    return {c: float(part[c].sum()) for c in ("income_share", "wealth_share")}


def shares_long(series: pd.DataFrame) -> pd.DataFrame:
    """Table B.1 / C.1 wide -> long: year, group, share_pct (+ tentative)."""
    cols = [c for c in SERIES if c in series.columns]
    keep = ["year"] + (["tentative"] if "tentative" in series.columns else [])
    long = series.melt(id_vars=keep, value_vars=cols, var_name="col", value_name="share_pct")
    long["group"] = long["col"].map(SERIES)
    return long.drop(columns="col")


def change_between(series: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Each group's share in `start` and `end`, with the percentage-point
    and relative change (DERIVED from two printed values)."""
    s = series.set_index("year")
    if start not in s.index or end not in s.index:
        raise KeyError(f"year {start} or {end} not in the table")
    rows = []
    for col, name in SERIES.items():
        a, b = float(s.loc[start, col]), float(s.loc[end, col])
        rows.append({"group": name, "start_year": start, "start_pct": a, "end_year": end, "end_pct": b,
                     "change_pp": round(b - a, 1), "change_rel_pct": (b / a - 1) * 100})
    return pd.DataFrame(rows)


def fmt_inr(x: float | None) -> str:
    """Indian-style short form: ₹71,163 · ₹1.65 lakh · ₹2.25 crore."""
    if x is None or pd.isna(x):
        return "no data"
    sign = "−" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        return f"{sign}₹{x / 1e7:,.2f} crore"
    if x >= 1e5:
        return f"{sign}₹{x / 1e5:.2f} lakh"
    return f"{sign}₹{x:,.0f}"


def riffle_captions(table: pd.DataFrame) -> list[str]:
    """Eight captions, bottom card to top, for the Wealth Lab's Riffle
    figure. A trailing * marks a DERIVED value."""
    caps = []
    for r in table.itertuples():
        head = f"{r.percentile_range} · {r.group}"
        if pd.isna(r.income_share) and pd.isna(r.wealth_share) and pd.isna(r.avg_income):
            caps.append(f"{head}\nDATA REQUIRED — not in the WIL tables")
            continue
        star = lambda status: "*" if status == DERIVED else ""
        parts = []
        if not pd.isna(r.income_share):
            parts.append(f"{r.income_share:.1f}% of income{star(r.income_share_status)}")
        if not pd.isna(r.wealth_share):
            parts.append(f"{r.wealth_share:.1f}% of wealth{star(r.wealth_share_status)}")
        if not pd.isna(r.avg_income):
            parts.append(f"avg {fmt_inr(r.avg_income)}/yr{star(r.avg_income_status)}")
        caps.append(f"{head}\n" + " · ".join(parts))
    return caps


# ---------------------------------------------------------------------------
# Distributional Gini from group shares
# ---------------------------------------------------------------------------
def lorenz_points(bottom_50: float, middle_40: float, top_1: float, top_0_1: float) -> list[tuple[float, float]]:
    """Lorenz-curve points (population share, cumulative share), both 0-1,
    from the group shares in percent. Top 10% is implied by the partition."""
    b, m, t1, t01 = (x / 100 for x in (bottom_50, middle_40, top_1, top_0_1))
    return [(0.0, 0.0), (0.5, b), (0.9, b + m), (0.99, 1 - t1), (0.999, 1 - t01), (1.0, 1.0)]


def gini_lower_bound(bottom_50: float, middle_40: float, top_1: float, top_0_1: float) -> float:
    """Gini of the piecewise-linear Lorenz curve through the group shares.

    Joining the known points with straight lines treats everyone inside a
    group as equal, so this is a LOWER BOUND on the true Gini (it ignores
    inequality within each group). Uses only the published shares.
    """
    pts = lorenz_points(bottom_50, middle_40, top_1, top_0_1)
    area = sum((x1 - x0) * (y0 + y1) / 2 for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
    return 1 - 2 * area


def gini_series(series: pd.DataFrame) -> pd.DataFrame:
    """Lower-bound Gini for every year of Table B.1 or C.1 (DERIVED)."""
    out = series[["year"]].copy()
    out["gini_lower_bound"] = [
        gini_lower_bound(r.bottom_50, r.middle_40, r.top_1, r.top_0_1) for r in series.itertuples()
    ]
    if "tentative" in series.columns:
        out["tentative"] = series["tentative"].to_numpy()
    return out


def redistribute(shares: dict[str, float], pp: float) -> dict[str, float]:
    """Scenario: move `pp` percentage points of the total from the Top 1% to
    the Bottom 50%. The Top 0.1% gives up the same fraction of its share as
    the Top 1% as a whole (an assumption: the cut is proportional within
    the Top 1%). Returns new shares in percent; raises if pp exceeds the
    Top 1% share."""
    if pp < 0 or pp > shares["top_1"]:
        raise ValueError("pp must be between 0 and the Top 1% share.")
    frac = pp / shares["top_1"] if shares["top_1"] else 0.0
    return {
        "bottom_50": shares["bottom_50"] + pp,
        "middle_40": shares["middle_40"],
        "top_10": shares["top_10"] - pp,
        "top_1": shares["top_1"] - pp,
        "top_0_1": shares["top_0_1"] * (1 - frac),
    }
