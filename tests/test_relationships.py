"""Unit tests for analysis.relationships."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from analysis import relationships as rel
from analysis.housing import financial_year_of_quarter


# ---------------------------------------------------------------- alignment

def _xy_frames():
    x = pd.DataFrame({"state": ["A", "B", "C", "India", "Jammu & Kashmir", "E"],
                      "inc": [1.0, 2.0, 3.0, 9.0, 4.0, np.nan]})
    y = pd.DataFrame({"state": ["A", "B", "C", "D", "All-India", "Jammu and Kashmir", "E"],
                      "u": [5.0, 6.0, 7.0, 8.0, 9.0, 1.0, 2.0]})
    return x, y


def test_align_inner_join_and_every_drop_has_a_reason():
    x, y = _xy_frames()
    res = rel.align_observations(
        x, y, "state", "inc", "u", x_label="Income", y_label="Unemp",
        exclude={"India": "aggregate", "All-India": "aggregate"},
    )
    assert res.data["state"].tolist() == ["A", "B", "C"]
    assert res.data["x"].tolist() == [1.0, 2.0, 3.0]
    assert res.data["y"].tolist() == [5.0, 6.0, 7.0]
    reasons = dict(zip(res.dropped["state"], res.dropped["reason"]))
    assert reasons["India"].startswith("excluded")
    assert reasons["All-India"].startswith("excluded")
    assert reasons["D"] == "not present in Income source"
    assert reasons["E"] == "Income value missing"
    assert "possible name mismatch" in reasons["Jammu & Kashmir"]
    # The Y-side spelling is reported once, via the X-side row, not twice.
    assert "Jammu and Kashmir" not in reasons
    assert res.possible_name_mismatches == [("Jammu & Kashmir", "Jammu and Kashmir")]
    # Accounting: every non-excluded key in either source is either kept or dropped.
    assert res.n == 3
    assert res.n_x_source == 5 and res.n_y_source == 6


def test_align_rejects_duplicate_keys():
    x = pd.DataFrame({"k": ["A", "A"], "v": [1.0, 2.0]})
    y = pd.DataFrame({"k": ["A"], "w": [1.0]})
    with pytest.raises(ValueError, match="duplicate"):
        rel.align_observations(x, y, "k", "v", "w")


def test_align_rejects_missing_column():
    x = pd.DataFrame({"k": ["A"], "v": [1.0]})
    with pytest.raises(ValueError, match="missing column"):
        rel.align_observations(x, x, "k", "v", "nope")


def test_align_on_dates_sorted():
    d = pd.to_datetime(["2020-06-30", "2020-03-31", "2020-09-30"])
    x = pd.DataFrame({"period": d, "a": [2.0, 1.0, 3.0]})
    y = pd.DataFrame({"period": d[:2], "b": [20.0, 10.0]})
    res = rel.align_observations(x, y, "period", "a", "b")
    assert list(res.data["x"]) == [1.0, 2.0]
    assert res.n_dropped == 1


def test_normalise_key():
    assert rel.normalise_key("Jammu & Kashmir") == rel.normalise_key("jammu and  kashmir")
    assert rel.normalise_key("Dadra & Nagar Haveli") != rel.normalise_key("Delhi")


# ------------------------------------------------------- frequency alignment

def test_quarterly_to_fy_averages_and_drops_partial_years():
    q = pd.DataFrame({
        "quarter": ["Jun-2013", "Sep-2013", "Dec-2013", "Mar-2014", "Jun-2014", "Sep-2014"],
        "v": [1.0, 2.0, 3.0, 6.0, 10.0, 20.0],
    })
    full = rel.quarterly_to_financial_year(q, "quarter", "v", financial_year_of_quarter)
    assert full.data["financial_year"].tolist() == ["2013-14"]
    assert full.data["value"].iloc[0] == pytest.approx(3.0)
    assert full.dropped["financial_year"].tolist() == ["2014-15"]
    assert "2 of 4" in full.dropped["reason"].iloc[0]

    partial = rel.quarterly_to_financial_year(q, "quarter", "v", financial_year_of_quarter,
                                              require_full_year=False)
    assert partial.data["financial_year"].tolist() == ["2013-14", "2014-15"]
    assert partial.data["value"].iloc[1] == pytest.approx(15.0)
    assert partial.dropped.empty


def test_quarterly_to_fy_ignores_missing_quarters_rather_than_filling():
    q = pd.DataFrame({"quarter": ["Jun-2013", "Sep-2013", "Dec-2013", "Mar-2014"],
                      "v": [1.0, np.nan, 3.0, 5.0]})
    res = rel.quarterly_to_financial_year(q, "quarter", "v", financial_year_of_quarter)
    assert res.data.empty  # only 3 real quarters -> incomplete, not interpolated
    assert "3 of 4" in res.dropped["reason"].iloc[0]


# -------------------------------------------------------------- transforms

def test_available_transforms():
    assert rel.available_transforms([1, 2, 3], time_series=False) == ["none", "log", "zscore"]
    assert rel.available_transforms([1, 2, 3], time_series=True) == ["none", "log", "zscore", "pct_change"]
    assert rel.available_transforms([-1, 2, 3], time_series=True) == ["none", "zscore"]
    assert rel.available_transforms([0, 2, 3], time_series=False) == ["none", "zscore"]
    assert rel.available_transforms([5, 5, 5], time_series=False) == ["none", "log"]


def test_apply_transform_values():
    s = pd.Series([1.0, 2.0, 4.0])
    assert rel.apply_transform(s, "log").tolist() == pytest.approx(np.log([1, 2, 4]).tolist())
    z = rel.apply_transform(s, "zscore")
    assert z.mean() == pytest.approx(0.0, abs=1e-12)
    assert z.std(ddof=1) == pytest.approx(1.0)
    pc = rel.apply_transform(s, "pct_change")
    assert math.isnan(pc.iloc[0])
    assert pc.iloc[1:].tolist() == pytest.approx([100.0, 100.0])
    with pytest.raises(ValueError):
        rel.apply_transform(pd.Series([1.0, -1.0]), "log")
    with pytest.raises(ValueError):
        rel.apply_transform(pd.Series([1.0, -1.0]), "pct_change")
    with pytest.raises(ValueError):
        rel.apply_transform(pd.Series([2.0, 2.0]), "zscore")
    with pytest.raises(ValueError):
        rel.apply_transform(s, "cube")


def test_transform_pair_drops_first_row_for_pct_change_then_zscores_remaining_sample():
    x = pd.DataFrame({"t": ["2001-02", "2002-03", "2003-04", "2004-05"], "a": [100.0, 110.0, 99.0, 120.0]})
    y = pd.DataFrame({"t": ["2001-02", "2002-03", "2003-04", "2004-05"], "b": [1.0, 3.0, 2.0, 5.0]})
    aligned = rel.align_observations(x, y, "t", "a", "b")
    tp = rel.transform_pair(aligned, "pct_change", "zscore")
    assert tp.data["t"].tolist() == ["2002-03", "2003-04", "2004-05"]
    assert tp.dropped["t"].tolist() == ["2001-02"]
    assert tp.data["x"].iloc[0] == pytest.approx(10.0)
    # z-score is computed over the 3 rows actually analysed, not all 4
    assert tp.data["y"].mean() == pytest.approx(0.0, abs=1e-12)
    assert tp.data["y"].std(ddof=1) == pytest.approx(1.0)
    assert tp.data["y_raw"].tolist() == [3.0, 2.0, 5.0]


# ------------------------------------------------------ correlation and OLS

def test_correlations_match_scipy():
    rng = np.random.default_rng(0)
    x = rng.normal(size=30)
    y = 0.5 * x + rng.normal(size=30)
    c = rel.correlations(x, y)
    pr, pp = stats.pearsonr(x, y)
    sr, sp = stats.spearmanr(x, y)
    assert c.n == 30
    assert c.pearson_r == pytest.approx(pr)
    assert c.pearson_p == pytest.approx(pp)
    assert c.spearman_rho == pytest.approx(sr)
    assert c.spearman_p == pytest.approx(sp)


def test_correlations_nan_for_small_or_constant():
    assert math.isnan(rel.correlations([1, 2], [3, 4]).pearson_r)
    assert math.isnan(rel.correlations([1, 1, 1], [3, 4, 5]).spearman_rho)


def test_spearman_detects_monotone_nonlinear():
    x = np.arange(1, 11, dtype=float)
    c = rel.correlations(x, np.exp(x))
    assert c.spearman_rho == pytest.approx(1.0)
    assert c.pearson_r < 1.0


def test_ols_matches_scipy_linregress_and_ci():
    rng = np.random.default_rng(42)
    x = rng.uniform(0, 10, size=25)
    y = 3.0 - 0.7 * x + rng.normal(scale=1.5, size=25)
    fit = rel.ols(x, y)
    lr = stats.linregress(x, y)
    assert fit.slope == pytest.approx(lr.slope)
    assert fit.intercept == pytest.approx(lr.intercept)
    assert fit.r_squared == pytest.approx(lr.rvalue ** 2)
    assert fit.slope_se == pytest.approx(lr.stderr)
    assert fit.intercept_se == pytest.approx(lr.intercept_stderr)
    assert fit.slope_p == pytest.approx(lr.pvalue)
    tcrit = stats.t.ppf(0.975, 23)
    assert fit.slope_ci_low == pytest.approx(lr.slope - tcrit * lr.stderr)
    assert fit.slope_ci_high == pytest.approx(lr.slope + tcrit * lr.stderr)
    assert fit.residuals.sum() == pytest.approx(0.0, abs=1e-9)
    assert np.allclose(fit.fitted + fit.residuals, y)
    # A wider CI level gives a wider interval
    fit99 = rel.ols(x, y, ci_level=0.99)
    assert fit99.slope_ci_high - fit99.slope_ci_low > fit.slope_ci_high - fit.slope_ci_low


def test_ols_exact_line():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    fit = rel.ols(x, 2 * x + 1)
    assert fit.slope == pytest.approx(2.0)
    assert fit.intercept == pytest.approx(1.0)
    assert fit.r_squared == pytest.approx(1.0)
    assert fit.slope_p == 0.0


def test_ols_insufficient():
    fit = rel.ols([1.0, 2.0], [1.0, 2.0])
    assert not fit.ok and fit.n == 2
    assert not rel.ols([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]).ok
    with pytest.raises(ValueError):
        rel.ols([1, 2, 3], [1, 2, 3], ci_level=1.5)


def test_zscore_slope_equals_pearson_r():
    rng = np.random.default_rng(3)
    x = rng.normal(size=40)
    y = x + rng.normal(size=40)
    zx = (x - x.mean()) / x.std(ddof=1)
    zy = (y - y.mean()) / y.std(ddof=1)
    assert rel.ols(zx, zy).slope == pytest.approx(rel.correlations(x, y).pearson_r)


# -------------------------------------------------- lagged / rolling / gaps

def test_lagged_correlation_recovers_known_lead():
    rng = np.random.default_rng(7)
    x = rng.normal(size=60)
    y = np.r_[rng.normal(size=2), x[:-2]]  # y_t = x_{t-2}: X leads Y by 2
    df = pd.DataFrame({"x": x, "y": y})
    lc = rel.lagged_correlation(df, "x", "y", range(-3, 4))
    best = lc.loc[lc["r"].idxmax()]
    assert int(best["lag"]) == 2
    assert best["r"] == pytest.approx(1.0)
    assert lc.set_index("lag").loc[2, "n"] == 58
    assert lc.set_index("lag").loc[0, "n"] == 60


def test_lagged_correlation_spearman_option():
    df = pd.DataFrame({"x": np.arange(10.0), "y": np.exp(np.arange(10.0))})
    lc = rel.lagged_correlation(df, "x", "y", [0], method="spearman")
    assert lc["r"].iloc[0] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        rel.lagged_correlation(df, "x", "y", [0], method="kendall")


def test_rolling_correlation_windows():
    df = pd.DataFrame({"t": list(range(8)),
                       "x": [1, 2, 3, 4, 5, 6, 7, 8],
                       "y": [1, 2, 3, 4, 4, 3, 2, 1]})
    rc = rel.rolling_correlation(df, "t", "x", "y", window=4)
    assert len(rc) == 5
    assert rc["t"].tolist() == [3, 4, 5, 6, 7]
    assert rc["window_start"].tolist() == [0, 1, 2, 3, 4]
    assert rc["r"].iloc[0] == pytest.approx(1.0)
    assert rc["r"].iloc[-1] == pytest.approx(-1.0)
    expected = df["x"].rolling(4).corr(df["y"]).dropna().to_numpy()
    assert np.allclose(rc["r"].to_numpy(), expected)
    with pytest.raises(ValueError):
        rel.rolling_correlation(df, "t", "x", "y", window=2)


def test_consecutive_periods():
    assert rel.consecutive_periods(["2013-14", "2014-15", "2015-16"])
    assert not rel.consecutive_periods(["2013-14", "2015-16"])
    q = pd.to_datetime(["2018-06-30", "2018-09-30", "2018-12-31", "2019-03-31"])
    assert rel.consecutive_periods(list(q))
    assert not rel.consecutive_periods([q[0], q[2]])


def test_sample_size_warning():
    assert rel.sample_size_warning(25) is None
    assert "Small sample" in rel.sample_size_warning(19)
    assert "too few" in rel.sample_size_warning(2)


def test_regression_summary_table():
    x = np.arange(10.0)
    y = 2 * x + np.sin(x)
    t = rel.regression_summary_table(rel.correlations(x, y), rel.ols(x, y), meta={"X": "a", "Y": "b"})
    assert list(t.columns) == ["statistic", "value"]
    assert t["statistic"].iloc[0] == "X"
    assert "OLS slope 95% CI lower" in t["statistic"].tolist()


# ------------------------------------------------- real-data consistency

def test_initial_income_vs_growth_reproduces_regional_beta_convergence():
    """OLS of avg growth on log(initial income) via this module must equal
    analysis.regional.beta_convergence on the same real spliced series."""
    from analysis import regional
    from data_sources import loaders

    nsdp = loaders.load_nsdp_spliced()
    beta = regional.beta_convergence(nsdp)
    first_year = sorted(nsdp["financial_year"].unique())[0]
    initial = nsdp[nsdp["financial_year"] == first_year]
    aligned = rel.align_observations(
        initial, beta.per_state, "state",
        "percapita_nsdp_constant_prices_inr_SPLICED", "avg_annual_growth_pct",
    )
    assert aligned.n == len(beta.per_state)
    tp = rel.transform_pair(aligned, "log", "none")
    fit = rel.ols(tp.data["x"], tp.data["y"])
    assert fit.slope == pytest.approx(beta.slope)
    assert fit.intercept == pytest.approx(beta.intercept)
    assert fit.r_squared == pytest.approx(beta.r_squared)
