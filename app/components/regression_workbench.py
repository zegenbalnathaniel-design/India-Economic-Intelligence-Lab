"""Regression workbench — the econometrics mode of the Economic Relationships Lab.

UI only: every number comes from `analysis.econometrics` (pure
calculations) applied to variables from `analysis.workbench_catalogue`
(real files in data/, read through data_sources.loaders). Nothing is
fetched, filled or interpolated; every dropped observation is listed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analysis import econometrics as em
from analysis import relationships as rel
from analysis import workbench_catalogue as wc
from app.components.glossary import indicator_note
from app.components.theme import GOLD, MUTED, TURQUOISE, VERMILLION, callout, stat_card

DEFAULTS = {
    "state": ("st_mpce_urban", ["st_nsdp_current"]),
    "india_annual": ("in_b1_top_1", ["in_c2_forbes_wealth_pct_nni"]),
}
MAX_X = 6


def _select(widget, label: str, options: list, key: str, default, **kwargs):
    """Keyed widget whose Session-State value is always a valid option."""
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]
    return widget(label, options=options, key=key, **kwargs)


def _fmt(v, d: int = 3) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "n/a"
    if not np.isfinite(v):
        return "n/a"
    return f"{v:,.{d}f}" if abs(v) < 1e6 else f"{v:,.4g}"


def _fmt_p(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "n/a"
    if not np.isfinite(p):
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _var_label(v: wc.CatalogueVariable) -> str:
    return f"[{v.group}] {v.label} · {v.status}"


def _variable_controls(cv: wc.CatalogueVariable, role: str, level: str, col) -> tuple[str, str, int]:
    """Period, transform and lag selectors for one variable; returns
    (period, transform, lag)."""
    ts = level == "india_annual"
    with col:
        tag = "Y" if role == "dependent" else "X"
        st.markdown(f"**{tag} · {cv.label}**")
        period = cv.default_period
        if len(cv.periods) > 1:
            period = _select(st.selectbox, "Year of the cross-section", list(cv.periods),
                             f"wb_period_{level}_{role}_{cv.id}", cv.default_period)
        frame = cv.frame(period)
        opts = em.transform_options(frame["value"].dropna().tolist(), time_series=ts)
        avail = [t for t, why in opts.items() if why is None]
        tf = _select(st.selectbox, "Transform", avail, f"wb_tf_{level}_{role}_{cv.id}", "level",
                     format_func=em.TRANSFORM_LABELS.get)
        lag = 0
        if ts and role == "explanatory":
            lag = _select(st.selectbox, "Lag k (periods)", [0, 1, 2, 3], f"wb_lag_{level}_{cv.id}", 0,
                          format_func=lambda k: "none (t)" if k == 0 else f"t−{k}")
        off = [f"{em.TRANSFORM_LABELS[t].split(' (')[0]}: {why}" for t, why in opts.items()
               if why is not None and not (not ts and t in em.TS_ONLY_TRANSFORMS)]
        cap = f"{cv.status} · {cv.unit} · {cv.period_text(period)}"
        if cv.note:
            cap += f" · {cv.note}"
        st.caption(cap)
        if off:
            st.caption("Disabled — " + "; ".join(off) + ".")
    return period, tf, int(lag)


def render() -> None:
    st.header("Regression workbench")
    st.markdown(
        "Estimate a **multiple OLS regression** of one dependent variable on one or more explanatory "
        "variables chosen from the real series in this project, with an audited alignment, per-variable "
        "transforms and lags, robust standard errors, a full set of diagnostics with plain-language "
        "readings, and exports that let anyone reproduce the run. Variables can only be combined at the "
        "**same geographic level**: a cross-section of states, or all-India annual time series."
    )
    callout(
        "<b>Descriptive econometrics on observational data.</b> Every coefficient below is a partial "
        "correlation in a small sample — not a causal effect. No panel, instrumental-variable or other "
        "causal method is offered. Missing values are excluded and reported, never filled.",
        kind="warn",
    )

    # ------------------------------------------------------------------ W1
    st.subheader("W1 · Level and variables")
    level = st.radio("Geographic level", list(wc.LEVELS), format_func=wc.LEVELS.get, key="wb_level",
                     horizontal=True)
    ts = level == "india_annual"
    cat = wc.catalogue(level)
    by_id = {v.id: v for v in cat}
    ids = list(by_id)
    with st.expander(f"Variable catalogue — {len(cat)} variables at this level (with n)"):
        tbl = wc.catalogue_table(level)
        st.dataframe(tbl.drop(columns=["level"]), use_container_width=True, hide_index=True)
        st.caption("Not offered: " + "; ".join(f"**{a}** — {b}" for a, b in wc.NOT_OFFERED) + ".")

    y_default, x_default = DEFAULTS[level]
    y_id = _select(st.selectbox, "Dependent variable (Y)", ids, f"wb_y_{level}", y_default,
                   format_func=lambda i: _var_label(by_id[i]))
    x_opts = [i for i in ids if i != y_id]
    xkey = f"wb_x_{level}"
    if xkey in st.session_state:
        st.session_state[xkey] = [i for i in st.session_state[xkey] if i in x_opts][:MAX_X]
    else:
        st.session_state[xkey] = [i for i in x_default if i in x_opts]
    x_ids = st.multiselect(f"Explanatory variables (X) — up to {MAX_X}", x_opts, key=xkey,
                           format_func=lambda i: _var_label(by_id[i]), max_selections=MAX_X)
    if not x_ids:
        st.info("Choose at least one explanatory variable.")
        return

    chosen = [(y_id, "dependent")] + [(i, "explanatory") for i in x_ids]
    settings = {}
    cols = st.columns(min(3, len(chosen)))
    for j, (vid, role) in enumerate(chosen):
        settings[(vid, role)] = _variable_controls(by_id[vid], role, level, cols[j % len(cols)])

    has_tent = any(by_id[v].tentative for v, _ in chosen)
    include_tent = False
    if has_tent:
        include_tent = st.checkbox(
            "Include tentative rows", value=False, key="wb_tentative",
            help="WIL Table C.1 flags its 2023 row as tentative. Excluded by default and then listed in "
                 "the alignment report.")

    share = {}
    for vid, _ in chosen:
        if by_id[vid].share_group:
            share.setdefault(by_id[vid].share_group, []).append(by_id[vid].label)
    for grp, labs in share.items():
        if len(labs) > 1:
            callout("<b>Linked by construction.</b> " + " and ".join(labs) + " are parts of the same total "
                    "(group shares add up to 100%; sectors add up to total GCF), so part of any relationship "
                    "between them is arithmetic. A set that adds up exactly is refused as perfectly collinear.",
                    kind="warn")

    design = []
    for vid, role in chosen:
        cv = by_id[vid]
        period, tf, lag = settings[(vid, role)]
        design.append(em.DesignVariable(
            id=cv.id, label=cv.label, short=cv.short, role=role, frame=cv.frame(period), tf=tf, lag=lag,
            unit=cv.unit, status=cv.status, source=cv.source, period=cv.period_text(period),
            exclude={} if include_tent else dict(cv.tentative),
        ))

    # ------------------------------------------------------------------ W2
    st.subheader("W2 · Sample and alignment report")
    sample = None
    if ts:
        years = sorted({int(y) for d in design for y in d.frame.dropna(subset=["value"])["year"]})
        lo, hi = years[0], years[-1]
        if lo == hi:
            st.warning("The selected series cover a single year — no time-series regression is possible.")
            return
        skey = f"wb_sample_{lo}_{hi}"
        if skey not in st.session_state:
            st.session_state[skey] = (lo, hi)
        sample = st.slider("Sample period (years, inclusive)", min_value=lo, max_value=hi, key=skey,
                           help="Restricts which years enter the regression. Differences and lags use each "
                                "series' full history, so the first sample year can use a pre-sample value.")
        sample = (int(sample[0]), int(sample[1]))
    key = wc.LEVEL_KEY[level]
    al = em.align_design(design, key=key, time_series=ts, sample=sample)

    a1, a2, a3 = st.columns(3)
    with a1:
        stat_card("Analysis sample", f"n = {al.n}", f"inner join of {len(design)} variables on {key}")
    with a2:
        stat_card("Dropped", f"{al.n_dropped}", "every one listed with its reason")
    with a3:
        stat_card("Keys seen", f"{al.n_universe}", "in any selected source")
    summ = al.reason_summary()
    if not summ.empty:
        st.dataframe(summ.rename(columns={"category": "why dropped"}), use_container_width=True, hide_index=True)
    if not al.dropped.empty:
        with st.expander(f"All dropped observations ({al.n_dropped}) and why"):
            st.dataframe(al.dropped, use_container_width=True, hide_index=True)
    st.dataframe(al.coverage, use_container_width=True, hide_index=True)
    if al.possible_name_mismatches:
        callout("<b>Possible name mismatches — not joined:</b> "
                + "; ".join(f"'{a}' vs '{b}'" for a, b in al.possible_name_mismatches), kind="warn")
    if ts and al.n and not al.consecutive:
        callout("The aligned years are <b>not consecutive</b> (gaps, e.g. WIL wealth survey years before "
                "2002). Durbin–Watson, Breusch–Godfrey and Newey–West treat neighbouring rows as one period "
                "apart, which is not true across a gap.", kind="warn")
    if ts and any(v.id.startswith(("in_gcf", "in_real")) for v in design):
        st.caption(wc.FY_NOTE)

    k = len(al.xs)
    if al.n < k + 2:
        st.warning(f"Only {al.n} aligned observation(s) for {k} regressor(s) plus an intercept — at least "
                   f"{k + 2} are needed. Change the variables, transforms, lags or sample period.")
        return

    labels = {v.column: v.term for v in al.variables}
    obs_noun = wc.LEVEL_OBS_NOUN[level]

    # ------------------------------------------------------------------ W3
    st.subheader("W3 · Pairwise correlation (Pearson & Spearman)")
    pc = em.pairwise_correlations(al.data, [v.column for v in al.variables], labels)
    pc_show = pc.copy()
    for c in ("Pearson r", "Spearman ρ"):
        pc_show[c] = pc_show[c].map(lambda v: _fmt(v, 3))
    for c in ("Pearson p", "Spearman p"):
        pc_show[c] = pc_show[c].map(_fmt_p)
    st.dataframe(pc_show, use_container_width=True, hide_index=True)
    st.caption(f"Computed on the {al.n} aligned {obs_noun}, variables as transformed. Spearman p-values are "
               f"exact permutation p-values when n ≤ {rel.EXACT_SPEARMAN_MAX_N}. Pairwise correlations ignore "
               "the other variables; the regression below does not.")

    # ------------------------------------------------------------------ W4
    st.subheader("W4 · OLS estimates")
    se_opts = ["HAC", "nonrobust"] if ts else ["HC1", "nonrobust"]
    se_type = _select(st.radio, "Standard errors", se_opts, f"wb_se_{level}", se_opts[0],
                      format_func=lambda s: em.SE_LABELS[s].capitalize(), horizontal=True)
    hac_lags = em.newey_west_lags(al.n) if se_type == "HAC" else None
    if se_type == "HAC":
        st.caption(f"Newey–West lag rule: {em.HAC_LAG_RULE} → L = {hac_lags} for n = {al.n}.")
    try:
        fit = em.fit_ols(al.data, al.y.column, [v.column for v in al.xs], se_type=se_type, hac_lags=hac_lags,
                         labels=labels)
    except em.ModelError as exc:
        st.error(f"Model not estimated: {exc}")
        return

    tab = fit.table.drop(columns=["term"]).rename(columns={
        "label": "term", "coef": "coefficient", "std_err": "std. error", "t": "t", "p": "p-value",
        "ci_low": "95% CI low", "ci_high": "95% CI high"})
    show = tab.copy()
    for c in ("coefficient", "std. error", "95% CI low", "95% CI high"):
        show[c] = show[c].map(lambda v: _fmt(v, 4))
    show["t"] = show["t"].map(lambda v: _fmt(v, 2))
    show["p-value"] = show["p-value"].map(_fmt_p)
    st.markdown(f"**Dependent variable:** {al.y.term} · {al.y.unit or 'units as loaded'}")
    st.dataframe(show, use_container_width=True, hide_index=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        stat_card("n", f"{fit.n}", f"df model {int(fit.df_model)} · df resid {int(fit.df_resid)}")
    with m2:
        stat_card("R²", _fmt(fit.r_squared), f"adjusted {_fmt(fit.adj_r_squared)}")
    with m3:
        stat_card("F-test", _fmt(fit.f_stat, 2), f"p = {_fmt_p(fit.f_pvalue)}")
    with m4:
        stat_card("Standard errors", {"HAC": "Newey–West", "HC1": "HC1", "nonrobust": "Classical"}[se_type],
                  f"{hac_lags} lag(s)" if hac_lags else ("robust" if se_type == "HC1" else "homoskedastic"))
    callout("<b>Model fit.</b> " + em.fit_summary_text(fit, y_term=al.y.term, obs_noun=obs_noun), kind="note")

    st.markdown("**Reading the coefficients**")
    by_col = {v.column: v for v in al.xs}
    sentences = []
    for r in fit.table.itertuples(index=False):
        if r.term == "const":
            continue
        v = by_col[r.term]
        sentences.append(em.coefficient_sentence(
            x_short=v.short, x_tf=v.tf, x_lag=v.lag, x_unit=v.unit, y_short=al.y.short, y_tf=al.y.tf,
            y_unit=al.y.unit, coef=r.coef, ci_low=r.ci_low, ci_high=r.ci_high, p=r.p, n_regressors=fit.k,
            se_label=fit.se_short))
    st.markdown("\n".join(f"- {s}" for s in sentences))
    st.caption("The intercept is the fitted Y when every regressor is zero — often far outside the data, and "
               "rarely meaningful on its own.")

    # ------------------------------------------------------------------ W5
    st.subheader("W5 · Diagnostics")
    keys = al.data[key].astype(str)
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Residuals vs fitted", "Residual histogram",
                                                        "Normal QQ plot"))
    fig.add_trace(go.Scatter(x=fit.fitted, y=fit.residuals, mode="markers", text=keys,
                             marker=dict(color=TURQUOISE, size=8), name="residual",
                             hovertemplate="<b>%{text}</b><br>fitted %{x:,.4g}<br>residual %{y:,.4g}<extra></extra>"),
                  row=1, col=1)
    fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"), row=1, col=1)
    fig.add_trace(go.Histogram(x=fit.residuals, marker_color=GOLD, name="residuals",
                               nbinsx=max(5, min(20, fit.n // 2))), row=1, col=2)
    osm, osr, qs, qi = em.qq_points(fit.residuals)
    fig.add_trace(go.Scatter(x=osm, y=osr, mode="markers", marker=dict(color=TURQUOISE, size=7),
                             name="ordered residuals"), row=1, col=3)
    fig.add_trace(go.Scatter(x=osm, y=qi + qs * osm, mode="lines", line=dict(color=VERMILLION, dash="dash"),
                             name="normal reference"), row=1, col=3)
    fig.update_xaxes(title_text="fitted Y", row=1, col=1)
    fig.update_xaxes(title_text="residual", row=1, col=2)
    fig.update_xaxes(title_text="theoretical normal quantile", row=1, col=3)
    fig.update_yaxes(title_text="residual", row=1, col=1)
    fig.update_layout(height=380, showlegend=False, title=f"Residual diagnostics — {al.y.term} (n = {fit.n})")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A funnel in the left panel suggests heteroskedasticity; a curve suggests a missing transform. "
               "Points far from the dashed line in the QQ plot are non-normal residuals (often outliers).")

    diags = [em.breusch_pagan(fit, cross_section=not ts), em.jarque_bera_test(fit)]
    if ts:
        diags.append(em.durbin_watson_test(fit, consecutive=al.consecutive))
        diags.append(em.breusch_godfrey(fit, hac_lags or em.newey_west_lags(fit.n), consecutive=al.consecutive))
    dt = pd.DataFrame([{"test": d.test, "checks": d.purpose, "statistic": _fmt(d.statistic, 3),
                        "p-value": _fmt_p(d.p_value), "result": d.verdict, "detail": d.detail} for d in diags])
    st.dataframe(dt, use_container_width=True, hide_index=True)
    st.markdown("\n".join(f"- **{d.test}.** {d.interpretation}" for d in diags))

    vif_df = pd.DataFrame()
    if fit.k >= 2:
        vif_df = em.vif_table(fit)
        st.markdown("**Multicollinearity (VIF)**")
        vshow = vif_df.drop(columns=["term"]).copy()
        vshow["VIF"] = vshow["VIF"].map(lambda v: _fmt(v, 2) if np.isfinite(v) else "∞")
        st.dataframe(vshow, use_container_width=True, hide_index=True)
        st.caption(em.vif_interpretation(vif_df))

    adf_rows = []
    if ts:
        st.markdown("**Stationarity (Augmented Dickey–Fuller)**")
        adf_reg = _select(st.radio, "ADF deterministic terms", ["c", "ct"], "wb_adf_reg", "c",
                          format_func={"c": "constant", "ct": "constant + linear trend"}.get, horizontal=True)
        adf_level = {}
        win = (int(al.data[key].min()), int(al.data[key].max()))
        for v in al.variables:
            f = v.frame.dropna(subset=["value"])
            f = f[~f["year"].isin(list(v.exclude))]
            f = f[(f["year"] >= win[0]) & (f["year"] <= win[1])]
            vals = f["value"].astype(float)
            form = "level"
            if v.tf == "log" and (vals > 0).all():
                vals, form = np.log(vals), "log level"
            yrs, run = em.longest_consecutive_run(f["year"].tolist(), vals.tolist())
            span = f"{yrs[0]}–{yrs[-1]}" if yrs else "—"
            res = em.adf_test(run, name=v.term, regression=adf_reg, span=span)
            adf_level[v.term] = res
            adf_rows.append((v.term, form, res))
            if v.tf in em.TS_ONLY_TRANSFORMS:
                tr = em.transform_series(f["year"].tolist(), f["value"].astype(float).tolist(), v.tf, 0,
                                         time_series=True)
                yrs2, run2 = em.longest_consecutive_run(tr.data["key"].tolist(), tr.data["value"].tolist())
                res2 = em.adf_test(run2, name=v.term, regression=adf_reg,
                                   span=f"{yrs2[0]}–{yrs2[-1]}" if yrs2 else "—")
                adf_rows.append((v.term, "as entered (" + em.TRANSFORM_LABELS[v.tf].split(" (")[0] + ")", res2))
        at = pd.DataFrame([{"variable": t, "series tested": form, "years": r.span, "n": r.n,
                            "ADF statistic": _fmt(r.statistic, 2), "p-value": _fmt_p(r.p_value),
                            "5% critical": _fmt(r.crit_5pct, 2), "lags (AIC)": str(r.used_lag) if r.used_lag is not None else "—",
                            "result": r.verdict} for t, form, r in adf_rows])
        st.dataframe(at, use_container_width=True, hide_index=True)
        small = [f"{t} ({form}, n = {r.n})" for t, form, r in adf_rows if r.status in ("too_small", "not_computed")]
        if small:
            st.warning("ADF not meaningful for: " + "; ".join(small) + f". With fewer than {em.ADF_MIN_N} "
                       "consecutive observations the test has too little power to separate a stationary series "
                       "from a random walk, so no verdict is given — treat these series as possibly "
                       "non-stationary.")
        with st.expander("ADF readings, one per series"):
            st.markdown("\n".join(f"- **{t}** ({form}, {r.span}): {r.interpretation}" for t, form, r in adf_rows))
        st.caption(f"Each series is tested on its own observations within the estimation window {win[0]}–{win[1]} "
                   "(the first and last year of the analysis sample; longest run of consecutive years), lag length "
                   "by AIC.")
        warn = em.spurious_regression_warning((al.y.term, al.y.tf), [(v.term, v.tf) for v in al.xs], adf_level)
        if warn:
            callout(f"<b>Spurious-regression risk.</b> {warn}", kind="warn")

    indicator_note(
        "the diagnostics",
        "**Breusch–Pagan** regresses the squared residuals on the regressors; a small p-value means the error "
        "variance changes with them (heteroskedasticity), so classical SEs are wrong — HC1 / HAC fix the SEs, "
        "not the coefficients.\n\n"
        "**Jarque–Bera** checks residual skewness and kurtosis against the normal distribution; exact small-"
        "sample t/F inference relies on normality.\n\n"
        f"**Durbin–Watson** (time series) is ≈ 2 with no first-order autocorrelation; below {em.DW_LOW} suggests "
        f"positive, above {em.DW_HIGH} negative autocorrelation (rule of thumb, no p-value). **Breusch–Godfrey** "
        "tests for autocorrelation up to the HAC lag and stays valid with lagged regressors.\n\n"
        f"**VIF** = 1 / (1 − R²ⱼ) from regressing each regressor on the others: ≥ {em.VIF_NOTABLE:.0f} notable, "
        f"≥ {em.VIF_HIGH:.0f} severe.\n\n"
        "**ADF** tests the null of a unit root; rejecting it (p < 0.05) supports stationarity. Below "
        f"{em.ADF_MIN_N} observations no verdict is given. Regressing non-stationary series on each other in "
        "levels is the classic spurious regression — compare with first differences.",
        kind="method",
    )

    # ------------------------------------------------------------------ W6
    st.subheader("W6 · Assumptions, limitations and causation")
    st.markdown("\n".join(f"- **{a}.** {b}" for a, b in em.ASSUMPTIONS))
    with st.expander("Limitations of this workbench"):
        st.markdown("\n".join(f"- {x}" for x in em.LIMITATIONS))
    callout(f"<b>Correlation vs causation.</b> {em.CAUSATION_NOTE}", kind="note")

    # ------------------------------------------------------------------ W7
    st.subheader("W7 · Exports")
    reg_tab = em.regression_table(fit, al)
    data_tab = em.aligned_data_export(al, fit)
    record = em.reproducibility_record(
        alignment=al, fit=fit, level=level, level_label=wc.LEVELS[level], se_type=se_type, hac_lags=hac_lags,
        adf_regression=st.session_state.get("wb_adf_reg") if ts else None, include_tentative=include_tent,
        extra={"diagnostics": [{"test": d.test, "statistic": d.statistic, "p_value": d.p_value,
                                "result": d.verdict} for d in diags],
               "vif": vif_df.drop(columns=["term"]).to_dict("records") if not vif_df.empty else [],
               "adf": [{"variable": t, "series": form, "years": r.span, "n": r.n, "statistic": r.statistic,
                        "p_value": r.p_value, "result": r.verdict} for t, form, r in adf_rows]},
    )
    slug = f"{al.y.id}_on_{'_'.join(v.id for v in al.xs)}"[:120]
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button("Regression table (CSV)", reg_tab.to_csv(index=False).encode("utf-8"),
                           file_name=f"regression_{slug}.csv", mime="text/csv", key="wb_dl_reg")
    with d2:
        st.download_button("Aligned data with units & status (CSV)", data_tab.to_csv(index=False).encode("utf-8"),
                           file_name=f"aligned_data_{slug}.csv", mime="text/csv", key="wb_dl_data")
    with d3:
        st.download_button("Reproducibility record (JSON)", em.record_to_json(record).encode("utf-8"),
                           file_name=f"reproducibility_{slug}.json", mime="application/json", key="wb_dl_json")
    with st.expander("Aligned analysis data"):
        st.dataframe(data_tab, use_container_width=True, hide_index=True)
    with st.expander("Reproducibility record (JSON preview)"):
        st.json(record, expanded=False)
