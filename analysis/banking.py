"""iBFPI — India Bank Financial Performance Index.

Adapts the BFPI methodology developed in the accompanying JP Morgan
research paper (2018-2024) to Indian scheduled commercial banks. The
transformation is deliberately identical to the paper:

    Z* = D * (X - median(X)) / (1.4826 * MAD(X))
    iBFPI_t = mean_i(Z*_it) with equal weights across 5 indicators

The scale factor 1.4826 makes the robust z-score consistent with the
standard normal distribution under Gaussian data.

This module implements the transformations, correlation tests and
rate-regime split, plus a small helper to fetch the illustrative panel
shipped in data/processed/.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from scipy import stats


# Indicator direction coefficients D: +1 if higher is better, -1 if worse.
# Interpretation follows the JP Morgan paper's construction of BFPI.
INDICATOR_DIRECTION: Dict[str, int] = {
    "ppnr_to_assets": +1,       # Pre-provision net revenue / assets
    "cet1_ratio": +1,            # Common Equity Tier 1 ratio
    "nco_rate": -1,              # Net charge-off rate
    "lcr": +1,                   # Liquidity coverage ratio
    "unrealised_loss_to_cet1": -1,  # Unrealised securities losses / CET1
}

INDICATOR_LABELS: Dict[str, str] = {
    "ppnr_to_assets": "PPNR / Assets",
    "cet1_ratio": "CET1 Ratio",
    "nco_rate": "Net Charge-Off Rate",
    "lcr": "Liquidity Coverage Ratio",
    "unrealised_loss_to_cet1": "Unrealised Losses / CET1",
}

MAD_SCALE = 1.4826  # Fisher constant for Gaussian consistency


def robust_zscore(x: pd.Series, direction: int = 1) -> pd.Series:
    """Robust z-score with median/MAD scaling and a direction coefficient.

    Uses the pooled historical median and MAD of the series so a bank's z
    at time t is comparable to its own history. If MAD is zero (constant
    series), returns zeros to avoid division errors.
    """
    m = float(np.median(x))
    mad = float(np.median(np.abs(x - m)))
    if mad == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return direction * (x - m) / (MAD_SCALE * mad)


def compute_ibfpi(
    panel: pd.DataFrame,
    indicator_cols: Iterable[str] = tuple(INDICATOR_DIRECTION),
    indicator_weights: Dict[str, float] | None = None,
    directions: Dict[str, int] | None = None,
) -> pd.DataFrame:
    """Compute iBFPI for every (bank, period) row.

    `directions` optionally overrides INDICATOR_DIRECTION (+1 / -1 per
    indicator) -- used only by the sensitivity analysis below.

    Parameters
    ----------
    panel : DataFrame
        Long-form: columns include `bank`, `period` (date) and the five
        indicators. Values are decimal fractions or ratios in native
        units (they are standardised internally, so scales don't matter).
    indicator_weights : optional mapping indicator_col -> weight.
        The published BFPI methodology this adapts gives every indicator
        equal weight (1/5 each) when combining the five robust z-scores —
        that is exactly what happens when this is left as `None` (the
        default, matching all prior behaviour exactly: a plain mean of the
        Z-columns). Passing a mapping instead computes a weighted sum of
        the Z-columns, with weights normalised to sum to 1 across
        `indicator_cols`. This is a **user-set exploration** ("what if
        this indicator mattered more to the composite") layered on the
        same real, already-computed z-scores — not an alternative
        published methodology or a claim that any weighting is more
        correct than equal-weighting.

    Returns
    -------
    DataFrame
        Original columns plus one Z-column per indicator and an
        `ibfpi` column (equal-weight mean of the Z-columns by default,
        or the weighted sum if `indicator_weights` is given).
    """
    df = panel.copy()
    indicator_cols = list(indicator_cols)
    for col in indicator_cols:
        if col not in df.columns:
            raise KeyError(f"panel missing indicator column: {col}")
        direction = (directions or INDICATOR_DIRECTION)[col]
        # Standardise per bank so within-bank history is the reference.
        z_col = f"z_{col}"
        df[z_col] = (
            df.groupby("bank", group_keys=False)[col]
            .apply(lambda s: robust_zscore(s, direction=direction))
        )
    z_cols = [f"z_{c}" for c in indicator_cols]
    if indicator_weights is None:
        df["ibfpi"] = df[z_cols].mean(axis=1)
    else:
        total = sum(indicator_weights.get(c, 0.0) for c in indicator_cols)
        if total <= 0:
            raise ValueError("indicator_weights must sum to a positive value.")
        w = {c: indicator_weights.get(c, 0.0) / total for c in indicator_cols}
        weighted = sum(df[f"z_{c}"] * w[c] for c in indicator_cols)
        df["ibfpi"] = weighted
    return df


def cross_bank_aggregate(ibfpi_panel: pd.DataFrame, weights: Dict[str, float] | None = None) -> pd.DataFrame:
    """Aggregate to a single index per period across banks.

    Default is an equal-weighted mean. Optional `weights` argument
    accepts a mapping bank -> weight (need not sum to 1; normalised).
    """
    if weights is None:
        agg = ibfpi_panel.groupby("period")["ibfpi"].mean().rename("ibfpi_system")
        return agg.reset_index()
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("weights must sum to positive value.")
    w = {k: v / total for k, v in weights.items()}
    df = ibfpi_panel.copy()
    df["w"] = df["bank"].map(w).fillna(0.0)
    agg = (df.assign(weighted=df["ibfpi"] * df["w"])
             .groupby("period")["weighted"].sum()
             .rename("ibfpi_system"))
    return agg.reset_index()


@dataclass
class CorrelationResult:
    rho: float
    p_value: float
    n: int


def spearman(a: pd.Series, b: pd.Series) -> CorrelationResult:
    """Spearman rank correlation with p-value. Drops rows where either is NaN."""
    df = pd.concat([a, b], axis=1).dropna()
    if len(df) < 3:
        return CorrelationResult(rho=float("nan"), p_value=float("nan"), n=len(df))
    rho, p = stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return CorrelationResult(rho=float(rho), p_value=float(p), n=int(len(df)))


def regime_split(
    df: pd.DataFrame,
    rate_col: str = "repo_rate",
    ibfpi_col: str = "ibfpi_system",
) -> Tuple[pd.DataFrame, CorrelationResult, CorrelationResult, CorrelationResult]:
    """Split the panel into rising / falling / stable rate regimes.

    Regime rule: three-quarter rolling change in the repo rate.
        > +25bp   -> rising
        < -25bp   -> falling
        otherwise -> stable
    """
    d = df.sort_values("period").copy()
    d["rate_delta"] = d[rate_col].diff().rolling(3, min_periods=1).sum()
    def classify(x: float) -> str:
        if pd.isna(x):
            return "stable"
        if x > 0.25:
            return "rising"
        if x < -0.25:
            return "falling"
        return "stable"
    d["regime"] = d["rate_delta"].apply(classify)

    def _corr(mask: pd.Series) -> CorrelationResult:
        return spearman(d.loc[mask, rate_col], d.loc[mask, ibfpi_col])

    return (
        d,
        _corr(d["regime"] == "rising"),
        _corr(d["regime"] == "falling"),
        _corr(d["regime"] == "stable"),
    )


# ---------------------------------------------------------------------------
# Robustness: sensitivity of the repo-rate association to the composite's
# construction choices, and a bank fixed-effects regression.
# ---------------------------------------------------------------------------
def system_rho(panel: pd.DataFrame, repo: pd.DataFrame, *, indicators=None, weights=None,
               directions=None) -> CorrelationResult:
    """Spearman rho between the repo rate and the equal-bank-weighted
    system iBFPI built with the given construction choices."""
    cols = list(indicators) if indicators is not None else list(INDICATOR_DIRECTION)
    scored = compute_ibfpi(panel, indicator_cols=cols, indicator_weights=weights, directions=directions)
    merged = cross_bank_aggregate(scored).merge(repo, on="period", how="inner").dropna()
    return spearman(merged["repo_rate"], merged["ibfpi_system"])


def weight_sensitivity(panel: pd.DataFrame, repo: pd.DataFrame, n_draws: int = 300,
                       seed: int = 11) -> pd.DataFrame:
    """rho under `n_draws` random indicator weightings drawn uniformly from
    the simplex (Dirichlet(1,...,1)). One row per draw with the weights.

    The composite is linear in the weights and the robust z-scores do not
    depend on them, so the per-period bank-average z-scores are computed
    once and each draw is a matrix product (same result as rebuilding the
    index, far faster)."""
    rng = np.random.default_rng(seed)
    cols = list(INDICATOR_DIRECTION)
    scored = compute_ibfpi(panel)
    zbar = scored.groupby("period")[[f"z_{c}" for c in cols]].mean()
    merged = zbar.merge(repo, left_index=True, right_on="period", how="inner").dropna()
    Z = merged[[f"z_{c}" for c in cols]].to_numpy()
    rows = []
    for w in rng.dirichlet(np.ones(len(cols)), size=n_draws):
        rows.append({**{f"w_{c}": wc for c, wc in zip(cols, w)},
                     "rho": spearman(merged["repo_rate"], pd.Series(Z @ w, index=merged.index)).rho})
    return pd.DataFrame(rows)


def leave_one_out(panel: pd.DataFrame, repo: pd.DataFrame) -> pd.DataFrame:
    """rho with each indicator dropped in turn (the rest equal-weighted)."""
    cols = list(INDICATOR_DIRECTION)
    out = [{"variant": "All five (baseline)", "rho": system_rho(panel, repo).rho}]
    for c in cols:
        r = system_rho(panel, repo, indicators=[k for k in cols if k != c])
        out.append({"variant": f"Without {INDICATOR_LABELS[c]}", "rho": r.rho, "p_value": r.p_value})
    return pd.DataFrame(out)


def direction_flips(panel: pd.DataFrame, repo: pd.DataFrame) -> pd.DataFrame:
    """rho with each indicator's direction coefficient reversed in turn."""
    out = []
    for c, d in INDICATOR_DIRECTION.items():
        flipped = {**INDICATOR_DIRECTION, c: -d}
        r = system_rho(panel, repo, directions=flipped)
        out.append({"variant": f"Flip {INDICATOR_LABELS[c]} ({d:+d} → {-d:+d})", "rho": r.rho,
                    "p_value": r.p_value})
    return pd.DataFrame(out)


@dataclass
class RegressionResult:
    label: str
    slope: float
    se: float
    p_value: float
    ci_low: float
    ci_high: float
    n: int
    se_type: str


def newey_west_lags(n: int) -> int:
    """Rule-of-thumb HAC lag length: floor(4 * (n / 100) ** (2 / 9))."""
    return max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))


def _ols(y: np.ndarray, X: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    return beta, resid, xtx_inv


def _result(label, slope, se, dof, n, se_type) -> RegressionResult:
    if dof is None:  # large-sample (normal) reference for robust SEs
        p = 2 * stats.norm.sf(abs(slope / se))
        crit = stats.norm.ppf(0.975)
    else:
        p = 2 * stats.t.sf(abs(slope / se), df=dof)
        crit = stats.t.ppf(0.975, df=dof)
    return RegressionResult(label, float(slope), float(se), float(p), float(slope - crit * se),
                            float(slope + crit * se), int(n), se_type)


def fixed_effects_regression(scored: pd.DataFrame, repo: pd.DataFrame) -> list[RegressionResult]:
    """iBFPI on the repo rate, three ways (numpy only):

    1. Bank fixed effects (within-bank OLS), conventional SEs with the
       degrees of freedom reduced for the absorbed bank means.
    2. The same slope, SEs clustered by bank (CR1). With five banks this
       is unreliable and is labelled as such.
    3. System iBFPI time series on the repo rate with Newey-West (Bartlett
       HAC) SEs, which allow for autocorrelated errors.
    No macro controls: quarterly GDP and CPI series are not in this project.
    """
    d = scored[["bank", "period", "ibfpi"]].merge(repo, on="period", how="inner").dropna()
    n, n_banks = len(d), d["bank"].nunique()
    y = (d["ibfpi"] - d.groupby("bank")["ibfpi"].transform("mean")).to_numpy()
    x = (d["repo_rate"] - d.groupby("bank")["repo_rate"].transform("mean")).to_numpy().reshape(-1, 1)
    beta, resid, xtx_inv = _ols(y, x)
    dof = n - n_banks - 1
    se_conv = np.sqrt(resid @ resid / dof * xtx_inv[0, 0])
    results = [_result("Bank fixed effects", beta[0], se_conv, dof, n, "conventional")]
    if n_banks >= 2:  # clustering needs at least two clusters
        meat = np.zeros((1, 1))
        for g in d["bank"].unique():
            m = (d["bank"] == g).to_numpy()
            sg = x[m].T @ resid[m]
            meat += np.outer(sg, sg)
        corr = n_banks / (n_banks - 1) * (n - 1) / (n - 1 - n_banks)
        se_cl = np.sqrt(corr * (xtx_inv @ meat @ xtx_inv)[0, 0])
        results.append(_result("Bank fixed effects, clustered by bank", beta[0], se_cl, n_banks - 1, n,
                               f"clustered, {n_banks} banks — too few clusters to rely on"))
    system = cross_bank_aggregate(scored).merge(repo, on="period", how="inner").dropna().sort_values("period")
    T = len(system)
    X = np.column_stack([np.ones(T), system["repo_rate"].to_numpy()])
    b, u, inv = _ols(system["ibfpi_system"].to_numpy(), X)
    lags = newey_west_lags(T)
    xu = X * u[:, None]
    S = xu.T @ xu
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = xu[L:].T @ xu[:-L]
        S += w * (G + G.T)
    se_hac = np.sqrt((inv @ S @ inv)[1, 1])
    results.append(_result("System iBFPI, Newey-West", b[1], se_hac, None, T, f"HAC, {lags} lags"))
    return results
