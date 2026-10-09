"""Unit tests for analysis.econometrics (Regression workbench) and the
workbench variable catalogue."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from analysis import econometrics as em
from analysis import relationships as rel
from analysis import workbench_catalogue as wc


# ------------------------------------------------------------------ helpers

def _design(n=40, seed=1, k=2):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = 1.5 + X @ np.arange(1, k + 1) + rng.normal(scale=0.7 + 0.5 * np.abs(X[:, 0]), size=n)
    cols = [f"x{j}" for j in range(k)]
    d = pd.DataFrame(X, columns=cols)
    d["y"] = y
    return d, cols


def _hand_ols(d, cols):
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy() for c in cols])
    y = d["y"].to_numpy()
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    n, p = X.shape
    s2 = e @ e / (n - p)
    se = np.sqrt(np.diag(s2 * XtXi))
    r2 = 1 - (e @ e) / np.sum((y - y.mean()) ** 2)
    adj = 1 - (1 - r2) * (n - 1) / (n - p)
    return X, y, b, e, se, r2, adj, XtXi


def _frame(keys, vals, key="year"):
    return pd.DataFrame({key: keys, "value": vals})


def _dv(id_, role, keys, vals, tf="level", lag=0, key="year", exclude=None, unit="u"):
    return em.DesignVariable(id=id_, label=id_.upper(), short=id_, role=role, frame=_frame(keys, vals, key),
                             tf=tf, lag=lag, unit=unit, status="VERIFIED", source=f"src {id_}",
                             period="p", exclude=exclude or {})


# ------------------------------------------------------------------ OLS vs hand numpy

def test_ols_matches_hand_numpy_computation():
    d, cols = _design(k=3)
    fit = em.fit_ols(d, "y", cols, se_type="nonrobust")
    X, y, b, e, se, r2, adj, _ = _hand_ols(d, cols)
    np.testing.assert_allclose(fit.table["coef"], b, rtol=1e-10)
    np.testing.assert_allclose(fit.table["std_err"], se, rtol=1e-10)
    np.testing.assert_allclose(fit.table["t"], b / se, rtol=1e-10)
    assert fit.r_squared == pytest.approx(r2, rel=1e-12)
    assert fit.adj_r_squared == pytest.approx(adj, rel=1e-12)
    np.testing.assert_allclose(fit.residuals, e, atol=1e-10)
    n, p = X.shape
    assert fit.n == n and fit.k == 3 and fit.df_resid == n - p and fit.df_model == 3
    # F-test of joint significance, by hand.
    f_hand = (r2 / 3) / ((1 - r2) / (n - p))
    assert fit.f_stat == pytest.approx(f_hand, rel=1e-10)
    # 95% CI = b ± t(0.975, n-p) * se
    from scipy import stats
    tc = stats.t.ppf(0.975, n - p)
    np.testing.assert_allclose(fit.table["ci_low"], b - tc * se, rtol=1e-10)
    np.testing.assert_allclose(fit.table["ci_high"], b + tc * se, rtol=1e-10)
    np.testing.assert_allclose(fit.table["p"], 2 * stats.t.sf(np.abs(b / se), n - p), rtol=1e-8)


def test_simple_ols_agrees_with_existing_relationships_ols():
    d, cols = _design(k=1, seed=7)
    fit = em.fit_ols(d, "y", cols)
    old = rel.ols(d["x0"], d["y"])
    assert fit.coef("x0") == pytest.approx(old.slope, rel=1e-10)
    assert fit.table.loc[1, "std_err"] == pytest.approx(old.slope_se, rel=1e-10)
    assert fit.r_squared == pytest.approx(old.r_squared, rel=1e-10)


def test_hc1_se_equals_statsmodels_and_hand_sandwich():
    d, cols = _design(k=2, seed=3)
    fit = em.fit_ols(d, "y", cols, se_type="HC1")
    X, y, b, e, _, _, _, XtXi = _hand_ols(d, cols)
    n, p = X.shape
    meat = X.T @ (X * (e ** 2)[:, None])
    se_hand = np.sqrt(np.diag(XtXi @ meat @ XtXi * n / (n - p)))
    ref = sm.OLS(y, X).fit(cov_type="HC1")
    np.testing.assert_allclose(fit.table["std_err"], ref.bse, rtol=1e-10)
    np.testing.assert_allclose(fit.table["std_err"], se_hand, rtol=1e-10)
    np.testing.assert_allclose(fit.table["coef"], b, rtol=1e-10)
    # inference uses t(n - p) for every SE type
    from scipy import stats
    np.testing.assert_allclose(fit.table["p"], 2 * stats.t.sf(np.abs(b / se_hand), n - p), rtol=1e-8)


def test_hac_se_equals_statsmodels_and_hand_newey_west():
    d, cols = _design(n=50, k=2, seed=5)
    L = em.newey_west_lags(50)
    assert L == math.floor(4 * (50 / 100) ** (2 / 9)) == 3
    fit = em.fit_ols(d, "y", cols, se_type="HAC")
    assert fit.hac_lags == L
    X, y, b, e, _, _, _, XtXi = _hand_ols(d, cols)
    u = X * e[:, None]
    S = u.T @ u
    for j in range(1, L + 1):
        w = 1 - j / (L + 1)
        G = u[j:].T @ u[:-j]
        S += w * (G + G.T)
    se_hand = np.sqrt(np.diag(XtXi @ S @ XtXi))
    ref = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    np.testing.assert_allclose(fit.table["std_err"], ref.bse, rtol=1e-10)
    np.testing.assert_allclose(fit.table["std_err"], se_hand, rtol=1e-10)
    # explicit lag override
    fit2 = em.fit_ols(d, "y", cols, se_type="HAC", hac_lags=1)
    ref2 = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    np.testing.assert_allclose(fit2.table["std_err"], ref2.bse, rtol=1e-10)


def test_newey_west_lag_rule():
    assert em.newey_west_lags(5) == 2        # 4·(0.05)^(2/9) = 2.06
    assert em.newey_west_lags(1) == 1
    assert em.newey_west_lags(100) == 4
    assert em.newey_west_lags(12) == math.floor(4 * 0.12 ** (2 / 9))


def test_fit_refuses_unidentified_models():
    d, cols = _design(k=2, seed=2)
    d["x2"] = d["x0"] + 2 * d["x1"]          # exact linear combination
    with pytest.raises(em.ModelError, match="perfect multicollinearity"):
        em.fit_ols(d, "y", cols + ["x2"])
    d["c"] = 3.0
    with pytest.raises(em.ModelError, match="constant"):
        em.fit_ols(d, "y", ["x0", "c"])
    with pytest.raises(em.ModelError, match="at least"):
        em.fit_ols(d.head(3), "y", ["x0", "x1"])
    d.loc[0, "x0"] = np.nan
    with pytest.raises(em.ModelError, match="missing"):
        em.fit_ols(d, "y", ["x0"])


# ------------------------------------------------------------------ VIF

def test_vif_on_constructed_collinear_example():
    rng = np.random.default_rng(11)
    n = 60
    x0 = rng.normal(size=n)
    x1 = rng.normal(size=n)
    x2 = x0 + x1 + rng.normal(scale=0.05, size=n)     # nearly collinear
    x3 = rng.normal(size=n)                            # independent
    d = pd.DataFrame({"x0": x0, "x1": x1, "x2": x2, "x3": x3})
    d["y"] = x0 - x3 + rng.normal(size=n)
    fit = em.fit_ols(d, "y", ["x0", "x1", "x2", "x3"])
    vif = em.vif_table(fit).set_index("term")["VIF"]

    def hand_vif(target, others):
        Xo = np.column_stack([np.ones(n)] + [d[o] for o in others])
        bb = np.linalg.lstsq(Xo, d[target], rcond=None)[0]
        r = d[target] - Xo @ bb
        r2 = 1 - (r @ r) / np.sum((d[target] - d[target].mean()) ** 2)
        return 1 / (1 - r2)

    for c in ("x0", "x1", "x2", "x3"):
        assert vif[c] == pytest.approx(hand_vif(c, [o for o in vif.index if o != c]), rel=1e-8)
    assert vif["x2"] > em.VIF_HIGH and vif["x0"] > em.VIF_HIGH
    assert vif["x3"] < 2
    assert "Severe multicollinearity" in em.vif_interpretation(em.vif_table(fit))
    low = em.fit_ols(d, "y", ["x0", "x3"])
    assert "Low multicollinearity" in em.vif_interpretation(em.vif_table(low))


# ------------------------------------------------------------------ ADF

def test_adf_small_n_gives_warning_not_verdict():
    rng = np.random.default_rng(0)
    r = em.adf_test(rng.normal(size=12), name="short")
    assert r.status == "too_small" and not r.meaningful
    assert "no verdict" in r.verdict.lower()
    assert "very little power" in r.interpretation
    assert r.nonstationary_or_unknown
    assert np.isfinite(r.statistic)                 # numbers still shown
    tiny = em.adf_test([1.0, 2.0, 3.0, 2.0, 5.0], name="tiny")
    assert tiny.status == "not_computed" and not np.isfinite(tiny.statistic)


def test_adf_verdicts_on_long_series():
    rng = np.random.default_rng(42)
    stationary = em.adf_test(rng.normal(size=200), name="white noise")
    assert stationary.status == "stationary" and stationary.p_value < 0.05
    walk = em.adf_test(np.cumsum(rng.normal(size=200)) + 50, name="random walk")
    assert walk.status == "unit_root" and walk.p_value >= 0.05
    assert "unit root cannot be rejected" in walk.interpretation


def test_longest_consecutive_run():
    keys, vals = em.longest_consecutive_run([1961, 1971, 2002, 2003, 2004, 2006, 2007], [1, 2, 3, 4, 5, 6, np.nan])
    assert keys == [2002, 2003, 2004]
    np.testing.assert_allclose(vals, [3, 4, 5])


def test_spurious_regression_warning_logic():
    ur = em.ADFResult("y", 40, -1.0, 0.7, 0, -2.9, "c", "unit_root", "", "")
    st_ = em.ADFResult("x", 40, -5.0, 0.001, 0, -2.9, "c", "stationary", "", "")
    small = em.ADFResult("z", 12, -1.0, 0.7, 0, -3.3, "c", "too_small", "", "")
    assert "Spurious-regression risk" in em.spurious_regression_warning(("y", "level"), [("x2", "log")],
                                                                        {"y": ur, "x2": ur})
    # untestable short series still trigger the warning (cannot rule out a unit root)
    assert em.spurious_regression_warning(("y", "log"), [("z", "level")], {"y": ur, "z": small}) is not None
    # differenced dependent variable or differenced regressors: no levels-on-levels regression
    assert em.spurious_regression_warning(("y", "diff"), [("x2", "level")], {"y": ur, "x2": ur}) is None
    assert em.spurious_regression_warning(("y", "level"), [("x2", "pct_change")], {"y": ur, "x2": ur}) is None
    # stationary regressor or dependent variable: no banner
    assert em.spurious_regression_warning(("y", "level"), [("x", "level")], {"y": ur, "x": st_}) is None
    assert em.spurious_regression_warning(("x", "level"), [("y", "level")], {"y": ur, "x": st_}) is None


# ------------------------------------------------------------------ transforms

def test_log_disabled_for_non_positive_values_with_reason():
    opts = em.transform_options([3.0, 0.0, -1.0, 2.0], time_series=True)
    assert opts["log"] is not None and "2 of 4 values are ≤ 0" in opts["log"]
    assert opts["pct_change"] is not None
    assert opts["diff"] is None and opts["level"] is None
    assert "log" not in em.available_transforms([1.0, -1.0], time_series=False)
    with pytest.raises(ValueError, match="not available"):
        em.transform_series([2000, 2001], [1.0, -1.0], "log", time_series=True)
    cs = em.transform_options([1.0, 2.0], time_series=False)
    assert cs["log"] is None and cs["diff"] == "only for time series" and cs["pct_change"] == "only for time series"
    with pytest.raises(ValueError):
        em.transform_series(["A", "B"], [1.0, 2.0], "diff", time_series=False)


def test_diff_pct_and_lag_respect_gaps():
    keys = [2000, 2001, 2002, 2004, 2005]
    vals = [10.0, 12.0, 15.0, 20.0, 30.0]
    d = em.transform_series(keys, vals, "diff", time_series=True)
    assert dict(zip(d.data["key"], d.data["value"])) == {2001: 2.0, 2002: 3.0, 2005: 10.0}
    reasons = dict(zip(d.undefined["key"], d.undefined["reason"]))
    assert set(reasons) == {2000, 2004}
    assert "start of the series" in reasons[2000] and "gap" in reasons[2004]
    p = em.transform_series(keys, vals, "pct_change", time_series=True)
    assert dict(zip(p.data["key"], p.data["value"]))[2005] == pytest.approx(50.0)
    lag = em.transform_series(keys, vals, "level", 1, time_series=True)
    got = dict(zip(lag.data["key"], lag.data["value"]))
    assert got == {2001: 10.0, 2002: 12.0, 2003: 15.0, 2005: 20.0, 2006: 30.0}
    assert dict(zip(lag.data["key"], lag.data["source_key"]))[2005] == 2004
    lag_reasons = dict(zip(lag.undefined["key"], lag.undefined["reason"]))
    assert set(lag_reasons) == {2000, 2004}       # 1999 and 2003 not observed
    dl = em.transform_series(keys, vals, "diff", 2, time_series=True)
    assert dict(zip(dl.data["key"], dl.data["value"])) == {2003: 2.0, 2004: 3.0, 2007: 10.0}
    lg = em.transform_series(keys, vals, "log", time_series=True)
    np.testing.assert_allclose(lg.data["value"], np.log(vals))
    with pytest.raises(ValueError):
        em.transform_series(keys, vals, "level", 4, time_series=True)
    with pytest.raises(ValueError, match="missing values"):
        em.transform_series(keys, [1.0, np.nan, 2.0, 3.0, 4.0], "level", time_series=True)


def test_align_design_accounts_for_every_observation():
    y = _dv("y", "dependent", [2000, 2001, 2002, 2003, 2004, 2005, 2006], [1, 2, 3, 4, 5, np.nan, 7.0])
    x = _dv("x", "explanatory", [1999, 2000, 2001, 2003, 2004, 2005, 2006], [5, 6, 7, 8, 9, 10, 11.0], tf="diff")
    z = _dv("z", "explanatory", [2000, 2001, 2002, 2003, 2004, 2005, 2006], [1, 3, 2, 5, 4, 6, 9.0], lag=1,
            exclude={2003: "tentative row"})
    al = em.align_design([y, x, z], key="year", time_series=True, sample=(2000, 2006))
    # kept: years where y observed, Δx defined (needs t-1 observed), z_{t-1} defined and not excluded
    assert al.data["year"].tolist() == [2001, 2006]
    row = al.data.set_index("year")
    assert row.loc[2001, x.column] == 1.0 and row.loc[2006, x.column] == 1.0
    assert row.loc[2001, z.column] == 1.0 and row.loc[2006, z.column] == 6.0
    assert row.loc[2006, f"{z.column}__src_key"] == 2005
    reasons = dict(zip(al.dropped["year"], al.dropped["reason"]))
    cats = dict(zip(al.dropped["year"], al.dropped["category"]))
    assert cats[1999] == "outside sample period" and cats[2007] == "outside sample period"
    assert "z (t−1)" in reasons[2000] and "1999" in reasons[2000]          # lag undefined
    assert "Δ x" not in reasons[2000]                                     # 1999 observed, so Δx(2000) exists
    assert "not present in x source" in reasons[2002]
    assert "Δ x" in reasons[2003] and "gap" in reasons[2003]
    # z's 2003 row is excluded: z(t−1) at 2004 needs it; z(t−1) at 2003 uses 2002 and is fine
    assert "z (t−1): needs z for 2003, which is excluded — tentative row" in reasons[2004]
    assert cats[2004] == "excluded / tentative"
    assert "z (t−1)" not in reasons[2003]
    assert "y: value missing in source" in reasons[2005]
    # every key seen is either kept or dropped exactly once
    seen = {1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007}   # 2007 = z(t−1) from 2006
    assert set(al.data["year"]) | set(al.dropped["year"]) == seen
    assert set(al.data["year"]).isdisjoint(al.dropped["year"])
    assert al.n + al.n_dropped == al.n_universe == len(seen)
    assert al.reason_summary()["observations"].sum() == al.n_dropped
    cov = al.coverage.set_index("variable")
    assert cov.loc["y", "missing in source"] == 1 and cov.loc["z (t−1)", "excluded rows"] == 1
    assert not al.consecutive


def test_align_design_cross_section_and_name_mismatch():
    y = _dv("y", "dependent", ["A", "B", "C", "Jammu & Kashmir", "D"], [1, 2, 3, 4, 5.0], key="state")
    x = _dv("x", "explanatory", ["A", "B", "C", "Jammu and Kashmir", "E"], [2, 4, 7, 1, 2.0], key="state",
            tf="log")
    al = em.align_design([y, x], key="state", time_series=False)
    assert al.data["state"].tolist() == ["A", "B", "C"]
    np.testing.assert_allclose(al.data[x.column], np.log([2, 4, 7]))
    assert al.possible_name_mismatches == [("Jammu & Kashmir", "Jammu and Kashmir")]
    reasons = dict(zip(al.dropped["state"], al.dropped["reason"]))
    assert "possible name mismatch" in reasons["Jammu & Kashmir"]
    assert reasons["D"] == "not present in x source" and reasons["E"] == "not present in y source"
    with pytest.raises(ValueError):
        em.align_design([y], key="state", time_series=False)


def test_pairwise_correlations_match_relationships():
    d, cols = _design(k=2, seed=9)
    pc = em.pairwise_correlations(d, ["y"] + cols, {"y": "Y"})
    assert len(pc) == 3
    c = rel.correlations(d["y"], d["x0"])
    first = pc.iloc[0]
    assert first["variable 1"] == "Y" and first["Pearson r"] == pytest.approx(c.pearson_r)
    assert first["Spearman ρ"] == pytest.approx(c.spearman_rho)


# ------------------------------------------------------------------ diagnostics

@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_diagnostics_match_statsmodels():
    from statsmodels.stats.diagnostic import acorr_breusch_godfrey, het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson, jarque_bera
    d, cols = _design(n=45, k=2, seed=4)
    fit = em.fit_ols(d, "y", cols)
    ref = sm.OLS(d["y"].to_numpy(), sm.add_constant(d[cols].to_numpy())).fit()
    bp = em.breusch_pagan(fit)
    assert bp.p_value == pytest.approx(het_breuschpagan(ref.resid, ref.model.exog)[1])
    rng = np.random.default_rng(0)
    xh = rng.uniform(1, 10, 300)
    het = pd.DataFrame({"x": xh, "y": 2 + xh + rng.normal(scale=xh, size=300)})
    assert em.breusch_pagan(em.fit_ols(het, "y", ["x"])).verdict.startswith("Heteroskedasticity")
    jb = em.jarque_bera_test(fit)
    assert jb.statistic == pytest.approx(jarque_bera(ref.resid)[0])
    dw = em.durbin_watson_test(fit)
    assert dw.statistic == pytest.approx(durbin_watson(ref.resid))
    bg = em.breusch_godfrey(fit, 2)
    assert bg.p_value == pytest.approx(acorr_breusch_godfrey(ref, nlags=2)[1])
    assert em.breusch_godfrey(em.fit_ols(d.head(5), "y", cols), 3).verdict == "Not computed"
    osm, osr, s, i = em.qq_points(fit.residuals)
    assert len(osm) == fit.n and np.all(np.diff(osr) >= 0)


# ------------------------------------------------------------------ interpretation text

def _sentence(x_tf, y_tf, coef=0.8, x_lag=0, k=1, p=0.01):
    return em.coefficient_sentence(x_short="NSDP", x_tf=x_tf, x_lag=x_lag, x_unit="₹", y_short="MPCE", y_tf=y_tf,
                                   y_unit="₹ per person per month", coef=coef, ci_low=coef - 0.2,
                                   ci_high=coef + 0.2, p=p, n_regressors=k, se_label="HC1 robust")


def test_interpretation_log_log_says_elasticity():
    s = _sentence("log", "log")
    assert "elasticity of 0.8" in s and "1% higher NSDP" in s and "0.8% higher" in s
    assert "is associated" in s


def test_interpretation_other_forms_and_never_causal():
    semi = _sentence("level", "log", coef=0.05)
    assert "semi-elasticity" in semi.lower() and "5% higher" in semi
    lin = _sentence("level", "level", coef=-2.5, k=3)
    assert "one-unit increase in NSDP (+₹1)" in lin and "lower" in lin
    assert "holding the other included regressors fixed" in lin
    linlog = _sentence("log", "level", coef=150.0)
    assert "1% higher NSDP" in linlog and "₹1.50 per person per month higher" in linlog
    lagged = _sentence("diff", "diff", x_lag=2)
    assert "(t−2)" in lagged and "change" in lagged
    ns = _sentence("level", "level", p=0.4)
    assert "not statistically distinguishable" in ns
    for s in (semi, lin, linlog, lagged, ns, _sentence("pct_change", "pct_change")):
        low = s.lower()
        assert "associated" in low
        for bad in ("causes", "caused", "effect of", "leads to", "impact"):
            assert bad not in low


def test_fit_summary_and_static_text():
    d, cols = _design(n=15, k=2, seed=8)
    fit = em.fit_ols(d, "y", cols, se_type="HC1")
    txt = em.fit_summary_text(fit, y_term="Y")
    assert "n = 15" in txt and "R² =" in txt and "adjusted R²" in txt and "Small sample" in txt
    assert "Wald F-test" in txt and "HC1" in txt
    assert "not causation" in em.CAUSATION_NOTE.lower()
    assert any("Stationarity" in a for a, _ in em.ASSUMPTIONS)


# ------------------------------------------------------------------ exports

def test_reproducibility_record_contains_every_setting():
    y = _dv("y", "dependent", list(range(2000, 2030)), np.linspace(1, 9, 30) + np.sin(np.arange(30)))
    x1 = _dv("x1", "explanatory", list(range(1998, 2030)), np.exp(np.linspace(0, 2, 32)), tf="log", lag=1)
    x2 = _dv("x2", "explanatory", list(range(2000, 2030)), np.cos(np.arange(30)) + 5, tf="diff",
             exclude={2029: "tentative"})
    al = em.align_design([y, x1, x2], key="year", time_series=True, sample=(2002, 2028))
    fit = em.fit_ols(al.data, al.y.column, [v.column for v in al.xs], se_type="HAC",
                     hac_lags=em.newey_west_lags(al.n), labels={v.column: v.term for v in al.variables})
    rec = em.reproducibility_record(alignment=al, fit=fit, level="india_annual", level_label="All-India",
                                    se_type="HAC", hac_lags=fit.hac_lags, adf_regression="c",
                                    include_tentative=False, generated_utc="2026-01-01T00:00:00Z")
    js = em.record_to_json(rec)
    back = json.loads(js)
    s = back["settings"]
    assert s["level"] == "india_annual" and s["key"] == "year" and s["time_series"] is True
    assert s["dependent"]["id"] == "y" and s["dependent"]["transform"] == "level"
    assert [(v["id"], v["transform"], v["lag"]) for v in s["explanatory"]] == [("x1", "log", 1), ("x2", "diff", 0)]
    assert s["explanatory"][1]["excluded_rows"] == {"2029": "tentative"}
    assert all(v["unit"] and v["status"] and v["source"] for v in [s["dependent"]] + s["explanatory"])
    assert s["sample_period"] == [2002, 2028]
    assert s["se_type"] == "HAC" and s["hac_lags"] == fit.hac_lags and "Newey–West" in s["hac_lag_rule"]
    assert s["include_tentative_rows"] is False and s["adf_regression"] == "c"
    assert set(back["versions"]) >= {"python", "numpy", "pandas", "statsmodels", "scipy"}
    assert back["versions"]["statsmodels"] == __import__("statsmodels").__version__
    assert back["versions"]["numpy"] == np.__version__ and back["versions"]["pandas"] == pd.__version__
    assert back["alignment"]["n_analysis_sample"] == al.n == fit.n
    assert back["alignment"]["keys_used"] == al.data["year"].tolist()
    assert len(back["alignment"]["dropped"]) == al.n_dropped
    assert [c["term"] for c in back["results"]["coefficients"]] == ["Intercept", "log x1 (t−1)", "Δ x2"]
    assert back["results"]["r_squared"] == pytest.approx(fit.r_squared)
    assert "NaN" not in js


def test_regression_table_and_aligned_export():
    y = _dv("y", "dependent", list(range(2000, 2012)), [3, 4, 4, 6, 7, 6, 8, 9, 9, 11, 12, 12.0])
    x = _dv("x", "explanatory", list(range(2000, 2012)), [1, 2, 2, 3, 4, 4, 5, 6, 7, 7, 8, 9.0], unit="₹")
    al = em.align_design([y, x], key="year", time_series=True)
    fit = em.fit_ols(al.data, al.y.column, [x.column], labels={x.column: x.term})
    rt = em.regression_table(fit, al)
    assert rt["term"].tolist() == ["Intercept", "x"]
    for c in ("coefficient", "std_error", "t_stat", "p_value", "ci_low_95", "ci_high_95", "r_squared",
              "adj_r_squared", "n", "se_type", "f_stat"):
        assert c in rt.columns
    ex = em.aligned_data_export(al, fit)
    assert len(ex) == al.n
    assert (ex["X: x [unit]"] == "₹").all() and (ex["Y: y [status]"] == "VERIFIED").all()
    assert "residual" in ex.columns and "X: x [raw value]" in ex.columns


# ------------------------------------------------------------------ catalogue on real data

def test_catalogue_variables_load_from_real_files():
    tbl = wc.catalogue_table()
    assert set(tbl["level"]) == {"State cross-section", "All-India annual time series"}
    assert (tbl["n (non-missing)"] > 0).all()
    for v in wc.catalogue():
        f = v.frame()
        assert list(f.columns) == [wc.LEVEL_KEY[v.level], "value", "note"]
        assert not f[wc.LEVEL_KEY[v.level]].duplicated().any()
        assert v.status in {"VERIFIED", "PARTIAL", "SPLICED", "DERIVED"}
    # ILLUSTRATIVE series are never offered
    assert not any("ILLUSTRATIVE" in v.status for v in wc.catalogue())


def test_catalogue_matches_loaders_exactly():
    from data_sources import loaders
    b1 = loaders.load_wil_income_shares()
    f = wc.get("in_b1_top_1").frame()
    assert f["year"].tolist() == b1["year"].tolist() and f["value"].tolist() == b1["top_1"].tolist()
    gcf = wc.get("in_gcf_public_nonfinancial_corp").frame().set_index("year")
    raw = loaders.load_gross_capital_formation()
    raw = raw[raw["sector"] == "public_nonfinancial_corp"].set_index("year")
    assert gcf.loc[2011, "value"] == raw.loc["2011-12", "gross_capital_formation_inr_crore"]
    assert wc.get("in_c1_top_1").tentative == ((2023, wc.TENTATIVE_C1),)
    un = wc.get("st_unemployment").frame()
    assert "India" not in set(un["state"]) and len(un) == 29


def _real(vid, role, tf="level", lag=0, include_tentative=False):
    c = wc.get(vid)
    return em.DesignVariable(c.id, c.label, c.short, role, c.frame(), tf, lag, c.unit, c.status, c.source,
                             c.period_text(), {} if include_tentative else dict(c.tentative))


def test_tentative_wealth_row_excluded_and_reported_on_real_data():
    al = em.align_design([_real("in_c1_top_1", "dependent"), _real("in_c2_forbes_wealth_pct_nni", "explanatory")],
                         key="year", time_series=True)
    assert 2023 not in set(al.data["year"])
    # 2023 is also absent from Table C.2, but the exclusion is reported first
    row = al.dropped.set_index("year").loc[2023]
    assert row["category"] == "excluded / tentative" and "tentative" in row["reason"]
    # survey years before 2002 align (Forbes starts 1988 -> only 1991 survives), gaps are flagged
    assert al.data["year"].tolist()[0] == 1991 and not al.consecutive
    # differenced wealth share: 2002 has no previous year (2001 not observed), 1991 neither
    d = em.align_design([_real("in_c1_top_1", "dependent", "diff"),
                         _real("in_c2_forbes_wealth_pct_nni", "explanatory", "diff")], key="year", time_series=True)
    assert d.data["year"].min() == 2003 and d.consecutive
    inc = em.align_design([_real("in_c1_top_1", "dependent", include_tentative=True),
                           _real("in_b1_top_1", "explanatory")], key="year", time_series=True)
    assert "excluded / tentative" not in set(inc.dropped["category"])


def test_workbench_reproduces_hypothesis_library_inc_mpce():
    """Same pair, same transforms as the library preset 'inc_mpce' (log-log, FY 2023-24): the
    workbench's n and OLS slope must equal the bivariate page's."""
    from analysis import hypotheses as hyp
    ev = hyp.evaluate(hyp.build("inc_mpce"))
    lib = rel.ols(ev.data["x"], ev.data["y"])
    c_y, c_x = wc.get("st_mpce_urban"), wc.get("st_nsdp_current")
    al = em.align_design([
        em.DesignVariable(c_y.id, c_y.label, c_y.short, "dependent", c_y.frame("2023-24"), "log"),
        em.DesignVariable(c_x.id, c_x.label, c_x.short, "explanatory", c_x.frame("2023-24"), "log"),
    ], key="state", time_series=False)
    fit = em.fit_ols(al.data, al.y.column, [al.xs[0].column])
    assert al.n == len(ev.data)
    assert fit.coef(al.xs[0].column) == pytest.approx(lib.slope, rel=1e-10)
    assert fit.table.loc[1, "std_err"] == pytest.approx(lib.slope_se, rel=1e-10)


def test_previous_period_excluded_blocks_difference():
    y = _dv("y", "dependent", [2000, 2001, 2002, 2003], [1, 2, 4, 3.0])
    x = _dv("x", "explanatory", [2000, 2001, 2002, 2003], [5, 7, 6, 9.0], tf="diff", exclude={2001: "tentative"})
    al = em.align_design([y, x], key="year", time_series=True)
    reasons = dict(zip(al.dropped["year"], al.dropped["reason"]))
    assert "x: excluded — tentative" in reasons[2001]
    assert "previous period 2001 is excluded" in reasons[2002]
    assert al.data["year"].tolist() == [2003]


def test_worked_example_on_real_data_reproduces_numpy():
    """Top 1% income share on Forbes billionaire wealth (WIL B.1, C.2)."""
    def dv(vid, role):
        c = wc.get(vid)
        return em.DesignVariable(c.id, c.label, c.short, role, c.frame(), "level", 0, c.unit, c.status,
                                 c.source, c.period_text(), dict(c.tentative))
    al = em.align_design([dv("in_b1_top_1", "dependent"), dv("in_c2_forbes_wealth_pct_nni", "explanatory")],
                         key="year", time_series=True)
    assert al.n == 35 and al.data["year"].min() == 1988 and al.data["year"].max() == 2022
    fit = em.fit_ols(al.data, al.y.column, [al.xs[0].column], se_type="HAC")
    xs, ys = al.data[al.xs[0].column].to_numpy(), al.data[al.y.column].to_numpy()
    slope = np.polyfit(xs, ys, 1)[0]
    assert fit.coef(al.xs[0].column) == pytest.approx(slope, rel=1e-10)
    assert fit.hac_lags == 3
