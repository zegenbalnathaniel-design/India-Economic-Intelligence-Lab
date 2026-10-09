"""Data validation: generic checks run on every CSV in the evidence ledger.

Checks (one report row per finding):
* duplicate rows (exact) and duplicate keys (state/city/group × period)
* missing cells, as a count — never filled
* period labels that are not valid years, financial years (YYYY-YY with
  consecutive years) or quarters
* names with stray whitespace or that differ only by case/spacing
* impossible values: negative prices/levels/counts, shares above 100%
* suspicious jumps: period-on-period changes within one state/city/
  series far outside that column's usual changes (|robust z| > 8) —
  flagged for review, never removed

Nothing here changes data; the report is shown on the Data page.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from data_sources import registry

ROOT = Path(__file__).resolve().parents[1]
FY = re.compile(r"^(\d{4})-(\d{2})$")
YEAR = re.compile(r"^\d{4}$")
QUARTER = re.compile(r"^(\d{4}-Q[1-4]|[A-Za-z]{3}[- ]\d{4}|\d{4}-\d{2}-\d{2})$")
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
RANGE = re.compile(r"^\d{4}\s*-\s*\d{4}$")
PERIOD_COLS = ("year", "financial_year", "period", "quarter", "reference_period", "fy")
NAME_COLS = ("state", "city", "group", "bank", "asset", "indicator", "series", "metric")
SHARE_HINT = ("share",)
NONNEG_HINT = ("price", "index", "nsdp", "gsdp", "mpce", "count", "adults", "income", "wealth", "level")


def _valid_period(v: str) -> bool:
    v = str(v).strip()
    m = FY.match(v)
    if m and (int(m.group(1)) + 1) % 100 == int(m.group(2)):
        return True
    return bool(YEAR.match(v) or QUARTER.match(v) or MONTH.match(v) or RANGE.match(v))


def _period_order(col: pd.Series) -> pd.Series | None:
    """A sortable key for a period column, or None if it can't be ordered
    reliably (then the jump check is skipped rather than guessed)."""
    vals = col.astype(str).str.strip()
    if vals.str.match(r"^\d{4}(-\d{2})?$").all():
        return vals  # years, financial years (YYYY-YY) and YYYY-MM sort as text
    parsed = pd.to_datetime(vals.str.title(), errors="coerce", format="mixed")
    return parsed if parsed.notna().all() else None


def check_frame(df: pd.DataFrame, source: str) -> list[dict]:
    out = []

    def add(check, severity, detail):
        out.append({"file": source, "check": check, "severity": severity, "detail": detail})

    dup = int(df.duplicated().sum())
    if dup:
        add("duplicate rows", "WARN", f"{dup} exact duplicate row(s)")
    names = [c for c in df.columns if c.lower() in NAME_COLS]
    periods = [c for c in df.columns if c.lower() in PERIOD_COLS]
    if names and periods:
        keys = names[:1] + periods[:1]
        extra = [c for c in df.columns if c.lower() in ("base_year", "unit_size", "series", "indicator") and c not in keys]
        k = int(df.duplicated(subset=keys + extra).sum())
        if k:
            add("duplicate keys", "WARN", f"{k} repeated {'/'.join(keys + extra)} combination(s)")
    miss = int(df.isna().sum().sum())
    if miss:
        cols = ", ".join(f"{c} ({n})" for c, n in df.isna().sum().items() if n)
        add("missing values", "INFO", f"{miss} missing cell(s), kept missing: {cols[:300]}")
    for c in periods:
        vals = df[c].dropna().astype(str)
        if df[c].dtype.kind in "if":
            bad = vals[~vals.str.match(r"^\d{4}(\.0)?$")]
        else:
            bad = vals[~vals.map(_valid_period)]
        if len(bad):
            # Labels with letters ("latest 10 years", "FY2026-27 Apr-Aug") are
            # descriptive windows, not malformed dates.
            descriptive = bad.str.contains(r"[A-Za-z]", regex=True)
            if (~descriptive).any():
                add("period labels", "WARN", f"{c}: {int((~descriptive).sum())} value(s) not a valid year/FY/quarter/"
                    f"month, e.g. {bad[~descriptive].iloc[0]!r}")
            if descriptive.any():
                add("period labels", "INFO", f"{c}: {int(descriptive.sum())} descriptive period label(s), "
                    f"e.g. {bad[descriptive].iloc[0]!r}")
    for c in names:
        vals = df[c].dropna().astype(str)
        ws = vals[vals != vals.str.strip()]
        if len(ws):
            add("name whitespace", "WARN", f"{c}: {ws.nunique()} name(s) with stray spaces, e.g. {ws.iloc[0]!r}")
        norm = vals.str.lower().str.replace(r"[\s&.]+", "", regex=True)
        clash = (pd.DataFrame({"raw": vals, "norm": norm}).drop_duplicates()
                 .groupby("norm")["raw"].nunique())
        if (clash > 1).any():
            add("inconsistent names", "WARN", f"{c}: {int((clash > 1).sum())} name(s) spelled more than one way")
    for c in df.select_dtypes(include="number").columns:
        s = df[c].dropna()
        if s.empty:
            continue
        lc = c.lower()
        if any(h in lc for h in SHARE_HINT) and (s > 100).any():
            add("impossible values", "WARN", f"{c}: {int((s > 100).sum())} share(s) above 100")
        if any(h in lc for h in NONNEG_HINT) and "change" not in lc and "growth" not in lc and "threshold" not in lc \
                and (s < 0).any():
            add("impossible values", "WARN", f"{c}: {int((s < 0).sum())} negative value(s)")
        order = _period_order(df[periods[0]]) if periods else None
        if names and order is not None and c not in periods and "year" not in c.lower():
            # Suspicious jumps: period-on-period % changes within one entity
            # (and one base year, where the table has several), flagged when
            # far outside that column's usual changes.
            grp = [names[0]] + [g for g in df.columns if g.lower() == "base_year"]
            d = df.assign(_order=order)[grp + ["_order", periods[0], c]].dropna(subset=[c, "_order"])
            d = d.sort_values(grp + ["_order"])
            chg = d.groupby(grp)[c].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
            if len(chg) >= 10:
                med = chg.median()
                mad = (chg - med).abs().median()
                if mad > 0:
                    z = 0.6745 * (chg - med) / mad
                    flagged = d.loc[z[z.abs() > 8].index]
                    if len(flagged):
                        ex = flagged.iloc[0]
                        add("suspicious jumps", "INFO",
                            f"{c}: {len(flagged)} period-on-period change(s) far outside the usual range, "
                            f"e.g. {ex[names[0]]} {ex[periods[0]]} — check, not removed")
    if not out:
        add("all checks", "OK", f"{len(df)} rows, {len(df.columns)} columns — no issues found")
    return out


def validate_all() -> pd.DataFrame:
    rows = []
    for d in registry.all_datasets():
        for f in d.files:
            p = ROOT / f
            try:
                df = pd.read_csv(p)
            except Exception as exc:  # unreadable file is itself a finding
                rows.append({"file": f, "check": "read", "severity": "ERROR", "detail": str(exc)[:200]})
                continue
            for r in check_frame(df, f):
                rows.append({"dataset": d.id, **r})
    return pd.DataFrame(rows, columns=["dataset", "file", "check", "severity", "detail"])
