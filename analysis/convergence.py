"""State Economy Lab v2 -- convergence statistics, tile-map layout,
comparison-workbench transforms and auto-generated research notes.

Everything here is a pure function of the data handed to it (no file I/O,
no Streamlit). Nothing is estimated, filled or interpolated: a state with
no value at an endpoint is *excluded* from a calculation and listed with
the reason, never given a substitute value.

Contents
--------
1. Panel helpers -- wide state x financial-year frames, balanced panels.
2. Sigma (σ) convergence with a choice of dispersion measure (SD of log
   income, coefficient of variation, Gini, max/min ratio, P90/P10) and a
   stated rule for calling the trend rising / falling / stable.
3. Beta (β) convergence: OLS of average annual log growth on log initial
   income over a user-chosen window, classical or HC1 (White,
   small-sample-scaled) standard errors, t-based 95% CI and p-value,
   implied speed of convergence and half-life. Validated against
   statsmodels in tests/test_convergence.py.
4. Comparison workbench: index to a base year (=100) and year-on-year
   growth, gaps kept as gaps.
5. Schematic tile map: one equal-size tile per state/UT on a grid that
   *approximates* relative geographic position. The grid is a design
   layout written by hand for this page -- it is not data, not to scale
   and does not depict boundaries.
6. Research notes: deterministic sentences built only from the numbers
   computed in 2-3 (and rank changes), split into observed facts,
   statistical results, cautious interpretation and open questions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy import stats

from analysis.states import CANONICAL_STATES, NATIONAL, NON_STATE_ROWS, fiscal_year_start, normalise_state

VALUE_COL = "percapita_nsdp_constant_prices_inr_SPLICED"
SPLICE_BOUNDARY = "2011-12"  # first year published on the 2011-12 base

# ---------------------------------------------------------------------------
# 1. Panel helpers
# ---------------------------------------------------------------------------


def wide_panel(nsdp_long: pd.DataFrame, value_col: str = VALUE_COL) -> pd.DataFrame:
    """state x financial_year (columns in chronological order). Blank
    cells stay NaN."""
    if nsdp_long.empty:
        return pd.DataFrame()
    w = nsdp_long.pivot_table(index="state", columns="financial_year", values=value_col, aggfunc="first",
                              dropna=False)
    cols = sorted(w.columns, key=fiscal_year_start)
    return w.reindex(columns=cols).sort_index()


def years_between(years: Iterable[str], start: str, end: str) -> list[str]:
    """Financial years in [start, end], chronological."""
    y0, y1 = fiscal_year_start(start), fiscal_year_start(end)
    if y1 < y0:
        y0, y1 = y1, y0
    return sorted([y for y in years if y0 <= fiscal_year_start(y) <= y1], key=fiscal_year_start)


def split_balanced(wide: pd.DataFrame, years: list[str]) -> tuple[list[str], pd.DataFrame]:
    """(states with a value in every one of ``years``, DataFrame of
    excluded states with the years they lack)."""
    included, rows = [], []
    for s in wide.index:
        missing = [y for y in years if y not in wide.columns or pd.isna(wide.at[s, y])]
        if missing:
            rows.append({"state": s, "reason": "no value in " + ", ".join(missing)})
        else:
            included.append(s)
    return included, pd.DataFrame(rows, columns=["state", "reason"])


AS_PUBLISHED_BLOCKS = {
    "2004-05": "RBI Table 26 as published, 2004-05 base (2004-05 → 2014-15)",
    "2011-12": "RBI Table 26 as published, 2011-12 base (2011-12 → 2022-23)",
}


def as_published_block(raw: pd.DataFrame, base_year: str) -> tuple[pd.DataFrame, list[str]]:
    """One base-year block of RBI Table 26 exactly as published, in the
    same long shape as the spliced series (state, financial_year, VALUE_COL,
    method), plus notes on what was left out.

    Footnote rows are dropped. Jammu & Kashmir is dropped from both blocks
    so the state universe matches the spliced series: the 2011-12 block
    reports it under two territorial definitions (incl. Ladakh to 2018-19;
    UT from 2019-20) that cannot be joined into one series."""
    if base_year not in AS_PUBLISHED_BLOCKS:
        raise ValueError(f"unknown base year {base_year!r}")
    blk = raw[raw["base_year"] == base_year].copy()
    blk["canon"] = blk["state"].map(normalise_state)
    jk = sorted(blk.loc[blk["canon"] == "Jammu & Kashmir", "state"].unique())
    blk = blk[blk["canon"].notna() & (blk["canon"] != NATIONAL) & (blk["canon"] != "Jammu & Kashmir")]
    out = pd.DataFrame({
        "state": blk["canon"].values,
        "financial_year": blk["financial_year"].values,
        VALUE_COL: pd.to_numeric(blk["percapita_nsdp_constant_prices_inr"], errors="raise").values,
        "method": f"as published ({base_year} base)",
    })
    notes = []
    if jk:
        notes.append("Excluded: " + ", ".join(jk) + " — territory changed in 2019 (RBI reports J&K incl. Ladakh "
                     "to 2018-19 and the J&K UT from 2019-20); dropped so the states match the spliced series.")
    return out.reset_index(drop=True), notes


# ---------------------------------------------------------------------------
# 2. Sigma convergence -- dispersion measures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Measure:
    key: str
    label: str
    unit: str
    formula: str
    reading: str


MEASURES: dict[str, Measure] = {
    "sd_log": Measure(
        "sd_log", "Standard deviation of log income", "log points",
        "σ_t = sqrt( (1/n) · Σ_i (ln y_it − mean_i ln y_it)² )  (population SD, ddof = 0)",
        "The classic Barro & Sala-i-Martin σ. Scale-free: doubling every state's income leaves it unchanged. "
        "0.10 ≈ a typical state is about 10% away from the (geometric) mean.",
    ),
    "cv": Measure(
        "cv", "Coefficient of variation", "%",
        "CV_t = 100 · SD(y_it) / mean(y_it)  (population SD, ddof = 0)",
        "Spread relative to the average, in %. Sensitive to a few very high values (e.g. Goa, Sikkim, Delhi).",
    ),
    "gini": Measure(
        "gini", "Gini coefficient across states (unweighted)", "0–1",
        "G_t = Σ_i Σ_j |y_it − y_jt| / (2 · n² · mean(y_t))",
        "0 = every state has the same per-capita NSDP; values towards 1 = concentrated in a few states. "
        "Each state counts once, whatever its population.",
    ),
    "max_min": Measure(
        "max_min", "Max / min ratio", "×",
        "R_t = max_i y_it / min_i y_it",
        "Richest state's per-capita NSDP as a multiple of the poorest's. Depends only on the two extremes.",
    ),
    "p90_p10": Measure(
        "p90_p10", "P90 / P10 ratio", "×",
        "P90_t / P10_t, percentiles of the cross-state distribution (numpy 'linear' method, Hyndman–Fan type 7)",
        "Less sensitive to a single extreme state than max/min. With ~20–30 states each percentile lies "
        "between two order statistics, so it moves in steps.",
    ),
}

POPULATION_WEIGHTING_CAVEAT = (
    "All dispersion measures here are **unweighted**: Sikkim (≈0.7 million people) counts as much as "
    "Uttar Pradesh (≈200 million). A population-weighted version is **DATA REQUIRED**: it needs a "
    "state population series for every year (e.g. the population figures behind RBI Handbook per-capita "
    "tables, or MoHFW/RGI Technical Group population projections), which this repository does not hold."
)


def _clean(values) -> np.ndarray:
    return np.asarray([float(v) for v in values if v is not None and pd.notna(v)], dtype=float)


def dispersion(values, measure: str) -> float:
    """One cross-sectional dispersion statistic. NaN when fewer than two
    values or a value is non-positive (logs and ratios undefined)."""
    if measure not in MEASURES:
        raise ValueError(f"unknown measure {measure!r}")
    x = _clean(values)
    if len(x) < 2 or (x <= 0).any():
        return float("nan")
    if measure == "sd_log":
        return float(np.std(np.log(x), ddof=0))
    if measure == "cv":
        return float(np.std(x, ddof=0) / x.mean() * 100.0)
    if measure == "gini":
        diffs = np.abs(x[:, None] - x[None, :]).sum()
        return float(diffs / (2.0 * len(x) ** 2 * x.mean()))
    if measure == "max_min":
        return float(x.max() / x.min())
    if measure == "p90_p10":
        return float(np.percentile(x, 90) / np.percentile(x, 10))
    raise AssertionError  # pragma: no cover


STABLE_THRESHOLD_PCT = 5.0


def sigma_rule_text(threshold_pct: float = STABLE_THRESHOLD_PCT) -> str:
    return (
        "Fit an OLS line of the measure on the financial year (start year, e.g. 2004 for 2004-05). "
        "Trend change over the window = slope × number of years in the window, expressed as a % of the "
        f"measure's mean over the window. If its absolute size is below {threshold_pct:g}% → **stable**; "
        "otherwise **falling** (consistent with σ-convergence) when negative and **rising** (σ-divergence) "
        "when positive."
    )


@dataclass
class SigmaResult:
    measure: str
    start: str
    end: str
    balanced: bool
    by_year: pd.DataFrame            # financial_year, value, n_states
    included_states: list[str]
    excluded: pd.DataFrame            # state, reason (balanced panel only)
    slope_per_year: float = float("nan")
    slope_se: float = float("nan")
    slope_p: float = float("nan")
    trend_change: float = float("nan")      # slope × years
    trend_change_pct_of_mean: float = float("nan")
    first_value: float = float("nan")
    last_value: float = float("nan")
    verdict: str = "insufficient data"      # rising / falling / stable / insufficient data
    composition_changes: bool = False
    threshold_pct: float = STABLE_THRESHOLD_PCT


def sigma_dispersion(nsdp_long: pd.DataFrame, start: str, end: str, measure: str = "sd_log",
                     balanced: bool = True, states: Optional[Iterable[str]] = None,
                     value_col: str = VALUE_COL, min_states: int = 5,
                     threshold_pct: float = STABLE_THRESHOLD_PCT) -> SigmaResult:
    """Dispersion of per-capita income across states in every year of
    [start, end] and a classified trend.

    ``balanced=True`` keeps only the states with a value in *every* year of
    the window, so the same states are compared each year. ``balanced=False``
    uses whatever states report each year; ``composition_changes`` is then
    True if that set differs between years (the verdict can be an artefact).
    Years with fewer than ``min_states`` values are dropped."""
    if measure not in MEASURES:
        raise ValueError(f"unknown measure {measure!r}")
    data = nsdp_long if states is None else nsdp_long[nsdp_long["state"].isin(list(states))]
    wide = wide_panel(data, value_col)
    empty = SigmaResult(measure, start, end, balanced, pd.DataFrame(columns=["financial_year", "value", "n_states"]),
                        [], pd.DataFrame(columns=["state", "reason"]), threshold_pct=threshold_pct)
    if wide.empty:
        return empty
    years = years_between(wide.columns, start, end)
    if not years:
        return empty
    if balanced:
        included, excluded = split_balanced(wide, years)
        sub = wide.loc[included, years]
    else:
        sub = wide[years]
        included = [s for s in sub.index if sub.loc[s].notna().any()]
        excluded = pd.DataFrame(columns=["state", "reason"])
    rows, sets = [], []
    for y in years:
        col = sub[y].dropna() if len(sub) else pd.Series(dtype=float)
        if len(col) >= min_states:
            rows.append({"financial_year": y, "value": dispersion(col.values, measure), "n_states": len(col)})
            sets.append(frozenset(col.index))
    by_year = pd.DataFrame(rows, columns=["financial_year", "value", "n_states"])
    res = SigmaResult(measure, start, end, balanced, by_year, included, excluded, threshold_pct=threshold_pct,
                      composition_changes=len(set(sets)) > 1)
    valid = by_year.dropna(subset=["value"])
    if len(valid) < 2:
        return res
    t = np.array([fiscal_year_start(y) for y in valid["financial_year"]], dtype=float)
    v = valid["value"].to_numpy(dtype=float)
    fit = ols(t, v)
    span = t.max() - t.min()
    res.slope_per_year = fit.slope
    res.slope_se = fit.se
    res.slope_p = fit.p
    res.trend_change = fit.slope * span
    mean_level = float(v.mean())
    res.trend_change_pct_of_mean = res.trend_change / mean_level * 100.0 if mean_level else float("nan")
    res.first_value, res.last_value = float(v[0]), float(v[-1])
    res.verdict = classify_trend(res.trend_change_pct_of_mean, threshold_pct)
    return res


def classify_trend(change_pct_of_mean: float, threshold_pct: float = STABLE_THRESHOLD_PCT) -> str:
    if change_pct_of_mean is None or pd.isna(change_pct_of_mean):
        return "insufficient data"
    if abs(change_pct_of_mean) < threshold_pct:
        return "stable"
    return "falling" if change_pct_of_mean < 0 else "rising"


# ---------------------------------------------------------------------------
# 3. Beta convergence
# ---------------------------------------------------------------------------


@dataclass
class OLSFit:
    slope: float
    intercept: float
    se: float
    se_intercept: float
    t: float
    p: float
    ci_low: float
    ci_high: float
    r_squared: float
    n: int
    df_resid: int
    se_type: str


def ols(x, y, robust: bool = False, alpha: float = 0.05) -> OLSFit:
    """Simple OLS y = a + b·x with classical or HC1 standard errors.
    t statistic, two-sided p-value and (1 − alpha) CI use Student's t with
    n − 2 degrees of freedom in both cases (statsmodels: ``use_t=True``)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    nan = float("nan")
    if n < 2 or np.ptp(x) == 0:
        return OLSFit(nan, nan, nan, nan, nan, nan, nan, nan, nan, n, max(n - 2, 0), "HC1" if robust else "classical")
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    df = n - 2
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else nan
    if df <= 0:
        return OLSFit(float(beta[1]), float(beta[0]), nan, nan, nan, nan, nan, nan, r2, n, df,
                      "HC1" if robust else "classical")
    if robust:
        meat = X.T @ (X * (resid ** 2)[:, None])
        cov = xtx_inv @ meat @ xtx_inv * (n / df)
    else:
        cov = xtx_inv * (ss_res / df)
    se_b, se_a = math.sqrt(cov[1, 1]), math.sqrt(cov[0, 0])
    t_stat = beta[1] / se_b if se_b > 0 else nan
    p = float(2 * stats.t.sf(abs(t_stat), df)) if se_b > 0 else nan
    q = stats.t.ppf(1 - alpha / 2, df)
    return OLSFit(float(beta[1]), float(beta[0]), se_b, se_a, float(t_stat), p,
                  float(beta[1] - q * se_b), float(beta[1] + q * se_b), r2, n, df,
                  "HC1" if robust else "classical")


def speed_of_convergence(slope_pct: float, years: float) -> tuple[float, float, str]:
    """Implied speed of convergence λ (per year) and half-life (years) from
    a β slope estimated on growth in % a year.

    With g_i = (1/T)·ln(y_iT / y_i0) = a + b·ln y_i0 and b = slope/100, the
    neoclassical approximation gives b = −(1 − e^(−λT)) / T, so
    λ = −ln(1 + b·T) / T and half-life = ln 2 / λ.
    Returns (NaN, NaN, reason) when slope ≥ 0 or 1 + b·T ≤ 0."""
    nan = float("nan")
    if slope_pct is None or pd.isna(slope_pct) or years is None or years <= 0:
        return nan, nan, "slope or window undefined"
    if slope_pct >= 0:
        return nan, nan, "slope is not negative, so no speed of convergence is implied"
    b = slope_pct / 100.0
    inside = 1.0 + b * years
    if inside <= 0:
        return nan, nan, "1 + b·T ≤ 0 — the formula is undefined for a slope this steep over this window"
    lam = -math.log(inside) / years
    return lam, math.log(2) / lam, ""


SPEED_FORMULA = ("b = slope ÷ 100;  λ = −ln(1 + b·T) ÷ T;  half-life = ln 2 ÷ λ  "
                 "(T = years in the window; from b = −(1 − e^(−λT)) ÷ T)")


@dataclass
class BetaResult:
    start: str
    end: str
    years: int
    per_state: pd.DataFrame       # state, initial_value, final_value, log_initial, avg_annual_growth_pct
    excluded: pd.DataFrame         # state, reason
    fit: Optional[OLSFit]
    speed: float = float("nan")
    half_life: float = float("nan")
    speed_note: str = ""

    @property
    def ok(self) -> bool:
        return self.fit is not None and pd.notna(self.fit.slope)


def beta_window(nsdp_long: pd.DataFrame, start: str, end: str, robust: bool = False,
                states: Optional[Iterable[str]] = None, value_col: str = VALUE_COL,
                min_states: int = 5) -> BetaResult:
    """Unconditional β-convergence over [start, end]:
    growth_i = 100 · (ln y_i,end − ln y_i,start) / T on ln y_i,start.
    A state needs a positive value at *both* endpoints; otherwise it is
    excluded and listed (no nearby year is substituted)."""
    data = nsdp_long if states is None else nsdp_long[nsdp_long["state"].isin(list(states))]
    wide = wide_panel(data, value_col)
    T = fiscal_year_start(end) - fiscal_year_start(start)
    rows, excl = [], []
    for s in (wide.index if not wide.empty else []):
        v0 = wide.at[s, start] if start in wide.columns else np.nan
        v1 = wide.at[s, end] if end in wide.columns else np.nan
        miss = [y for y, v in ((start, v0), (end, v1)) if pd.isna(v)]
        if miss:
            excl.append({"state": s, "reason": "no value in " + " and ".join(miss)})
            continue
        if v0 <= 0 or v1 <= 0:
            excl.append({"state": s, "reason": "non-positive value (log undefined)"})
            continue
        rows.append({"state": s, "initial_value": float(v0), "final_value": float(v1),
                     "log_initial": math.log(v0),
                     "avg_annual_growth_pct": (math.log(v1) - math.log(v0)) / T * 100.0 if T > 0 else np.nan})
    per_state = pd.DataFrame(rows, columns=["state", "initial_value", "final_value", "log_initial",
                                            "avg_annual_growth_pct"])
    excluded = pd.DataFrame(excl, columns=["state", "reason"])
    res = BetaResult(start, end, T, per_state, excluded, None)
    if T <= 0 or len(per_state) < min_states:
        res.speed_note = "insufficient data"
        return res
    res.fit = ols(per_state["log_initial"], per_state["avg_annual_growth_pct"], robust=robust)
    res.speed, res.half_life, res.speed_note = speed_of_convergence(res.fit.slope, T)
    return res


def rank_changes(nsdp_long: pd.DataFrame, start: str, end: str, states: Optional[Iterable[str]] = None,
                 value_col: str = VALUE_COL) -> pd.DataFrame:
    """Rank (1 = highest per-capita NSDP) in the start and end year among
    the states that report *both* years. ``places`` > 0 = moved up."""
    data = nsdp_long if states is None else nsdp_long[nsdp_long["state"].isin(list(states))]
    wide = wide_panel(data, value_col)
    cols = ["state", "rank_start", "rank_end", "places", "n_compared"]
    if wide.empty or start not in wide.columns or end not in wide.columns:
        return pd.DataFrame(columns=cols)
    both = wide[[start, end]].dropna()
    out = pd.DataFrame({
        "state": both.index,
        "rank_start": both[start].rank(ascending=False, method="min").astype(int).values,
        "rank_end": both[end].rank(ascending=False, method="min").astype(int).values,
    })
    out["places"] = out["rank_start"] - out["rank_end"]
    out["n_compared"] = len(out)
    return out.sort_values(["places", "state"], ascending=[False, True]).reset_index(drop=True)[cols]


# ---------------------------------------------------------------------------
# 4. Comparison workbench
# ---------------------------------------------------------------------------


def index_to_base(wide: pd.DataFrame, base_year: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Each state's series ÷ its own base-year value × 100. A state with no
    (or non-positive) base-year value gets an all-NaN row and a reason --
    it is not rebased to some other year."""
    if base_year not in wide.columns:
        return wide * np.nan, {s: f"no {base_year} column" for s in wide.index}
    base = wide[base_year]
    reasons = {}
    out = wide.copy().astype(float)
    for s in wide.index:
        b = base.loc[s]
        if pd.isna(b) or b <= 0:
            out.loc[s] = np.nan
            reasons[s] = f"no value in base year {base_year}"
        else:
            out.loc[s] = wide.loc[s] / b * 100.0
    return out, reasons


def annual_growth(wide: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year % change, (y_t / y_t−1 − 1) × 100, only between
    consecutive financial years that both have a value. The first column
    and any year after a gap are NaN."""
    cols = list(wide.columns)
    out = pd.DataFrame(np.nan, index=wide.index, columns=cols, dtype=float)
    for prev, cur in zip(cols, cols[1:]):
        if fiscal_year_start(cur) - fiscal_year_start(prev) != 1:
            continue
        a, b = wide[prev].astype(float), wide[cur].astype(float)
        ok = a.notna() & b.notna() & (a > 0)
        out.loc[ok, cur] = (b[ok] / a[ok] - 1.0) * 100.0
    return out


# ---------------------------------------------------------------------------
# 5. Schematic tile map
# ---------------------------------------------------------------------------

# (row, col): row 0 = north, col 0 = west. Hand-made design layout that
# keeps neighbours roughly adjacent; it is NOT derived from coordinates,
# not to scale, and says nothing about boundaries. Every canonical state/UT
# in analysis.states.CANONICAL_STATES has exactly one tile.
TILE_GRID: dict[str, tuple[int, int]] = {
    "Jammu & Kashmir": (0, 2), "Ladakh": (0, 3),
    "Punjab": (1, 1), "Chandigarh": (1, 2), "Himachal Pradesh": (1, 3),
    "Rajasthan": (2, 1), "Haryana": (2, 2), "Delhi": (2, 3), "Uttarakhand": (2, 4),
    "Arunachal Pradesh": (2, 7),
    "Gujarat": (3, 1), "Madhya Pradesh": (3, 2), "Uttar Pradesh": (3, 3), "Bihar": (3, 4),
    "Sikkim": (3, 5), "Assam": (3, 6), "Nagaland": (3, 7),
    "Dadra & Nagar Haveli and Daman & Diu": (4, 1), "Maharashtra": (4, 2), "Chhattisgarh": (4, 3),
    "Jharkhand": (4, 4), "West Bengal": (4, 5), "Meghalaya": (4, 6), "Manipur": (4, 7),
    "Goa": (5, 1), "Karnataka": (5, 2), "Telangana": (5, 3), "Odisha": (5, 4),
    "Tripura": (5, 6), "Mizoram": (5, 7),
    "Lakshadweep": (6, 0), "Kerala": (6, 1), "Tamil Nadu": (6, 2), "Andhra Pradesh": (6, 3),
    "Andaman & Nicobar Islands": (6, 6),
    "Puducherry": (7, 2),
}

# Short labels drawn on the tiles (page convention, not an official code list).
TILE_ABBR: dict[str, str] = {
    "Jammu & Kashmir": "JK", "Ladakh": "LA", "Punjab": "PB", "Chandigarh": "CH", "Himachal Pradesh": "HP",
    "Rajasthan": "RJ", "Haryana": "HR", "Delhi": "DL", "Uttarakhand": "UK", "Arunachal Pradesh": "AR",
    "Gujarat": "GJ", "Madhya Pradesh": "MP", "Uttar Pradesh": "UP", "Bihar": "BR", "Sikkim": "SK",
    "Assam": "AS", "Nagaland": "NL", "Dadra & Nagar Haveli and Daman & Diu": "DNH",
    "Maharashtra": "MH", "Chhattisgarh": "CG", "Jharkhand": "JH", "West Bengal": "WB",
    "Meghalaya": "ML", "Manipur": "MN", "Goa": "GA", "Karnataka": "KA", "Telangana": "TS",
    "Odisha": "OD", "Tripura": "TR", "Mizoram": "MZ", "Lakshadweep": "LD", "Kerala": "KL",
    "Tamil Nadu": "TN", "Andhra Pradesh": "AP", "Andaman & Nicobar Islands": "AN", "Puducherry": "PY",
}

TILE_CAPTION = "Schematic tile map — tiles are not to scale and do not depict boundaries."


def tile_coverage(names: Iterable[object]) -> tuple[dict[str, str], list[str]]:
    """({raw name: tile state}, [names with no tile]). National rows and
    known footnote rows are ignored; anything else that does not resolve
    to a tile is reported, never guessed."""
    matched, unmatched = {}, []
    for n in names:
        if not isinstance(n, str) or not n.strip() or n.strip() in NON_STATE_ROWS:
            continue
        canon = normalise_state(n)
        if canon == NATIONAL:
            continue
        if canon is not None and canon in TILE_GRID:
            matched[n] = canon
        else:
            unmatched.append(n)
    return matched, sorted(set(unmatched))


def tile_frame(values: dict[str, float], extra: Optional[dict[str, dict]] = None,
               ascending: bool = False) -> pd.DataFrame:
    """One row per tile: state, abbr, row, col, value (NaN = no data),
    rank among tiles with data (1 = highest unless ``ascending``),
    n_reporting, plus any per-state ``extra`` fields. ``values`` keys may be
    raw names; they are normalised and must resolve to a tile."""
    norm = {}
    for k, v in values.items():
        c = normalise_state(k)
        if c is None or c not in TILE_GRID:
            raise ValueError(f"state name without a tile: {k!r}")
        norm[c] = v
    rows = []
    for s, (r, c) in TILE_GRID.items():
        v = norm.get(s, np.nan)
        row = {"state": s, "abbr": TILE_ABBR[s], "row": r, "col": c,
               "value": float(v) if v is not None and pd.notna(v) else np.nan}
        if extra and s in extra:
            row.update(extra[s])
        rows.append(row)
    df = pd.DataFrame(rows)
    has = df["value"].notna()
    df["rank"] = df["value"].rank(ascending=ascending, method="min")
    df["n_reporting"] = int(has.sum())
    return df


# ---------------------------------------------------------------------------
# 6. Research notes
# ---------------------------------------------------------------------------


def _fmt_list(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _places(k) -> str:
    k = int(k)
    return f"{k} place" if k == 1 else f"{k} places"


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return "p n/a"
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def fmt_measure(value: float, measure: str) -> str:
    if pd.isna(value):
        return "n/a"
    if measure == "cv":
        return f"{value:.1f}%"
    if measure in ("max_min", "p90_p10"):
        return f"{value:.2f}×"
    return f"{value:.3f}"


def research_notes(beta: BetaResult, sigma: SigmaResult, ranks: pd.DataFrame, alpha: float = 0.05,
                   n_extremes: int = 3) -> dict[str, list[str]]:
    """Deterministic, descriptive notes from computed results only.
    Keys: observed, statistical, interpretation, questions."""
    obs, st_, interp, qs = [], [], [], []
    window = f"{beta.start} → {beta.end}"
    crosses_splice = (fiscal_year_start(beta.start) < fiscal_year_start(SPLICE_BOUNDARY)
                      <= fiscal_year_start(beta.end))

    # Observed facts ------------------------------------------------------
    ps = beta.per_state.dropna(subset=["avg_annual_growth_pct"]).sort_values(
        ["avg_annual_growth_pct", "state"], ascending=[False, True])
    if len(ps):
        k = min(n_extremes, len(ps))
        top = [f"{r.state} ({r.avg_annual_growth_pct:.2f}%)" for r in ps.head(k).itertuples()]
        bottom = [f"{r.state} ({r.avg_annual_growth_pct:.2f}%)" for r in ps.tail(k).iloc[::-1].itertuples()]
        obs.append(
            f"Over {window} ({beta.years} years), among the {len(ps)} states/UTs with real per-capita NSDP at "
            f"both ends, the fastest average annual growth (log-difference ÷ years) was in {_fmt_list(top)}; "
            f"the slowest in {_fmt_list(bottom)}."
        )
        spread = ps["avg_annual_growth_pct"].max() - ps["avg_annual_growth_pct"].min()
        obs.append(f"The gap between the fastest and slowest grower is {spread:.2f} percentage points a year.")
    if len(beta.excluded):
        obs.append(f"{len(beta.excluded)} state(s)/UT(s) are left out of the growth comparison for lack of a value "
                   f"at an endpoint: {_fmt_list(sorted(beta.excluded['state']))}.")
    if len(ranks):
        moved = ranks[ranks["places"] != 0]
        n = int(ranks["n_compared"].iloc[0])
        if moved.empty:
            obs.append(f"No state changed rank between {beta.start} and {beta.end} among the {n} compared.")
        else:
            up = moved.sort_values(["places", "state"], ascending=[False, True]).iloc[0]
            down = moved.sort_values(["places", "state"], ascending=[True, True]).iloc[0]
            if up["places"] > 0:
                obs.append(f"Biggest rank gain: {up['state']}, from {int(up['rank_start'])} to "
                           f"{int(up['rank_end'])} of {n} (+{_places(up['places'])}).")
            if down["places"] < 0:
                obs.append(f"Biggest rank fall: {down['state']}, from {int(down['rank_start'])} to "
                           f"{int(down['rank_end'])} of {n} (−{_places(-down['places'])}).")
    m = MEASURES[sigma.measure]
    if sigma.verdict != "insufficient data":
        panel_txt = (f"balanced panel of {len(sigma.included_states)} states/UTs"
                     if sigma.balanced else "all reporting states (unbalanced — composition varies)")
        obs.append(f"{m.label} went from {fmt_measure(sigma.first_value, sigma.measure)} in "
                   f"{sigma.by_year['financial_year'].iloc[0]} to {fmt_measure(sigma.last_value, sigma.measure)} in "
                   f"{sigma.by_year['financial_year'].iloc[-1]} ({panel_txt}).")

    # Statistical results -------------------------------------------------
    beta_sig = None
    if beta.ok:
        f = beta.fit
        beta_sig = pd.notna(f.p) and f.p < alpha
        st_.append(
            f"β regression ({f.se_type} SE): slope = {f.slope:+.3f} (SE {f.se:.3f}), 95% CI "
            f"[{f.ci_low:+.3f}, {f.ci_high:+.3f}], {fmt_p(f.p)}, n = {f.n}, R² = {f.r_squared:.3f}. "
            f"The slope is {'statistically significant' if beta_sig else 'not statistically significant'} "
            f"at the {alpha:.0%} level."
        )
        if pd.notna(beta.speed):
            st_.append(f"Implied speed of convergence λ = {beta.speed * 100:.2f}% a year; half-life = "
                       f"{beta.half_life:.1f} years (λ = −ln(1 + b·T)/T, b = slope/100, T = {beta.years}).")
        else:
            st_.append(f"No speed of convergence or half-life computed: {beta.speed_note}.")
    else:
        st_.append("β regression not estimated: fewer than 5 states with values at both ends of the window.")
    if sigma.verdict != "insufficient data":
        st_.append(
            f"σ trend ({m.label}): OLS slope {sigma.slope_per_year:+.4f} {m.unit} per year; trend change over the "
            f"window = {sigma.trend_change_pct_of_mean:+.1f}% of the mean level → **{sigma.verdict}** under the "
            f"±{sigma.threshold_pct:g}% rule (trend slope {fmt_p(sigma.slope_p)}; consecutive years are not "
            "independent, so treat this p-value as indicative only)."
        )
    else:
        st_.append("σ trend not computed: fewer than 2 years with at least 5 states in the selected panel.")

    # Interpretation (cautious, non-causal) -------------------------------
    if beta.ok:
        f = beta.fit
        if f.slope < 0 and beta_sig:
            interp.append("Initially poorer states grew faster on average over this window — a pattern "
                          "*consistent with* unconditional β-convergence. It is an association, not evidence "
                          "of why.")
        elif f.slope < 0:
            interp.append("The slope is negative but its 95% CI includes zero, so this sample cannot "
                          "distinguish catch-up from no relationship between initial income and growth.")
        elif f.slope > 0 and beta_sig:
            interp.append("Initially richer states grew faster on average — the opposite of β-convergence "
                          "(descriptive only).")
        else:
            interp.append("There is no clear relationship between initial income and later growth in this "
                          "window.")
        if pd.notna(f.r_squared) and f.r_squared < 0.3:
            interp.append(f"Initial income accounts for only {f.r_squared:.0%} of the cross-state variation in "
                          "growth (R²); most of it is unrelated to the starting level.")
    if sigma.verdict in ("rising", "falling", "stable") and beta.ok:
        if beta.fit.slope < 0 and beta_sig and sigma.verdict != "falling":
            interp.append(f"β and σ point different ways (dispersion {sigma.verdict}). β-convergence is "
                          "necessary but not sufficient for σ-convergence: catch-up by some poorer states can "
                          "coexist with a spread that does not narrow.")
        elif sigma.verdict == "falling" and (beta.fit.slope < 0 and beta_sig):
            interp.append("β and σ agree: poorer states caught up on average and the cross-state spread "
                          "narrowed.")
        elif sigma.verdict == "rising":
            interp.append("The cross-state spread widened over the window (σ-divergence on this measure).")
    if not sigma.balanced and sigma.composition_changes:
        interp.append("The dispersion series mixes different sets of states in different years, so part of its "
                      "movement may reflect coverage rather than incomes.")
    if crosses_splice:
        interp.append(f"The window crosses {SPLICE_BOUNDARY}: values before it are 2004-05-base figures × a "
                      "per-state link factor, so growth across the boundary depends on that derived factor.")
    interp.append("All results are descriptive statistics of an unweighted cross-section of states and are "
                  "not causal estimates.")

    # Questions for further research --------------------------------------
    if len(ps):
        qs.append(f"Does the β result hold without the fastest-growing state ({ps.iloc[0]['state']}) or the "
                  "smallest economies, whose growth rates are volatile?")
    if len(ranks) and not ranks[ranks["places"] > 0].empty:
        up = ranks.sort_values(["places", "state"], ascending=[False, True]).iloc[0]
        qs.append(f"What accounts for {up['state']}'s rise of {_places(up['places'])} — sector mix, "
                  "investment, or measurement (base-year change)?")
    qs.append("Is convergence *conditional* on structure? Testing that needs state GVA by sector (RBI Handbook) "
              "and PLFS employment by industry — DATA REQUIRED, not in this repository.")
    qs.append("Would a population-weighted dispersion measure tell the same story? DATA REQUIRED: a state "
              "population series for every year.")
    if sigma.balanced and len(sigma.excluded):
        qs.append(f"Would the {len(sigma.excluded)} state(s)/UT(s) left out of the balanced panel "
                  f"({_fmt_list(sorted(sigma.excluded['state']))}) change the σ verdict once their missing years "
                  "are published?")
    return {"observed": obs, "statistical": st_, "interpretation": interp, "questions": qs}


__all__ = [
    "VALUE_COL", "MEASURES", "dispersion", "sigma_dispersion", "SigmaResult", "classify_trend",
    "sigma_rule_text", "ols", "OLSFit", "beta_window", "BetaResult", "speed_of_convergence", "SPEED_FORMULA",
    "rank_changes", "index_to_base", "annual_growth", "TILE_GRID", "TILE_ABBR", "TILE_CAPTION",
    "tile_coverage", "tile_frame", "research_notes", "wide_panel", "years_between", "split_balanced",
    "POPULATION_WEIGHTING_CAVEAT", "CANONICAL_STATES", "as_published_block", "AS_PUBLISHED_BLOCKS",
]
