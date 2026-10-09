"""Economic Relationships Lab.

Research question: do two economic variables already in this project move
together — and how strongly, how robustly, and with what caveats?

Every variable offered here is built from a real file already loaded by
another Lab (see DATA_REGISTRY.md). Nothing is fetched, imputed or
interpolated; the only operations are an explicit join, an optional
within-financial-year average of a quarterly index, the user's chosen
transform, optional first differences of consecutive periods, and standard
descriptive statistics (analysis/relationships.py). The hypothesis library
lives in analysis/hypotheses.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analysis import banking, housing, regional
from analysis import hypotheses as hyp
from analysis import relationships as rel
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote,
    TURQUOISE, GOLD, MUTED, VERMILLION,
)
from app.components.glossary import indicator_note
from data_sources import loaders

setup("Economic Relationships Lab", accent=TURQUOISE)

with st.sidebar:
    st.markdown("## Relationships Lab")
    st.caption("Sections")
    st.markdown(
        "- All hypotheses at a glance\n"
        "- A · Choose a hypothesis\n"
        "- B · Alignment report\n"
        "- C · Result, analysis & statistics\n"
        "- D · Scatter & residuals\n"
        "- E · Lagged & rolling correlation (time series)\n"
        "- F · Aligned data & downloads"
    )
    st.markdown("---")
    st.caption("Status: real data except the quarterly banking pair, which is ILLUSTRATIVE — every "
               "variable shows its own VERIFIED / PARTIAL / SPLICED / DERIVED / ILLUSTRATIVE status")


# ---------------------------------------------------------------------------
# Real source data (cached loaders) and the coverage facts quoted in the copy.
# ---------------------------------------------------------------------------

NSDP_CUR_COL = "percapita_nsdp_current_prices_inr"
NSDP_CON_COL = "percapita_nsdp_constant_prices_inr_SPLICED"
UNEMP_COL = "unemployment_rate_usual_status_15plus_2023_24"
MPCE_COL = "average_monthly_per_capita_consumption_expenditure_inr"

nsdp_cur = loaders.load_nsdp_current()
nsdp_con = loaders.load_nsdp_spliced()
unemp = loaders.load_unemployment_by_state()
mpce = loaders.load_hces_urban_mpce().rename(columns={"state_ut": "state"})
repo = loaders.load_repo_rate()
residex = loaders.load_residex_index()

CUR_YEARS = sorted(nsdp_cur.dropna(subset=[NSDP_CUR_COL])["financial_year"].unique())
CON_YEARS = sorted(nsdp_con.dropna(subset=[NSDP_CON_COL])["financial_year"].unique())
MPCE_YEAR = ", ".join(sorted(mpce["survey_year"].astype(str).unique()))
REPO_FIRST = repo["period"].min().to_period("Q")
REPO_LAST = repo["period"].max().to_period("Q")
RESIDEX_SORTED = housing.sort_quarters(residex, "quarter_raw")
RESIDEX_FIRST = RESIDEX_SORTED["quarter_raw"].iloc[0]
RESIDEX_LAST = RESIDEX_SORTED["quarter_raw"].iloc[-1]
WIL_B1 = loaders.load_wil_income_shares()
WIL_C1 = loaders.load_wil_wealth_shares()
WIL_C2 = loaders.load_wil_vhnwi()

# Aggregate rows that must never be treated as a state observation.
AGGREGATES = hyp.AGGREGATES

# Documented reasons for known gaps, appended to the generic join reason so
# a reader sees *why* a state is missing, not just that it is.
KNOWN_GAPS = {
    ("nsdp_current", "Delhi"): "current-price row held out in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv (ambiguous column count in the source screenshot; DATA_REGISTRY.md)",
    ("nsdp_current", "Puducherry"): "current-price row held out in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv (ambiguous column count in the source screenshot; DATA_REGISTRY.md)",
}


# ---------------------------------------------------------------------------
# Variable catalogue for the custom explorers. Each builder returns a
# DataFrame [key, "value"] from a real loader; `period` states the actual
# year(s) the values refer to; `unit` feeds the generated slope sentence.
# ---------------------------------------------------------------------------

def _nsdp_cur_state(year: str) -> pd.DataFrame:
    d = nsdp_cur[nsdp_cur["financial_year"] == year]
    return d[["state", NSDP_CUR_COL]].rename(columns={NSDP_CUR_COL: "value"})


def _nsdp_con_state(year: str) -> pd.DataFrame:
    d = nsdp_con[nsdp_con["financial_year"] == year]
    return d[["state", NSDP_CON_COL]].rename(columns={NSDP_CON_COL: "value"})


def _beta_growth(window: tuple) -> tuple[pd.DataFrame, str]:
    i0, i1 = CON_YEARS.index(window[0]), CON_YEARS.index(window[1])
    sub = nsdp_con[nsdp_con["financial_year"].isin(CON_YEARS[i0:i1 + 1])]
    beta = regional.beta_convergence(sub)
    per = beta.per_state
    if per.empty:
        return pd.DataFrame(columns=["state", "value"]), beta.direction
    return per[["state", "avg_annual_growth_pct"]].rename(columns={"avg_annual_growth_pct": "value"}), beta.direction


CS_VARS = {
    "nsdp_current": {
        "label": "Per-capita NSDP, current prices (₹)",
        "short": "Per-capita NSDP (current ₹)", "unit": "₹",
        "status": "PARTIAL", "source": "RBI Handbook of Statistics on Indian States (dbie.rbihub.in), transcribed",
        "kind": "year", "years": CUR_YEARS, "default_year": "2023-24" if "2023-24" in CUR_YEARS else CUR_YEARS[-1],
    },
    "nsdp_constant": {
        "label": "Per-capita NSDP, constant prices, spliced (₹)",
        "short": "Per-capita NSDP (constant ₹, spliced)", "unit": "₹",
        "status": "SPLICED", "source": "RBI Handbook Table 26, two base years linked by overlap factor",
        "kind": "year", "years": CON_YEARS, "default_year": CON_YEARS[-1],
    },
    "unemployment": {
        "label": "Unemployment rate, usual status, age 15+ (%)",
        "short": "PLFS unemployment rate (%)", "unit": "percentage points",
        "status": "PARTIAL", "source": "PLFS (MoSPI), survey year 2023-24",
        "kind": "fixed", "period": "PLFS survey year 2023-24",
    },
    "mpce_urban": {
        "label": "Urban average MPCE (₹ / person / month)",
        "short": "Urban MPCE (₹/month)", "unit": "₹ per person per month",
        "status": "VERIFIED", "source": "MoSPI HCES 2023-24 Statement 7 — consumption, not income",
        "kind": "fixed", "period": f"HCES survey year {MPCE_YEAR}",
    },
    "beta_growth": {
        "label": "Average annual growth of per-capita NSDP, constant prices (% / yr)",
        "short": "Avg annual NSDP growth (%)", "unit": "percentage points",
        "status": "DERIVED", "source": "Log-difference growth over the spliced series (analysis.regional.beta_convergence)",
        "kind": "window",
    },
}

PRESETS = {
    "custom": "Custom — pick X and Y yourself",
    "inc_unemp": hyp.QUESTIONS["inc_unemp"],
    "inc_mpce": hyp.QUESTIONS["inc_mpce"],
    "beta": hyp.QUESTIONS["beta"],
}
PRESET_SPECS = {
    "inc_unemp": dict(x="nsdp_current", y="unemployment", x_year="2023-24", x_tf="none", y_tf="none"),
    "inc_mpce": dict(x="nsdp_current", y="mpce_urban", x_year="2023-24", x_tf="log", y_tf="log"),
    "beta": dict(x="nsdp_constant", y="beta_growth", x_year=CON_YEARS[0], x_tf="log", y_tf="none"),
}


def _apply_preset() -> None:
    p = st.session_state.get("rel_preset", "custom")
    if p not in PRESET_SPECS:
        return
    spec = PRESET_SPECS[p]
    st.session_state["rel_cs_x"] = spec["x"]
    st.session_state["rel_cs_y"] = spec["y"]
    st.session_state[f"rel_cs_x_year_{spec['x']}"] = spec["x_year"]
    st.session_state[f"rel_tf_x_cs_{spec['x']}"] = spec["x_tf"]
    st.session_state[f"rel_tf_y_cs_{spec['y']}"] = spec["y_tf"]
    if spec["y"] == "beta_growth":
        st.session_state["rel_cs_y_window"] = (CON_YEARS[0], CON_YEARS[-1])


def _to_custom() -> None:
    st.session_state["rel_preset"] = "custom"


def _select(widget, label: str, options: list, key: str, default, **kwargs):
    """Create a keyed widget whose Session-State value is always valid for
    the current options (falls back to `default` if not)."""
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]
    return widget(label, options=options, key=key, **kwargs)


def _clamp_state(key: str, lo: int, hi: int, default) -> None:
    """Keep a slider's Session-State value inside its current [lo, hi]
    range (the range depends on n, which changes with the selection)."""
    v = st.session_state.get(key, default)
    if isinstance(default, tuple):
        a, b = (max(lo, min(hi, int(x))) for x in v)
        st.session_state[key] = (min(a, b), max(a, b))
    else:
        st.session_state[key] = max(lo, min(hi, int(v)))


def _fmt(v: float, d: int = 3) -> str:
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def _fmt_p(p: float) -> str:
    if p is None or not np.isfinite(p):
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _key_str(k) -> str:
    return str(k.date()) if hasattr(k, "date") else str(k)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

kicker("ECONOMIC RELATIONSHIPS · INDIA")
st.title("Do two economic variables move together?")
st.markdown(
    "Formulate a hypothesis about two variables **already in this project** — income and "
    "wealth concentration (World Inequality Lab), billionaire wealth, real per-capita NNI, "
    "corporate investment, per-capita state income, unemployment, urban consumption, growth, "
    "house prices, the repo rate — and test it: an explicit, audited join of the two series, "
    "Pearson and Spearman correlation, a simple OLS fit with a confidence interval, residuals "
    "and, for time series, levels vs first differences, a trend check, and lagged and rolling "
    "correlation. Every test ends in a **verdict** and a short **analysis written from the "
    "computed numbers**. No new data is introduced on this page."
)
source_badge(
    "WIL 2024/09 Tables B.1, C.1, C.2 · VERIFIED", "RBI Handbook (NSDP) · PARTIAL / SPLICED",
    "PLFS 2023-24 · PARTIAL", "HCES 2023-24 · VERIFIED", "Real per-capita NNI · PARTIAL",
    "RBI Handbook GCF · PARTIAL", "NHB RESIDEX · PARTIAL", "Bank panel · ILLUSTRATIVE",
)

callout(
    "<b>Observational data — correlation is not causation.</b> Everything on this page "
    "describes how two series co-move in data that were never designed to answer a causal "
    "question. There is <b>no identification strategy</b> here: no instrument, no natural "
    "experiment, no control variables. A relationship between two state-level variables "
    "can be produced entirely by a third factor — <b>state size, urbanisation, sectoral mix, "
    "migration, price levels</b>, or how a survey sampled each state — and reverse causation "
    "is always possible. Two national series that both trend over time will correlate in "
    "levels whether or not they are related, which is why every time-series test here is "
    "also run on <b>first differences</b>. The variables also come from <b>different years and "
    "different sources</b>: per-capita NSDP is an April-March financial-year series (current "
    f"prices {CUR_YEARS[0]}→{CUR_YEARS[-1]}; constant-price spliced {CON_YEARS[0]}→{CON_YEARS[-1]}); "
    "unemployment is PLFS survey year 2023-24; urban MPCE is HCES survey year "
    f"{MPCE_YEAR}; the WIL income shares are annual {WIL_B1['year'].min()}→{WIL_B1['year'].max()}, the "
    f"wealth shares cover survey years {', '.join(str(y) for y in WIL_C1['year'] if y < 2002)} and then "
    f"2002→{WIL_C1['year'].max()} (the last year tentative), and the rich-list series run "
    f"{WIL_C2['year'].min()}→{WIL_C2['year'].max()}; the RESIDEX composite index is quarterly "
    f"{RESIDEX_FIRST}→{RESIDEX_LAST}; the repo-rate and iBFPI series are quarterly "
    f"{REPO_FIRST}→{REPO_LAST} from this project's illustrative build. Survey reference "
    "periods (PLFS, HCES) do not line up exactly with the April-March financial year.",
    kind="warn",
)

# ---------------------------------------------------------------------------
# All hypotheses at a glance (computed live)
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("All hypotheses at a glance")
@st.cache_data(ttl=3600, show_spinner=False)
def _overview(include_tentative: bool) -> pd.DataFrame:
    return hyp.overview_table(include_tentative=include_tentative)


include_tentative_state = bool(st.session_state.get("rel_lib_tentative", False))
overview = _overview(include_tentative_state)
ov_show = overview.drop(columns=["id"]).copy()
ov_show["Spearman ρ"] = ov_show["Spearman ρ"].map(lambda v: _fmt(v, 2))
ov_show["p-value"] = ov_show["p-value"].map(_fmt_p)
st.dataframe(ov_show, use_container_width=True, hide_index=True)

sig = [(p is not None and np.isfinite(p) and p < rel.ALPHA) for p in overview["p-value"]]
fig_ov = go.Figure(go.Bar(
    y=[f"{q[:70]}{'…' if len(q) > 70 else ''}" for q in overview["Hypothesis"]],
    x=overview["Spearman ρ"], orientation="h",
    marker_color=[TURQUOISE if s else MUTED for s in sig],
    customdata=np.c_[overview["n"], overview["p-value"].map(_fmt_p), overview["Data status"]],
    hovertemplate="%{y}<br>ρ = %{x:.2f} · p = %{customdata[1]} · n = %{customdata[0]}"
                  "<br>%{customdata[2]}<extra></extra>",
))
for xv in (-rel.STRONG_FROM, -rel.WEAK_BELOW, rel.WEAK_BELOW, rel.STRONG_FROM):
    fig_ov.add_vline(x=xv, line=dict(color=MUTED, dash="dot", width=1))
fig_ov.update_layout(
    title="Spearman ρ in levels for every hypothesis (turquoise = p < 0.05; dotted lines = strength thresholds)",
    xaxis_title="Spearman ρ", xaxis_range=[-1.05, 1.05], height=60 + 28 * len(overview),
    yaxis=dict(autorange="reversed"), margin=dict(l=20),
)
st.plotly_chart(fig_ov, use_container_width=True)
st.caption(
    f"Computed live from the loaders with each hypothesis's default transforms, in levels. Strength "
    f"thresholds on |ρ|: < {rel.WEAK_BELOW} weak, {rel.WEAK_BELOW}–{rel.STRONG_FROM} moderate, "
    f"≥ {rel.STRONG_FROM} strong; '(n.s.)' = not significant at {rel.ALPHA:.0%}. For n ≤ "
    f"{rel.EXACT_SPEARMAN_MAX_N} the Spearman p-value is an exact permutation p-value. 'Survives "
    "differencing?' re-runs each time series on year-on-year changes (only between consecutive years). "
    + ("The tentative 2023 WIL wealth row is **included**." if include_tentative_state
       else "The tentative 2023 WIL wealth row is excluded (toggle in section A).")
    + " Many tests on one page also means some 'significant' results are expected by chance alone."
)

st.markdown("---")

# ---------------------------------------------------------------------------
# A. Choose a hypothesis
# ---------------------------------------------------------------------------

st.header("A · Choose a hypothesis")
mode = st.radio(
    "Analysis mode", ["Hypothesis library", "Cross-section of states", "Time series"],
    horizontal=True, key="rel_mode",
    help="Hypothesis library: ready-made, documented tests (states, cities, WIL inequality, growth, "
         "investment). Cross-section: build your own state-level pair. Time series: city house prices "
         "vs state income, or the illustrative repo-rate / iBFPI pair.",
)
is_lib = mode == "Hypothesis library"
is_ts = mode == "Time series"

x_df = y_df = None
x_meta: dict = {}
y_meta: dict = {}
key_col = "state"
x_var_id = y_var_id = ""
extra_badges: list[str] = []
align_exclude: dict | None = None
default_tfs = ("none", "none")
caveat_codes: tuple = ()
caveat_note = ""
obs_noun, period_word = "states", "year"
gap_vids: tuple = ()
nsdp_cur_years_used: list[str] = []
h = None

if is_lib:
    ids = hyp.HYPOTHESIS_IDS
    hid = _select(
        st.selectbox, "Hypothesis", ids, "rel_lib_id", "wil_top1_income_vs_wealth",
        format_func=lambda i: f"[{hyp.GROUPS[i]}] {hyp.QUESTIONS[i]}" + ("" if i in hyp.NEW_IDS else " (original preset)"),
    )
    include_tentative = False
    if hid in hyp.TENTATIVE_IDS:
        include_tentative = st.checkbox(
            "Include tentative 2023 wealth row", value=False, key="rel_lib_tentative",
            help="WIL Table C.1 flags its 2023 row as tentative. Excluded by default; when excluded it is "
                 "listed in the alignment report with that reason.",
        )
    h = hyp.build(hid, include_tentative=include_tentative)
    is_ts = h.is_ts
    key_col = h.key
    x_var_id, y_var_id = f"lib_{hid}_x", f"lib_{hid}_y"
    x_df, y_df = h.x_df, h.y_df
    x_meta = dict(label=h.x.label, short=h.x.short, unit=h.x.unit, status=h.x.status,
                  source=h.x.source, period=h.x.period)
    y_meta = dict(label=h.y.label, short=h.y.short, unit=h.y.unit, status=h.y.status,
                  source=h.y.source, period=h.y.period)
    align_exclude = h.exclude or None
    default_tfs = (h.x_tf, h.y_tf)
    caveat_codes, caveat_note = h.caveats, h.caveat_note
    obs_noun, period_word = h.obs_noun, h.period_word
    if hid in ("inc_unemp", "inc_mpce"):
        gap_vids, nsdp_cur_years_used = ("nsdp_current",), ["2023-24"]

    callout(f"<b>Why test this?</b> {h.rationale}", kind="note")
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown(f"**X** — {h.x.label}")
        st.caption(f"{h.x.status} · {h.x.period}")
    with lc2:
        st.markdown(f"**Y** — {h.y.label}")
        st.caption(f"{h.y.status} · {h.y.period}")
    st.caption(f"**Source.** {h.source_line}")
    for note in h.notes:
        st.caption(note)
    if "mechanical" in h.caveats or "partly_mechanical" in h.caveats:
        callout("<b>Mechanical link.</b> " + rel.CAVEAT_TEXT["mechanical" if "mechanical" in h.caveats
                                                             else "partly_mechanical"].capitalize()
                + (f" — {h.caveat_note}." if h.caveat_note else "."), kind="warn")
    extra_badges = [f"X · {h.x.status}", f"Y · {h.y.status}"]

elif not is_ts:
    if "rel_cs_x" not in st.session_state:
        st.session_state.setdefault("rel_preset", "inc_unemp")
        _apply_preset()
    st.selectbox(
        "Suggested hypothesis", list(PRESETS), format_func=PRESETS.get,
        key="rel_preset", on_change=_apply_preset,
        help="Pre-fills X, Y, year and transforms. Changing any of those switches this back to 'Custom'.",
    )
    var_ids = list(CS_VARS)
    cx, cy = st.columns(2)

    def _cs_side(side: str, col) -> tuple[str, pd.DataFrame, dict]:
        with col:
            default = "nsdp_current" if side == "x" else "unemployment"
            vid = _select(st.selectbox, f"{side.upper()} variable", var_ids, f"rel_cs_{side}", default,
                          format_func=lambda v: CS_VARS[v]["label"], on_change=_to_custom)
            spec = CS_VARS[vid]
            if spec["kind"] == "year":
                yr = _select(st.selectbox, f"{side.upper()} financial year", spec["years"],
                             f"rel_cs_{side}_year_{vid}", spec["default_year"], on_change=_to_custom)
                df = (_nsdp_cur_state if vid == "nsdp_current" else _nsdp_con_state)(yr)
                period = f"FY {yr}"
            elif spec["kind"] == "window":
                if f"rel_cs_{side}_window" not in st.session_state:
                    st.session_state[f"rel_cs_{side}_window"] = (CON_YEARS[0], CON_YEARS[-1])
                win = st.select_slider(
                    f"{side.upper()} growth window (financial years)", options=CON_YEARS,
                    key=f"rel_cs_{side}_window", on_change=_to_custom,
                )
                if not (isinstance(win, (tuple, list)) and len(win) == 2 and all(w in CON_YEARS for w in win)):
                    # Defensive: a range value that is not two known financial
                    # years (seen when widget state is replayed by a test
                    # harness) falls back to the full window, stated openly.
                    win = (CON_YEARS[0], CON_YEARS[-1])
                    st.caption(f"Growth window reset to the full range FY {win[0]}→{win[1]}.")
                if win[0] == win[1]:
                    st.warning("Pick a growth window spanning at least two financial years.")
                    st.stop()
                df, _direction = _beta_growth(win)
                period = f"FY {win[0]}→{win[1]}"
            else:
                df = unemp.rename(columns={UNEMP_COL: "value"})[["state", "value"]] if vid == "unemployment" \
                    else mpce.rename(columns={MPCE_COL: "value"})[["state", "value"]]
                period = spec["period"]
            st.caption(f"{spec['status']} · {spec['source']} · {period}")
        return vid, df, dict(spec, period=period)

    x_var_id, x_df, x_meta = _cs_side("x", cx)
    y_var_id, y_df, y_meta = _cs_side("y", cy)
    if x_var_id == y_var_id and x_meta["period"] == y_meta["period"]:
        st.warning("X and Y are the same variable for the same period — choose two different series.")
        st.stop()
    align_exclude = AGGREGATES
    default_tfs = ("none", "none")
    vids = {x_var_id, y_var_id}
    codes = []
    if x_var_id == "nsdp_constant" and y_var_id == "beta_growth":
        codes.append("shared_term")
        caveat_note = "growth is computed from the same series as initial income"
    if "mpce_urban" in vids:
        codes.append("proxy")
        caveat_note = caveat_note or "MPCE is urban household consumption, not income"
    caveat_codes = tuple(codes)
    gap_vids = tuple(v for v in (x_var_id, y_var_id) if v == "nsdp_current")
    nsdp_cur_years_used = [st.session_state.get(f"rel_cs_{s}_year_nsdp_current") for s in ("x", "y")
                           if (x_var_id if s == "x" else y_var_id) == "nsdp_current"]
else:
    family = st.selectbox(
        "Time-series family",
        ["housing", "banking"],
        format_func={
            "housing": "Annual · city house-price index vs its state's per-capita NSDP (financial years)",
            "banking": f"Quarterly · RBI repo rate vs system iBFPI ({REPO_FIRST}→{REPO_LAST}) — ILLUSTRATIVE",
        }.get,
        key="rel_ts_family",
        help="X and Y must share a frequency, so each family only offers series observed on the same calendar.",
    )
    if family == "banking":
        key_col = "period"
        obs_noun, period_word = "quarters", "quarter"
        callout(
            "<b>ILLUSTRATIVE — not real bank data.</b> The bank panel behind iBFPI "
            "(<code>data/processed/bank_panel.csv</code>) is <b>synthetic</b>, generated by "
            "<code>data_sources/build_illustrative_data.py</code> to exercise the methodology, "
            "exactly as disclosed on the Banking Lab. The repo-rate file shipped with it is "
            "generated by the same script and is described in <code>data_dictionary.md</code> "
            "as values that <i>approximate</i> the RBI repo-rate history, rounded — it has not "
            "been verified quarter-by-quarter against RBI's published series. Treat every "
            "statistic below as a demonstration of the method, not as evidence about Indian banks.",
            kind="warn",
        )
        extra_badges = ["Bank panel · ILLUSTRATIVE (synthetic)", "Repo rate · APPROXIMATE (illustrative build)"]
        scored = banking.compute_ibfpi(loaders.load_bank_panel())
        ibfpi = banking.cross_bank_aggregate(scored).rename(columns={"ibfpi_system": "value"})
        TS_VARS = {
            "repo": dict(label="RBI repo rate at quarter-end (%)", short="Repo rate (%)", unit="percentage points",
                         status="APPROXIMATE (illustrative build)",
                         source="data/processed/repo_rate.csv",
                         period=f"quarter-ends {REPO_FIRST}→{REPO_LAST}",
                         df=repo.rename(columns={"repo_rate": "value"})[["period", "value"]]),
            "ibfpi": dict(label="System iBFPI, equal-weighted across 5 banks (robust z-units)",
                          short="System iBFPI (ILLUSTRATIVE)", unit="robust z-units", status="ILLUSTRATIVE (synthetic)",
                          source="data/processed/bank_panel.csv → analysis.banking",
                          period=f"quarter-ends {ibfpi['period'].min().to_period('Q')}→{ibfpi['period'].max().to_period('Q')}",
                          df=ibfpi[["period", "value"]]),
        }
        defaults = ("repo", "ibfpi")
    else:
        key_col = "financial_year"
        obs_noun, period_word = "financial years", "year"
        caveat_codes = ("proxy",)
        cities = sorted(c for c in residex["City"].unique() if c in housing.CITY_TO_STATE)
        hc1, hc2 = st.columns([1.2, 1])
        with hc1:
            city = _select(st.selectbox, "City (RESIDEX)", cities, "rel_ts_city",
                           "Mumbai" if "Mumbai" in cities else cities[0])
        state = housing.CITY_TO_STATE[city]
        caveat_note = f"{state}'s state-level per-capita NSDP stands in for {city} household income"
        with hc2:
            full_year = st.checkbox(
                "Only financial years with all 4 quarters", value=True, key="rel_ts_fullyear",
                help="Unticked, a financial year observed for only some quarters is averaged over "
                     "those quarters — mixing seasons. Ticked (default), such years are dropped and reported.",
            )
        city_idx = residex[residex["City"] == city]
        fy = rel.quarterly_to_financial_year(
            city_idx, "quarter_raw", "composite_index", housing.financial_year_of_quarter,
            require_full_year=full_year,
        )
        if not fy.dropped.empty:
            st.caption(
                "RESIDEX financial years dropped before alignment: "
                + "; ".join(f"{r.financial_year} — {r.reason}" for r in fy.dropped.itertuples())
            )
        extra_badges = [f"RESIDEX {city} · PARTIAL", f"NSDP {state} · PARTIAL / SPLICED"]
        st.caption(
            f"Income here is **{state}'s state-level per-capita NSDP**, used as a proxy for {city} — "
            "not city household income (the same documented assumption as the Housing Lab)."
        )
        TS_VARS = {
            "residex": dict(label=f"RESIDEX composite index, {city} (FY average, Mar-2018 = 100)",
                            short=f"RESIDEX {city}", unit="index points", status="PARTIAL",
                            source="NHB RESIDEX city composite index, quarterly → FY mean",
                            period=(f"FY {fy.data['financial_year'].iloc[0]}→{fy.data['financial_year'].iloc[-1]}"
                                    if not fy.data.empty else "none"),
                            df=fy.data[["financial_year", "value"]]),
            "nsdp_current": dict(label=f"Per-capita NSDP, current prices, {state} (₹)",
                                 short=f"NSDP {state} (current ₹)", unit="₹", status="PARTIAL",
                                 source="RBI Handbook (dbie.rbihub.in), transcribed",
                                 period=f"FY {CUR_YEARS[0]}→{CUR_YEARS[-1]}",
                                 df=nsdp_cur[nsdp_cur["state"] == state][["financial_year", NSDP_CUR_COL]]
                                 .rename(columns={NSDP_CUR_COL: "value"})),
            "nsdp_constant": dict(label=f"Per-capita NSDP, constant prices spliced, {state} (₹)",
                                  short=f"NSDP {state} (constant ₹)", unit="₹", status="SPLICED",
                                  source="RBI Handbook Table 26, spliced",
                                  period=f"FY {CON_YEARS[0]}→{CON_YEARS[-1]}",
                                  df=nsdp_con[nsdp_con["state"] == state][["financial_year", NSDP_CON_COL]]
                                  .rename(columns={NSDP_CON_COL: "value"})),
        }
        defaults = ("nsdp_current", "residex")

    ts_ids = list(TS_VARS)
    tx, ty = st.columns(2)
    with tx:
        x_var_id = _select(st.selectbox, "X variable", ts_ids, f"rel_ts_x_{family}", defaults[0],
                           format_func=lambda v: TS_VARS[v]["label"])
        st.caption(f"{TS_VARS[x_var_id]['status']} · {TS_VARS[x_var_id]['source']} · {TS_VARS[x_var_id]['period']}")
    with ty:
        y_var_id = _select(st.selectbox, "Y variable", ts_ids, f"rel_ts_y_{family}", defaults[1],
                           format_func=lambda v: TS_VARS[v]["label"])
        st.caption(f"{TS_VARS[y_var_id]['status']} · {TS_VARS[y_var_id]['source']} · {TS_VARS[y_var_id]['period']}")
    if x_var_id == y_var_id:
        st.warning("X and Y are the same series — choose two different variables.")
        st.stop()
    x_meta, y_meta = dict(TS_VARS[x_var_id]), dict(TS_VARS[y_var_id])
    x_df = x_meta.pop("df")
    y_df = y_meta.pop("df")
    if family == "housing" and "nsdp_current" in (x_var_id, y_var_id):
        caveat_codes = ("nominal", "proxy")

if extra_badges:
    source_badge(*extra_badges)

st.markdown(
    f"**This comparison:** X = {x_meta['label']} — *{x_meta['period']}*, **{x_meta['status']}**. "
    f"Y = {y_meta['label']} — *{y_meta['period']}*, **{y_meta['status']}**."
)

# ---------------------------------------------------------------------------
# B. Alignment report
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("B · Alignment report")
aligned = rel.align_observations(
    x_df, y_df, key_col, "value", "value",
    x_label=x_meta["short"], y_label=y_meta["short"],
    exclude=align_exclude,
)

a1, a2, a3 = st.columns(3)
with a1:
    stat_card("Aligned observations", f"{aligned.n}", f"inner join on {key_col.replace('_', ' ')}")
with a2:
    stat_card("Dropped", f"{aligned.n_dropped}", "every one listed below with its reason")
with a3:
    stat_card("Source rows", f"X {aligned.n_x_source} · Y {aligned.n_y_source}", "after explicit exclusions")

if aligned.possible_name_mismatches:
    callout(
        "<b>Possible name mismatches — not joined automatically:</b> "
        + "; ".join(f"'{a}' vs '{b}'" for a, b in aligned.possible_name_mismatches)
        + ". These look like the same entity spelled differently; they are reported, not merged.",
        kind="warn",
    )
elif not is_ts:
    st.caption("No probable spelling mismatches between the two sources' keys (checked after normalising case, '&'/'and' and punctuation).")

if not aligned.dropped.empty:
    dropped_show = aligned.dropped.copy()
    if not is_ts:
        def _gap_note(row) -> str:
            for vid in gap_vids:
                note = KNOWN_GAPS.get((vid, row[key_col]))
                if note and "not present in" in row["reason"]:
                    return note
            return ""
        dropped_show["documented context"] = dropped_show.apply(_gap_note, axis=1)
    else:
        dropped_show[key_col] = dropped_show[key_col].map(_key_str)
    with st.expander(f"Dropped observations ({aligned.n_dropped})", expanded=not is_ts and aligned.n_dropped <= 12):
        st.dataframe(dropped_show, use_container_width=True, hide_index=True)

indicator_note(
    "the alignment step",
    "**What it does.** The two variables come from different files, so before any "
    "statistic is computed they are matched row-by-row on a shared key — state or city "
    "name for a cross-section, calendar year, financial year or quarter-end date for a "
    "time series — with an **inner join**: an observation is kept only if *both* variables "
    "have a real value for it. Nothing is filled in, carried forward or interpolated.\n\n"
    "**Why every drop is listed.** A silent join can quietly change the sample — e.g. a "
    "state missing from one survey, or the same state spelled two ways. Each dropped key "
    "is listed with its reason: an explicitly excluded national aggregate ('India', "
    "'All-India') or tentative row (WIL 2023 wealth), a key present in only one source, a "
    "missing value, or (for time series) a period lost to a percent-change transform or to "
    "first-differencing across a gap. Keys that differ only in spelling are flagged as "
    "possible mismatches, not merged.\n\n"
    "**Caveat.** Which observations survive the join is not random — small states and UTs "
    "are the ones most often missing, and the WIL wealth series has no data between survey "
    "years before 2002 — so the aligned sample may not represent the whole period or country.",
    kind="method",
)

if aligned.n < rel.MIN_OBS:
    st.warning(rel.sample_size_warning(aligned.n))
    st.stop()

# ---------------------------------------------------------------------------
# Transforms and (time series) levels vs first differences
# ---------------------------------------------------------------------------

st.subheader("Transforms")
t1, t2, t3 = st.columns([1, 1, 1])
if is_lib:
    sfx = f"lib_{st.session_state.get('rel_lib_id', '')}"
elif is_ts:
    sfx = "ts_" + st.session_state.get("rel_ts_family", "")
else:
    sfx = "cs"
with t1:
    x_opts = rel.available_transforms(aligned.data["x"], time_series=is_ts)
    x_tf = _select(st.selectbox, "X transform", x_opts, f"rel_tf_x_{sfx}_{x_var_id}", default_tfs[0],
                   format_func=rel.TRANSFORM_LABELS.get, on_change=_to_custom if mode == "Cross-section of states" else None)
with t2:
    y_opts = rel.available_transforms(aligned.data["y"], time_series=is_ts)
    y_tf = _select(st.selectbox, "Y transform", y_opts, f"rel_tf_y_{sfx}_{y_var_id}", default_tfs[1],
                   format_func=rel.TRANSFORM_LABELS.get, on_change=_to_custom if mode == "Cross-section of states" else None)
with t3:
    show_fit = st.checkbox("Show regression line", value=True, key="rel_show_fit")
unavailable = []
for side, opts in (("X", x_opts), ("Y", y_opts)):
    if "log" not in opts:
        unavailable.append(f"log is not offered for {side} (not every aligned value is > 0)")
    if is_ts and "pct_change" not in opts:
        unavailable.append(f"percent change is not offered for {side} (series is not strictly positive)")
if unavailable:
    st.caption("; ".join(unavailable) + ".")

tp = rel.transform_pair(aligned, x_tf, y_tf)
levels = tp.data
if not tp.dropped.empty:
    st.caption(f"{len(tp.dropped)} observation(s) lost to the percent-change transform (no previous period): "
               + ", ".join(_key_str(k) for k in tp.dropped[key_col]))

form = "levels"
diff = None
if is_ts:
    form_label = st.radio(
        "Analyse the series as",
        ["Levels", "First differences (period-on-period changes)"],
        horizontal=True, key="rel_ts_form",
        help="First differences replace each value with its change from the previous period. Changes are "
             "computed only between consecutive periods — never across a gap — so survey-year gaps "
             "(e.g. WIL wealth 1961, 1971, 1981, 1991) drop out rather than being bridged.",
    )
    form = "differences" if form_label.startswith("First") else "levels"
    diff = rel.first_differences(levels, key_col)

data = diff.data if form == "differences" else levels


def _axis_label(meta: dict, tf: str) -> str:
    base = meta["short"] if tf == "none" else f"{rel.TRANSFORM_LABELS[tf]} of {meta['short']}"
    return f"Δ {base} ({period_word}-on-{period_word} change)" if form == "differences" else base


x_axis, y_axis = _axis_label(x_meta, x_tf), _axis_label(y_meta, y_tf)

indicator_note(
    "the transforms and first differences",
    "**Natural log** compresses large values, so a slope reads roughly in proportional "
    "terms (with both variables logged, the slope is an elasticity: % change in Y per 1% "
    "change in X). Offered only when every aligned value is strictly positive.\n\n"
    "**Z-score** rescales a variable to mean 0 and standard deviation 1 over the analysis "
    "sample. It does not change either correlation; it changes the units of the OLS slope "
    "(with both variables z-scored, the slope equals Pearson r).\n\n"
    "**Percent change** (time series only) replaces each level with its change from the "
    "previous period in percent. The first period is lost. Offered only for strictly "
    "positive level series (a percent change of a z-scored index like iBFPI is meaningless).\n\n"
    "**First differences** (time series only, applied after the transform) replace each "
    "value with its change from the previous period: Δx_t = x_t − x_(t−1). Two series that "
    "both simply grow over time look strongly correlated in levels even if they are "
    "unrelated (spurious correlation); in differences the question becomes 'in years when "
    "X rose by more, did Y also rise by more?'. A change is computed only when the previous "
    "period is actually observed, so gaps shrink the sample instead of being filled in. "
    "Log + first differences ≈ growth rates.",
)

# ---------------------------------------------------------------------------
# C. Result, analysis & association statistics
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("C · Result, analysis & statistics")
corr = rel.correlations(data["x"], data["y"])
fit = rel.ols(data["x"], data["y"])
n = int(len(data))
vd = rel.verdict(corr)

levels_corr = diff_corr = None
x_trend = y_trend = None
if is_ts:
    levels_corr = rel.correlations(levels["x"], levels["y"])
    diff_corr = rel.correlations(diff.data["x"], diff.data["y"])
    x_trend = rel.trend_check(levels[key_col], levels["x"])
    y_trend = rel.trend_check(levels[key_col], levels["y"])
influence = rel.influential_observation(
    [_key_str(k) for k in data[key_col]], data["x"], data["y"]) if n > rel.MIN_OBS else None

paragraph_sentences = rel.analysis_sentences(
    x_name=x_meta["short"], y_name=y_meta["short"], corr=corr, fit=fit, obs_noun=obs_noun,
    x_unit=x_meta.get("unit", ""), y_unit=y_meta.get("unit", ""), x_tf=x_tf, y_tf=y_tf, form=form,
    period_word=period_word, time_series=is_ts, levels_corr=levels_corr, diff_corr=diff_corr,
    x_trend=x_trend, y_trend=y_trend, influence=influence, caveats=caveat_codes,
    statuses=(x_meta["status"], y_meta["status"]), caveat_note=caveat_note,
    x_sd=float(data["x"].std()) if n > 1 else None,
)
analysis_text = " ".join(paragraph_sentences)

v1, v2 = st.columns([1, 2])
with v1:
    stat_card("Verdict" + (" (first differences)" if form == "differences" else ""), vd.label,
              vd.stats_text + ("" if vd.significant or not vd.computable
                               else f" · not significant at {rel.ALPHA:.0%}"))
with v2:
    question = h.question if h is not None else (PRESETS.get(st.session_state.get("rel_preset", ""), "")
                                                 if mode == "Cross-section of states" else "")
    if question and not question.startswith("Custom"):
        st.markdown(f"**Hypothesis:** {question}")
    st.markdown(f"**Result:** {vd.headline}.")
callout("<b>Analysis.</b> " + analysis_text, kind="note")
st.caption(
    f"Verdict rule (stated, not tuned): strength from Spearman |ρ| — < {rel.WEAK_BELOW} weak, "
    f"{rel.WEAK_BELOW}–{rel.STRONG_FROM} moderate, ≥ {rel.STRONG_FROM} strong; significance at "
    f"{rel.ALPHA:.0%} (two-sided; exact permutation p-value when n ≤ {rel.EXACT_SPEARMAN_MAX_N}). "
    "Every sentence above is generated from the numbers on this page "
    "(analysis.relationships.analysis_sentences); none is written by hand for a particular pair."
)

if is_ts:
    st.subheader("Levels vs first differences")
    lv_v, df_v = rel.verdict(levels_corr), rel.verdict(diff_corr)
    comp = pd.DataFrame([
        {"Form": "Levels", "n": levels_corr.n, "Pearson r": _fmt(levels_corr.pearson_r, 2),
         "Spearman ρ": _fmt(levels_corr.spearman_rho, 2), "Spearman p": _fmt_p(levels_corr.spearman_p),
         "Verdict": lv_v.label + ("" if lv_v.significant or not lv_v.computable else " (n.s.)")},
        {"Form": f"First differences ({period_word}-on-{period_word})", "n": diff_corr.n,
         "Pearson r": _fmt(diff_corr.pearson_r, 2), "Spearman ρ": _fmt(diff_corr.spearman_rho, 2),
         "Spearman p": _fmt_p(diff_corr.spearman_p),
         "Verdict": df_v.label + ("" if df_v.significant or not df_v.computable else " (n.s.)")},
    ])
    cc1, cc2 = st.columns([3, 2])
    with cc1:
        st.dataframe(comp, use_container_width=True, hide_index=True)
    with cc2:
        outcome = rel.differencing_outcome(lv_v, df_v)
        stat_card("Survives differencing?", outcome.replace("_", " ").capitalize(),
                  "same sign & p < 0.05 in differences = survives")
    trend_rows = pd.DataFrame([
        {"Series": f"X: {x_meta['short']}", "Spearman ρ with time": _fmt(x_trend.rho, 2),
         "p": _fmt_p(x_trend.p), "Trending?": x_trend.direction if x_trend.trending else "no"},
        {"Series": f"Y: {y_meta['short']}", "Spearman ρ with time": _fmt(y_trend.rho, 2),
         "p": _fmt_p(y_trend.p), "Trending?": y_trend.direction if y_trend.trending else "no"},
    ])
    st.dataframe(trend_rows, use_container_width=True, hide_index=True)
    warn_trend = rel.spurious_trend_warning(x_trend, y_trend, x_meta["short"], y_meta["short"])
    if warn_trend:
        callout("<b>Spurious-correlation risk.</b> " + warn_trend, kind="warn")
    else:
        st.caption(f"Trend check: a series counts as trending when its Spearman ρ with time has "
                   f"|ρ| ≥ {rel.TREND_MIN_RHO} and p < {rel.ALPHA}. At most one series trends here, so the "
                   "levels correlation is less exposed to a shared-trend artefact.")
    if not diff.dropped.empty:
        with st.expander(f"Observations without a first difference ({len(diff.dropped)})"):
            dd = diff.dropped.copy()
            dd[key_col] = dd[key_col].map(_key_str)
            st.dataframe(dd, use_container_width=True, hide_index=True)

warn = rel.sample_size_warning(n)
if warn:
    extra = (" State and city cross-sections in this project top out at roughly 21-50 aligned "
             "observations (beta-convergence growth needs both endpoints; PLFS covers 29 states; Delhi and "
             "Puducherry are held out of the current-price NSDP file), so most cross-sections here are small.") \
        if not is_ts else (
             " Time series here are short (≤ 26 quarters, ≤ 13 financial years, or 5-72 calendar years), and "
             "consecutive observations are not independent, which makes p-values over-confident.")
    callout(warn + extra, kind="warn")

s1, s2, s3, s4 = st.columns(4)
with s1:
    lost = aligned.n_dropped + len(tp.dropped) + (len(diff.dropped) if form == "differences" else 0)
    stat_card("n (analysis sample)", f"{n}", f"{lost} dropped in total")
with s2:
    stat_card("Pearson r", _fmt(corr.pearson_r), f"p = {_fmt_p(corr.pearson_p)} · linear")
with s3:
    stat_card("Spearman rank correlation", _fmt(corr.spearman_rho), f"p = {_fmt_p(corr.spearman_p)} · rank / monotone")
with s4:
    stat_card("R²", _fmt(fit.r_squared), "share of Y variance fitted by X")
s5, s6, s7 = st.columns(3)
with s5:
    stat_card("OLS slope", _fmt(fit.slope, 4), f"SE {_fmt(fit.slope_se, 4)} · p = {_fmt_p(fit.slope_p)}")
with s6:
    stat_card("95% CI for slope", f"[{_fmt(fit.slope_ci_low, 4)}, {_fmt(fit.slope_ci_high, 4)}]",
              "excludes 0" if fit.ok and (fit.slope_ci_low > 0 or fit.slope_ci_high < 0) else "includes 0")
with s7:
    stat_card("Intercept", _fmt(fit.intercept, 4), f"SE {_fmt(fit.intercept_se, 4)}")
st.caption(f"Units: slope = change in [{y_axis}] per one unit of [{x_axis}].")

indicator_note(
    "Pearson vs. Spearman correlation",
    "**Pearson r** measures how close the points lie to a *straight line* (−1 to +1). It "
    "uses the actual values, so one or two extreme observations (a very rich small UT, a "
    "boom year) can dominate it.\n\n"
    "**Spearman ρ** is Pearson's r computed on the *ranks* — it asks whether higher X goes "
    "with higher Y at all (any monotone relationship, straight or curved), and is far less "
    "sensitive to outliers. If Spearman is much stronger than Pearson, the relationship is "
    "monotone but curved or outlier-distorted; if Pearson is much stronger, a few extreme "
    "points are probably driving it. The verdict uses Spearman for this reason.\n\n"
    "**The p-values** test the null hypothesis of zero association, assuming independent "
    "observations. A small p-value says 'this pattern would be unusual if there were truly "
    "no association' — not that the association is large, important or causal. With "
    "n < 20, treat p-values as rough guides; with time series, as over-confident. For "
    f"n ≤ {rel.EXACT_SPEARMAN_MAX_N} the Spearman p-value is computed exactly over all n! "
    "orderings, because the usual approximation is far too optimistic for tiny samples.",
)
indicator_note(
    "the OLS slope, R² and its 95% confidence interval",
    "**OLS** fits the line Y = a + b·X that minimises the sum of squared vertical "
    "distances (residuals). The **slope b** is the average difference in Y between "
    "observations one unit of X apart — a descriptive association across this sample, "
    "*not* the effect of raising X.\n\n"
    "**R²** is the share of Y's variance the line accounts for (0 to 1; for a "
    "one-variable regression it equals Pearson r²). A low R² means most of the variation "
    "in Y has nothing to do with X in this sample.\n\n"
    "**Standard error and 95% CI.** SE(b) = √(s² / Σ(x − x̄)²), with s² the residual "
    "variance on n − 2 degrees of freedom; the CI is b ± t(0.975, n − 2)·SE(b). These are "
    "classical (homoskedastic, independent-errors) formulas. If the interval includes 0, "
    "the data are consistent with no linear association. With small n, heteroskedasticity "
    "across states of very different size, or autocorrelated time-series errors, the true "
    "uncertainty is usually larger than this interval suggests.",
    kind="method",
)
indicator_note(
    "the verdict and the generated analysis",
    f"**Verdict.** Strength comes from the size of Spearman's ρ: |ρ| < {rel.WEAK_BELOW} weak, "
    f"{rel.WEAK_BELOW} to {rel.STRONG_FROM} moderate, ≥ {rel.STRONG_FROM} strong; direction from its "
    f"sign; and 'not statistically significant' is added when p ≥ {rel.ALPHA}. These are conventional "
    "rules of thumb, fixed in advance and identical for every pair.\n\n"
    "**Analysis paragraph.** Built by `analysis.relationships.analysis_sentences` from the numbers "
    "above: (1) strength and direction, with a note when Pearson and Spearman disagree by more "
    "than 0.2; (2) significance and R²; (3) the slope read in the variables' own units "
    "(elasticity for log-log); (4) for time series, whether the association survives first "
    "differencing (same sign and p < 0.05 = survives; same sign, not significant, |ρ| ≥ 0.3 = "
    "weakens; otherwise vanishes or reverses) and whether both series trend; (5) the most "
    "influential observation, found by dropping each observation in turn and recomputing ρ, plus "
    "the largest residual; (6) the main caveat, chosen by a fixed priority: mechanical link → "
    "illustrative data → X entering Y's calculation → measurement comparison → partly mechanical → "
    "shared inputs → nominal prices → repeated values → proxy → small n → trend → causality.",
    kind="method",
)

# ---------------------------------------------------------------------------
# D. Scatter & residuals
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("D · Scatter & residuals")
hover_keys = data[key_col].map(_key_str)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data["x"], y=data["y"], mode="markers", name="Observations",
    marker=dict(size=10, color=TURQUOISE, line=dict(width=0)),
    text=hover_keys,
    customdata=np.c_[data["x_raw"], data["y_raw"]],
    hovertemplate="<b>%{text}</b><br>X: %{x:,.4g}<br>Y: %{y:,.4g}"
                  "<br>raw X: %{customdata[0]:,.4g} · raw Y: %{customdata[1]:,.4g}<extra></extra>",
))
if influence is not None:
    sel = hover_keys == str(influence.loo_key)
    if sel.any():
        fig.add_trace(go.Scatter(
            x=data["x"][sel], y=data["y"][sel], mode="markers", name="Most influential (leave-one-out)",
            marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(width=2, color=VERMILLION)),
            hoverinfo="skip",
        ))
if show_fit and fit.ok:
    xs = np.linspace(data["x"].min(), data["x"].max(), 50)
    fig.add_trace(go.Scatter(
        x=xs, y=fit.intercept + fit.slope * xs, mode="lines", name="OLS fit",
        line=dict(color=GOLD, dash="dash", width=2), hoverinfo="skip",
    ))
fig.update_layout(
    title=f"{y_axis} vs {x_axis} (n = {n})", xaxis_title=x_axis, yaxis_title=y_axis,
    height=480, showlegend=True,
)
st.plotly_chart(fig, use_container_width=True)
st.caption("Hover over a point to see which " + ("period" if is_ts else ("city" if key_col == "city" else "state"))
           + " it is. The ringed point is the observation whose removal changes Spearman ρ the most.")

if fit.ok:
    fig_r = go.Figure()
    fig_r.add_trace(go.Scatter(
        x=data["x"], y=fit.residuals, mode="markers", marker=dict(size=9, color=TURQUOISE),
        text=hover_keys, hovertemplate="<b>%{text}</b><br>X: %{x:,.4g}<br>residual: %{y:,.4g}<extra></extra>",
        name="Residual",
    ))
    fig_r.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
    fig_r.update_layout(title="Residuals (actual Y − fitted Y) against X", xaxis_title=x_axis,
                        yaxis_title="Residual", height=360, showlegend=False)
    st.plotly_chart(fig_r, use_container_width=True)
    order = np.argsort(-np.abs(fit.residuals))[:3]
    st.caption(
        "Largest residuals (furthest from the line): "
        + "; ".join(f"{hover_keys.iloc[i]} ({fit.residuals[i]:+,.4g})" for i in order)
        + ". A funnel shape (residuals spreading as X grows) or a curve suggests the straight-line "
        "summary is a poor fit; try a log transform."
    )
else:
    st.info("OLS could not be computed (fewer than 3 observations, or X has no variation in this sample).")

# ---------------------------------------------------------------------------
# E. Time-series only: levels over time, lagged and rolling correlation
# ---------------------------------------------------------------------------

lag_df = pd.DataFrame()
roll_df = pd.DataFrame()
if is_ts:
    st.markdown("---")
    st.header("E · Over time: lagged & rolling correlation")
    fig_t = make_subplots(specs=[[{"secondary_y": True}]])
    fig_t.add_trace(go.Scatter(x=data[key_col], y=data["x"], name=x_axis, mode="lines+markers",
                               line=dict(color=TURQUOISE)), secondary_y=False)
    fig_t.add_trace(go.Scatter(x=data[key_col], y=data["y"], name=y_axis, mode="lines+markers",
                               line=dict(color=GOLD)), secondary_y=True)
    fig_t.update_yaxes(title_text=x_axis, secondary_y=False)
    fig_t.update_yaxes(title_text=y_axis, secondary_y=True, showgrid=False)
    fig_t.update_layout(title="Both series over the analysis sample", height=380, hovermode="x unified")
    st.plotly_chart(fig_t, use_container_width=True)

    if not rel.consecutive_periods(list(data[key_col])):
        callout("The aligned periods are <b>not consecutive</b> (there are gaps), so a lag of k "
                "below means k <i>observations</i>, not k periods. Interpret with care.", kind="warn")

    method = st.radio("Correlation used for lag and rolling analysis", ["pearson", "spearman"],
                      format_func=str.title, horizontal=True, key="rel_ts_method")
    max_lag = max(1, min(8, n - rel.MIN_OBS - 1))
    unit = {"period": "quarter", "financial_year": "financial year"}.get(key_col, "year")
    _clamp_state("rel_ts_lags", -max_lag, max_lag, (-min(4, max_lag), min(4, max_lag)))
    lag_range = st.slider(
        f"Lag range ({unit}s; positive = X leads Y)", min_value=-max_lag, max_value=max_lag,
        key="rel_ts_lags",
    )
    lag_df = rel.lagged_correlation(data, "x", "y", range(lag_range[0], lag_range[1] + 1), method=method)
    fig_l = go.Figure(go.Bar(
        x=lag_df["lag"], y=lag_df["r"],
        marker_color=[GOLD if l == 0 else TURQUOISE for l in lag_df["lag"]],
        customdata=np.c_[lag_df["p_value"], lag_df["n"]],
        hovertemplate="lag %{x}<br>r = %{y:.3f}<br>p = %{customdata[0]:.3f}<br>n = %{customdata[1]}<extra></extra>",
    ))
    fig_l.update_layout(title=f"{method.title()} correlation of X(t) with Y(t+k)", xaxis_title=f"k ({unit}s)",
                        yaxis_title="correlation", yaxis_range=[-1.05, 1.05], height=360)
    st.plotly_chart(fig_l, use_container_width=True)
    valid = lag_df.dropna(subset=["r"])
    if not valid.empty:
        best = valid.loc[valid["r"].abs().idxmax()]
        st.caption(
            f"Strongest |r| in the chosen range: k = {int(best['lag'])} (r = {best['r']:.3f}, "
            f"p = {_fmt_p(best['p_value'])}, n = {int(best['n'])}). Picking the best of "
            f"{len(valid)} lags inflates the chance of a spurious 'significant' result."
        )

    if n >= 6:
        w_max = n - 1
        w_default = max(4, min(8 if key_col == "period" else 5, w_max))
        _clamp_state("rel_ts_window", 4, w_max, w_default)
        window = st.slider(f"Rolling window ({unit}s)", min_value=4, max_value=w_max, key="rel_ts_window")
        roll_df = rel.rolling_correlation(data, key_col, "x", "y", window, method=method)
        fig_w = go.Figure(go.Scatter(x=roll_df[key_col], y=roll_df["r"], mode="lines+markers",
                                     line=dict(color=TURQUOISE)))
        fig_w.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
        fig_w.update_layout(title=f"Rolling {window}-{unit} {method.title()} correlation (labelled at window end)",
                            yaxis_title="correlation", yaxis_range=[-1.05, 1.05], height=340)
        st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.info("Too few observations for a rolling correlation (needs at least 6).")

    indicator_note(
        "lagged and rolling correlation",
        "**Lagged correlation** pairs X in period t with Y in period t + k. A positive k "
        "asks whether X *leads* Y (e.g. does the repo rate move before the index does?); a "
        "negative k asks whether Y leads X. Each lag uses only overlapping periods, so n "
        "shrinks as |k| grows. A peak at k ≠ 0 is consistent with a lead-lag pattern, but "
        "is not Granger causality and certainly not causation — and scanning many lags and "
        "reporting the best one is a multiple-comparisons problem.\n\n"
        "**Rolling correlation** recomputes the correlation over a moving window of "
        "consecutive periods, showing whether the relationship is stable or flips sign "
        "across sub-periods (e.g. before vs. after 2020). With short windows each value "
        "rests on only a handful of points and will swing widely by chance alone.\n\n"
        "**Caveat for all time-series statistics here.** Trending series (prices, nominal "
        "income, concentration shares that rose after 1980) correlate strongly in levels "
        "whether or not they are related — the classic 'spurious regression' problem. First "
        "differences and percent-change transforms remove much of that shared trend. "
        "Consecutive observations are also autocorrelated, so the p-values and confidence "
        "intervals on this page, which assume independence, are too optimistic.",
    )

# ---------------------------------------------------------------------------
# F. Aligned data & downloads
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("F · Aligned data & downloads")
table = pd.DataFrame({
    key_col: hover_keys,
    f"X raw: {x_meta['short']}": data["x_raw"],
    f"Y raw: {y_meta['short']}": data["y_raw"],
})
if x_tf != "none" or form == "differences":
    table[f"X: {x_axis}"] = data["x"]
if y_tf != "none" or form == "differences":
    table[f"Y: {y_axis}"] = data["y"]
if fit.ok:
    table["fitted Y"] = fit.fitted
    table["residual"] = fit.residuals
st.dataframe(table, use_container_width=True, hide_index=True)

if not is_ts and nsdp_cur_years_used:
    flagged = nsdp_cur[nsdp_cur["transcription_flag"].notna() & nsdp_cur["state"].isin(data[key_col])]
    flagged = flagged[flagged["financial_year"].isin([y for y in nsdp_cur_years_used if y])]
    if not flagged.empty:
        st.caption(
            "Transcription flag on current-price NSDP for: "
            + ", ".join(sorted(flagged["state"].unique()))
            + " — two source vintages disagree for this row (see DATA_REGISTRY.md); the value used is the screenshot transcription."
        )

meta = {
    "mode": mode,
    "hypothesis": h.question if h is not None else "",
    "X variable": x_meta["label"], "X period": x_meta["period"], "X status": x_meta["status"],
    "X source": x_meta["source"], "X transform": rel.TRANSFORM_LABELS[x_tf],
    "Y variable": y_meta["label"], "Y period": y_meta["period"], "Y status": y_meta["status"],
    "Y source": y_meta["source"], "Y transform": rel.TRANSFORM_LABELS[y_tf],
    "analysed form": form,
    "observations dropped at alignment": aligned.n_dropped,
    "observations dropped by transform": len(tp.dropped),
    "observations dropped by differencing": len(diff.dropped) if form == "differences" else 0,
    "verdict": vd.headline,
    "analysis": analysis_text,
    "caveat": "Observational association only; no identification strategy; not causal.",
}
summary = rel.regression_summary_table(corr, fit, meta=meta)
summary["value"] = summary["value"].astype(str)
with st.expander("Regression summary table"):
    st.dataframe(summary, use_container_width=True, hide_index=True)

slug = f"{x_var_id}_vs_{y_var_id}_{form}".replace(" ", "_")
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button("Download aligned data (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"aligned_{slug}.csv", mime="text/csv", key="rel_dl_data")
with d2:
    st.download_button("Download regression summary (CSV)", summary.to_csv(index=False).encode("utf-8"),
                       file_name=f"regression_summary_{slug}.csv", mime="text/csv", key="rel_dl_summary")
with d3:
    st.download_button("Download hypothesis overview (CSV)", overview.to_csv(index=False).encode("utf-8"),
                       file_name="hypotheses_overview.csv", mime="text/csv", key="rel_dl_overview")

st.markdown("---")
with st.expander("Methodology & limitations"):
    st.markdown(
        f"""
**Alignment**: explicit inner join on state or city name (cross-section) or period (time series). Aggregate rows ('India', 'All-India') and, by default, the tentative 2023 row of WIL Table C.1 are excluded by name and listed. Keys are matched exactly; near-matches are reported, never merged. Every dropped key is listed with its reason.

**Calendar mapping (WIL)**: {hyp.WIL_YEAR_NOTE}

**Frequency alignment (housing)**: quarterly RESIDEX values are averaged within each April-March financial year (`analysis.housing.financial_year_of_quarter`). By default only financial years with all four quarters observed are kept. No value is interpolated. City-level comparisons use `analysis.housing.CITY_TO_STATE` to attach the state's value to each city.

**First differences**: Δx_t = x_t − x_(t−1), computed only when period t−1 is observed (`analysis.relationships.first_differences`); gaps are reported, never bridged.

**Trend check**: Spearman ρ between each series and time; trending if |ρ| ≥ {rel.TREND_MIN_RHO} and p < {rel.ALPHA}. When both trend, the page warns that the levels correlation may be spurious.

**Statistics**: Pearson and Spearman correlation with two-sided p-values (`scipy.stats`; exact permutation p-value for Spearman when n ≤ {rel.EXACT_SPEARMAN_MAX_N}); OLS with an intercept, classical standard errors, and a t-distribution 95% CI for the slope (`analysis/relationships.py`, tested against `scipy.stats.linregress`). Initial income (log) vs. growth reproduces `analysis.regional.beta_convergence` exactly (a unit test checks this). Leave-one-out influence: Spearman ρ recomputed without each observation in turn.

**Verdict and analysis text**: thresholds |ρ| < {rel.WEAK_BELOW} weak, {rel.WEAK_BELOW}–{rel.STRONG_FROM} moderate, ≥ {rel.STRONG_FROM} strong; significance at {rel.ALPHA:.0%}. The paragraph is generated by `analysis.relationships.analysis_sentences` and unit-tested.

**Limitations**:
- Bivariate and observational: no controls, no identification, no causal interpretation.
- Different sources, survey designs and reference periods (see the warning at the top of the page).
- Small samples: state cross-sections are ~20-31 states, city cross-sections 50 cities sharing state values; national time series run from 5 (real NNI) to 72 (WIL income shares) years; real per-capita NNI has only seven non-consecutive financial years.
- Some pairs are linked by construction (WIL group shares sum to 100%; growth computed from initial income) — flagged on the page.
- Time-series p-values assume independent observations, which autocorrelated series violate; testing many pairs on one page makes some chance 'significant' results likely.
- The quarterly repo-rate / iBFPI pair is from the ILLUSTRATIVE build — a method demonstration only.
- State NSDP or MPCE is used as a proxy for city income in the housing comparisons — not city household income.
"""
    )

footnote(
    "All series are loaded from files in data/raw/ and data/processed/ via data_sources.loaders; statuses "
    "(VERIFIED / PARTIAL / SPLICED / DERIVED / ILLUSTRATIVE) follow DATA_REGISTRY.md. Results are descriptive "
    "statistics of these specific samples, not causal claims."
)
