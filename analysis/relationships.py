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
  p-values (`correlations`); OLS slope / intercept / R² / standard errors /
  confidence interval for the slope, fitted values and residuals (`ols`).
- **Time-series only**: lagged correlation over a lag range
  (`lagged_correlation`) and rolling-window correlation
  (`rolling_correlation`), plus a check that the aligned keys are
  consecutive periods (`consecutive_periods`), since both shift by
  *observations*, not by calendar time.

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


def correlations(x, y) -> CorrelationSummary:
    """Pearson (linear) and Spearman (rank) correlation with two-sided
    p-values. NaN when n < MIN_OBS or either variable is constant."""
    xa, ya = _clean_xy(x, y)
    n = int(len(xa))
    nan = float("nan")
    if n < MIN_OBS or np.std(xa) == 0 or np.std(ya) == 0:
        return CorrelationSummary(nan, nan, nan, nan, n)
    pr, pp = stats.pearsonr(xa, ya)
    sr, sp = stats.spearmanr(xa, ya)
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


def consecutive_periods(keys: Sequence) -> bool:
    """True if `keys` (in order) are consecutive periods with no gaps:
    either datetime-like quarter-ends (checked at quarterly frequency) or
    Indian financial-year labels 'YYYY-YY'. Lagged/rolling correlation
    shift by observations, so a gap would silently change their meaning."""
    keys = list(keys)
    if len(keys) < 2:
        return True
    if all(isinstance(k, str) and _FY_RE.match(k) for k in keys):
        starts = [int(_FY_RE.match(k).group(1)) for k in keys]
        return all(b - a == 1 for a, b in zip(starts, starts[1:]))
    try:
        q = pd.PeriodIndex(pd.to_datetime(pd.Series(keys)), freq="Q")
    except (ValueError, TypeError):
        return False
    ordinals = q.asi8
    return bool(np.all(np.diff(ordinals) == 1))


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
