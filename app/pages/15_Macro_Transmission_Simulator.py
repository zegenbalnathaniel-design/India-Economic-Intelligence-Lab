"""Macro Transmission Simulator.

Transparent, linear partial-equilibrium transmission chains for four
shocks — policy rate, crude oil, rupee, public capex. HYPOTHETICAL
arithmetic under stated assumptions: not a forecast, not an RBI or
government projection. Every default coefficient comes from
data/raw/transmission/parameters.csv with its citation; a coefficient that
could not be verified starts blank and every link that needs it shows
"needs parameter" instead of a number. All calculation is in
analysis/transmission.py.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import transmission as T
from app.components.theme import (
    setup, set_chart_source, kicker, callout, stat_card, footnote,
    GOLD, TURQUOISE, VERMILLION, MUTED, RULE, ESPRESSO, INK, WARM_WHITE, INK_SOFT,
)
from app.components.glossary import indicator_note
from app.components.provenance import sources_panel

setup("Macro Transmission Simulator", accent=GOLD)
set_chart_source("HYPOTHETICAL arithmetic on cited coefficients (data/raw/transmission/parameters.csv); not a forecast")

PARAMS = T.load_parameters()
DEFAULT_A = T.defaults(PARAMS, "A")
DEFAULT_B = T.defaults(PARAMS, "B")
PREFIX = "tm_"

# Persistent label: a fixed banner on every scroll position, plus the top callout and sidebar.
st.markdown(
    f"""<style>
    .tm-banner {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 1000; text-align: center;
        background: {INK}; border-top: 2px solid {VERMILLION}; color: {WARM_WHITE};
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; letter-spacing: .06em;
        padding: .45rem 1rem; }}
    .tm-banner b {{ color: {VERMILLION}; }}
    .block-container {{ padding-bottom: 4.5rem; }}
    .tm-big {{ border: 2px solid {VERMILLION}; background: #2A1414; color: {WARM_WHITE}; border-radius: 4px;
        padding: .9rem 1.1rem; font-size: 1.05rem; font-weight: 700; letter-spacing: .02em; margin: .4rem 0 1rem; }}
    </style>
<div class="tm-banner"><b>HYPOTHETICAL</b> — illustrative arithmetic under stated assumptions, not an RBI or government forecast</div>""",
    unsafe_allow_html=True,
)


def _reset_all() -> None:
    """Back to the cited defaults: forget every simulator widget except the scenario choice."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(PREFIX) and k != f"{PREFIX}scenario":
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Sidebar: scenario, shock, reset
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Transmission Simulator")
    st.markdown(
        f"<div style='border:1px solid {VERMILLION};padding:.5rem .7rem;border-radius:3px;font-size:12px;"
        f"color:{WARM_WHITE}'><b style='color:{VERMILLION}'>HYPOTHETICAL</b> — illustrative arithmetic, "
        "not a forecast.</div>", unsafe_allow_html=True,
    )
    scenario = st.radio("Scenario", T.SCENARIO_KEYS, format_func=lambda k: T.SCENARIOS[k].title,
                        key=f"{PREFIX}scenario")
    SC = T.SCENARIOS[scenario]
    lo, hi, default_shock, step = SC.slider
    shock = st.slider(f"{SC.shock_label} ({SC.shock_unit})", lo, hi, default_shock, step,
                      key=f"{PREFIX}shock_{scenario}")
    regime = T.FULL_PASS_THROUGH
    if scenario == "oil":
        regime = st.radio("Who bears the oil shock?", T.OIL_REGIMES, key=f"{PREFIX}oil_regime",
                          help="The cited CPI and growth effects assume full pass-through; the cited fiscal cost "
                               "assumes the government absorbs everything. The two are polar cases.")
    st.button("Reset to cited defaults", on_click=_reset_all, use_container_width=True, key=f"{PREFIX}reset_btn")
    st.caption("Reset restores the shock size and every parameter to the cited values (blank where none was verified).")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
kicker("Macro Transmission Simulator · India")
st.title("How a shock travels through the economy — link by link")
st.markdown(
    f"<div class='tm-big'>{html.escape(T.HYPOTHETICAL_LABEL)}</div>", unsafe_allow_html=True,
)
st.markdown(
    "Pick a shock in the sidebar. The simulator multiplies it through a chain of **published Indian estimates** — "
    "each one cited, with its source sentence — and shows where the chain is quantified, where it needs a number "
    "you must supply, and where the economics is real but no reliable coefficient exists. "
    "It is deliberately simple: straight-line arithmetic, one link at a time, no feedback."
)
callout(
    "**What this is not.** Not a forecast, not a macro model, not the RBI's or the government's view. Coefficients "
    "come from different studies, samples and episodes; adding them up is not legitimate (for example, the cumulative "
    "inflation effect of a rate change already includes the lending-rate channel). Defaults were checked through "
    "search-result summaries of the sources, not the PDFs themselves — re-check before relying on any of them.",
    kind="warn",
)

diagram_box = st.container()
results_box = st.container()
params_box = st.container()


# ---------------------------------------------------------------------------
# Parameters (rendered lower on the page, but read first)
# ---------------------------------------------------------------------------
def _help(key: str, set_name: str) -> str:
    row = T.citation_row(PARAMS, key, set_name)
    if row is None:
        return "No row in the parameters file."
    if pd.isna(row["value"]):
        return (f"ⓘ DATA REQUIRED — no value verified. {row['quote_or_context']} Unit: {row['unit']}. "
                "Enter a number from a source you trust; the links that use it stay 'needs parameter' until you do.")
    src = "alternative estimate (set B)" if (set_name == "B" and row["param_set"] == "B") else "cited default"
    return (f"ⓘ {src}: {row['value']:g} — {row['unit']}. Horizon: {row['horizon']}.\n\n"
            f"Source: {row['source_citation']}\n\nContext: {row['quote_or_context']}\n\n"
            f"URL: {row['url']}\n\nChecked: {row['verified_via']}")


def _input(key: str, set_name: str, default: float | None) -> float | None:
    spec = T.PARAMETERS[key]
    return st.number_input(
        spec.label + (" ⓘ" if default is not None else " — DATA REQUIRED"),
        value=default, step=spec.step, format="%.3f",
        key=f"{PREFIX}{set_name}_{key}", help=_help(key, set_name),
        placeholder="needs a value",
    )


scn_params = [k for k, s in T.PARAMETERS.items() if s.scenario == scenario]
coef_keys = [k for k in scn_params if not T.PARAMETERS[k].is_data_input]
data_keys = [k for k in scn_params if T.PARAMETERS[k].is_data_input]

with params_box:
    st.header("3 · Parameters — cited defaults, editable")
    st.markdown(
        "**Set A** starts from the cited default for each link. **Set B** starts from an *alternative* cited estimate "
        "where one was found (marked ◆), otherwise from set A — edit either to compare. Hover ⓘ for the source, its "
        "wording and how it was checked. A blank box is a coefficient no source could be verified for."
    )
    ca, cb = st.columns(2)
    params_a: dict[str, float | None] = {}
    params_b: dict[str, float | None] = {}
    with ca:
        st.subheader("Set A · cited defaults")
        for k in coef_keys:
            params_a[k] = _input(k, "A", DEFAULT_A[k])
    with cb:
        st.subheader("Set B · comparison")
        for k in coef_keys:
            if T.has_alternative(PARAMS, k):
                st.caption(f"◆ alternative estimate for: {T.PARAMETERS[k].label}")
            params_b[k] = _input(k, "B", DEFAULT_B[k])
    if data_keys:
        st.subheader("Data inputs (shared by both sets)")
        st.caption("Facts about the economy, not behavioural coefficients. None is pre-filled: enter the latest value "
                   "from a source you cite (the help text suggests where).")
        dcols = st.columns(len(data_keys))
        for col, k in zip(dcols, data_keys):
            with col:
                v = _input(k, "D", DEFAULT_A[k])
                params_a[k] = params_b[k] = v

table = T.comparison_table(scenario, shock, params_a, params_b, regime)
res_a = T.run(scenario, shock, params_a, regime)
res_b = T.run(scenario, shock, params_b, regime)


# ---------------------------------------------------------------------------
# 1 · Diagram
# ---------------------------------------------------------------------------
POS: dict[str, dict[str, tuple[float, float]]] = {
    "policy": {
        "Policy repo rate": (0.07, 0.40), "Lending rate (fresh loans)": (0.37, 0.92),
        "Lending rate (outstanding loans)": (0.37, 0.70), "Bank credit growth": (0.37, 0.48),
        "Exchange rate & capital flows": (0.50, 0.05), "Investment / GDP": (0.67, 0.97),
        "Consumption": (0.67, 0.70), "GDP growth": (0.93, 0.82), "CPI inflation": (0.93, 0.22),
    },
    "oil": {
        "Crude oil price": (0.07, 0.50), "Oil import bill": (0.30, 0.90), "Current account deficit": (0.62, 0.90),
        "Rupee pressure": (0.92, 0.90), "CPI inflation": (0.42, 0.62), "GDP growth": (0.75, 0.35),
        "Fiscal deficit (subsidy / excise)": (0.42, 0.10),
    },
    "rupee": {
        "INR per US$": (0.07, 0.50), "Import prices (₹)": (0.37, 0.86), "CPI inflation (imported)": (0.72, 0.92),
        "Trade volumes (X, M)": (0.40, 0.30), "Trade balance (short run)": (0.92, 0.58),
        "Trade balance (long run)": (0.92, 0.30), "GDP growth": (0.72, 0.06),
    },
    "capex": {
        "Public capex": (0.07, 0.50), "Aggregate demand (nominal GDP)": (0.45, 0.88), "Fiscal deficit": (0.45, 0.15),
        "Interest rates": (0.72, 0.15), "Private investment": (0.93, 0.78),
    },
}
BOX_W, BOX_H = 0.20, 0.13
EDGE_STYLE = {
    T.QUANTIFIED: dict(color=GOLD, dash="solid", width=3, name="Quantified (cited coefficient or identity)"),
    T.NEEDS_PARAMETER: dict(color=VERMILLION, dash="dash", width=2.5, name="Needs a parameter you supply"),
    T.QUALITATIVE: dict(color=MUTED, dash="dot", width=2, name="Qualitative only (no cited coefficient)"),
    T.NOT_APPLICABLE: dict(color=RULE, dash="dot", width=2, name="Not applied in this regime"),
}


def _clip(x0, y0, x1, y1):
    """Shorten the centre-to-centre segment so it starts and ends at the box edges."""
    dx, dy = x1 - x0, y1 - y0

    def t_exit(dx, dy):
        tx = (BOX_W / 2) / abs(dx) if dx else float("inf")
        ty = (BOX_H / 2) / abs(dy) if dy else float("inf")
        return min(tx, ty)

    t0 = t_exit(dx, dy)
    return x0 + dx * t0, y0 + dy * t0, x1 - dx * t0 * 1.04, y1 - dy * t0 * 1.04


def diagram(scn: str, results: list[T.Result]) -> go.Figure:
    pos = POS[scn]
    fig = go.Figure()
    values = {(r.link.source, r.link.target): r for r in results}
    for e in T.diagram_edges(scn, results):
        st_ = EDGE_STYLE[e["status"]]
        (xa, ya), (xb, yb) = pos[e["source"]], pos[e["target"]]
        x0, y0, x1, y1 = _clip(xa, ya, xb, yb)
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", showlegend=False,
                                 line=dict(color=st_["color"], width=st_["width"], dash=st_["dash"]),
                                 hoverinfo="text", hovertext=f"{e['source']} → {e['target']}<br>{e['label']}"))
        length = max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, 1e-9)
        fig.add_annotation(x=x1, y=y1, ax=x1 - (x1 - x0) / length * 0.03, ay=y1 - (y1 - y0) / length * 0.03,
                           xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowsize=1.0, arrowwidth=max(st_["width"], 2.5), arrowcolor=st_["color"], text="")
        r = values.get((e["source"], e["target"]))
        if r is not None and r.status in (T.QUANTIFIED, T.NEEDS_PARAMETER):
            txt = T.format_value(r.value, r.status, r.link.unit)
            fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=html.escape(txt), showarrow=False,
                               font=dict(size=11, color=st_["color"]), bgcolor=ESPRESSO, borderpad=2)
    for name, (x, y) in pos.items():
        is_shock = name == T.SCENARIOS[scn].nodes[0]
        fig.add_shape(type="rect", x0=x - BOX_W / 2, x1=x + BOX_W / 2, y0=y - BOX_H / 2, y1=y + BOX_H / 2,
                      line=dict(color=GOLD if is_shock else RULE, width=2 if is_shock else 1),
                      fillcolor=INK, layer="above")
        fig.add_annotation(x=x, y=y, text=html.escape(name).replace(" (", "<br>("), showarrow=False,
                           font=dict(size=12, color=WARM_WHITE if is_shock else INK_SOFT))
    for status, s in EDGE_STYLE.items():
        if status == T.NOT_APPLICABLE and scn != "oil":
            continue
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=s["name"],
                                 line=dict(color=s["color"], width=s["width"], dash=s["dash"])))
    fig.update_layout(
        height=470, title=f"HYPOTHETICAL · {T.SCENARIOS[scn].title}: transmission chain",
        xaxis=dict(visible=False, range=[-0.06, 1.06]), yaxis=dict(visible=False, range=[-0.06, 1.06]),
        legend=dict(orientation="h", y=-0.02, x=0, font=dict(size=11)), margin=dict(l=10, r=10, t=56, b=40),
        hovermode="closest",
    )
    return fig


with diagram_box:
    st.header(f"1 · The chain — {SC.title.lower()}")
    st.plotly_chart(diagram(scenario, res_a), use_container_width=True, key=f"{PREFIX}diagram_{scenario}")
    n_q = sum(r.status == T.QUANTIFIED for r in res_a)
    n_n = sum(r.status == T.NEEDS_PARAMETER for r in res_a)
    st.caption(
        f"Values on arrows use parameter set A and a shock of {shock:+g} {SC.shock_unit}. "
        f"{n_q} link(s) quantified, {n_n} waiting for a parameter, {len(SC.qualitative)} qualitative. "
        "Gold = quantified, red dashed = needs a parameter, grey dotted = qualitative."
    )


# ---------------------------------------------------------------------------
# 2 · Results
# ---------------------------------------------------------------------------
HORIZON_GROUPS = [
    ("Short run (within about a year)", ("short run",)),
    ("Medium / long run", ("medium run", "long run")),
    ("Accounting identities (hold at any horizon)", ("identity",)),
]


def _fmt_table(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "Effect": df["effect"], "From → to": df["from → to"],
        "Baseline (no shock)": [T.format_value(v if pd.notna(v) else None, s, u)
                                for v, s, u in zip(df["baseline (no shock)"], df["status A"], df["unit"])],
        "Scenario · set A": [T.format_value(v, s, u) for v, s, u in zip(df["scenario · set A"], df["status A"], df["unit"])],
        "Scenario · set B": [T.format_value(v, s, u) for v, s, u in zip(df["scenario · set B"], df["status B"], df["unit"])],
    })
    return out


with results_box:
    st.header("2 · Baseline vs scenario")
    st.markdown(
        f"Shock: **{shock:+g} {SC.shock_unit}** ({SC.shock_label.lower()})"
        + (f" · regime: **{regime}**" if scenario == "oil" else "")
        + ". The baseline is the same arithmetic with a zero shock — every quantified link is zero there, "
          "because each link is a straight line through the origin. Results are *changes* relative to whatever "
          "the baseline path would have been, not levels."
    )
    quant = [r for r in res_a if r.status == T.QUANTIFIED and r.link.unit in ("pp", "pp of GDP")][:4]
    if quant:
        cols = st.columns(len(quant))
        for col, r in zip(cols, quant):
            with col:
                stat_card(r.link.label, T.format_value(r.value, r.status, r.link.unit),
                          f"set A · {r.link.horizon}")
    for title, hs in HORIZON_GROUPS:
        part = table[table["horizon"].isin(hs)]
        if part.empty:
            continue
        st.subheader(title)
        st.dataframe(_fmt_table(part), hide_index=True, use_container_width=True)

    chart = table[table["unit"].isin(["pp", "pp of GDP"])]
    if not chart.empty:
        labels = [f"{e} ({u})" for e, u in zip(chart["effect"], chart["unit"])]
        fig = go.Figure()
        for set_name, col, colour in (("Set A", "scenario · set A", GOLD), ("Set B", "scenario · set B", TURQUOISE)):
            vals = chart[col].tolist()
            status = chart["status " + set_name[-1]].tolist()
            fig.add_trace(go.Bar(
                y=labels, x=[v if v is not None and pd.notna(v) else 0 for v in vals], orientation="h",
                name=set_name, marker_color=colour,
                text=[T.format_value(v if pd.notna(v) else None, s, "pp") for v, s in zip(vals, status)],
                textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{text}<extra>" + set_name + "</extra>",
            ))
        fig.add_vline(x=0, line_color=MUTED, line_width=1)
        fig.update_layout(
            height=max(300, 70 * len(labels) + 120), barmode="group",
            title=f"HYPOTHETICAL · change vs baseline, set A vs set B ({shock:+g} {SC.shock_unit})",
            xaxis_title="percentage points (pp, or pp of GDP)", yaxis=dict(autorange="reversed", automargin=True),
            legend=dict(orientation="h", y=1.02, x=0),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{PREFIX}bars_{scenario}")
        st.caption("Bars at zero labelled 'needs parameter' or 'not applied' have no value — they are not zero effects. "
                   "Links measured in % or US$ bn are in the tables above only.")

    if scenario == "rupee":
        st.subheader("Short run vs long run: the J-curve")
        ex_sr = params_a.get("export_price_elasticity_sr")
        im_sr = params_a.get("import_price_elasticity_sr")
        ex_lr = params_a.get("export_price_elasticity_lr")
        im_lr = params_a.get("import_price_elasticity_lr")
        ml_sr, ml_lr = T.marshall_lerner(ex_sr, im_sr), T.marshall_lerner(ex_lr, im_lr)
        st.markdown(
            "A depreciation makes imports dearer in rupees **at once**, but trade volumes adjust **slowly** "
            "(contracts, dollar invoicing, inelastic oil and gold imports). So the trade balance can first *worsen* "
            "and only later *improve* — the J-curve. Whether it improves at all depends on the "
            "**Marshall–Lerner condition**: starting from balanced trade, a depreciation improves the trade balance "
            "only if the export and import price elasticities sum to more than one, "
            r"$|\varepsilon_X| + |\varepsilon_M| > 1$."
        )
        def _ml_text(v):
            return "needs parameter" if v is None else ("holds (sum > 1)" if v else "fails (sum ≤ 1)")
        m1, m2 = st.columns(2)
        with m1:
            stat_card("Marshall–Lerner · short run (set A)", _ml_text(ml_sr), "elasticities you enter")
        with m2:
            stat_card("Marshall–Lerner · long run (set A)", _ml_text(ml_lr), "elasticities you enter")
        st.caption("No India price elasticities could be verified to a specific published number, so these start blank. "
                   "The trade-balance links stay 'needs parameter' until you enter them and the trade shares.")


# ---------------------------------------------------------------------------
# 4 · Equations and assumptions
# ---------------------------------------------------------------------------
st.header("4 · Equations, assumptions and sources — link by link")
for r in res_a:
    link = r.link
    status_txt = {T.QUANTIFIED: "quantified", T.NEEDS_PARAMETER: "needs parameter",
                  T.NOT_APPLICABLE: "not applied in this regime"}[r.status]
    with st.expander(f"{link.source} → {link.target} · {link.label} · {link.horizon} · {status_txt}"):
        st.latex(link.equation)
        st.markdown("**Assumptions**\n" + "\n".join(f"- {a}" for a in link.assumptions)
                    + "\n- Linear: zero shock gives zero; doubling the shock doubles the effect."
                    + "\n- Partial equilibrium: everything not in this link is held fixed.")
        if r.missing:
            st.markdown("**Missing:** " + ", ".join(f"`{m}`" for m in r.missing)
                        + " — enter a value in section 3 to quantify this link.")
        for k in link.params:
            row = T.citation_row(PARAMS, k, "A")
            if row is None:
                continue
            if pd.isna(row["value"]):
                st.markdown(f"`{k}` — **DATA REQUIRED.** {row['quote_or_context']}")
            else:
                st.markdown(f"`{k}` = **{row['value']:g}** ({row['unit']}; {row['horizon']}) — "
                            f"{row['source_citation']} [link]({row['url']})  \n"
                            f"<span style='color:{MUTED};font-size:13px'>“{html.escape(row['quote_or_context'])}” · "
                            f"checked: {html.escape(row['verified_via'])}</span>", unsafe_allow_html=True)

st.subheader("Qualitative links (real channels, no cited coefficient)")
for src, tgt, why in SC.qualitative:
    st.markdown(f"- **{src} → {tgt}.** {why}")

indicator_note(
    "a transmission chain",
    "**What it is.** A shock (say, a 50 bps repo hike) passes from one variable to the next: policy rate → bank "
    "lending rates → borrowing, investment and spending → output and prices. Each arrow here is one published "
    "estimate of how much the next variable moves.\n\n"
    "**How to read it.** Each number is *the change caused by this shock, other things equal*, over the horizon "
    "the source studied. Short-run links (within about a year) and medium-run cumulative effects are kept apart.\n\n"
    "**Where it misleads.** Real economies have feedback (the RBI reacts, the rupee moves, expectations shift), "
    "non-linearity (big shocks are not scaled-up small ones) and overlap between channels. Estimates from different "
    "studies are not additive. Treat every output as an order-of-magnitude illustration of the cited study's number, "
    "applied to your shock.",
    kind="caveat",
)


# ---------------------------------------------------------------------------
# 5 · Export
# ---------------------------------------------------------------------------
st.header("5 · Export this run")
payload = T.export_payload(scenario, shock, params_a, params_b, table, regime)
e1, e2 = st.columns(2)
with e1:
    st.download_button("Download inputs, outputs & citations (CSV)", T.export_csv(payload).encode("utf-8"),
                       file_name=f"transmission_{scenario}.csv", mime="text/csv", use_container_width=True,
                       key=f"{PREFIX}dl_csv")
with e2:
    st.download_button("Download inputs, outputs & citations (JSON)", T.export_json(payload).encode("utf-8"),
                       file_name=f"transmission_{scenario}.json", mime="application/json",
                       use_container_width=True, key=f"{PREFIX}dl_json")
st.caption("Both files carry the HYPOTHETICAL label, the shock, both parameter sets (edited values are marked "
           "USER-SET and lose the citation), every output with its status, and the qualitative links.")

with st.expander("The full parameters file (every default, its citation and how it was checked)"):
    st.dataframe(PARAMS, hide_index=True, use_container_width=True)

sources_panel("transmission_parameters")
footnote(
    "Status: HYPOTHETICAL arithmetic. Default coefficients are CITED (search-verified; primary PDFs not opened) or "
    "DATA REQUIRED (blank). Calculations in analysis/transmission.py; tests in tests/test_transmission.py."
)
