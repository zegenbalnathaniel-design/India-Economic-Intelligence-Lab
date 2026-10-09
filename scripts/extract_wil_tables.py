"""Extract the India tables from the WIL working paper into data/raw/wil/.

Source: Bharti, Chancel, Piketty & Somanchi (2024), "Income and Wealth
Inequality in India, 1922-2023: The Rise of the Billionaire Raj", World
Inequality Lab Working Paper 2024/09.

Usage:
    pdftotext -layout WorldInequalityLab_WP2024_09_...pdf wil.txt
    python scripts/extract_wil_tables.py wil.txt

Parses Table 2 (income, 2022-23), Table 3 (wealth, 2022-23), Table B.1
(income shares 1951-2022), Table C.1 (wealth shares 1961-2023) and Table
C.2 (very-high-net-worth individuals 1988-2022) from the text layer, so no
number is retyped by hand. Fails loudly if a table's row count changes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "wil"
NUM = r"-?[\d,]+(?:\.\d+)?"


def _n(s: str) -> float:
    return float(s.replace(",", ""))


def _block(lines: list[str], title: str, stop: str) -> list[str]:
    i = next(k for k, l in enumerate(lines) if title in l)
    j = next(k for k in range(i + 1, len(lines)) if stop in lines[k])
    return lines[i:j]


def group_table(lines, title, stop, value_name):
    rows = []
    pat = re.compile(rf"^\s*(Average|Bottom 50%|Middle 40%|Top 10%|Top 1%|incl\. Top 0\.1%|incl\. Top 0\.01%|"
                     rf"incl\. Top 0\.001%)\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")
    for l in _block(lines, title, stop):
        m = pat.match(l)
        if m:
            g = m.group(1).replace("incl. ", "")
            rows.append({"group": g, "adults": int(_n(m.group(2))), f"{value_name}_share_pct": _n(m.group(3)),
                         "threshold_inr": _n(m.group(4)), f"avg_{value_name}_inr": _n(m.group(5)),
                         "ratio_to_average": _n(m.group(6))})
    assert len(rows) == 8, f"{title}: expected 8 rows, got {len(rows)}"
    return pd.DataFrame(rows)


def share_series(lines, title, stop, first_year, last_year):
    rows = []
    pat = re.compile(rf"^\s*(\d{{4}})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")
    for l in _block(lines, title, stop):
        m = pat.match(l)
        if m and first_year <= int(m.group(1)) <= last_year:
            rows.append([int(m.group(1))] + [_n(m.group(k)) for k in range(2, 7)])
    df = pd.DataFrame(rows, columns=["year", "bottom_50", "middle_40", "top_10", "top_1", "top_0_1"])
    df = df.drop_duplicates("year")
    assert df["year"].min() == first_year and df["year"].max() == last_year, title
    return df


def vhnwi(lines):
    rows = []
    pat = re.compile(r"^\s*(\d{4})\s+(\d+)\s+([\d.]+)\s+(\*|\d+)\s+(\*|[\d.]+)\s*$")
    for l in _block(lines, "Table C.2: Growth of very high net worth", "Table C.3"):
        m = pat.match(l)
        if m:
            rows.append({"year": int(m.group(1)), "forbes_count": int(m.group(2)),
                         "forbes_wealth_pct_nni": float(m.group(3)),
                         "hurun_count": None if m.group(4) == "*" else int(m.group(4)),
                         "hurun_wealth_pct_nni": None if m.group(5) == "*" else float(m.group(5))})
    df = pd.DataFrame(rows)
    assert len(df) == 35 and df["year"].min() == 1988 and df["year"].max() == 2022
    return df


def main(txt: str) -> None:
    lines = Path(txt).read_text(encoding="utf-8").splitlines()
    OUT.mkdir(parents=True, exist_ok=True)
    group_table(lines, "Table 2: Income inequality in India, 2022-23", "Notes:", "income") \
        .to_csv(OUT / "table2_income_2022_23.csv", index=False)
    group_table(lines, "Table 3: Wealth inequality in India, 2022-23", "Notes:", "wealth") \
        .to_csv(OUT / "table3_wealth_2022_23.csv", index=False)
    share_series(lines, "Table B.1: Per-adult pre-tax national income shares", "Sources:", 1951, 2022) \
        .to_csv(OUT / "tableB1_income_shares_1951_2022.csv", index=False)
    c1 = share_series(lines, "Table C.1: Per-adult national wealth shares", "Note:", 1961, 2023)
    c1["tentative"] = c1["year"] == 2023  # per the table's own note (Hurun 2023, top 100 only)
    c1.to_csv(OUT / "tableC1_wealth_shares_1961_2023.csv", index=False)
    vhnwi(lines).to_csv(OUT / "tableC2_vhnwi_1988_2022.csv", index=False)
    print("wrote", sorted(p.name for p in OUT.glob("table*.csv")))


if __name__ == "__main__":
    main(sys.argv[1])
