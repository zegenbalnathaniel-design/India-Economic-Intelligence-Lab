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
) -> pd.DataFrame:
    """Compute iBFPI for every (bank, period) row.

    Parameters
    ----------
    panel : DataFrame
        Long-form: columns include `bank`, `period` (date) and the five
        indicators. Values are decimal fractions or ratios in native
        units (they are standardised internally, so scales don't matter).

    Returns
    -------
    DataFrame
        Original columns plus one Z-column per indicator and an
        `ibfpi` column equal to the equal-weight mean of the Z-columns.
    """
    df = panel.copy()
    for col in indicator_cols:
        if col not in df.columns:
            raise KeyError(f"panel missing indicator column: {col}")
        direction = INDICATOR_DIRECTION[col]
        # Standardise per bank so within-bank history is the reference.
        z_col = f"z_{col}"
        df[z_col] = (
            df.groupby("bank", group_keys=False)[col]
            .apply(lambda s: robust_zscore(s, direction=direction))
        )
    z_cols = [f"z_{c}" for c in indicator_cols]
    df["ibfpi"] = df[z_cols].mean(axis=1)
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
