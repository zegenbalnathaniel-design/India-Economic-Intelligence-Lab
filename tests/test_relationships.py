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


# ------------------------------------------------- period keys / differences

def test_period_ordinals_and_consecutive_years():
    assert rel.period_ordinals([2001, 2002, 2005]).tolist() == [2001, 2002, 2005]
    assert rel.period_ordinals(np.array([2001, 2002])).tolist() == [2001, 2002]
    assert rel.period_ordinals(["2011-12", "2012-13"]).tolist() == [2011, 2012]
    q = rel.period_ordinals(list(pd.to_datetime(["2018-06-30", "2018-09-30"])))
    assert q[1] - q[0] == 1
    assert rel.period_ordinals(["Kerala", "Goa"]) is None
    assert rel.consecutive_periods([2002, 2003, 2004])
    assert not rel.consecutive_periods([1991, 2002, 2003])


def test_first_differences_never_bridge_a_gap():
    # WIL-style key: survey years, then annual.
    df = pd.DataFrame({"year": [1961, 1971, 2002, 2003, 2004],
                       "x": [1.0, 2.0, 5.0, 6.0, 8.0], "y": [10.0, 9.0, 4.0, 4.5, 3.0]})
    d = rel.first_differences(df, "year")
    assert d.data["year"].tolist() == [2003, 2004]
    assert d.data["x"].tolist() == [1.0, 2.0]
    assert d.data["y"].tolist() == [0.5, -1.5]
    assert d.data["x_level"].tolist() == [6.0, 8.0]
    reasons = dict(zip(d.dropped["year"], d.dropped["reason"]))
    assert reasons[1961].startswith("first observation")
    assert "10 periods earlier" in reasons[1971]
    assert "31 periods earlier" in reasons[2002] and "no interpolation" in reasons[2002]
    # unsorted input is sorted first; every input row is either kept or reported
    d2 = rel.first_differences(df.sample(frac=1.0, random_state=1), "year")
    assert d2.data["year"].tolist() == [2003, 2004]
    assert len(d.data) + len(d.dropped) == len(df)


def test_first_differences_on_financial_years_and_quarters():
    df = pd.DataFrame({"financial_year": ["2011-12", "2012-13", "2014-15"], "x": [1.0, 3.0, 4.0],
                       "y": [2.0, 2.0, 7.0], "x_raw": [1, 3, 4], "y_raw": [2, 2, 7]})
    d = rel.first_differences(df, "financial_year")
    assert d.data["financial_year"].tolist() == ["2012-13"]
    assert d.data["x_raw"].tolist() == [3]
    q = pd.DataFrame({"period": pd.to_datetime(["2018-03-31", "2018-06-30", "2018-09-30"]),
                      "x": [1.0, 2.0, 4.0], "y": [1.0, 1.0, 1.0]})
    assert rel.first_differences(q, "period").data["x"].tolist() == [1.0, 2.0]


def test_first_differences_rejects_non_period_keys():
    df = pd.DataFrame({"state": ["A", "B"], "x": [1.0, 2.0], "y": [1.0, 2.0]})
    with pytest.raises(ValueError, match="period keys"):
        rel.first_differences(df, "state")


def test_trend_check_and_spurious_warning():
    years = list(range(2000, 2020))
    rng = np.random.default_rng(5)
    up = np.arange(20.0) + rng.normal(scale=0.5, size=20)
    down = -np.arange(20.0) + rng.normal(scale=0.5, size=20)
    noise = rng.normal(size=20)
    tu, td, tn = (rel.trend_check(years, v) for v in (up, down, noise))
    assert tu.trending and tu.direction == "upward" and tu.n == 20
    assert td.trending and td.direction == "downward"
    assert not tn.trending and tn.direction == "none"
    w = rel.spurious_trend_warning(tu, td, "A", "B")
    assert w and "Both series trend" in w and "negative levels correlation" in w
    assert "positive levels correlation" in rel.spurious_trend_warning(tu, tu)
    assert rel.spurious_trend_warning(tu, tn) is None
    # gaps count as elapsed time, and NaN values are ignored, not filled
    t = rel.trend_check([1961, 1971, 2002, 2003], [1.0, np.nan, 3.0, 4.0])
    assert t.n == 3
    with pytest.raises(ValueError):
        rel.trend_check(["A", "B", "C"], [1, 2, 3])


# --------------------------------------------------------------- verdicts

@pytest.mark.parametrize("rho,expected", [
    (0.0, "weak"), (0.29, "weak"), (-0.299, "weak"), (0.3, "moderate"), (-0.45, "moderate"),
    (0.599, "moderate"), (0.6, "strong"), (-0.95, "strong"), (1.0, "strong"), (float("nan"), "undetermined"),
])
def test_strength_thresholds(rho, expected):
    assert rel.classify_strength(rho) == expected
    assert rel.WEAK_BELOW == 0.3 and rel.STRONG_FROM == 0.6


def test_verdict_labels_and_significance():
    v = rel.verdict(rel.CorrelationSummary(0.9, 1e-6, 0.82, 1e-5, 21))
    assert v.label == "Strong positive association"
    assert v.significant
    assert v.headline == "Strong positive association (Spearman ρ = 0.82, p < 0.001, n = 21)"
    v2 = rel.verdict(rel.CorrelationSummary(-0.4, 0.2, -0.35, 0.12, 15))
    assert v2.label == "Moderate negative association" and not v2.significant
    assert "not statistically significant at the 5% level" in v2.headline
    assert "p = 0.120" in v2.headline
    v3 = rel.verdict(rel.correlations([1.0, 2.0], [3.0, 4.0]))
    assert not v3.computable and v3.label == "Not computable" and "n = 2" in v3.headline


def test_differencing_outcome_cases():
    def v(rho, p, n=20):
        return rel.verdict(rel.CorrelationSummary(rho, p, rho, p, n))
    lv = v(0.85, 1e-6)
    assert rel.differencing_outcome(lv, v(0.6, 0.004)) == "survives"
    assert rel.differencing_outcome(lv, v(0.4, 0.09)) == "weakens"
    assert rel.differencing_outcome(lv, v(0.05, 0.8)) == "vanishes"
    assert rel.differencing_outcome(lv, v(-0.1, 0.7)) == "vanishes"
    assert rel.differencing_outcome(lv, v(-0.6, 0.01)) == "reverses"
    nan = float("nan")
    assert rel.differencing_outcome(lv, v(nan, nan, 1)) == "not_computable"


def test_spearman_exact_p_small_samples():
    # perfect rank agreement at n = 5: 2 of 5! orderings have |rho| = 1
    assert rel.spearman_exact_p([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) == pytest.approx(2 / 120)
    c = rel.correlations([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
    assert c.spearman_rho == pytest.approx(-1.0) and c.spearman_p == pytest.approx(2 / 120)
    # matches brute-force enumeration on a tied example
    from itertools import permutations
    x, y = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], [2.0, 1.0, 4.0, 4.0, 6.0, 5.0]
    rho = stats.spearmanr(x, y)[0]
    ry = stats.rankdata(y)
    rhos = [stats.pearsonr(stats.rankdata(x), ry[list(p)])[0] for p in permutations(range(6))]
    expected = np.mean(np.abs(rhos) >= abs(rho) - 1e-12)
    assert rel.spearman_exact_p(x, y) == pytest.approx(expected)
    with pytest.raises(ValueError):
        rel.spearman_exact_p(range(9), range(9))


def test_influential_observation_finds_injected_outlier():
    x = np.arange(1.0, 13.0)
    y = x + np.array([0.1, -0.1] * 6)
    y[5] = -20.0  # one wild point
    keys = [f"k{i}" for i in range(12)]
    inf = rel.influential_observation(keys, x, y)
    assert inf.loo_key == "k5" and inf.resid_key == "k5"
    assert inf.rho_without == pytest.approx(rel.correlations(np.delete(x, 5), np.delete(y, 5)).spearman_rho)
    assert inf.delta > 0
    assert rel.influential_observation(["a", "b", "c"], [1, 2, 3], [1, 2, 3]) is None


# ------------------------------------------------------- analysis text

def _fit_inputs(x, y):
    return rel.correlations(x, y), rel.ols(x, y)


def test_analysis_text_strong_positive_cross_section():
    rng = np.random.default_rng(11)
    x = np.linspace(1, 30, 30)
    y = 2 * x + rng.normal(scale=2, size=30)
    corr, fit = _fit_inputs(x, y)
    keys = [f"S{i}" for i in range(30)]
    s = rel.analysis_sentences(x_name="income", y_name="spending", corr=corr, fit=fit, obs_noun="states",
                               x_unit="₹", y_unit="₹",
                               influence=rel.influential_observation(keys, x, y), x_sd=float(np.std(x, ddof=1)))
    text = " ".join(s)
    assert 3 <= len(s) <= 6
    assert "strong positive association" in text
    assert f"Spearman ρ = {corr.spearman_rho:.2f}" in text
    assert "30 states" in text
    assert "statistically distinguishable from zero" in text
    assert f"R² = {fit.r_squared:.2f}" in text
    assert "higher" in text and "₹" in text
    assert "Main caveat" in text and "causes" in text  # default caveat is causality


def test_analysis_text_negative_not_significant_small_n():
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    y = [3.0, 1.0, 2.5, 0.5, 2.8, 0.9]
    corr, fit = _fit_inputs(x, y)
    s = rel.analysis_sentences(x_name="X", y_name="Y", corr=corr, fit=fit)
    text = " ".join(s)
    assert rel.verdict(corr).direction == "negative"
    assert "negative association" in text
    assert "not statistically distinguishable" in text
    assert "only n = 6 observations" in text  # small-n caveat chosen automatically
    assert 3 <= len(s) <= 6


def test_analysis_text_flags_mechanical_pair_and_differencing():
    years = list(range(1990, 2015))
    rng = np.random.default_rng(2)
    top = 30 + 0.8 * np.arange(25) + rng.normal(scale=0.4, size=25)
    bottom = 100 - top - 40 + rng.normal(scale=0.2, size=25)
    lv = pd.DataFrame({"year": years, "x": top, "y": bottom})
    d = rel.first_differences(lv, "year")
    corr, fit = _fit_inputs(lv["x"], lv["y"])
    s = rel.analysis_sentences(
        x_name="the Top 10% share", y_name="the Bottom 50% share", corr=corr, fit=fit, obs_noun="years",
        x_unit="percentage points", y_unit="percentage points", time_series=True,
        levels_corr=corr, diff_corr=rel.correlations(d.data["x"], d.data["y"]),
        x_trend=rel.trend_check(years, top), y_trend=rel.trend_check(years, bottom),
        caveats=("mechanical",), caveat_note="the shares sum to 100",
    )
    text = " ".join(s)
    assert 3 <= len(s) <= 6
    assert "strong negative" in text
    assert "by construction" in text and "Main caveat: the two variables are slices" in text
    assert "Both series trend over time" in text
    assert "first differences" in text and "n = 24" in text
    assert "1 percentage point of the Top 10% share" in text and "lower" in text


def test_analysis_text_trend_only_levels_relationship_does_not_survive():
    years = list(range(2000, 2030))
    rng = np.random.default_rng(9)
    a = np.cumsum(rng.normal(loc=1.0, scale=0.3, size=30))
    b = np.cumsum(rng.normal(loc=1.0, scale=0.3, size=30))  # independent increments
    lv = pd.DataFrame({"year": years, "x": a, "y": b})
    d = rel.first_differences(lv, "year")
    lc, dc = rel.correlations(a, b), rel.correlations(d.data["x"], d.data["y"])
    assert rel.differencing_outcome(rel.verdict(lc), rel.verdict(dc)) in ("vanishes", "weakens")
    s = rel.analysis_sentences(x_name="A", y_name="B", corr=lc, fit=rel.ols(a, b), obs_noun="years",
                               time_series=True, levels_corr=lc, diff_corr=dc,
                               x_trend=rel.trend_check(years, a), y_trend=rel.trend_check(years, b))
    text = " ".join(s)
    assert "strong positive" in text
    assert "prone to being spurious" in text
    assert ("does not survive differencing" in text) or ("not statistically significant" in text)
    assert "Main caveat: both series trend over time" in text


def test_analysis_text_illustrative_status_and_not_computable():
    x, y = np.arange(10.0), np.arange(10.0) ** 1.5
    corr, fit = _fit_inputs(x, y)
    text = rel.analysis_paragraph(x_name="repo", y_name="iBFPI", corr=corr, fit=fit,
                                  statuses=("APPROXIMATE", "ILLUSTRATIVE (synthetic)"), caveats=("proxy",))
    assert "ILLUSTRATIVE" in text and "Main caveat: at least one series is ILLUSTRATIVE" in text
    c2, f2 = _fit_inputs([1.0, 2.0], [2.0, 3.0])
    s = rel.analysis_sentences(x_name="X", y_name="Y", corr=c2, fit=f2, obs_noun="years", form="differences")
    assert len(s) == 3 and "Only 2 usable years" in s[0] and "no correlation" in s[1]


def test_analysis_text_log_log_elasticity_and_pearson_spearman_gap():
    x = np.exp(np.linspace(1, 3, 20))
    y = x ** 0.5
    corr, fit = _fit_inputs(np.log(x), np.log(y))
    text = rel.analysis_paragraph(x_name="income", y_name="consumption", corr=corr, fit=fit, x_tf="log", y_tf="log")
    assert "elasticity of 0.50" in text and "1% higher income" in text
    # a monotone but very curved relationship: Spearman 1, Pearson clearly lower
    xx = np.arange(1.0, 16.0)
    yy = np.exp(xx)
    c3, f3 = _fit_inputs(xx, yy)
    assert "Pearson being much weaker than Spearman" in rel.analysis_paragraph(x_name="a", y_name="b", corr=c3, fit=f3)


def test_main_caveat_priority():
    assert rel.main_caveat(["proxy", "mechanical"], n=50)[0] == "mechanical"
    assert rel.main_caveat(["proxy"], n=50, statuses=["ILLUSTRATIVE"])[0] == "illustrative"
    assert rel.main_caveat([], n=10)[0] == "small_n"
    assert rel.main_caveat([], n=50, both_trending=True)[0] == "trend"
    assert rel.main_caveat([], n=50, both_trending=True, form="differences")[0] == "causality"
    assert set(rel.CAVEAT_PRIORITY) == set(rel.CAVEAT_TEXT)


# ------------------------------------------------- hypothesis library (real data)

VALID_STATUSES = {"VERIFIED", "PARTIAL", "SPLICED", "DERIVED", "ILLUSTRATIVE"}


@pytest.fixture(scope="module")
def library():
    from analysis import hypotheses as hyp
    return hyp


def test_every_hypothesis_builds_with_status_rationale_and_source(library):
    assert len(library.NEW_IDS) >= 6
    for hid in library.HYPOTHESIS_IDS:
        h = library.build(hid)
        assert h.question and h.rationale and h.source_line
        assert h.x.status in VALID_STATUSES and h.y.status in VALID_STATUSES
        assert set(h.caveats) <= set(rel.CAVEAT_TEXT)
        ev = library.evaluate(h)
        assert ev.aligned.n >= rel.MIN_OBS, hid
        # every non-excluded source key is either aligned or reported as dropped
        assert len(ev.aligned.data) + len(ev.aligned.dropped) >= max(ev.aligned.n_x_source, ev.aligned.n_y_source)


def test_wil_top1_income_vs_wealth_uses_real_rows_only(library):
    from data_sources import loaders
    h = library.build("wil_top1_income_vs_wealth")
    ev = library.evaluate(h)
    years = ev.aligned.data["year"].tolist()
    assert years == [1961, 1971, 1981, 1991] + list(range(2002, 2023))
    row = ev.aligned.data.set_index("year").loc[2022]
    assert (row["x"], row["y"]) == (22.6, 40.1)  # B.1 and C.1, 2022
    b1 = loaders.load_wil_income_shares().set_index("year")["top_1"]
    c1 = loaders.load_wil_wealth_shares().set_index("year")["top_1"]
    for _, r in ev.aligned.data.iterrows():
        assert r["x"] == b1[r["year"]] and r["y"] == c1[r["year"]]
    # first differences only over 2003-2022 (consecutive annual years)
    assert ev.diff.data["year"].tolist() == list(range(2003, 2023))


def test_tentative_2023_wealth_row_excluded_by_default(library):
    ev = library.evaluate(library.build("wil_top1_vs_bottom50_wealth"))
    assert 2023 not in ev.aligned.data["year"].tolist()
    reasons = dict(zip(ev.aligned.dropped["year"], ev.aligned.dropped["reason"]))
    assert "tentative" in reasons[2023]
    ev_t = library.evaluate(library.build("wil_top1_vs_bottom50_wealth", include_tentative=True))
    assert 2023 in ev_t.aligned.data["year"].tolist()
    assert ev_t.aligned.n == ev.aligned.n + 1


def test_mechanical_partition_pair_is_flagged(library):
    h = library.build("wil_bottom50_vs_top10_income")
    assert "mechanical" in h.caveats
    ev = library.evaluate(h)
    assert ev.aligned.n == 72 and ev.verdict.direction == "negative" and ev.verdict.strength == "strong"


def test_real_percapita_nni_loader_parses_without_filling():
    from data_sources import loaders
    nni = loaders.load_real_percapita_nni()
    assert nni["financial_year"].tolist() == ["2011-12", "2014-15", "2019-20", "2020-21",
                                              "2022-23", "2023-24", "2024-25"]
    assert nni["real_percapita_nni_inr"].tolist() == [63462, 72805, 94420, 86034, 100163, 108786, 114710]
    assert nni["value_as_published"].iloc[0] == "₹63,462"


def test_nni_hypothesis_small_n_and_no_differences(library):
    ev = library.evaluate(library.build("nni_vs_top10_income"))
    assert ev.aligned.data["year"].tolist() == [2011, 2014, 2019, 2020, 2022]
    assert ev.diff_verdict.n == 1 and not ev.diff_verdict.computable
    assert ev.outcome == "not_computable"


def test_overview_table_has_one_row_per_hypothesis(library):
    t = library.overview_table()
    assert t["id"].tolist() == library.HYPOTHESIS_IDS
    assert {"n", "Spearman ρ", "p-value", "Verdict", "Data status"} <= set(t.columns)
    assert (t["n"] >= rel.MIN_OBS).all()
    ts = t[t["Type"] == "time series"]
    assert (ts["Survives differencing?"] != "—").all()
