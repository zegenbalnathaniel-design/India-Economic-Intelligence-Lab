"""Economic Relationships — bivariate hypothesis-testing toolkit.

Pure analysis functions (no I/O, no Streamlit) behind the Economic
Relationships Lab page. Everything here operates on DataFrames handed in by
the caller; nothing loads, fetches, imputes or interpolates data.

What this module does, and only this:

- **Alignment** (`align_observations`): an explicit inner join of two
  series on a shared key (state name, quarter-end date, financial year)
  that reports *every* dropped observation and why — excluded aggregate
  rows, keys present in only one source, missing values — and flags keys
  that look like the same entity spelled differently (e.g. "Jammu &
  Kashmir" vs "Jammu and Kashmir") instead of silently joining or silently
  dropping them.
- **Frequency alignment** (`quarterly_to_financial_year`): averages a
  quarterly series within each Indian financial year (April-March), by
  default only for financial years with all four quarters observed.
  Averaging only — never interpolation.
- **Transforms** (`apply_transform`, `transform_pair`): log (only when
  every value is > 0), z-score standardisation, percent change (time
  series only, and only for strictly positive level series).
- **Association statistics**: Pearson and Spearman correlation with
  p-values (`correlations`; exact permutation p-value for Spearman when
  n <= 8, `spearman_exact_p`); OLS slope / intercept / R² / standard
  errors / confidence interval for the slope, fitted values and residuals
  (`ols`).
- **Time-series only**: lagged correlation over a lag range
  (`lagged_correlation`) and rolling-window correlation
  (`rolling_correlation`), plus a check that the aligned keys are
  consecutive periods (`consecutive_periods`, `period_ordinals`), since
  both shift by *observations*, not by calendar time; first differences
  between consecutive periods only (`first_differences`) and a trend check
  that flags spurious-correlation risk (`trend_check`,
  `spurious_trend_warning`, `differencing_outcome`).
- **Verdict and analysis text**: a documented strength/significance
  verdict on Spearman's rho (`verdict`; |rho| < 0.3 weak, 0.3-0.6
  moderate, >= 0.6 strong; alpha = 0.05), leave-one-out influence
  (`influential_observation`), and a 3-6 sentence paragraph generated
  only from the computed numbers (`analysis_sentences`,
  `analysis_paragraph`).

Everything returned is a descriptive statistic of observational data. No
function here identifies a causal effect, and the page that uses this
module says so prominently.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Below this many aligned observations, every statistic on the page is
# flagged as small-sample. State cross-sections in this repository top out
# around 21-31 rows, so they will almost always carry this flag.
SMALL_SAMPLE_THRESHOLD = 20

# Minimum aligned observations for any correlation / regression to be
# computed at all (OLS needs n - 2 >= 1 residual degrees of freedom).
MIN_OBS = 3

TRANSFORM_LABELS: Dict[str, str] = {
    "none": "None (levels)",
    "log": "Natural log",
    "zscore": "Z-score (standardised)",
    "pct_change": "Percent change vs previous period",
}


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def normalise_key(value) -> str:
    """Loose normalisation used *only* to detect probable name mismatches
    (never to join): lower-case, '&' -> 'and', punctuation stripped,
    whitespace collapsed."""
    s = str(value).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


@dataclass
class AlignmentResult:
    """Result of `align_observations`.

    data : columns [key, "x", "y"], one row per key present with a
        non-missing value in *both* sources, sorted by key.
    dropped : columns [key, "reason"], one row per key that appeared in
        either source but is not in `data`.
    possible_name_mismatches : (x-source key, y-source key) pairs that
        differ as written but match after `normalise_key` — reported, NOT
        joined.
    """
    key: str
    data: pd.DataFrame
    dropped: pd.DataFrame
    n_x_source: int
    n_y_source: int
    possible_name_mismatches: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def n(self) -> int:
        return int(len(self.data))

    @property
    def n_dropped(self) -> int:
        return int(len(self.dropped))


def align_observations(
    x_df: pd.DataFrame,
    y_df: pd.DataFrame,
    key: str,
    x_col: str,
    y_col: str,
    *,
    x_label: str = "X",
    y_label: str = "Y",
    exclude: Optional[Mapping[object, str]] = None,
) -> AlignmentResult:
    """Explicit inner join of `x_df[[key, x_col]]` and `y_df[[key, y_col]]`
    on `key`, reporting every dropped observation and the reason.

    `exclude` maps key values to a reason they must never be treated as an
    observation (e.g. {"India": "national aggregate, not a state"}). Keys
    are joined exactly as written; probable spelling mismatches are
    reported in `possible_name_mismatches`, never silently merged.

    Raises ValueError if either source has duplicate keys (the join would
    otherwise be ambiguous) or is missing a required column.
    """
    exclude = dict(exclude or {})
    for df, col, label in ((x_df, x_col, x_label), (y_df, y_col, y_label)):
        for c in (key, col):
            if c not in df.columns:
                raise ValueError(f"{label} source is missing column {c!r}.")

    x = x_df[[key, x_col]].dropna(subset=[key]).rename(columns={x_col: "x"})
    y = y_df[[key, y_col]].dropna(subset=[key]).rename(columns={y_col: "y"})
    for df, label in ((x, x_label), (y, y_label)):
        dup = df[key][df[key].duplicated()].unique().tolist()
        if dup:
            raise ValueError(f"{label} source has duplicate keys: {dup[:5]}")

    dropped: List[dict] = []

    # 1. Explicit exclusions (aggregate rows etc.).
    for k in sorted(set(x[key]).union(set(y[key])) & set(exclude), key=str):
        dropped.append({key: k, "reason": f"excluded: {exclude[k]}"})
    excluded_keys = list(exclude)
    x = x[~x[key].isin(excluded_keys)]
    y = y[~y[key].isin(excluded_keys)]
    n_x_source, n_y_source = int(len(x)), int(len(y))

    x_keys, y_keys = set(x[key]), set(y[key])
    only_x = sorted(x_keys - y_keys, key=str)
    only_y = sorted(y_keys - x_keys, key=str)

    # 2. Probable spelling mismatches between the one-sided keys.
    mismatches: List[Tuple[str, str]] = []
    if only_x and only_y and all(isinstance(k, str) for k in only_x + only_y):
        norm_y: Dict[str, List[str]] = {}
        for k in only_y:
            norm_y.setdefault(normalise_key(k), []).append(k)
        for kx in only_x:
            for ky in norm_y.get(normalise_key(kx), []):
                mismatches.append((kx, ky))
    mismatch_x = {a for a, _ in mismatches}
    mismatch_y = {b for _, b in mismatches}

    for k in only_x:
        if k in mismatch_x:
            partner = next(b for a, b in mismatches if a == k)
            reason = (f"possible name mismatch: {k!r} ({x_label}) vs {partner!r} ({y_label}) "
                      "— not auto-joined")
        else:
            reason = f"not present in {y_label} source"
        dropped.append({key: k, "reason": reason})
    for k in only_y:
        if k in mismatch_y:
            continue  # already reported once, on the X-side row
        dropped.append({key: k, "reason": f"not present in {x_label} source"})

    # 3. Inner join, then drop rows with a missing value on either side.
    merged = x.merge(y, on=key, how="inner", validate="one_to_one")
    for _, row in merged.iterrows():
        missing = [lbl for lbl, v in ((x_label, row["x"]), (y_label, row["y"])) if pd.isna(v)]
        if missing:
            dropped.append({key: row[key], "reason": " and ".join(missing) + " value missing"})
    merged = merged.dropna(subset=["x", "y"])
    merged["x"] = merged["x"].astype(float)
    merged["y"] = merged["y"].astype(float)
    merged = merged.sort_values(key).reset_index(drop=True)

    dropped_df = pd.DataFrame(dropped, columns=[key, "reason"])
    return AlignmentResult(
        key=key, data=merged, dropped=dropped_df,
        n_x_source=n_x_source, n_y_source=n_y_source,
        possible_name_mismatches=mismatches,
    )


# ---------------------------------------------------------------------------
# Frequency alignment (quarterly -> financial year), averaging only
# ---------------------------------------------------------------------------

@dataclass
class FinancialYearAverage:
    """data: columns [financial_year, value, n_quarters]; dropped:
    [financial_year, reason] for financial years excluded as incomplete."""
    data: pd.DataFrame
    dropped: pd.DataFrame


def quarterly_to_financial_year(
    df: pd.DataFrame,
    quarter_col: str,
    value_col: str,
    fy_of_quarter: Callable[[str], str],
    *,
    require_full_year: bool = True,
) -> FinancialYearAverage:
    """Average a quarterly series within each financial year.

    `fy_of_quarter` maps a quarter label to its financial year (for NHB
    RESIDEX labels use `analysis.housing.financial_year_of_quarter`). Only
    non-missing quarterly values count. With `require_full_year=True`
    (default), financial years with fewer than four observed quarters are
    dropped and reported — a partial-year average would mix seasons and is
    not comparable with an annual April-March flow such as NSDP. No value
    is ever interpolated.
    """
    d = df[[quarter_col, value_col]].dropna(subset=[value_col]).copy()
    d["financial_year"] = d[quarter_col].map(fy_of_quarter)
    g = d.groupby("financial_year")
    out = pd.DataFrame({
        "value": g[value_col].mean(),
        "n_quarters": g[quarter_col].nunique(),
    }).reset_index()
    dropped_rows = []
    if require_full_year:
        partial = out[out["n_quarters"] < 4]
        for _, r in partial.iterrows():
            dropped_rows.append({
                "financial_year": r["financial_year"],
                "reason": f"incomplete financial year ({int(r['n_quarters'])} of 4 quarters observed)",
            })
        out = out[out["n_quarters"] >= 4]
    out = out.sort_values("financial_year").reset_index(drop=True)
    return FinancialYearAverage(
        data=out, dropped=pd.DataFrame(dropped_rows, columns=["financial_year", "reason"])
    )


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def available_transforms(values: Iterable[float], *, time_series: bool) -> List[str]:
    """Transforms that are mathematically valid for these values.

    - "log": only if every value is strictly positive.
    - "zscore": only if there are >= 2 values with non-zero spread.
    - "pct_change": time series only, and only for a strictly positive
      level series (percent change of a series that crosses zero — e.g. a
      z-scored index — is meaningless).
    """
    v = np.asarray(list(values), dtype=float)
    v = v[~np.isnan(v)]
    out = ["none"]
    positive = len(v) > 0 and bool(np.all(v > 0))
    if positive:
        out.append("log")
    if len(v) >= 2 and float(np.std(v)) > 0:
        out.append("zscore")
    if time_series and positive and len(v) >= 2:
        out.append("pct_change")
    return out


def apply_transform(values: pd.Series, kind: str) -> pd.Series:
    """Apply one transform. `values` must already be in key order for
    "pct_change" (first value becomes NaN)."""
    s = pd.Series(values, dtype=float)
    if kind == "none":
        return s.copy()
    if kind == "log":
        if (s.dropna() <= 0).any():
            raise ValueError("log transform requires all values > 0.")
        return np.log(s)
    if kind == "zscore":
        sd = s.std(ddof=1)
        if s.notna().sum() < 2 or not np.isfinite(sd) or sd == 0:
            raise ValueError("z-score requires at least 2 values with non-zero spread.")
        return (s - s.mean()) / sd
    if kind == "pct_change":
        if (s.dropna() <= 0).any():
            raise ValueError("percent change requires a strictly positive level series.")
        return (s / s.shift(1) - 1.0) * 100.0
    raise ValueError(f"Unknown transform: {kind!r}")


@dataclass
class TransformedPair:
    """data: columns [key, x_raw, y_raw, x, y] — the analysis sample after
    transforms; dropped: [key, reason] rows lost to a transform."""
    data: pd.DataFrame
    dropped: pd.DataFrame


def transform_pair(aligned: AlignmentResult, x_transform: str, y_transform: str) -> TransformedPair:
    """Apply transforms to an aligned pair.

    Order matters and is fixed: percent change and log first (row-wise),
    then rows made undefined by percent change (the first observation) are
    dropped and reported, and only then are z-scores computed — so a
    z-score is always standardised over exactly the sample being analysed.
    """
    key = aligned.key
    d = aligned.data.sort_values(key).reset_index(drop=True)
    out = pd.DataFrame({key: d[key], "x_raw": d["x"], "y_raw": d["y"]})
    pre = {"x": x_transform, "y": y_transform}
    for col, kind in pre.items():
        out[col] = apply_transform(d[col], kind) if kind in ("log", "pct_change") else d[col].astype(float)
    lost = out[out[["x", "y"]].isna().any(axis=1)]
    dropped = pd.DataFrame(
        [{key: k, "reason": "first observation has no previous period for percent change"} for k in lost[key]],
        columns=[key, "reason"],
    )
    out = out.dropna(subset=["x", "y"]).reset_index(drop=True)
    for col, kind in pre.items():
        if kind == "zscore":
            out[col] = apply_transform(out[col], "zscore")
    return TransformedPair(data=out, dropped=dropped)


# ---------------------------------------------------------------------------
# Correlation and OLS
# ---------------------------------------------------------------------------

def _clean_xy(x, y) -> Tuple[np.ndarray, np.ndarray]:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if xa.shape != ya.shape:
        raise ValueError("x and y must have the same length.")
    mask = ~(np.isnan(xa) | np.isnan(ya))
    return xa[mask], ya[mask]


@dataclass
class CorrelationSummary:
    pearson_r: float
    pearson_p: float
    spearman_rho: float
    spearman_p: float
    n: int


# At or below this n the Spearman p-value is computed exactly by
# enumerating every permutation of the ranks (n! <= 40,320), instead of
# scipy's t-approximation, which is badly anti-conservative for tiny
# samples (it returns p ~ 0 for a perfect rank correlation at n = 5, where
# the exact two-sided p is 2/120 = 0.017).
EXACT_SPEARMAN_MAX_N = 8


def spearman_exact_p(x, y) -> float:
    """Exact two-sided permutation p-value for Spearman's rho: the share of
    the n! orderings of y's ranks whose |rho| is at least the observed
    |rho| (ties keep their average ranks). Only for n <= EXACT_SPEARMAN_MAX_N."""
    from itertools import permutations

    xa, ya = _clean_xy(x, y)
    n = len(xa)
    if n < MIN_OBS or n > EXACT_SPEARMAN_MAX_N:
        raise ValueError(f"exact Spearman p-value is only computed for {MIN_OBS} <= n <= {EXACT_SPEARMAN_MAX_N}.")
    rx = stats.rankdata(xa) - (n + 1) / 2.0
    ry = stats.rankdata(ya)
    perms = ry[np.array(list(permutations(range(n))))]
    perms = perms - perms.mean(axis=1, keepdims=True)
    denom = np.sqrt((rx ** 2).sum() * (perms ** 2).sum(axis=1))
    rhos = perms @ rx / denom
    obs = abs(float(np.dot(rx, ry - ry.mean()) / np.sqrt((rx ** 2).sum() * ((ry - ry.mean()) ** 2).sum())))
    return float(np.mean(np.abs(rhos) >= obs - 1e-12))


def correlations(x, y) -> CorrelationSummary:
    """Pearson (linear) and Spearman (rank) correlation with two-sided
    p-values. NaN when n < MIN_OBS or either variable is constant. For
    n <= EXACT_SPEARMAN_MAX_N the Spearman p-value is the exact permutation
    p-value (`spearman_exact_p`); above that, scipy's t-approximation."""
    xa, ya = _clean_xy(x, y)
    n = int(len(xa))
    nan = float("nan")
    if n < MIN_OBS or np.std(xa) == 0 or np.std(ya) == 0:
        return CorrelationSummary(nan, nan, nan, nan, n)
    pr, pp = stats.pearsonr(xa, ya)
    sr, sp = stats.spearmanr(xa, ya)
    if n <= EXACT_SPEARMAN_MAX_N:
        sp = spearman_exact_p(xa, ya)
    return CorrelationSummary(float(pr), float(pp), float(sr), float(sp), n)


@dataclass
class OLSResult:
    slope: float
    intercept: float
    r_squared: float
    slope_se: float
    intercept_se: float
    slope_t: float
    slope_p: float
    ci_level: float
    slope_ci_low: float
    slope_ci_high: float
    residual_std_error: float
    n: int
    df_resid: int
    fitted: np.ndarray
    residuals: np.ndarray

    @property
    def ok(self) -> bool:
        return bool(np.isfinite(self.slope))


def ols(x, y, ci_level: float = 0.95) -> OLSResult:
    """Simple OLS of y on x with an intercept, classical (homoskedastic)
    standard errors and a t-distribution confidence interval for the slope.

        slope = Sxy / Sxx,  intercept = ȳ − slope·x̄
        s² = Σ e² / (n − 2)
        SE(slope) = √(s² / Sxx),  SE(intercept) = √(s² (1/n + x̄²/Sxx))
        CI = slope ± t_{(1+ci)/2, n−2} · SE(slope)

    Returns all-NaN statistics (with empty fitted/residual arrays) when
    n < MIN_OBS or x has no variation.
    """
    if not 0 < ci_level < 1:
        raise ValueError("ci_level must be in (0, 1).")
    xa, ya = _clean_xy(x, y)
    n = int(len(xa))
    nan = float("nan")
    sxx = float(np.sum((xa - xa.mean()) ** 2)) if n else 0.0
    if n < MIN_OBS or sxx == 0:
        return OLSResult(nan, nan, nan, nan, nan, nan, nan, ci_level, nan, nan, nan, n,
                         max(n - 2, 0), np.array([]), np.array([]))
    xbar, ybar = xa.mean(), ya.mean()
    sxy = float(np.sum((xa - xbar) * (ya - ybar)))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    fitted = intercept + slope * xa
    resid = ya - fitted
    df_resid = n - 2
    ssr = float(np.sum(resid ** 2))
    sst = float(np.sum((ya - ybar) ** 2))
    r2 = 1.0 - ssr / sst if sst > 0 else nan
    s2 = ssr / df_resid
    slope_se = float(np.sqrt(s2 / sxx))
    intercept_se = float(np.sqrt(s2 * (1.0 / n + xbar ** 2 / sxx)))
    if slope_se > 0:
        t_stat = slope / slope_se
        p = float(2 * stats.t.sf(abs(t_stat), df_resid))
    elif slope != 0:  # perfect linear fit: zero residual variance
        t_stat, p = float("inf"), 0.0
    else:
        t_stat, p = nan, nan
    tcrit = float(stats.t.ppf(0.5 + ci_level / 2.0, df_resid))
    return OLSResult(
        slope=float(slope), intercept=float(intercept), r_squared=float(r2),
        slope_se=slope_se, intercept_se=intercept_se, slope_t=float(t_stat), slope_p=p,
        ci_level=ci_level, slope_ci_low=float(slope - tcrit * slope_se),
        slope_ci_high=float(slope + tcrit * slope_se),
        residual_std_error=float(np.sqrt(s2)), n=n, df_resid=df_resid,
        fitted=fitted, residuals=resid,
    )


# ---------------------------------------------------------------------------
# Time-series only: lagged and rolling correlation
# ---------------------------------------------------------------------------

def _corr(xa: np.ndarray, ya: np.ndarray, method: str) -> Tuple[float, float]:
    if len(xa) < MIN_OBS or np.std(xa) == 0 or np.std(ya) == 0:
        return float("nan"), float("nan")
    if method == "pearson":
        r, p = stats.pearsonr(xa, ya)
    elif method == "spearman":
        r, p = stats.spearmanr(xa, ya)
    else:
        raise ValueError(f"Unknown correlation method: {method!r}")
    return float(r), float(p)


def lagged_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    lags: Iterable[int],
    method: str = "pearson",
) -> pd.DataFrame:
    """Correlation of x_t with y_{t+k} for each lag k.

    Convention: **positive k means X leads Y by k periods** (X today is
    paired with Y k periods later); negative k means Y leads X. `df` must
    be sorted in time order; shifting is by *observations*, so the caller
    should check `consecutive_periods` first. Each lag uses only the
    overlapping observations, so n shrinks as |k| grows.

    Returns columns [lag, r, p_value, n].
    """
    x = df[x_col].astype(float).reset_index(drop=True)
    y = df[y_col].astype(float).reset_index(drop=True)
    rows = []
    for k in lags:
        k = int(k)
        ys = y.shift(-k)
        pair = pd.concat([x, ys], axis=1).dropna()
        r, p = _corr(pair.iloc[:, 0].to_numpy(), pair.iloc[:, 1].to_numpy(), method)
        rows.append({"lag": k, "r": r, "p_value": p, "n": int(len(pair))})
    return pd.DataFrame(rows, columns=["lag", "r", "p_value", "n"])


def rolling_correlation(
    df: pd.DataFrame,
    key_col: str,
    x_col: str,
    y_col: str,
    window: int,
    method: str = "pearson",
) -> pd.DataFrame:
    """Correlation over a moving window of `window` consecutive
    observations, labelled by the window's last key. `df` must be in time
    order. Returns columns [key_col, r, window_start]."""
    window = int(window)
    if window < MIN_OBS:
        raise ValueError(f"window must be at least {MIN_OBS}.")
    d = df.reset_index(drop=True)
    rows = []
    for end in range(window - 1, len(d)):
        w = d.iloc[end - window + 1:end + 1]
        r, _ = _corr(w[x_col].to_numpy(dtype=float), w[y_col].to_numpy(dtype=float), method)
        rows.append({key_col: d.loc[end, key_col], "r": r, "window_start": d.loc[end - window + 1, key_col]})
    return pd.DataFrame(rows, columns=[key_col, "r", "window_start"])


_FY_RE = re.compile(r"^(\d{4})-(\d{2})$")


def period_ordinals(keys: Sequence) -> Optional[np.ndarray]:
    """Integer position of each period key on its own calendar, so that
    consecutive periods differ by exactly 1:

    - integer calendar years (WIL tables)        -> the year itself;
    - Indian financial-year labels 'YYYY-YY'     -> the starting year;
    - datetime-like quarter-ends (repo / iBFPI)  -> quarterly period ordinal.

    Returns None when the keys are not recognisably one of these (e.g.
    state names), so callers can tell "not a time series" from "gappy"."""
    keys = list(keys)
    if not keys:
        return np.array([], dtype=np.int64)
    if all(isinstance(k, (int, np.integer)) and not isinstance(k, bool) for k in keys):
        return np.asarray(keys, dtype=np.int64)
    if all(isinstance(k, str) and _FY_RE.match(k) for k in keys):
        return np.asarray([int(_FY_RE.match(k).group(1)) for k in keys], dtype=np.int64)
    if all(isinstance(k, str) for k in keys):
        return None
    try:
        q = pd.PeriodIndex(pd.to_datetime(pd.Series(keys)), freq="Q")
    except (ValueError, TypeError):
        return None
    return np.asarray(q.asi8, dtype=np.int64)


def consecutive_periods(keys: Sequence) -> bool:
    """True if `keys` (in order) are consecutive periods with no gaps:
    integer calendar years, Indian financial-year labels 'YYYY-YY', or
    datetime-like quarter-ends (checked at quarterly frequency).
    Lagged/rolling correlation shift by observations, so a gap would
    silently change their meaning."""
    keys = list(keys)
    if len(keys) < 2:
        return True
    ords = period_ordinals(keys)
    if ords is None:
        return False
    return bool(np.all(np.diff(ords) == 1))


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def sample_size_warning(n: int, threshold: int = SMALL_SAMPLE_THRESHOLD) -> Optional[str]:
    """A plain-language warning when n is small, else None."""
    if n < MIN_OBS:
        return (f"Only {n} aligned observation(s) — too few to compute any correlation or "
                f"regression (minimum {MIN_OBS}).")
    if n < threshold:
        return (f"Small sample: n = {n} (< {threshold}). p-values and confidence intervals "
                "rest on distributional assumptions that are fragile at this size, and one or "
                "two observations can move every statistic substantially.")
    return None


def regression_summary_table(
    corr: CorrelationSummary,
    fit: OLSResult,
    *,
    meta: Optional[Mapping[str, object]] = None,
) -> pd.DataFrame:
    """Two-column (statistic, value) table for display and CSV download.
    `meta` rows (variable names, transforms, sources) come first."""
    rows: List[Tuple[str, object]] = list((meta or {}).items())
    ci = int(round(fit.ci_level * 100))
    rows += [
        ("n (analysis sample)", fit.n),
        ("Pearson r", corr.pearson_r),
        ("Pearson p-value (two-sided)", corr.pearson_p),
        ("Spearman rho", corr.spearman_rho),
        ("Spearman p-value (two-sided)", corr.spearman_p),
        ("OLS slope", fit.slope),
        ("OLS intercept", fit.intercept),
        ("OLS slope standard error", fit.slope_se),
        ("OLS intercept standard error", fit.intercept_se),
        ("OLS slope t-statistic", fit.slope_t),
        ("OLS slope p-value (two-sided)", fit.slope_p),
        (f"OLS slope {ci}% CI lower", fit.slope_ci_low),
        (f"OLS slope {ci}% CI upper", fit.slope_ci_high),
        ("R-squared", fit.r_squared),
        ("Residual standard error", fit.residual_std_error),
        ("Residual degrees of freedom", fit.df_resid),
    ]
    return pd.DataFrame(rows, columns=["statistic", "value"])


# ---------------------------------------------------------------------------
# Verdicts: documented strength thresholds on Spearman's rho
# ---------------------------------------------------------------------------

# |rho| < WEAK_BELOW -> weak; WEAK_BELOW <= |rho| < STRONG_FROM -> moderate;
# |rho| >= STRONG_FROM -> strong. Conventional rules of thumb, stated on the
# page; they describe the size of a rank correlation, not its importance.
WEAK_BELOW = 0.3
STRONG_FROM = 0.6
# Significance level used in every verdict and in the analysis text.
ALPHA = 0.05
# A series "trends" when its Spearman correlation with time has |rho| at
# least this large AND p < ALPHA.
TREND_MIN_RHO = 0.5
# Leave-one-out changes in rho smaller than this are reported as "no single
# observation dominates".
INFLUENCE_NOTABLE = 0.05


def classify_strength(rho: float) -> str:
    """'weak' / 'moderate' / 'strong' by |rho| (thresholds above), or
    'undetermined' when rho is NaN."""
    if rho is None or not np.isfinite(rho):
        return "undetermined"
    a = abs(float(rho))
    if a < WEAK_BELOW:
        return "weak"
    if a < STRONG_FROM:
        return "moderate"
    return "strong"


def classify_direction(rho: float) -> str:
    if rho is None or not np.isfinite(rho):
        return "undetermined"
    if rho > 0:
        return "positive"
    if rho < 0:
        return "negative"
    return "no"


def format_p(p: float) -> str:
    """'p < 0.001', 'p = 0.034' or 'p n/a'."""
    if p is None or not np.isfinite(p):
        return "p n/a"
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


@dataclass
class Verdict:
    """One-line verdict on a Spearman correlation."""
    strength: str
    direction: str
    rho: float
    p: float
    n: int
    significant: bool
    alpha: float = ALPHA

    @property
    def computable(self) -> bool:
        return self.strength != "undetermined"

    @property
    def label(self) -> str:
        if not self.computable:
            return "Not computable"
        if self.direction == "no":
            return "No monotone association"
        return f"{self.strength.capitalize()} {self.direction} association"

    @property
    def stats_text(self) -> str:
        if not self.computable:
            return f"n = {self.n}"
        return f"Spearman ρ = {self.rho:.2f}, {format_p(self.p)}, n = {self.n}"

    @property
    def headline(self) -> str:
        if not self.computable:
            return (f"Not computable (n = {self.n}; at least {MIN_OBS} observations with "
                    "variation in both series are needed)")
        out = f"{self.label} ({self.stats_text})"
        if not self.significant:
            out += f" — not statistically significant at the {self.alpha:.0%} level"
        return out


def verdict(corr: CorrelationSummary, alpha: float = ALPHA) -> Verdict:
    """Verdict from the Spearman rank correlation: strength by the
    documented thresholds, direction by sign, significance at `alpha`."""
    rho, p = corr.spearman_rho, corr.spearman_p
    sig = bool(p is not None and np.isfinite(p) and p < alpha)
    return Verdict(classify_strength(rho), classify_direction(rho), rho, p, corr.n, sig, alpha)


# ---------------------------------------------------------------------------
# Time series: first differences, trend check, differencing outcome
# ---------------------------------------------------------------------------

@dataclass
class DifferencedPair:
    """data: [key, (x_raw, y_raw,) x_level, y_level, x, y] where x and y are
    the period-on-period changes; dropped: [key, reason]."""
    data: pd.DataFrame
    dropped: pd.DataFrame


def first_differences(df: pd.DataFrame, key: str, x_col: str = "x", y_col: str = "y") -> DifferencedPair:
    """Period-on-period changes Δx_t = x_t − x_{t−1}, Δy_t = y_t − y_{t−1}.

    A change is computed only when the previous observation is exactly one
    period earlier on the key's own calendar (`period_ordinals`). The first
    observation, and any observation that follows a gap (e.g. the WIL
    wealth survey years 1961 → 1971), is dropped and reported — a change
    across a gap is never computed and no missing period is interpolated.
    """
    d = df.sort_values(key).reset_index(drop=True)
    ords = period_ordinals(d[key].tolist())
    if ords is None:
        raise ValueError("first differences need period keys (calendar years, 'YYYY-YY' "
                         "financial years or quarter-end dates).")
    rows, dropped = [], []
    for i in range(len(d)):
        k = d.loc[i, key]
        if i == 0:
            dropped.append({key: k, "reason": "first observation — no previous period to take a change from"})
            continue
        gap = int(ords[i] - ords[i - 1])
        if gap != 1:
            dropped.append({key: k, "reason": (f"previous observation ({d.loc[i - 1, key]}) is {gap} periods "
                                                "earlier — no change computed across a gap (no interpolation)")})
            continue
        row = {key: k}
        for extra in ("x_raw", "y_raw"):
            if extra in d.columns:
                row[extra] = d.loc[i, extra]
        row["x_level"] = float(d.loc[i, x_col])
        row["y_level"] = float(d.loc[i, y_col])
        row["x"] = float(d.loc[i, x_col]) - float(d.loc[i - 1, x_col])
        row["y"] = float(d.loc[i, y_col]) - float(d.loc[i - 1, y_col])
        rows.append(row)
    cols = [key] + [c for c in ("x_raw", "y_raw") if c in d.columns] + ["x_level", "y_level", "x", "y"]
    return DifferencedPair(data=pd.DataFrame(rows, columns=cols),
                           dropped=pd.DataFrame(dropped, columns=[key, "reason"]))


@dataclass
class TrendCheck:
    """Spearman correlation of a series with time (gaps respected)."""
    rho: float
    p: float
    n: int
    trending: bool

    @property
    def direction(self) -> str:
        if not self.trending:
            return "none"
        return "upward" if self.rho > 0 else "downward"


def trend_check(keys: Sequence, values, *, alpha: float = ALPHA,
                min_abs_rho: float = TREND_MIN_RHO) -> TrendCheck:
    """Flag a monotone trend: Spearman rho between the series and its
    period position (`period_ordinals`, so a gap counts as elapsed time).
    Trending = p < alpha and |rho| >= min_abs_rho."""
    ords = period_ordinals(list(keys))
    if ords is None:
        raise ValueError("trend_check needs period keys.")
    v = np.asarray(values, dtype=float)
    t = ords.astype(float)
    mask = ~np.isnan(v)
    rho, p = _corr(t[mask], v[mask], "spearman")
    trending = bool(np.isfinite(rho) and np.isfinite(p) and p < alpha and abs(rho) >= min_abs_rho)
    return TrendCheck(rho, p, int(mask.sum()), trending)


def spurious_trend_warning(x_trend: TrendCheck, y_trend: TrendCheck, x_name: str = "X",
                           y_name: str = "Y") -> Optional[str]:
    """A warning string when both series trend, else None."""
    if not (x_trend.trending and y_trend.trending):
        return None
    same = (x_trend.rho > 0) == (y_trend.rho > 0)
    return (f"Both series trend over time ({x_name}: {x_trend.direction}, Spearman ρ with time = "
            f"{x_trend.rho:.2f}; {y_name}: {y_trend.direction}, ρ = {y_trend.rho:.2f}). Two trending "
            "series correlate in levels whether or not they are related — "
            + ("here the shared direction alone would produce a positive levels correlation"
               if same else "here the opposite directions alone would produce a negative levels correlation")
            + ". Compare with the first-difference result before reading anything into the levels figure.")


def differencing_outcome(levels: Verdict, diffs: Verdict) -> str:
    """How a levels association fares in first differences:

    - 'survives'  : same sign and significant in differences;
    - 'weakens'   : same sign, at least moderate, but not significant;
    - 'vanishes'  : weak and not significant in differences (or sign flips
                    without significance);
    - 'reverses'  : opposite sign and significant in differences;
    - 'not_computable' : either side could not be computed.
    """
    if not (levels.computable and diffs.computable) or levels.direction == "no":
        return "not_computable"
    same = np.sign(levels.rho) == np.sign(diffs.rho)
    if diffs.significant:
        return "survives" if same else "reverses"
    if same and diffs.strength != "weak":
        return "weakens"
    return "vanishes"


# ---------------------------------------------------------------------------
# Influence: which single observation matters most
# ---------------------------------------------------------------------------

@dataclass
class Influence:
    loo_key: object          # observation whose removal changes Spearman rho most
    rho_full: float
    rho_without: float
    resid_key: object        # observation with the largest |OLS residual|
    residual: float

    @property
    def delta(self) -> float:
        return float(self.rho_without - self.rho_full)


def influential_observation(keys: Sequence, x, y) -> Optional[Influence]:
    """Leave-one-out Spearman rho for every observation plus the largest
    absolute OLS residual. None if fewer than MIN_OBS + 1 observations (a
    leave-one-out sample must itself be computable)."""
    keys = list(keys)
    xa, ya = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(xa)
    if n < MIN_OBS + 1 or len(keys) != n:
        return None
    full, _ = _corr(xa, ya, "spearman")
    if not np.isfinite(full):
        return None
    best_i, best_rho, best_delta = None, float("nan"), -1.0
    for i in range(n):
        m = np.ones(n, dtype=bool)
        m[i] = False
        r, _ = _corr(xa[m], ya[m], "spearman")
        if np.isfinite(r) and abs(r - full) > best_delta:
            best_i, best_rho, best_delta = i, r, abs(r - full)
    fit = ols(xa, ya)
    if best_i is None or not fit.ok:
        return None
    j = int(np.argmax(np.abs(fit.residuals)))
    return Influence(keys[best_i], float(full), float(best_rho), keys[j], float(fit.residuals[j]))


# ---------------------------------------------------------------------------
# Auto-generated analysis text (every sentence derived from the numbers)
# ---------------------------------------------------------------------------

# Caveat codes a hypothesis can carry, in priority order: the first one that
# applies becomes the "main caveat" sentence. 'small_n' and 'trend' are
# added automatically from the numbers; 'illustrative' is added
# automatically when a variable's status says ILLUSTRATIVE.
CAVEAT_PRIORITY: Tuple[str, ...] = (
    "mechanical", "illustrative", "shared_term", "measurement", "partly_mechanical", "shared_inputs",
    "nominal", "repeated_values", "proxy", "small_n", "trend", "causality",
)
CAVEAT_TEXT: Dict[str, str] = {
    "mechanical": ("the two variables are slices of the same fixed total (the group shares add up to "
                   "100%), so a negative correlation is largely built in by construction and says "
                   "little about economic behaviour"),
    "shared_term": ("the X value also enters the calculation of Y, so measurement error in X pushes the "
                    "correlation in a predictable direction by construction (regression to the mean)"),
    "partly_mechanical": ("both are shares of the same national total, so a gain for one group must "
                          "be matched by losses somewhere else — part of any negative co-movement is "
                          "accounting rather than behaviour"),
    "illustrative": ("at least one series is ILLUSTRATIVE (synthetic), so the result only demonstrates "
                     "the method and says nothing about the real economy"),
    "measurement": ("the two series measure closely related things, so this is a consistency check "
                    "between sources rather than a test of an economic mechanism"),
    "shared_inputs": ("both series are model-based estimates from the same research programme and may "
                      "share inputs and methodological choices, so part of the co-movement could be "
                      "common construction rather than independent evidence"),
    "nominal": ("both series are in current (nominal) prices, so shared inflation and real growth "
                "push them up together regardless of any link between them"),
    "repeated_values": ("several observations share one value of a variable (e.g. every city in a "
                        "state is given that state's figure), so the observations are not independent "
                        "and the effective sample is smaller than n"),
    "proxy": ("one variable stands in for a concept it does not measure directly, so the result "
              "describes the proxy, not the underlying concept"),
    "small_n": ("with only n = {n} observations, one or two points can move every statistic and the "
                "p-value is fragile"),
    "trend": "both series trend over time, so the levels correlation may be largely spurious",
    "causality": ("this is an observational association with no identification strategy, so it cannot "
                  "show that one variable causes the other"),
}


def main_caveat(codes: Iterable[str], *, n: int, statuses: Iterable[str] = (),
                both_trending: bool = False, form: str = "levels") -> Tuple[str, str]:
    """(code, text) of the highest-priority caveat that applies."""
    active = set(codes)
    if any("ILLUSTRATIVE" in str(s).upper() for s in statuses):
        active.add("illustrative")
    if n < SMALL_SAMPLE_THRESHOLD:
        active.add("small_n")
    if both_trending and form == "levels":
        active.add("trend")
    active.add("causality")
    for code in CAVEAT_PRIORITY:
        if code in active:
            return code, CAVEAT_TEXT[code].format(n=n)
    return "causality", CAVEAT_TEXT["causality"]


def fmt_num(v: float) -> str:
    """Compact human formatting used in the generated text."""
    if v is None or not np.isfinite(v):
        return "n/a"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 100:
        return f"{v:.0f}"
    if a >= 1:
        return f"{v:.2f}"
    return f"{v:.3g}"


def _qty(amount: str, unit: str) -> str:
    """'₹10,000 per sq m', '1 percentage point', '0.42 percentage points'."""
    if not unit:
        return amount
    if unit.startswith("₹"):
        return f"₹{amount}{unit[1:]}"
    if amount == "1":
        unit = unit.replace("points", "point", 1).replace("deviations", "deviation", 1)
    return f"{amount} {unit}"


def _effective_unit(unit: str, tf: str) -> str:
    """Unit of one analysed value after a transform."""
    return {"zscore": "standard deviations", "pct_change": "percentage points",
            "log": "log points"}.get(tf, unit)


def _x_scale(b: float, x_sd: Optional[float], min_effect: float) -> float:
    """A power of ten for "each additional <scale> units of X": the order of
    magnitude of X's standard deviation when known (so the step is a
    realistic difference between observations, never more than that);
    otherwise raised until the effect is at least `min_effect`."""
    if x_sd is not None and np.isfinite(x_sd) and x_sd > 0:
        # Never step further than a typical difference between observations.
        return float(10 ** int(np.floor(np.log10(x_sd)))) if x_sd >= 10 else 1.0
    scale = 1.0
    while abs(b * scale) < min_effect and scale < 1e9:
        scale *= 10
    return scale


def _slope_sentence(fit: OLSResult, *, x_name: str, y_name: str, x_unit: str, y_unit: str,
                    x_tf: str, y_tf: str, form: str, period_word: str,
                    x_sd: Optional[float] = None) -> Optional[str]:
    """The OLS slope read in the variables' own units, transform-aware."""
    if not fit.ok:
        return None
    b, lo, hi = fit.slope, fit.slope_ci_low, fit.slope_ci_high
    ci_pct = int(round(fit.ci_level * 100))
    more = "higher" if b > 0 else "lower"
    diff = form == "differences"

    def name_of(name: str, tf: str) -> str:
        base = {"pct_change": f"growth of {name}", "zscore": f"{name} (z-score)",
                "log": f"log {name}"}.get(tf, name)
        return f"the {period_word}-on-{period_word} change in {base}" if diff else base

    if x_tf == "log" and y_tf == "log":
        if diff:
            lead = (f"growth of {x_name} that is 1 percentage point faster goes with growth of {y_name} "
                    f"roughly {abs(b):.2f} percentage points {'faster' if b > 0 else 'slower'}")
        else:
            lead = f"a 1% higher {x_name} goes with {y_name} roughly {abs(b):.2f}% {more}"
        return (f"On the fitted OLS line, {lead} — an elasticity of {b:.2f} "
                f"({ci_pct}% CI {lo:.2f} to {hi:.2f}).")
    if x_tf == "log" and y_tf in ("none", "pct_change") and not diff:
        k = np.log(1.1)
        yu = _effective_unit(y_unit, y_tf)
        return (f"On the fitted OLS line, a 10% higher {x_name} goes with {name_of(y_name, y_tf)} "
                f"{_qty(fmt_num(abs(b * k)), yu)} {more} ({ci_pct}% CI {fmt_num(lo * k)} to "
                f"{fmt_num(hi * k)}).")
    if y_tf == "log" and x_tf in ("none", "pct_change") and not diff:
        scale = _x_scale(b, x_sd, 0.001)
        pct = (np.exp(b * scale) - 1.0) * 100.0
        lo_pct, hi_pct = ((np.exp(v * scale) - 1.0) * 100.0 for v in (lo, hi))
        return (f"On the fitted OLS line, each additional {_qty(f'{scale:,.0f}', _effective_unit(x_unit, x_tf))} "
                f"of {name_of(x_name, x_tf)} goes with {y_name} roughly {abs(pct):.2f}% {more} "
                f"({ci_pct}% CI {lo_pct:+.2f}% to {hi_pct:+.2f}%).")
    # Linear (or mixed / differenced) reading.
    scale = _x_scale(b, x_sd, 0.1)
    xu, yu = _effective_unit(x_unit, x_tf), _effective_unit(y_unit, y_tf)
    if diff:
        bx = {"pct_change": f"growth of {x_name}", "zscore": f"{x_name} (z-score)", "log": f"log {x_name}"}.get(x_tf, x_name)
        by = {"pct_change": f"growth of {y_name}", "zscore": f"{y_name} (z-score)", "log": f"log {y_name}"}.get(y_tf, y_name)
        return (f"On the fitted OLS line, a {period_word} in which {bx} rises by {_qty(f'{scale:,.0f}', xu)} "
                f"more goes with {by} rising by {_qty(fmt_num(abs(b * scale)), yu)} "
                f"{'more' if b > 0 else 'less'} on average ({ci_pct}% CI {fmt_num(lo * scale)} to "
                f"{fmt_num(hi * scale)}).")
    return (f"On the fitted OLS line, each additional {_qty(f'{scale:,.0f}', xu)} of {name_of(x_name, x_tf)} "
            f"goes with {name_of(y_name, y_tf)} {_qty(fmt_num(abs(b * scale)), yu)} {more} on average "
            f"({ci_pct}% CI {fmt_num(lo * scale)} to {fmt_num(hi * scale)}).")


def analysis_sentences(
    *,
    x_name: str,
    y_name: str,
    corr: CorrelationSummary,
    fit: OLSResult,
    obs_noun: str = "observations",
    x_unit: str = "",
    y_unit: str = "",
    x_tf: str = "none",
    y_tf: str = "none",
    form: str = "levels",
    period_word: str = "year",
    time_series: bool = False,
    levels_corr: Optional[CorrelationSummary] = None,
    diff_corr: Optional[CorrelationSummary] = None,
    x_trend: Optional[TrendCheck] = None,
    y_trend: Optional[TrendCheck] = None,
    influence: Optional[Influence] = None,
    caveats: Iterable[str] = (),
    statuses: Iterable[str] = (),
    caveat_note: str = "",
    x_sd: Optional[float] = None,
) -> List[str]:
    """Three to six sentences describing one hypothesis test, built only
    from the numbers passed in (no hard-coded conclusions):

    1. direction and strength (documented thresholds), Pearson vs Spearman;
    2. significance and R²;
    3. the OLS slope in the variables' own units (transform-aware; `x_sd`,
       the spread of the analysed X, sets a realistic step size);
    4. time series only: whether the association survives first-differencing,
       with the trend warning when both series trend;
    5. the most influential observation (leave-one-out) and largest residual;
    6. the main caveat for the pair (mechanical link, illustrative data,
       proxy, small n, trend, ...) with the causality reminder.

    `corr` / `fit` describe the analysed form (`form` = "levels" or
    "differences"); `levels_corr` and `diff_corr` are both forms, for the
    comparison sentence.
    """
    v = verdict(corr)
    n = corr.n
    both_trending = bool(x_trend and y_trend and x_trend.trending and y_trend.trending)
    code, cav = main_caveat(caveats, n=n, statuses=statuses, both_trending=both_trending, form=form)
    cav_sentence = f"Main caveat: {cav}"
    if caveat_note:
        cav_sentence += f"; note also that {caveat_note.rstrip('.')}"
    if code != "causality":
        cav_sentence += "; and, like everything on this page, the association is observational, not causal."
    else:
        cav_sentence += "."

    if not v.computable:
        return [
            f"Only {n} usable {'observation' if n == 1 else obs_noun} "
            f"{'has' if n == 1 else 'have'} values for both {x_name} and {y_name}"
            + (" after differencing" if form == "differences" else "") + ".",
            f"At least {MIN_OBS} observations with variation in both series are needed, so no "
            "correlation, slope or verdict is reported.",
            cav_sentence,
        ]

    out: List[str] = []
    form_phrase = " (measured as period-on-period changes)" if form == "differences" else ""
    if v.direction == "no":
        s1 = (f"Across the {n} {obs_noun}{form_phrase}, {y_name} and {x_name} show no monotone "
              f"association (Spearman ρ = 0.00; Pearson r = {corr.pearson_r:.2f}).")
    else:
        s1 = (f"Across the {n} {obs_noun}{form_phrase}, {y_name} and {x_name} show a {v.strength} "
              f"{v.direction} association (Spearman ρ = {v.rho:.2f}; Pearson r = {corr.pearson_r:.2f}) "
              f"on this page's scale of |ρ| < {WEAK_BELOW} weak, {WEAK_BELOW}–{STRONG_FROM} moderate "
              f"and ≥ {STRONG_FROM} strong")
        if np.isfinite(corr.pearson_r) and abs(abs(corr.pearson_r) - abs(corr.spearman_rho)) > 0.2:
            if abs(corr.pearson_r) < abs(corr.spearman_rho):
                s1 += (", and Pearson being much weaker than Spearman points to outliers or a curved "
                       "but monotone relationship")
            else:
                s1 += (", and Pearson being much stronger than Spearman suggests a few extreme points "
                       "drive the straight-line fit")
        s1 += "."
    out.append(s1)

    y_desc = f"the {period_word}-on-{period_word} change in {y_name}" if form == "differences" else y_name
    r2 = fit.r_squared if fit.ok else float("nan")
    r2_txt = f"R² = {r2:.2f}" if np.isfinite(r2) else "R² n/a"
    if v.significant:
        out.append(f"The association is statistically distinguishable from zero at the {ALPHA:.0%} level "
                   f"({format_p(v.p)}), and a straight line accounts for {r2_txt} of the variation "
                   f"in {y_desc}.")
    else:
        out.append(f"It is not statistically distinguishable from zero at the {ALPHA:.0%} level "
                   f"({format_p(v.p)}), so these data are consistent with no monotone association; "
                   f"a straight line accounts for {r2_txt} of the variation in {y_desc}.")

    slope = _slope_sentence(fit, x_name=x_name, y_name=y_name, x_unit=x_unit, y_unit=y_unit,
                            x_tf=x_tf, y_tf=y_tf, form=form, period_word=period_word, x_sd=x_sd)
    if slope:
        out.append(slope)

    if time_series and levels_corr is not None and diff_corr is not None:
        lv, dv = verdict(levels_corr), verdict(diff_corr)
        outcome = differencing_outcome(lv, dv)
        trend_txt = ""
        if both_trending:
            trend_txt = (f"Both series trend over time (Spearman ρ with time {x_trend.rho:.2f} and "
                         f"{y_trend.rho:.2f}), which makes a levels correlation prone to being spurious; ")
        if outcome == "not_computable":
            body = (f"the first-difference check could not be computed (levels n = {lv.n}, only "
                    f"{dv.n} consecutive-period change(s)), so it is not possible to say whether the "
                    "association survives differencing.")
        else:
            body = (f"in first differences ({period_word}-on-{period_word} changes, n = {dv.n}) "
                    f"Spearman ρ is {dv.rho:.2f} ({format_p(dv.p)}) against {lv.rho:.2f} in levels "
                    f"(n = {lv.n})") + {
                "survives": ", so the association survives differencing — the two series also tend to "
                            "move together from one period to the next, not only along a shared trend.",
                "weakens": ", so the sign holds but the period-to-period evidence is not statistically "
                           "significant — weaker than the levels figure suggests.",
                "vanishes": ", so the association does not survive differencing — the levels figure "
                            "mostly reflects slow-moving trends rather than period-to-period co-movement.",
                "reverses": ", so the sign reverses — period-to-period changes move in the opposite "
                            "direction to the long-run levels relationship.",
            }[outcome]
        if not trend_txt:
            body = body[0].upper() + body[1:]
        out.append(trend_txt + body)

    if influence is not None:
        if abs(influence.delta) < INFLUENCE_NOTABLE:
            s5 = (f"No single observation dominates: dropping any one moves ρ by less than "
                  f"{INFLUENCE_NOTABLE} (the largest change, from removing {influence.loo_key}, is "
                  f"{influence.rho_full:.2f} → {influence.rho_without:.2f})")
        else:
            s5 = (f"The most influential observation is {influence.loo_key}: leaving it out moves ρ from "
                  f"{influence.rho_full:.2f} to {influence.rho_without:.2f}")
        yu = _effective_unit(y_unit, y_tf)
        sign = "+" if influence.residual >= 0 else "−"
        s5 += (f"; the point furthest from the fitted line is {influence.resid_key} "
               f"(residual {sign}{_qty(fmt_num(abs(influence.residual)), yu)}).")
        out.append(s5)

    out.append(cav_sentence)
    return out


def analysis_paragraph(**kwargs) -> str:
    """`analysis_sentences` joined into one paragraph."""
    return " ".join(analysis_sentences(**kwargs))
