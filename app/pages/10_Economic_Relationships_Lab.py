"""Economic Relationships Lab.

Research question: do two economic variables already in this project move
together — and how strongly, how robustly, and with what caveats?

Every variable offered here is built from a real file already loaded by
another Lab (see DATA_REGISTRY.md). Nothing is fetched, imputed or
interpolated; the only operations are an explicit join, an optional
within-financial-year average of a quarterly index, the user's chosen
transform, and standard descriptive statistics (analysis/relationships.py).
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
from analysis import relationships as rel
from app.components.theme import (
    setup, kicker, callout, source_badge, stat_card, footnote,
    TURQUOISE, GOLD, MUTED,
)
from app.components.glossary import indicator_note
from data_sources import loaders

setup("Economic Relationships Lab", accent=TURQUOISE)

with st.sidebar:
    st.markdown("## Relationships Lab")
    st.caption("Sections")
    st.markdown(
        "- A · Choose a hypothesis\n"
        "- B · Alignment report\n"
        "- C · Association statistics\n"
        "- D · Scatter & residuals\n"
        "- E · Lagged & rolling correlation (time series)\n"
        "- F · Aligned data & downloads"
    )
    st.markdown("---")
    st.caption("Status: real data except the quarterly banking pair, which is ILLUSTRATIVE — see badges")


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

# Aggregate rows that must never be treated as a state observation.
AGGREGATES = {
    "India": "national aggregate row (PLFS), not a state",
    "All-India": "national aggregate row (HCES), not a state",
}

# Documented reasons for known gaps, appended to the generic join reason so
# a reader sees *why* a state is missing, not just that it is.
KNOWN_GAPS = {
    ("nsdp_current", "Delhi"): "current-price row held out in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv (ambiguous column count in the source screenshot; DATA_REGISTRY.md)",
    ("nsdp_current", "Puducherry"): "current-price row held out in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv (ambiguous column count in the source screenshot; DATA_REGISTRY.md)",
}


# ---------------------------------------------------------------------------
# Variable catalogue. Each builder returns a DataFrame [key, "value"] from a
# real loader; `period` states the actual year(s) the values refer to.
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
        "short": "Per-capita NSDP (current ₹)",
        "status": "PARTIAL", "source": "RBI Handbook of Statistics on Indian States (dbie.rbihub.in), transcribed",
        "kind": "year", "years": CUR_YEARS, "default_year": "2023-24" if "2023-24" in CUR_YEARS else CUR_YEARS[-1],
    },
    "nsdp_constant": {
        "label": "Per-capita NSDP, constant prices, spliced (₹)",
        "short": "Per-capita NSDP (constant ₹, spliced)",
        "status": "SPLICED", "source": "RBI Handbook Table 26, two base years linked by overlap factor",
        "kind": "year", "years": CON_YEARS, "default_year": CON_YEARS[-1],
    },
    "unemployment": {
        "label": "Unemployment rate, usual status, age 15+ (%)",
        "short": "PLFS unemployment rate (%)",
        "status": "PARTIAL", "source": "PLFS (MoSPI), survey year 2023-24",
        "kind": "fixed", "period": "PLFS survey year 2023-24",
    },
    "mpce_urban": {
        "label": "Urban average MPCE (₹ / person / month)",
        "short": "Urban MPCE (₹/month)",
        "status": "VERIFIED", "source": "MoSPI HCES 2023-24 Statement 7 — consumption, not income",
        "kind": "fixed", "period": f"HCES survey year {MPCE_YEAR}",
    },
    "beta_growth": {
        "label": "Average annual growth of per-capita NSDP, constant prices (% / yr)",
        "short": "Avg annual NSDP growth (%)",
        "status": "DERIVED", "source": "Log-difference growth over the spliced series (analysis.regional.beta_convergence)",
        "kind": "window",
    },
}

PRESETS = {
    "custom": "Custom — pick X and Y yourself",
    "inc_unemp": "Is higher per-capita income associated with lower unemployment?",
    "inc_mpce": "Do richer states have higher urban consumption?",
    "beta": "Did initially poorer states grow faster? (initial income vs growth)",
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


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

kicker("ECONOMIC RELATIONSHIPS · INDIA")
st.title("Do two economic variables move together?")
st.markdown(
    "Formulate a hypothesis about two variables **already in this project** — per-capita "
    "state income, unemployment, urban consumption, growth, house prices, the repo rate — "
    "and test it: an explicit, audited join of the two series, Pearson and Spearman "
    "correlation, a simple OLS fit with a confidence interval, residuals and, for time "
    "series, lagged and rolling correlation. No new data is introduced on this page."
)
source_badge(
    "RBI Handbook (NSDP) · PARTIAL / SPLICED", "PLFS 2023-24 · PARTIAL",
    "HCES 2023-24 · VERIFIED", "NHB RESIDEX · PARTIAL", "Bank panel · ILLUSTRATIVE",
)

callout(
    "<b>Observational data — correlation is not causation.</b> Everything on this page "
    "describes how two series co-move in data that were never designed to answer a causal "
    "question. There is <b>no identification strategy</b> here: no instrument, no natural "
    "experiment, no control variables. A relationship between two state-level variables "
    "can be produced entirely by a third factor — <b>state size, urbanisation, sectoral mix, "
    "migration, price levels</b>, or how a survey sampled each state — and reverse causation "
    "is always possible. The variables also come from <b>different years and different "
    "sources</b>: per-capita NSDP is an April-March financial-year series (current prices "
    f"{CUR_YEARS[0]}→{CUR_YEARS[-1]}; constant-price spliced {CON_YEARS[0]}→{CON_YEARS[-1]}); "
    "unemployment is PLFS survey year 2023-24; urban MPCE is HCES survey year "
    f"{MPCE_YEAR}; the RESIDEX composite index is quarterly {RESIDEX_FIRST}→{RESIDEX_LAST}; "
    f"the repo-rate and iBFPI series are quarterly {REPO_FIRST}→{REPO_LAST} from this "
    "project's illustrative build. Survey reference periods (PLFS, HCES) do not line up "
    "exactly with the April-March financial year.",
    kind="warn",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# A. Choose a hypothesis
# ---------------------------------------------------------------------------

st.header("A · Choose a hypothesis")
mode = st.radio(
    "Analysis mode", ["Cross-section of states", "Time series"],
    horizontal=True, key="rel_mode",
    help="Cross-section: one row per state, joined on state name. Time series: one row per period.",
)
is_ts = mode == "Time series"

x_df = y_df = None
x_meta: dict = {}
y_meta: dict = {}
key_col = "state"
x_var_id = y_var_id = ""
extra_badges: list[str] = []

if not is_ts:
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
else:
    family = st.selectbox(
        "Time-series family",
        ["housing", "banking"],
        format_func={
            "housing": f"Annual · city house-price index vs its state's per-capita NSDP (financial years)",
            "banking": f"Quarterly · RBI repo rate vs system iBFPI ({REPO_FIRST}→{REPO_LAST}) — ILLUSTRATIVE",
        }.get,
        key="rel_ts_family",
        help="X and Y must share a frequency, so each family only offers series observed on the same calendar.",
    )
    if family == "banking":
        key_col = "period"
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
            "repo": dict(label="RBI repo rate at quarter-end (%)", short="Repo rate (%)",
                         status="APPROXIMATE (illustrative build)",
                         source="data/processed/repo_rate.csv",
                         period=f"quarter-ends {REPO_FIRST}→{REPO_LAST}",
                         df=repo.rename(columns={"repo_rate": "value"})[["period", "value"]]),
            "ibfpi": dict(label="System iBFPI, equal-weighted across 5 banks (robust z-units)",
                          short="System iBFPI (ILLUSTRATIVE)", status="ILLUSTRATIVE (synthetic)",
                          source="data/processed/bank_panel.csv → analysis.banking",
                          period=f"quarter-ends {ibfpi['period'].min().to_period('Q')}→{ibfpi['period'].max().to_period('Q')}",
                          df=ibfpi[["period", "value"]]),
        }
        defaults = ("repo", "ibfpi")
    else:
        key_col = "financial_year"
        cities = sorted(c for c in residex["City"].unique() if c in housing.CITY_TO_STATE)
        hc1, hc2 = st.columns([1.2, 1])
        with hc1:
            city = _select(st.selectbox, "City (RESIDEX)", cities, "rel_ts_city",
                           "Mumbai" if "Mumbai" in cities else cities[0])
        state = housing.CITY_TO_STATE[city]
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
                            short=f"RESIDEX {city}", status="PARTIAL",
                            source="NHB RESIDEX city composite index, quarterly → FY mean",
                            period=(f"FY {fy.data['financial_year'].iloc[0]}→{fy.data['financial_year'].iloc[-1]}"
                                    if not fy.data.empty else "none"),
                            df=fy.data[["financial_year", "value"]]),
            "nsdp_current": dict(label=f"Per-capita NSDP, current prices, {state} (₹)",
                                 short=f"NSDP {state} (current ₹)", status="PARTIAL",
                                 source="RBI Handbook (dbie.rbihub.in), transcribed",
                                 period=f"FY {CUR_YEARS[0]}→{CUR_YEARS[-1]}",
                                 df=nsdp_cur[nsdp_cur["state"] == state][["financial_year", NSDP_CUR_COL]]
                                 .rename(columns={NSDP_CUR_COL: "value"})),
            "nsdp_constant": dict(label=f"Per-capita NSDP, constant prices spliced, {state} (₹)",
                                  short=f"NSDP {state} (constant ₹)", status="SPLICED",
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

if extra_badges:
    source_badge(*extra_badges)

st.markdown(
    f"**This comparison:** X = {x_meta['label']} — *{x_meta['period']}*, {x_meta['status']}. "
    f"Y = {y_meta['label']} — *{y_meta['period']}*, {y_meta['status']}."
)

# ---------------------------------------------------------------------------
# B. Alignment report
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("B · Alignment report")
aligned = rel.align_observations(
    x_df, y_df, key_col, "value", "value",
    x_label=x_meta["short"], y_label=y_meta["short"],
    exclude=AGGREGATES if not is_ts else None,
)

a1, a2, a3 = st.columns(3)
with a1:
    stat_card("Aligned observations", f"{aligned.n}", f"inner join on {key_col.replace('_', ' ')}")
with a2:
    stat_card("Dropped", f"{aligned.n_dropped}", "every one listed below with its reason")
with a3:
    stat_card("Source rows", f"X {aligned.n_x_source} · Y {aligned.n_y_source}", "after excluding aggregates")

if aligned.possible_name_mismatches:
    callout(
        "<b>Possible name mismatches — not joined automatically:</b> "
        + "; ".join(f"'{a}' vs '{b}'" for a, b in aligned.possible_name_mismatches)
        + ". These look like the same entity spelled differently; they are reported, not merged.",
        kind="warn",
    )
else:
    st.caption("No probable spelling mismatches between the two sources' keys (checked after normalising case, '&'/'and' and punctuation).")

if not aligned.dropped.empty:
    dropped_show = aligned.dropped.copy()
    if not is_ts:
        def _gap_note(row) -> str:
            for vid in (x_var_id, y_var_id):
                note = KNOWN_GAPS.get((vid, row[key_col]))
                if note and "not present in" in row["reason"]:
                    return note
            return ""
        dropped_show["documented context"] = dropped_show.apply(_gap_note, axis=1)
    else:
        dropped_show[key_col] = dropped_show[key_col].astype(str)
    with st.expander(f"Dropped observations ({aligned.n_dropped})", expanded=not is_ts and aligned.n_dropped <= 12):
        st.dataframe(dropped_show, use_container_width=True, hide_index=True)

indicator_note(
    "the alignment step",
    "**What it does.** The two variables come from different files, so before any "
    "statistic is computed they are matched row-by-row on a shared key — state name for "
    "a cross-section, quarter-end date or financial year for a time series — with an "
    "**inner join**: an observation is kept only if *both* variables have a real value for "
    "it. Nothing is filled in, carried forward or interpolated.\n\n"
    "**Why every drop is listed.** A silent join can quietly change the sample — e.g. a "
    "state missing from one survey, or the same state spelled two ways. Each dropped key "
    "is listed with its reason: an explicitly excluded national aggregate ('India', "
    "'All-India'), a key present in only one source, a missing value, or (for time "
    "series) a period lost to a percent-change transform. Keys that differ only in "
    "spelling are flagged as possible mismatches, not merged.\n\n"
    "**Caveat.** Which states survive the join is not random — small states and UTs are "
    "the ones most often missing — so the aligned sample may not represent India as a whole.",
    kind="method",
)

if aligned.n < rel.MIN_OBS:
    st.warning(rel.sample_size_warning(aligned.n))
    st.stop()

# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

st.subheader("Transforms")
t1, t2, t3 = st.columns([1, 1, 1])
sfx = "ts_" + st.session_state.get("rel_ts_family", "") if is_ts else "cs"
with t1:
    x_opts = rel.available_transforms(aligned.data["x"], time_series=is_ts)
    x_tf = _select(st.selectbox, "X transform", x_opts, f"rel_tf_x_{sfx}_{x_var_id}", "none",
                   format_func=rel.TRANSFORM_LABELS.get, on_change=None if is_ts else _to_custom)
with t2:
    y_opts = rel.available_transforms(aligned.data["y"], time_series=is_ts)
    y_tf = _select(st.selectbox, "Y transform", y_opts, f"rel_tf_y_{sfx}_{y_var_id}", "none",
                   format_func=rel.TRANSFORM_LABELS.get, on_change=None if is_ts else _to_custom)
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
data = tp.data
if not tp.dropped.empty:
    st.caption(f"{len(tp.dropped)} observation(s) lost to the percent-change transform (no previous period): "
               + ", ".join(str(k.date()) if hasattr(k, "date") else str(k) for k in tp.dropped[key_col]))


def _axis_label(meta: dict, tf: str) -> str:
    return meta["short"] if tf == "none" else f"{rel.TRANSFORM_LABELS[tf]} of {meta['short']}"


x_axis, y_axis = _axis_label(x_meta, x_tf), _axis_label(y_meta, y_tf)

indicator_note(
    "the transforms",
    "**Natural log** compresses large values, so a slope reads roughly in proportional "
    "terms (with both variables logged, the slope is an elasticity: % change in Y per 1% "
    "change in X). Offered only when every aligned value is strictly positive.\n\n"
    "**Z-score** rescales a variable to mean 0 and standard deviation 1 over the analysis "
    "sample. It does not change either correlation; it changes the units of the OLS slope "
    "(with both variables z-scored, the slope equals Pearson r).\n\n"
    "**Percent change** (time series only) replaces each level with its change from the "
    "previous period, which removes a shared upward trend — two series that both simply "
    "grow over time will look strongly correlated in levels even if they are unrelated. "
    "The first period is lost. Offered only for strictly positive level series (a percent "
    "change of a z-scored index like iBFPI is meaningless).",
)

# ---------------------------------------------------------------------------
# C. Association statistics
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("C · Association statistics")
corr = rel.correlations(data["x"], data["y"])
fit = rel.ols(data["x"], data["y"])
n = int(len(data))

warn = rel.sample_size_warning(n)
if warn:
    extra = (" State cross-sections in this project top out at roughly 21-31 aligned states "
             "(beta-convergence growth needs both endpoints; PLFS covers 29 states; Delhi and "
             "Puducherry are held out of the current-price NSDP file), so almost every "
             "cross-section here is small.") if not is_ts else (
             " Time series here are short (≤ 26 quarters or ≤ 11 complete financial years), and "
             "consecutive observations are not independent, which makes p-values over-confident.")
    callout(warn + extra, kind="warn")


def _fmt(v: float, d: int = 3) -> str:
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def _fmt_p(p: float) -> str:
    if p is None or not np.isfinite(p):
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


s1, s2, s3, s4 = st.columns(4)
with s1:
    stat_card("n (analysis sample)", f"{n}", f"{aligned.n_dropped + len(tp.dropped)} dropped in total")
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
    "uses the actual values, so one or two extreme states (a very rich small UT, say) can "
    "dominate it.\n\n"
    "**Spearman ρ** is Pearson's r computed on the *ranks* — it asks whether higher X goes "
    "with higher Y at all (any monotone relationship, straight or curved), and is far less "
    "sensitive to outliers. If Spearman is much stronger than Pearson, the relationship is "
    "monotone but curved or outlier-distorted; if Pearson is much stronger, a few extreme "
    "points are probably driving it.\n\n"
    "**The p-values** test the null hypothesis of zero association, assuming independent "
    "observations. A small p-value says 'this pattern would be unusual if there were truly "
    "no association' — not that the association is large, important or causal. With "
    "n < 20, treat p-values as rough guides; with time series, as over-confident.",
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

# ---------------------------------------------------------------------------
# D. Scatter & residuals
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("D · Scatter & residuals")
hover_keys = data[key_col].map(lambda k: str(k.date()) if hasattr(k, "date") else str(k))
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data["x"], y=data["y"], mode="markers", name="Observations",
    marker=dict(size=10, color=TURQUOISE, line=dict(width=0)),
    text=hover_keys,
    customdata=np.c_[data["x_raw"], data["y_raw"]],
    hovertemplate="<b>%{text}</b><br>X: %{x:,.4g}<br>Y: %{y:,.4g}"
                  "<br>raw X: %{customdata[0]:,.4g} · raw Y: %{customdata[1]:,.4g}<extra></extra>",
))
if show_fit and fit.ok:
    xs = np.linspace(data["x"].min(), data["x"].max(), 50)
    fig.add_trace(go.Scatter(
        x=xs, y=fit.intercept + fit.slope * xs, mode="lines", name="OLS fit",
        line=dict(color=GOLD, dash="dash", width=2), hoverinfo="skip",
    ))
fig.update_layout(
    title=f"{y_axis} vs {x_axis} (n = {n})", xaxis_title=x_axis, yaxis_title=y_axis,
    height=480, showlegend=show_fit,
)
st.plotly_chart(fig, use_container_width=True)
st.caption("Hover over a point to see which " + ("state" if not is_ts else "period") + " it is.")

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
    st.info("OLS could not be computed (X has no variation in this sample).")

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
    unit = "quarter" if key_col == "period" else "financial year"
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
        "income) correlate strongly in levels whether or not they are related — the classic "
        "'spurious regression' problem. Percent-change transforms remove much of that "
        "shared trend. Consecutive observations are also autocorrelated, so the p-values "
        "and confidence intervals on this page, which assume independence, are too optimistic.",
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
if x_tf != "none":
    table[f"X: {x_axis}"] = data["x"]
if y_tf != "none":
    table[f"Y: {y_axis}"] = data["y"]
if fit.ok:
    table["fitted Y"] = fit.fitted
    table["residual"] = fit.residuals
st.dataframe(table, use_container_width=True, hide_index=True)

if not is_ts and "nsdp_current" in (x_var_id, y_var_id):
    flagged = nsdp_cur[nsdp_cur["transcription_flag"].notna() & nsdp_cur["state"].isin(data[key_col])]
    yr_keys = [st.session_state.get(f"rel_cs_{s}_year_nsdp_current") for s in ("x", "y")]
    flagged = flagged[flagged["financial_year"].isin([y for y in yr_keys if y])]
    if not flagged.empty:
        st.caption(
            "Transcription flag on current-price NSDP for: "
            + ", ".join(sorted(flagged["state"].unique()))
            + " — two source vintages disagree for this row (see DATA_REGISTRY.md); the value used is the screenshot transcription."
        )

meta = {
    "mode": mode,
    "X variable": x_meta["label"], "X period": x_meta["period"], "X status": x_meta["status"],
    "X source": x_meta["source"], "X transform": rel.TRANSFORM_LABELS[x_tf],
    "Y variable": y_meta["label"], "Y period": y_meta["period"], "Y status": y_meta["status"],
    "Y source": y_meta["source"], "Y transform": rel.TRANSFORM_LABELS[y_tf],
    "observations dropped at alignment": aligned.n_dropped,
    "observations dropped by transform": len(tp.dropped),
    "caveat": "Observational association only; no identification strategy; not causal.",
}
summary = rel.regression_summary_table(corr, fit, meta=meta)
summary["value"] = summary["value"].astype(str)
with st.expander("Regression summary table"):
    st.dataframe(summary, use_container_width=True, hide_index=True)

slug = f"{x_var_id}_vs_{y_var_id}".replace(" ", "_")
d1, d2 = st.columns(2)
with d1:
    st.download_button("Download aligned data (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"aligned_{slug}.csv", mime="text/csv", key="rel_dl_data")
with d2:
    st.download_button("Download regression summary (CSV)", summary.to_csv(index=False).encode("utf-8"),
                       file_name=f"regression_summary_{slug}.csv", mime="text/csv", key="rel_dl_summary")

st.markdown("---")
with st.expander("Methodology & limitations"):
    st.markdown(
        """
**Alignment**: explicit inner join on state name (cross-section) or period (time series). Aggregate rows ('India', 'All-India') are excluded by name. Keys are matched exactly; near-matches are reported, never merged. Every dropped key is listed with its reason.

**Frequency alignment (housing family)**: the quarterly RESIDEX composite index is averaged within each April-March financial year (`analysis.housing.financial_year_of_quarter`). By default only financial years with all four quarters observed are kept. No value is interpolated.

**Statistics**: Pearson and Spearman correlation with two-sided p-values (`scipy.stats`); OLS with an intercept, classical standard errors, and a t-distribution 95% CI for the slope (`analysis/relationships.py`, tested against `scipy.stats.linregress`). Initial income (log) vs. growth reproduces `analysis.regional.beta_convergence` exactly (a unit test checks this).

**Limitations**:
- Bivariate and observational: no controls, no identification, no causal interpretation.
- Different sources, survey designs and reference periods (see the warning at the top of the page).
- Small samples: state cross-sections are ~20-31 states; time series are ≤ 26 quarters or ≤ 11 financial years.
- Time-series p-values assume independent observations, which autocorrelated series violate.
- The quarterly repo-rate / iBFPI pair is from the ILLUSTRATIVE build — a method demonstration only.
- State NSDP is used as a proxy for city income in the housing family — not city household income.
"""
    )

footnote(
    "All series are loaded from files in data/raw/ and data/processed/ via data_sources.loaders; statuses "
    "(VERIFIED / PARTIAL / SPLICED / DERIVED / ILLUSTRATIVE) follow DATA_REGISTRY.md. Results are descriptive "
    "statistics of these specific samples, not causal claims."
)
