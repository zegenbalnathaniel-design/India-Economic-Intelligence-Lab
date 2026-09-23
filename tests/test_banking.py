"""Unit tests for analysis.banking."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from analysis import banking


def test_robust_zscore_zero_when_constant():
    s = pd.Series([0.02] * 10)
    z = banking.robust_zscore(s)
    assert (z == 0).all()


def test_robust_zscore_direction_flips_sign():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z_up = banking.robust_zscore(s, direction=+1)
    z_dn = banking.robust_zscore(s, direction=-1)
    assert np.allclose(z_up.values, -z_dn.values)


def test_robust_zscore_matches_manual_computation():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = banking.robust_zscore(s, direction=+1)
    # median = 3, MAD = median(|1-3|,|2-3|,|3-3|,|4-3|,|5-3|) = median(2,1,0,1,2) = 1
    # z = (x - 3) / (1.4826 * 1)
    expected = (s - 3.0) / (banking.MAD_SCALE * 1.0)
    assert np.allclose(z.values, expected.values)


def _mini_panel() -> pd.DataFrame:
    dates = pd.date_range("2020-03-31", periods=8, freq="QE")
    rows = []
    for bank in ["A", "B"]:
        for i, d in enumerate(dates):
            rows.append(dict(
                bank=bank, period=d,
                ppnr_to_assets=0.02 + 0.001 * i,
                cet1_ratio=0.15 + 0.002 * i,
                nco_rate=0.01,
                lcr=1.3,
                unrealised_loss_to_cet1=0.02,
            ))
    return pd.DataFrame(rows)


def test_compute_ibfpi_produces_expected_columns():
    scored = banking.compute_ibfpi(_mini_panel())
    for k in banking.INDICATOR_DIRECTION:
        assert f"z_{k}" in scored.columns
    assert "ibfpi" in scored.columns


def test_cross_bank_aggregate_equal_weight_matches_group_mean():
    scored = banking.compute_ibfpi(_mini_panel())
    agg = banking.cross_bank_aggregate(scored)
    manual = scored.groupby("period")["ibfpi"].mean().reset_index()
    merged = agg.merge(manual, on="period")
    assert np.allclose(merged["ibfpi_system"].values, merged["ibfpi"].values)


def test_spearman_returns_nan_when_too_few_points():
    a = pd.Series([1.0, 2.0])
    b = pd.Series([2.0, 4.0])
    r = banking.spearman(a, b)
    assert math.isnan(r.rho)


def test_spearman_positive_for_monotone_series():
    a = pd.Series(range(10))
    b = pd.Series(range(10)) ** 2
    r = banking.spearman(a, b)
    assert math.isclose(r.rho, 1.0, rel_tol=1e-9)
    assert r.n == 10


def test_regime_split_classifies_directions():
    dates = pd.date_range("2020-03-31", periods=10, freq="QE")
    repo = [4.0, 4.0, 4.0, 4.5, 5.0, 5.5, 5.5, 5.0, 4.5, 4.0]
    ibfpi = [0.1] * 10
    df = pd.DataFrame({"period": dates, "repo_rate": repo, "ibfpi_system": ibfpi})
    labelled, _, _, _ = banking.regime_split(df)
    assert set(labelled["regime"].unique()).issubset({"rising", "falling", "stable"})
