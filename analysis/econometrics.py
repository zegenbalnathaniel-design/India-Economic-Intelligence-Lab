"""Econometrics workbench — pure calculations (no I/O, no Streamlit).

Backs the "Regression workbench" mode of the Economic Relationships Lab.
Everything here operates on DataFrames handed in by the caller; nothing
loads, fetches, imputes or interpolates data. A value that is missing, or a
transform that is undefined for an observation (a log of a non-positive
number, a change across a gap), drops that observation — and every drop is
reported with its reason.

What this module does:

- **Transforms** (`transform_options`, `transform_series`): level, natural
  log (only when every value is > 0), first difference and percent change
  (time series only, computed only between *consecutive* periods), and a
  lag of k = 1..3 periods (time series only). Applied to each variable on
  its own calendar before the join, so a gap in one variable never removes
  a usable change in another.
- **Multi-variable alignment** (`align_design`): an explicit inner join of
  one dependent and one or more explanatory variables on a shared key, with
  a sample-period filter for time series, reporting every dropped key and
  why (excluded / tentative row, not present in a source, value missing,
  transform undefined, outside the sample period) and flagging probable
  name mismatches instead of joining them.
- **Association**: pairwise Pearson and Spearman correlations
  (`pairwise_correlations`, reusing `analysis.relationships.correlations`).
- **OLS** (`fit_ols`) via statsmodels: coefficients, SE, t, p, 95% CI,
  R², adjusted R², F-test, n, df, with classical, HC1 or Newey–West HAC
  standard errors (`newey_west_lags` states the lag rule).
- **Diagnostics**: Breusch–Pagan, Jarque–Bera, Durbin–Watson,
  Breusch–Godfrey, VIF, ADF (with a small-n warning instead of a verdict),
  a spurious-regression check, residual/QQ plot data — each with a
  plain-language interpretation.
- **Text**: coefficient interpretation in the variables' own units
  (elasticity / semi-elasticity wording for logs, never causal), a model
  fit summary, assumptions & limitations, a correlation-vs-causation note.
- **Exports**: regression table, aligned data with units/status, and a
  JSON reproducibility record of every setting and library version.

No function here identifies a causal effect. Panel and causal-inference
methods are deliberately out of scope.
"""
from __future__ import annotations

import json
import math
import platform
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from analysis import relationships as rel

ALPHA = rel.ALPHA
CI_LEVEL = 0.95

TRANSFORMS: Tuple[str, ...] = ("level", "log", "diff", "pct_change")
TRANSFORM_LABELS: Dict[str, str] = {
    "level": "Level",
    "log": "Natural log",
    "diff": "First difference (Δ, change on previous period)",
    "pct_change": "% change on previous period",
}
TRANSFORM_SHORT: Dict[str, str] = {"level": "", "log": "log ", "diff": "Δ ", "pct_change": "% chg "}
TS_ONLY_TRANSFORMS = ("diff", "pct_change")
MAX_LAG = 3

SE_LABELS: Dict[str, str] = {
    "nonrobust": "classical (homoskedastic)",
    "HC1": "HC1 heteroskedasticity-robust",
    "HAC": "Newey–West HAC (heteroskedasticity- and autocorrelation-robust)",
}

# ADF below this many consecutive observations: statistics are shown but no
# verdict is given (the test has very little power and its critical values
# are asymptotic approximations).
ADF_MIN_N = 20
# Below this many observations the ADF regression is not run at all.
ADF_MIN_COMPUTE = 8
# Jarque–Bera relies on asymptotic chi-square critical values.
JB_SMALL_N = 30
VIF_HIGH = 10.0
VIF_NOTABLE = 5.0
DW_LOW, DW_HIGH = 1.5, 2.5


class ModelError(ValueError):
    """The requested model cannot be estimated on this sample (too few
    observations, perfect multicollinearity, a constant regressor...)."""


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def transform_options(values: Iterable[float], *, time_series: bool) -> Dict[str, Optional[str]]:
    """Every transform in TRANSFORMS mapped to None when it is available for
    these values, or to the plain-language reason it is disabled.

    - log: every non-missing value must be strictly positive;
    - first difference: time series only;
    - % change: time series only, and only for a strictly positive series
      (a percent change of a series that crosses or touches zero is
      meaningless).
    """
    v = np.asarray([x for x in values if x is not None], dtype=float)
    v = v[np.isfinite(v)]
    out: Dict[str, Optional[str]] = {"level": None}
    nonpos = int(np.sum(v <= 0))
    if len(v) == 0:
        out["log"] = "no observed values"
    elif nonpos:
        out["log"] = (f"{nonpos} of {len(v)} values are ≤ 0 (minimum {v.min():,.4g}); "
                      "the natural log is undefined for them")
    else:
        out["log"] = None
    if not time_series:
        out["diff"] = "only for time series"
        out["pct_change"] = "only for time series"
    else:
        out["diff"] = None if len(v) >= 2 else "needs at least two observations"
        if len(v) < 2:
            out["pct_change"] = "needs at least two observations"
        elif nonpos:
            out["pct_change"] = (f"{nonpos} of {len(v)} values are ≤ 0; percent change needs a "
                                 "strictly positive series")
        else:
            out["pct_change"] = None
    return out


def available_transforms(values: Iterable[float], *, time_series: bool) -> List[str]:
    return [k for k, why in transform_options(values, time_series=time_series).items() if why is None]


def term_name(short: str, tf: str, lag: int = 0) -> str:
    """Display name of a transformed variable, e.g. 'log GCF (t−1)'."""
    base = {"level": short, "log": f"log {short}", "diff": f"Δ {short}",
            "pct_change": f"% change in {short}"}[tf]
    return f"{base} (t−{lag})" if lag else base


@dataclass
class TransformedSeries:
    """data: [key, value, source_key, source_value] — `value` is the
    transformed (and lagged) value at `key`; `source_key`/`source_value`
    are the period and raw level it was computed from. undefined: [key,
    reason] for observed keys whose transformed value cannot be computed."""
    data: pd.DataFrame
    undefined: pd.DataFrame


def _is_int_key(k) -> bool:
    return isinstance(k, (int, np.integer)) and not isinstance(k, bool)


def transform_series(keys: Sequence, values: Sequence[float], tf: str, lag: int = 0, *,
                     time_series: bool, period_word: str = "year") -> TransformedSeries:
    """Transform one variable on its own calendar.

    Missing values must already have been removed (the caller reports
    them). For time series, keys must be integer periods (e.g. calendar
    years, or the starting year of a financial year), so that "the previous
    period" is key − 1: a first difference or percent change at t is
    computed only when t − 1 is observed, and a lag of k at t uses the
    value at t − k only when it exists — never across a gap, never
    interpolated.
    """
    if tf not in TRANSFORMS:
        raise ValueError(f"Unknown transform: {tf!r}")
    lag = int(lag)
    if not 0 <= lag <= MAX_LAG:
        raise ValueError(f"lag must be between 0 and {MAX_LAG}.")
    keys = list(keys)
    vals = np.asarray(values, dtype=float)
    if len(keys) != len(vals):
        raise ValueError("keys and values must have the same length.")
    if np.isnan(vals).any():
        raise ValueError("transform_series expects missing values to be removed (and reported) first.")
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate keys")
    if not time_series and (tf in TS_ONLY_TRANSFORMS or lag):
        raise ValueError("differences, percent changes and lags are only defined for time series.")
    why = transform_options(vals, time_series=time_series).get(tf)
    if why is not None:
        raise ValueError(f"{TRANSFORM_LABELS[tf]} is not available: {why}.")

    cols = ["key", "value", "source_key", "source_value"]
    undefined: List[dict] = []
    if not time_series:
        out = pd.DataFrame({"key": keys, "value": np.log(vals) if tf == "log" else vals,
                            "source_key": keys, "source_value": vals}, columns=cols)
        return TransformedSeries(out, pd.DataFrame(undefined, columns=["key", "reason"]))

    if not all(_is_int_key(k) for k in keys):
        raise ValueError("time-series keys must be integer periods (e.g. years).")
    raw = {int(k): float(v) for k, v in zip(keys, vals)}
    base: Dict[int, float] = {}
    base_why: Dict[int, str] = {}
    what = {"diff": "first difference", "pct_change": "percent change"}.get(tf, "")
    for t in sorted(raw):
        v = raw[t]
        if tf == "level":
            base[t] = v
        elif tf == "log":
            base[t] = math.log(v)
        else:
            prev = raw.get(t - 1)
            if prev is None:
                base_why[t] = (f"no observation for the previous {period_word} ({t - 1}, "
                               + ("start of the series" if t == min(raw) else "a gap in the series")
                               + f"), so the {what} is not computed (no interpolation)")
                continue
            base[t] = v - prev if tf == "diff" else (v / prev - 1.0) * 100.0
    rows = [{"key": t + lag, "value": base[t], "source_key": t, "source_value": raw[t]} for t in sorted(base)]
    for t in sorted(raw):
        if (t - lag) in base:
            continue
        src = t - lag
        if not lag:
            reason = base_why[t]
        elif src in base_why:
            reason = f"lag {lag} needs the value for {src}, but there is " + base_why[src]
        else:
            reason = (f"lag {lag} needs the value for {src}, which is not observed "
                      "(before the series starts or a gap); not interpolated")
        undefined.append({"key": t, "reason": reason})
    return TransformedSeries(pd.DataFrame(rows, columns=cols),
                             pd.DataFrame(undefined, columns=["key", "reason"]))


# ---------------------------------------------------------------------------
# Multi-variable alignment
# ---------------------------------------------------------------------------

@dataclass
class DesignVariable:
    """One variable entering the model, as handed in by the caller.

    frame : columns [key, "value"] (+ optional "note"), one row per
        observation exactly as loaded; NaN values are kept so they can be
        reported as missing.
    exclude : key -> reason; rows never treated as observations of this
        variable (e.g. a tentative row), reported in the alignment.
    """
    id: str
    label: str
    short: str
    role: str                         # "dependent" | "explanatory"
    frame: pd.DataFrame
    tf: str = "level"
    lag: int = 0
    unit: str = ""
    status: str = ""
    source: str = ""
    period: str = ""
    exclude: Dict[object, str] = field(default_factory=dict)

    @property
    def column(self) -> str:
        return f"{self.id}__{self.tf}__L{self.lag}"

    @property
    def term(self) -> str:
        return term_name(self.short, self.tf, self.lag)


@dataclass
class DesignAlignment:
    key: str
    time_series: bool
    variables: List[DesignVariable]
    data: pd.DataFrame        # [key, <col>, <col>__src_key, <col>__src_value, <col>__note ...]
    dropped: pd.DataFrame     # [key, reason, category]
    coverage: pd.DataFrame    # one row per variable
    possible_name_mismatches: List[Tuple[str, str]] = field(default_factory=list)
    sample: Optional[Tuple[int, int]] = None
    n_universe: int = 0

    @property
    def n(self) -> int:
        return int(len(self.data))

    @property
    def n_dropped(self) -> int:
        return int(len(self.dropped))

    @property
    def y(self) -> DesignVariable:
        return next(v for v in self.variables if v.role == "dependent")

    @property
    def xs(self) -> List[DesignVariable]:
        return [v for v in self.variables if v.role == "explanatory"]

    @property
    def consecutive(self) -> bool:
        if not self.time_series:
            return True
        return rel.consecutive_periods(list(self.data[self.key]))

    def reason_summary(self) -> pd.DataFrame:
        if self.dropped.empty:
            return pd.DataFrame(columns=["category", "observations"])
        g = self.dropped.groupby("category").size().reset_index(name="observations")
        return g.sort_values("observations", ascending=False).reset_index(drop=True)


DROP_CATEGORIES = ("outside sample period", "excluded / tentative", "not present in a source",
                   "value missing in source", "transform or lag undefined")


def align_design(variables: Sequence[DesignVariable], *, key: str, time_series: bool,
                 sample: Optional[Tuple[int, int]] = None,
                 period_word: str = "year") -> DesignAlignment:
    """Transform each variable on its own calendar, then inner-join them all
    on `key`, restricted (time series) to `sample` = (first, last) period
    inclusive. Every key seen in any variable that is not in the result is
    listed in `dropped` with every applicable reason.

    Transforms and lags use each series' full history, so a lag or change
    at the first sample period uses the pre-sample observation when it
    exists (as standard econometrics software does)."""
    variables = list(variables)
    roles = [v.role for v in variables]
    if roles.count("dependent") != 1 or roles.count("explanatory") < 1:
        raise ValueError("need exactly one dependent and at least one explanatory variable.")
    if len({v.column for v in variables}) != len(variables):
        raise ValueError("the same variable with the same transform and lag is selected twice.")

    per_var = {}
    coverage_rows = []
    all_keys: set = set()
    for v in variables:
        f = v.frame
        for c in (key, "value"):
            if c not in f.columns:
                raise ValueError(f"{v.short} frame is missing column {c!r}.")
        f = f.dropna(subset=[key])
        if f[key].duplicated().any():
            raise ValueError(f"{v.short} has duplicate keys: {f[key][f[key].duplicated()].tolist()[:5]}")
        notes = dict(zip(f[key], f["note"])) if "note" in f.columns else {}
        excl = {k: r for k, r in v.exclude.items() if k in set(f[key])}
        f = f[~f[key].isin(list(excl))]
        missing = f[f["value"].isna()]
        obs = f[f["value"].notna()]
        ts = transform_series(obs[key].tolist(), obs["value"].astype(float).tolist(), v.tf, v.lag,
                              time_series=time_series, period_word=period_word)
        per_var[v.column] = dict(
            var=v, source_keys=set(f[key]), missing={k: notes.get(k, "") for k in missing[key]},
            values=dict(zip(ts.data["key"], ts.data["value"])),
            src_key=dict(zip(ts.data["key"], ts.data["source_key"])),
            src_val=dict(zip(ts.data["key"], ts.data["source_value"])),
            undefined=dict(zip(ts.undefined["key"], ts.undefined["reason"])),
            notes=notes, excluded=excl,
        )
        all_keys |= set(f[key]) | set(ts.data["key"]) | set(excl)
        coverage_rows.append({
            "variable": v.term, "role": v.role, "status": v.status,
            "observations in source": int(len(obs)), "missing in source": int(len(missing)),
            "excluded rows": int(len(excl)),
            "undefined after transform/lag": int(len(ts.undefined)),
        })

    # Probable spelling mismatches between keys present in only some sources.
    mismatches: List[Tuple[str, str]] = []
    if not time_series:
        key_sets = [pv["source_keys"] for pv in per_var.values()]
        common = set.intersection(*key_sets) if key_sets else set()
        partial = sorted({k for s in key_sets for k in s} - common, key=str)
        seen: Dict[str, str] = {}
        for k in partial:
            if not isinstance(k, str):
                continue
            nk = rel.normalise_key(k)
            if nk in seen and seen[nk] != k:
                mismatches.append((seen[nk], k))
            else:
                seen[nk] = k
    mismatch_keys = {k for pair in mismatches for k in pair}

    rows, dropped = [], []
    lo, hi = (sample if sample is not None else (None, None))
    for k in sorted(all_keys, key=lambda z: (str(type(z)), z)):
        if time_series and sample is not None and not (lo <= k <= hi):
            dropped.append({key: k, "reason": f"outside the selected sample period {lo}–{hi}",
                            "category": "outside sample period"})
            continue
        reasons, cats = [], []
        for col, pv in per_var.items():
            v = pv["var"]
            if k in pv["values"]:
                continue
            excl = pv["excluded"]
            src = k - v.lag if (time_series and v.lag) else k
            prev = src - 1 if (time_series and v.tf in TS_ONLY_TRANSFORMS) else None
            if k in excl and not v.lag:
                reasons.append(f"{v.short}: excluded — {excl[k]}")
                cats.append("excluded / tentative")
            elif src in excl:
                reasons.append(f"{v.term}: needs {v.short} for {src}, which is excluded — {excl[src]}")
                cats.append("excluded / tentative")
            elif prev is not None and prev in excl and src in pv["source_keys"]:
                reasons.append(f"{v.term}: the previous period {prev} is excluded — {excl[prev]}")
                cats.append("excluded / tentative")
            elif k in pv["missing"]:
                note = pv["missing"][k]
                reasons.append(f"{v.short}: value missing in source" + (f" ({note})" if note else ""))
                cats.append("value missing in source")
            elif k in pv["undefined"]:
                reasons.append(f"{v.term}: {pv['undefined'][k]}")
                cats.append("transform or lag undefined")
            elif k in pv["source_keys"]:
                reasons.append(f"{v.term}: not defined for this period")
                cats.append("transform or lag undefined")
            else:
                if k in mismatch_keys:
                    partner = next(b if a == k else a for a, b in mismatches if k in (a, b))
                    reasons.append(f"not present in {v.short} source — possible name mismatch with "
                                   f"{partner!r}, not auto-joined")
                else:
                    reasons.append(
                        f"{v.term}: needs {v.short} for {k - v.lag}, which is not observed (not interpolated)"
                        if time_series and v.lag else f"not present in {v.short} source")
                cats.append("not present in a source")
        if reasons:
            # The first category is the headline; reasons list all of them.
            order = {c: i for i, c in enumerate(DROP_CATEGORIES)}
            dropped.append({key: k, "reason": "; ".join(reasons),
                            "category": sorted(set(cats), key=order.get)[0]})
            continue
        row = {key: k}
        for col, pv in per_var.items():
            row[col] = float(pv["values"][k])
            row[f"{col}__src_key"] = pv["src_key"][k]
            row[f"{col}__src_value"] = float(pv["src_val"][k])
            row[f"{col}__note"] = pv["notes"].get(pv["src_key"][k], "") or ""
        rows.append(row)

    cols = [key]
    for v in variables:
        cols += [v.column, f"{v.column}__src_key", f"{v.column}__src_value", f"{v.column}__note"]
    data = pd.DataFrame(rows, columns=cols)
    in_sample = {v.column: int(data[v.column].notna().sum()) for v in variables}
    cov = pd.DataFrame(coverage_rows)
    cov["in analysis sample"] = [in_sample[v.column] for v in variables]
    return DesignAlignment(
        key=key, time_series=time_series, variables=variables, data=data,
        dropped=pd.DataFrame(dropped, columns=[key, "reason", "category"]),
        coverage=cov, possible_name_mismatches=mismatches,
        sample=tuple(sample) if sample is not None else None, n_universe=len(all_keys),
    )


# ---------------------------------------------------------------------------
# Pairwise correlation
# ---------------------------------------------------------------------------

def pairwise_correlations(data: pd.DataFrame, columns: Sequence[str],
                          labels: Mapping[str, str]) -> pd.DataFrame:
    """Pearson and Spearman correlation (two-sided p-values) for every pair
    of `columns` over the rows of `data` (the aligned analysis sample)."""
    out = []
    cols = list(columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = rel.correlations(data[cols[i]], data[cols[j]])
            out.append({"variable 1": labels.get(cols[i], cols[i]), "variable 2": labels.get(cols[j], cols[j]),
                        "n": c.n, "Pearson r": c.pearson_r, "Pearson p": c.pearson_p,
                        "Spearman ρ": c.spearman_rho, "Spearman p": c.spearman_p})
    return pd.DataFrame(out, columns=["variable 1", "variable 2", "n", "Pearson r", "Pearson p",
                                      "Spearman ρ", "Spearman p"])


# ---------------------------------------------------------------------------
# OLS
# ---------------------------------------------------------------------------

def newey_west_lags(n: int) -> int:
    """Newey–West (1994) rule of thumb for the HAC truncation lag:
    L = floor(4 · (n / 100)^(2/9)), at least 1."""
    if n <= 0:
        return 1
    return max(1, int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))))


HAC_LAG_RULE = "L = ⌊4·(n/100)^(2/9)⌋, minimum 1 (Newey–West 1994 rule of thumb), Bartlett kernel"


@dataclass
class OLSFit:
    terms: List[str]                 # "const" then the column names
    labels: Dict[str, str]           # column -> display label
    table: pd.DataFrame              # one row per term
    n: int
    k: int                           # regressors excluding the intercept
    df_model: float
    df_resid: float
    r_squared: float
    adj_r_squared: float
    f_stat: float
    f_pvalue: float
    se_type: str
    hac_lags: Optional[int]
    fitted: np.ndarray
    residuals: np.ndarray
    exog: np.ndarray                 # design matrix incl. constant
    results: object = None           # statsmodels results (for diagnostics)

    @property
    def se_label(self) -> str:
        lab = SE_LABELS[self.se_type]
        return f"{lab}, {self.hac_lags} lag(s)" if self.se_type == "HAC" else lab

    @property
    def se_short(self) -> str:
        """Short SE description for use inside sentences."""
        return {"nonrobust": "classical", "HC1": "HC1 robust",
                "HAC": f"Newey–West HAC ({self.hac_lags} lag{'s' if (self.hac_lags or 0) > 1 else ''})"}[self.se_type]

    @property
    def f_label(self) -> str:
        return ("F-test (classical)" if self.se_type == "nonrobust"
                else f"Wald F-test using the {SE_LABELS[self.se_type].split(' (')[0]} covariance")

    def coef(self, col: str) -> float:
        return float(self.table.loc[self.table["term"] == col, "coef"].iloc[0])


def fit_ols(data: pd.DataFrame, y_col: str, x_cols: Sequence[str], *, se_type: str = "nonrobust",
            hac_lags: Optional[int] = None, labels: Optional[Mapping[str, str]] = None,
            ci_level: float = CI_LEVEL) -> OLSFit:
    """OLS of y on the x columns plus an intercept (statsmodels).

    se_type: "nonrobust" (classical), "HC1" or "HAC" (Newey–West, Bartlett
    kernel, `hac_lags` lags — default `newey_west_lags(n)` — no small-sample
    correction, statsmodels' default). Every SE type uses t(n − k − 1)
    p-values and confidence intervals (statsmodels `use_t=True`), and with
    a robust covariance the F-test is the corresponding robust Wald test.

    Raises ModelError when the model cannot be estimated honestly: fewer
    than k + 2 observations, a constant regressor, or perfect
    multicollinearity (rank-deficient design matrix)."""
    import statsmodels.api as sm

    if se_type not in SE_LABELS:
        raise ValueError(f"Unknown se_type {se_type!r}")
    x_cols = list(x_cols)
    if not x_cols:
        raise ModelError("choose at least one explanatory variable.")
    labels = dict(labels or {})
    d = data[[y_col] + x_cols].astype(float)
    if d.isna().any().any():
        raise ModelError("the analysis sample contains missing values — align first.")
    n, k = len(d), len(x_cols)
    if n < k + 2:
        raise ModelError(f"only {n} observations for {k} regressor(s) plus an intercept — at least "
                         f"{k + 2} are needed to leave one residual degree of freedom.")
    for c in x_cols:
        if d[c].std(ddof=0) == 0:
            raise ModelError(f"{labels.get(c, c)} is constant in this sample, so its coefficient is not identified.")
    X = sm.add_constant(d[x_cols].to_numpy(), has_constant="add")
    rank = int(np.linalg.matrix_rank(X))
    if rank < X.shape[1]:
        raise ModelError("perfect multicollinearity: at least one explanatory variable is an exact linear "
                         "combination of the others (e.g. group shares that add up to 100%, or sectors that "
                         "add up to a total), so the coefficients are not separately identified.")
    y = d[y_col].to_numpy()
    model = sm.OLS(y, X)
    if se_type == "nonrobust":
        res = model.fit()
        lags = None
    elif se_type == "HC1":
        res = model.fit(cov_type="HC1", use_t=True)
        lags = None
    else:
        lags = int(hac_lags) if hac_lags is not None else newey_west_lags(n)
        res = model.fit(cov_type="HAC", cov_kwds={"maxlags": lags}, use_t=True)
    ci = np.asarray(res.conf_int(alpha=1 - ci_level))
    terms = ["const"] + x_cols
    labels.setdefault("const", "Intercept")
    table = pd.DataFrame({
        "term": terms,
        "label": [labels.get(t, t) for t in terms],
        "coef": np.asarray(res.params, dtype=float),
        "std_err": np.asarray(res.bse, dtype=float),
        "t": np.asarray(res.tvalues, dtype=float),
        "p": np.asarray(res.pvalues, dtype=float),
        "ci_low": ci[:, 0],
        "ci_high": ci[:, 1],
    })
    try:
        f_stat, f_p = float(np.squeeze(res.fvalue)), float(np.squeeze(res.f_pvalue))
    except Exception:  # pragma: no cover - statsmodels edge cases
        f_stat, f_p = float("nan"), float("nan")
    return OLSFit(
        terms=terms, labels=labels, table=table, n=n, k=k, df_model=float(res.df_model),
        df_resid=float(res.df_resid), r_squared=float(res.rsquared), adj_r_squared=float(res.rsquared_adj),
        f_stat=f_stat, f_pvalue=f_p, se_type=se_type, hac_lags=lags,
        fitted=np.asarray(res.fittedvalues, dtype=float), residuals=np.asarray(res.resid, dtype=float),
        exog=X, results=res,
    )


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@dataclass
class Diagnostic:
    test: str
    purpose: str
    statistic: float
    p_value: float
    verdict: str
    interpretation: str
    detail: str = ""


def _p_txt(p: float) -> str:
    return rel.format_p(p)


def breusch_pagan(fit: OLSFit, *, cross_section: bool = True) -> Diagnostic:
    """Breusch–Pagan LM test of H0: residual variance does not depend on
    the regressors (homoskedasticity)."""
    from statsmodels.stats.diagnostic import het_breuschpagan

    lm, lm_p, _, _ = het_breuschpagan(fit.residuals, fit.exog)
    fix = ("HC1 robust standard errors" if cross_section else "Newey–West HAC standard errors")
    if lm_p < ALPHA:
        verdict = "Heteroskedasticity detected"
        text = (f"The residual spread changes systematically with the regressors ({_p_txt(lm_p)}). Coefficients "
                f"are still unbiased under the other assumptions, but classical standard errors are unreliable — "
                f"use {fix} (selectable above).")
    else:
        verdict = "No evidence of heteroskedasticity"
        text = (f"No evidence at the {ALPHA:.0%} level that the residual spread depends on the regressors "
                f"({_p_txt(lm_p)}). With n = {fit.n} the test has limited power, so this is absence of evidence, "
                "not proof of constant variance.")
    return Diagnostic("Breusch–Pagan", "heteroskedasticity", float(lm), float(lm_p), verdict, text,
                      f"LM statistic, χ²({fit.k})")


def jarque_bera_test(fit: OLSFit) -> Diagnostic:
    """Jarque–Bera test of H0: residuals are normally distributed (skewness
    0, kurtosis 3)."""
    from statsmodels.stats.stattools import jarque_bera

    jb, p, skew, kurt = jarque_bera(fit.residuals)
    small = (f" With n = {fit.n} (< {JB_SMALL_N}) the test's chi-square approximation is rough and its power "
             "is low; read the QQ plot alongside it.") if fit.n < JB_SMALL_N else ""
    if p < ALPHA:
        verdict = "Residuals not normal"
        text = (f"Residuals depart from normality (skewness {skew:.2f}, kurtosis {kurt:.2f}; {_p_txt(p)}). OLS "
                "coefficients remain the best linear fit, but in small samples t- and F-based p-values and "
                "confidence intervals may be inaccurate; outliers are a common cause — check the residual plots."
                + small)
    else:
        verdict = "No evidence against normality"
        text = (f"No evidence at the {ALPHA:.0%} level against normal residuals (skewness {skew:.2f}, kurtosis "
                f"{kurt:.2f}; {_p_txt(p)})." + small)
    return Diagnostic("Jarque–Bera", "normality of residuals", float(jb), float(p), verdict, text,
                      f"skewness {skew:.3f}, kurtosis {kurt:.3f}")


def durbin_watson_test(fit: OLSFit, *, consecutive: bool = True) -> Diagnostic:
    """Durbin–Watson statistic (≈ 2 − 2·first-order residual
    autocorrelation). Rule of thumb used here: < 1.5 positive, > 2.5
    negative autocorrelation (no p-value is computed)."""
    from statsmodels.stats.stattools import durbin_watson

    dw = float(durbin_watson(fit.residuals))
    if dw < DW_LOW:
        verdict = "Positive autocorrelation likely"
        text = (f"DW = {dw:.2f} is well below 2: residuals in neighbouring periods tend to share a sign. "
                "Classical standard errors are then too small (over-confident p-values) — use Newey–West HAC "
                "errors, and consider first differences.")
    elif dw > DW_HIGH:
        verdict = "Negative autocorrelation likely"
        text = (f"DW = {dw:.2f} is well above 2: residuals tend to alternate in sign between periods, which "
                "often signals over-differencing. Classical standard errors are unreliable.")
    else:
        verdict = "No strong first-order autocorrelation"
        text = (f"DW = {dw:.2f} is close to 2, consistent with little first-order autocorrelation "
                f"(rule of thumb: {DW_LOW}–{DW_HIGH}).")
    if not consecutive:
        text += (" Caution: the sample periods are not consecutive (there are gaps), so 'neighbouring' "
                 "residuals are not always one period apart.")
    return Diagnostic("Durbin–Watson", "first-order serial correlation", dw, float("nan"), verdict, text,
                      "rule of thumb; no p-value")


def breusch_godfrey(fit: OLSFit, nlags: int, *, consecutive: bool = True) -> Diagnostic:
    """Breusch–Godfrey LM test of H0: no serial correlation up to `nlags`."""
    from statsmodels.stats.diagnostic import acorr_breusch_godfrey

    nlags = int(max(1, nlags))
    if fit.n - fit.k - 1 - nlags < 1:
        return Diagnostic("Breusch–Godfrey", f"serial correlation up to lag {nlags}", float("nan"), float("nan"),
                          "Not computed", f"Too few observations (n = {fit.n}) for the auxiliary regression "
                          f"with {nlags} lagged residual(s).")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        lm, p, _, _ = acorr_breusch_godfrey(fit.results, nlags=nlags)
    if p < ALPHA:
        verdict = "Serial correlation detected"
        text = (f"Residuals are correlated over time up to lag {nlags} ({_p_txt(p)}): consecutive errors are "
                "not independent, so classical standard errors and p-values are over-confident — use "
                "Newey–West HAC errors, and consider first differences or adding dynamics.")
    else:
        verdict = "No evidence of serial correlation"
        text = (f"No evidence at the {ALPHA:.0%} level of serial correlation up to lag {nlags} ({_p_txt(p)}); "
                f"with n = {fit.n} the test has limited power.")
    if not consecutive:
        text += " Caution: the sample periods are not consecutive, so 'lag 1' is not always one period."
    return Diagnostic("Breusch–Godfrey", f"serial correlation up to lag {nlags}", float(lm), float(p), verdict,
                      text, f"LM statistic, χ²({nlags})")


def vif_table(fit: OLSFit) -> pd.DataFrame:
    """Variance inflation factor for each regressor (excluding the
    intercept): VIF_j = 1 / (1 − R²_j), R²_j from regressing x_j on the
    other regressors with an intercept."""
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    rows = []
    X = fit.exog
    for j, term in enumerate(fit.terms):
        if term == "const":
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            v = float(variance_inflation_factor(X, j))
        if not np.isfinite(v) or v >= VIF_HIGH:
            verdict = "severe — coefficient barely identified" if np.isfinite(v) else "perfect collinearity"
        elif v >= VIF_NOTABLE:
            verdict = "notable — standard error inflated"
        else:
            verdict = "low"
        rows.append({"term": term, "label": fit.labels.get(term, term), "VIF": v, "assessment": verdict})
    return pd.DataFrame(rows, columns=["term", "label", "VIF", "assessment"])


def vif_interpretation(vif: pd.DataFrame) -> str:
    if vif.empty:
        return "VIF needs at least two regressors."
    worst = vif.loc[vif["VIF"].fillna(np.inf).idxmax()]
    if worst["VIF"] >= VIF_HIGH or not np.isfinite(worst["VIF"]):
        return (f"Severe multicollinearity: {worst['label']} has VIF = {worst['VIF']:.1f} (≥ {VIF_HIGH:.0f}). The "
                "regressors move so closely together that the data cannot separate their individual "
                "associations; individual coefficients and their signs are unstable, even if the joint fit (R², "
                "F-test) is fine. Consider dropping one of the overlapping variables.")
    if worst["VIF"] >= VIF_NOTABLE:
        return (f"Moderate multicollinearity: the largest VIF is {worst['VIF']:.1f} ({worst['label']}). Its "
                f"standard error is about √{worst['VIF']:.1f} ≈ {math.sqrt(worst['VIF']):.1f}× what it would be "
                "with uncorrelated regressors.")
    return (f"Low multicollinearity: every VIF is below {VIF_NOTABLE:.0f} (largest {worst['VIF']:.1f}), so the "
            "regressors carry largely separate information.")


@dataclass
class ADFResult:
    variable: str
    n: int
    statistic: float
    p_value: float
    used_lag: Optional[int]
    crit_5pct: float
    regression: str
    status: str            # "stationary" | "unit_root" | "too_small" | "not_computed"
    verdict: str
    interpretation: str
    span: str = ""

    @property
    def meaningful(self) -> bool:
        return self.status in ("stationary", "unit_root")

    @property
    def nonstationary_or_unknown(self) -> bool:
        return self.status != "stationary"


def longest_consecutive_run(keys: Sequence[int], values: Sequence[float]) -> Tuple[List[int], np.ndarray]:
    """The longest run of consecutive integer periods with non-missing
    values (ties: the latest run)."""
    pairs = sorted((int(k), float(v)) for k, v in zip(keys, values) if v is not None and np.isfinite(v))
    best: List[Tuple[int, float]] = []
    cur: List[Tuple[int, float]] = []
    for k, v in pairs:
        if cur and k == cur[-1][0] + 1:
            cur.append((k, v))
        else:
            cur = [(k, v)]
        if len(cur) >= len(best):
            best = list(cur)
    return [k for k, _ in best], np.asarray([v for _, v in best], dtype=float)


def adf_test(values: Sequence[float], *, name: str = "series", regression: str = "c",
             span: str = "") -> ADFResult:
    """Augmented Dickey–Fuller test of H0: the series has a unit root
    (non-stationary). Lag length chosen by AIC up to
    min(⌊12·(n/100)^(1/4)⌋, the largest lag the sample allows).

    For n < ADF_MIN_N the statistics are reported but no verdict is given —
    the test has very little power in short samples and its critical values
    are asymptotic, so "cannot reject a unit root" says almost nothing.
    For n < ADF_MIN_COMPUTE it is not run at all."""
    from statsmodels.tsa.stattools import adfuller

    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    n = int(len(v))
    nan = float("nan")
    if n < ADF_MIN_COMPUTE or np.std(v) == 0:
        why = (f"only {n} consecutive observations (the test is not run below {ADF_MIN_COMPUTE})"
               if n < ADF_MIN_COMPUTE else "the series is constant")
        return ADFResult(name, n, nan, nan, None, nan, regression, "not_computed", "Not computed",
                         f"ADF not computed: {why}. Stationarity cannot be assessed from these data.", span)
    ntrend = 1 if regression == "c" else 2
    cap = int(math.floor(12 * (n / 100.0) ** 0.25))
    allowed = int(math.ceil(n / 2.0 - ntrend - 1)) - 1
    maxlag = max(0, min(cap, allowed))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = adfuller(v, maxlag=maxlag, regression=regression, autolag="AIC")
    except Exception as exc:  # pragma: no cover - defensive
        return ADFResult(name, n, nan, nan, None, nan, regression, "not_computed", "Not computed",
                         f"ADF could not be computed on this sample ({exc}).", span)
    stat, p, used_lag, crit = out[0], out[1], out[2], out[4]
    c5 = float(crit["5%"])
    if n < ADF_MIN_N:
        return ADFResult(
            name, n, float(stat), float(p), int(used_lag), c5, regression, "too_small",
            f"Too few observations (n = {n} < {ADF_MIN_N}) — no verdict",
            (f"With only {n} observations the ADF test has very little power: failing to reject a unit root "
             "(p ≥ 0.05) is expected even for a stationary series, and the critical values are asymptotic "
             f"approximations. The numbers are shown for completeness (ADF = {stat:.2f}, {_p_txt(p)}) but no "
             "conclusion about stationarity is drawn. Treat the series as possibly non-stationary."), span)
    if p < ALPHA:
        return ADFResult(name, n, float(stat), float(p), int(used_lag), c5, regression, "stationary",
                         "Stationary (unit root rejected at 5%)",
                         (f"ADF = {stat:.2f} below the 5% critical value {c5:.2f} ({_p_txt(p)}): the unit-root "
                          "hypothesis is rejected, consistent with a series that reverts to a stable mean"
                          + (" around a trend" if regression == "ct" else "") + "."), span)
    return ADFResult(name, n, float(stat), float(p), int(used_lag), c5, regression, "unit_root",
                     "Unit root not rejected (non-stationary)",
                     (f"ADF = {stat:.2f} vs 5% critical value {c5:.2f} ({_p_txt(p)}): a unit root cannot be "
                      "rejected — the series behaves like a random walk"
                      + (" around a trend" if regression == "ct" else "")
                      + ". Regressing it in levels on another non-stationary series risks a spurious regression."),
                     span)


LEVEL_FORMS = ("level", "log")


def spurious_regression_warning(y: Tuple[str, str], xs: Sequence[Tuple[str, str]],
                                adf: Mapping[str, ADFResult]) -> Optional[str]:
    """Banner text when non-stationary (or untestable) series are regressed
    on each other in levels.

    y and each x are (display name, transform); `adf` maps display name to
    the ADF result on that variable's level series. Risk is flagged when the
    dependent variable and at least one regressor enter in level or log
    form and none of them is shown stationary by an ADF test with
    n ≥ ADF_MIN_N. Returns None otherwise."""
    y_name, y_tf = y
    if y_tf not in LEVEL_FORMS:
        return None
    lvl_x = [name for name, tf in xs if tf in LEVEL_FORMS]
    if not lvl_x:
        return None
    y_res = adf.get(y_name)
    if y_res is not None and y_res.status == "stationary":
        return None
    risky = [x for x in lvl_x if adf.get(x) is None or adf[x].status != "stationary"]
    if not risky:
        return None
    def why(name: str) -> str:
        r = adf.get(name)
        if r is None:
            return "not tested"
        return {"unit_root": "unit root not rejected", "too_small": f"n = {r.n}, too short to test",
                "not_computed": "not testable"}.get(r.status, r.status)
    listed = "; ".join(f"{nm} ({why(nm)})" for nm in [y_name] + risky)
    return ("Spurious-regression risk: the dependent variable and "
            + ("a regressor" if len(risky) == 1 else f"{len(risky)} regressors")
            + f" enter in levels and none of them is shown to be stationary — {listed}. Two unrelated "
            "trending or random-walk series routinely produce a high R² and 'significant' t-statistics "
            "(Granger & Newbold 1974). Re-run with first differences or % changes (and compare), or treat "
            "the levels result as descriptive of shared trends only. A genuine long-run (cointegrating) "
            "relationship would need a dedicated test, which this workbench does not perform.")


def qq_points(residuals: Sequence[float]) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """(theoretical normal quantiles, ordered residuals, line slope,
    line intercept) for a normal QQ plot."""
    (osm, osr), (slope, intercept, _r) = stats.probplot(np.asarray(residuals, dtype=float), dist="norm")
    return np.asarray(osm), np.asarray(osr), float(slope), float(intercept)


# ---------------------------------------------------------------------------
# Interpretation text (generated from the numbers; never causal)
# ---------------------------------------------------------------------------

def _num(v: float) -> str:
    return rel.fmt_num(v)


def _lag_phrase(lag: int, period_word: str) -> str:
    if not lag:
        return ""
    return f" {lag} {period_word}{'s' if lag > 1 else ''} earlier (t−{lag})"


def _x_phrase(short: str, tf: str, lag: int, unit: str, period_word: str) -> str:
    lp = _lag_phrase(lag, period_word)
    if tf == "log":
        return f"a 1% higher {short}{lp}"
    if tf == "diff":
        return (f"a {period_word}-on-{period_word} change in {short}{lp} that is larger by "
                f"{rel._qty('1', unit) if unit else 'one unit'}")
    if tf == "pct_change":
        return f"growth of {short}{lp} that is 1 percentage point faster"
    return f"a one-unit increase in {short}{lp} ({'+' + rel._qty('1', unit) if unit else '+1'})"


def _y_effect(short: str, tf: str, unit: str, b: float, period_word: str) -> str:
    more = "higher" if b > 0 else "lower"
    if tf == "log":
        exact = (math.exp(b) - 1.0) * 100.0
        return f"{short} being approximately {abs(b) * 100:.3g}% {more} (exact: {exact:+.3g}%)"
    if tf == "diff":
        return (f"the {period_word}-on-{period_word} change in {short} being "
                f"{rel._qty(_num(abs(b)), unit) if unit else _num(abs(b))} {'larger' if b > 0 else 'smaller'}")
    if tf == "pct_change":
        return f"growth of {short} being {_num(abs(b))} percentage points {more}"
    return f"{short} being {rel._qty(_num(abs(b)), unit) if unit else _num(abs(b))} {more}"


def coefficient_sentence(*, x_short: str, x_tf: str, x_lag: int, x_unit: str, y_short: str, y_tf: str,
                         y_unit: str, coef: float, ci_low: float, ci_high: float, p: float, n_regressors: int,
                         se_label: str, period_word: str = "year", ci_level: float = CI_LEVEL) -> str:
    """One plain-language sentence for one slope coefficient.

    Wording by transform: both logs → elasticity; log Y with X in levels →
    semi-elasticity; log X with Y in levels → effect of a 1% change = b/100
    Y-units; otherwise "a one-unit increase in X is associated with…".
    Always 'is associated with', never causal language."""
    if not np.isfinite(coef):
        return f"The coefficient on {term_name(x_short, x_tf, x_lag)} could not be estimated."
    ci_pct = int(round(ci_level * 100))
    ceteris = ", holding the other included regressors fixed," if n_regressors > 1 else ""
    sig = ("statistically distinguishable from zero" if np.isfinite(p) and p < ALPHA
           else "not statistically distinguishable from zero")
    tail = (f" ({ci_pct}% CI {{lo}} to {{hi}}; {rel.format_p(p)}, {sig} at the {ALPHA:.0%} level with "
            f"{se_label} standard errors).")
    x_ph = _x_phrase(x_short, x_tf, x_lag, x_unit, period_word)
    if x_tf == "log" and y_tf == "log":
        more = "higher" if coef > 0 else "lower"
        body = (f"Elasticity: {x_ph} is associated{ceteris} with {y_short} being approximately "
                f"{abs(coef):.3g}% {more} — an elasticity of {coef:.3g}")
        return body + tail.format(lo=f"{ci_low:.3g}", hi=f"{ci_high:.3g}")
    if y_tf == "log" and x_tf != "log":
        body = (f"Semi-elasticity: {x_ph} is associated{ceteris} with "
                f"{_y_effect(y_short, 'log', y_unit, coef, period_word)} — a semi-elasticity of {coef:.4g}")
        return body + tail.format(lo=f"{ci_low * 100:.3g}%", hi=f"{ci_high * 100:.3g}%")
    if x_tf == "log":
        b = coef / 100.0
        body = (f"{x_ph[0].upper() + x_ph[1:]} is associated{ceteris} with "
                f"{_y_effect(y_short, y_tf, y_unit, b, period_word)} (coefficient {coef:.4g} ÷ 100)")
        return body + tail.format(lo=_num(ci_low / 100.0), hi=_num(ci_high / 100.0))
    body = (f"{x_ph[0].upper() + x_ph[1:]} is associated{ceteris} with "
            f"{_y_effect(y_short, y_tf, y_unit, coef, period_word)}")
    return body + tail.format(lo=_num(ci_low), hi=_num(ci_high))


def fit_summary_text(fit: OLSFit, *, y_term: str, obs_noun: str = "observations") -> str:
    """Sample size and model-fit summary in plain language."""
    parts = [f"Estimated on n = {fit.n} {obs_noun} with {fit.k} regressor{'s' if fit.k > 1 else ''} plus an "
             f"intercept ({int(fit.df_resid)} residual degrees of freedom)."]
    if np.isfinite(fit.r_squared):
        parts.append(f"R² = {fit.r_squared:.3f}: the regressors jointly account for {fit.r_squared:.1%} of the "
                     f"sample variation in {y_term}; adjusted R² = {fit.adj_r_squared:.3f} (penalised for the "
                     "number of regressors).")
    if np.isfinite(fit.f_stat):
        sig = ("so the regressors are jointly statistically significant" if fit.f_pvalue < ALPHA
               else "so the regressors are not jointly statistically significant")
        parts.append(f"{fit.f_label}: F({int(fit.df_model)}, {int(fit.df_resid)}) = {fit.f_stat:.3g}, "
                     f"{rel.format_p(fit.f_pvalue)}, {sig} at the {ALPHA:.0%} level.")
    parts.append(f"Standard errors: {fit.se_label}.")
    if fit.n < rel.SMALL_SAMPLE_THRESHOLD:
        parts.append(f"Small sample (n < {rel.SMALL_SAMPLE_THRESHOLD}): one or two observations can move every "
                     "estimate, and p-values lean on normality of the errors.")
    if fit.df_resid < 5:
        parts.append("With fewer than 5 residual degrees of freedom the estimates are extremely imprecise.")
    return " ".join(parts)


ASSUMPTIONS: Tuple[Tuple[str, str], ...] = (
    ("Linearity", "Y is modelled as a linear function of the (transformed) regressors. Curvature not captured by "
                  "the chosen transforms ends up in the residuals — check the residual-vs-fitted plot."),
    ("Exogeneity", "The errors are assumed uncorrelated with the regressors. Omitted variables, reverse causation "
                   "and measurement error all violate this, and then no coefficient here is a causal effect."),
    ("No perfect multicollinearity", "No regressor is an exact linear combination of the others (enforced: such "
                                     "models are refused). High but imperfect collinearity is shown by the VIF."),
    ("Error variance", "Classical standard errors assume constant error variance and independent errors; HC1 "
                       "relaxes the first, Newey–West HAC both (asymptotically — in short samples they are "
                       "themselves imprecise)."),
    ("Normality", "Exact t and F inference in small samples assumes normal errors (Jarque–Bera, QQ plot)."),
    ("Stationarity (time series)", "Inference in levels assumes stationary series; regressing non-stationary "
                                   "series on each other can produce spurious results (ADF, banner)."),
)

LIMITATIONS: Tuple[str, ...] = (
    "Observational data from different sources, survey designs and reference periods; no identification "
    "strategy, so no coefficient is a causal effect.",
    "Small samples: state cross-sections have at most ~36 states/UTs and usually far fewer after alignment; "
    "all-India annual series run from 5 to 72 years.",
    "Several variables are linked by construction (WIL group shares add up to 100%; GCF sectors add up to the "
    "total; NSDP growth is computed from initial NSDP) — part of any association is arithmetic.",
    "Data status matters: PARTIAL, SPLICED and DERIVED series carry known transcription, splicing or "
    "construction caveats (see each variable's status and the sources panel).",
    "Choosing among many specifications and reporting the 'best' one inflates the chance of a spurious "
    "significant result; the reproducibility record lists exactly what was run.",
    "Not implemented by design: panel-data estimators, instrumental variables, difference-in-differences or any "
    "other causal-inference method; cointegration and structural-break tests.",
)

CAUSATION_NOTE = (
    "Correlation is not causation. A coefficient here says how Y and X co-vary in this sample after the "
    "other included regressors are accounted for linearly. It does not say what would happen to Y if X were "
    "changed: a third factor may drive both, Y may drive X, and selection into the aligned sample is not "
    "random. Wording such as 'is associated with' is deliberate."
)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def regression_table(fit: OLSFit, alignment: DesignAlignment) -> pd.DataFrame:
    """Tidy coefficient table with model statistics repeated on each row,
    for CSV export."""
    by_col = {v.column: v for v in alignment.variables}
    rows = []
    for r in fit.table.itertuples(index=False):
        v = by_col.get(r.term)
        rows.append({
            "term": r.label,
            "variable_id": v.id if v else "const",
            "transform": v.tf if v else "",
            "lag": v.lag if v else 0,
            "coefficient": r.coef, "std_error": r.std_err, "t_stat": r.t, "p_value": r.p,
            "ci_low_95": r.ci_low, "ci_high_95": r.ci_high,
            "dependent": alignment.y.term, "se_type": fit.se_label,
            "n": fit.n, "df_model": int(fit.df_model), "df_resid": int(fit.df_resid),
            "r_squared": fit.r_squared, "adj_r_squared": fit.adj_r_squared,
            "f_stat": fit.f_stat, "f_pvalue": fit.f_pvalue,
        })
    return pd.DataFrame(rows)


def aligned_data_export(alignment: DesignAlignment, fit: Optional[OLSFit] = None) -> pd.DataFrame:
    """The aligned analysis sample with, for each variable: the value used
    in the model, the source period and raw value it came from, unit,
    status and any row note from the source; plus fitted values and
    residuals when a fit is given."""
    d = alignment.data
    out = pd.DataFrame({alignment.key: d[alignment.key]})
    for v in alignment.variables:
        tag = f"{'Y' if v.role == 'dependent' else 'X'}: {v.term}"
        out[f"{tag} [value used]"] = d[v.column]
        out[f"{tag} [source period]"] = d[f"{v.column}__src_key"]
        out[f"{tag} [raw value]"] = d[f"{v.column}__src_value"]
        out[f"{tag} [unit]"] = v.unit
        out[f"{tag} [transform]"] = TRANSFORM_LABELS[v.tf] + (f", lag {v.lag}" if v.lag else "")
        out[f"{tag} [status]"] = v.status
        out[f"{tag} [row note]"] = d[f"{v.column}__note"]
    if fit is not None and len(fit.fitted) == len(out):
        out["fitted Y"] = fit.fitted
        out["residual"] = fit.residuals
    return out


def library_versions() -> Dict[str, str]:
    import scipy
    import statsmodels
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "statsmodels": statsmodels.__version__}


def _clean(v):
    """JSON-safe conversion (NaN/inf -> None, numpy scalars -> Python)."""
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return f if math.isfinite(f) else None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def reproducibility_record(*, alignment: DesignAlignment, fit: Optional[OLSFit], level: str,
                           level_label: str, se_type: str, hac_lags: Optional[int],
                           adf_regression: Optional[str] = None, include_tentative: bool = False,
                           extra: Optional[Mapping[str, object]] = None,
                           generated_utc: Optional[str] = None) -> Dict[str, object]:
    """Every setting needed to re-run this exact regression, the data files
    and statuses behind it, the headline results, and library versions."""
    def var_rec(v: DesignVariable) -> dict:
        return {"id": v.id, "label": v.label, "role": v.role, "transform": v.tf,
                "transform_label": TRANSFORM_LABELS[v.tf], "lag": v.lag, "term": v.term, "unit": v.unit,
                "status": v.status, "source": v.source, "period": v.period,
                "excluded_rows": {str(k): r for k, r in v.exclude.items()}}
    rec: Dict[str, object] = {
        "record_type": "India Economic Intelligence Lab — Regression workbench reproducibility record",
        "generated_utc": generated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "settings": {
            "level": level, "level_label": level_label, "key": alignment.key,
            "time_series": alignment.time_series,
            "dependent": var_rec(alignment.y),
            "explanatory": [var_rec(v) for v in alignment.xs],
            "sample_period": list(alignment.sample) if alignment.sample else None,
            "include_tentative_rows": include_tentative,
            "estimator": "OLS with intercept (statsmodels.api.OLS)",
            "se_type": se_type, "se_label": SE_LABELS[se_type],
            "hac_lags": hac_lags if se_type == "HAC" else None,
            "hac_lag_rule": HAC_LAG_RULE if se_type == "HAC" else None,
            "p_values_and_ci": "t distribution with n − k − 1 df (use_t=True); 95% confidence intervals",
            "adf_regression": adf_regression,
            "adf_lag_selection": "AIC, max lag min(⌊12·(n/100)^(1/4)⌋, sample limit); verdict only when n ≥ "
                                 f"{ADF_MIN_N}",
            "transform_rules": ("log only if every value > 0; first difference and % change only between "
                                "consecutive periods; lag k uses period t−k only if observed; transforms use each "
                                "series' full history before the sample filter; nothing interpolated"),
            "alpha": ALPHA,
        },
        "alignment": {
            "n_analysis_sample": alignment.n,
            "n_keys_seen": alignment.n_universe,
            "n_dropped": alignment.n_dropped,
            "dropped_by_category": dict(zip(alignment.reason_summary()["category"],
                                            alignment.reason_summary()["observations"])),
            "dropped": [{"key": r[alignment.key], "reason": r["reason"]}
                        for r in alignment.dropped.to_dict("records")],
            "keys_used": alignment.data[alignment.key].tolist(),
            "possible_name_mismatches": [list(p) for p in alignment.possible_name_mismatches],
        },
        "results": None,
        "versions": library_versions(),
        "how_to_reproduce": (
            "Load each variable with data_sources.loaders as named in 'source'; apply the transforms and lags "
            "listed (analysis.econometrics.transform_series); inner-join on the key and keep 'keys_used'; fit "
            "statsmodels OLS(y, add_constant(X)) with the stated covariance type; compare with 'results'."
        ),
    }
    if fit is not None:
        rec["results"] = {
            "n": fit.n, "k": fit.k, "df_model": fit.df_model, "df_resid": fit.df_resid,
            "r_squared": fit.r_squared, "adj_r_squared": fit.adj_r_squared,
            "f_stat": fit.f_stat, "f_pvalue": fit.f_pvalue,
            "coefficients": [{"term": r.label, "coef": r.coef, "std_err": r.std_err, "t": r.t, "p": r.p,
                              "ci_low": r.ci_low, "ci_high": r.ci_high}
                             for r in fit.table.itertuples(index=False)],
        }
    if extra:
        rec["settings"].update(dict(extra))
    return _clean(rec)


def record_to_json(record: Mapping[str, object]) -> str:
    return json.dumps(_clean(dict(record)), indent=2, ensure_ascii=False, default=str)
