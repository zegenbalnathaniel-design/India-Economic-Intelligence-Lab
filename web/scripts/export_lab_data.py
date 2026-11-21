"""Export the Streamlit labs' data to JSON bundles for the web application.

Run from the repository root:

    SSL_CERT_FILE=$(.venv/bin/python -m certifi) .venv/bin/python web/scripts/export_lab_data.py

Every number the web labs show comes from here, and every one is produced by
the repository's own loaders and analysis modules -- nothing is retyped. The
World Bank series the Streamlit pages fetched live are snapshotted at export
time (the retrieval date is written into each bundle), so the static site
never depends on the API being up.

Alongside the data, each bundle carries a few `reference` results computed by
the Python analysis code. The TypeScript engines' tests assert they reproduce
these numbers, so the web labs cannot silently drift from the Python ones.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis import convergence as C  # noqa: E402
from analysis import econometrics as E  # noqa: E402
from analysis import financialisation as F  # noqa: E402
from analysis import housing as Hs  # noqa: E402
from analysis import hypotheses as H  # noqa: E402
from analysis import inequality as I  # noqa: E402
from analysis import relationships as R  # noqa: E402
from analysis import states as S  # noqa: E402
from analysis import structural as ST  # noqa: E402
from analysis import transmission as T  # noqa: E402
from analysis import workbench_catalogue as W  # noqa: E402
from data_sources import loaders as L  # noqa: E402
from data_sources import wdi_financial as WF  # noqa: E402
from data_sources import worldbank as WB  # noqa: E402

OUT = ROOT / "web" / "src" / "data" / "labs"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clean(v):
    """JSON-safe: NaN/inf -> None, numpy scalars -> Python, round floats."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return float(f"{f:.10g}")
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d")
    if v is pd.NaT:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def records(df: pd.DataFrame, cols=None) -> list[dict]:
    d = df if cols is None else df[cols]
    return clean(d.to_dict(orient="records"))


def write(name: str, payload: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(clean(payload), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


def wb_snapshot(codes, countries, start, end) -> dict:
    """{code: {iso3: [[year, value], ...]}} plus country names."""
    df = WB.fetch(list(codes), list(countries), start, end)
    out: dict = {}
    names = {}
    for (code, iso), g in df.dropna(subset=["value"]).groupby(["indicator", "iso3"]):
        g = g.sort_values("year")
        out.setdefault(code, {})[iso] = [[int(y), float(v)] for y, v in zip(g["year"], g["value"])]
        names[iso] = g["country"].iloc[0]
    return {"series": out, "countries": names, "retrieved": NOW, "source": "World Bank WDI API v2"}


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

def export_states() -> None:
    panel = S.build_panel()
    nsdp = L.load_nsdp_spliced()
    ind = {k: {"key": k, "label": m.label, "unit": m.unit, "status": m.status, "source": m.source,
               "priceBasis": m.price_basis, "explainer": m.explainer} for k, m in S.INDICATORS.items()}
    years = sorted(nsdp["financial_year"].unique(), key=S.fiscal_year_start)
    sigma = C.sigma_dispersion(nsdp, years[0], years[-1], "sd_log")
    beta = C.beta_window(nsdp, years[0], years[-1])
    beta_hc1 = C.beta_window(nsdp, years[0], years[-1], robust=True)
    write("states", {
        "retrieved": NOW,
        "indicators": ind,
        "panel": [[r.state, r.indicator, r.period, clean(r.value)] for r in panel.itertuples()],
        "notes": {f"{r.state}|{r.indicator}|{r.period}": r.note for r in panel.itertuples()
                  if isinstance(r.note, str) and r.note.strip()},
        "benchmarks": records(S.national_benchmarks()),
        "spliced": [[r.state, r.financial_year, clean(getattr(r, C.VALUE_COL)), r.method]
                    for r in nsdp.itertuples()],
        "spliceBoundary": C.SPLICE_BOUNDARY,
        "measures": {k: {"key": k, "label": m.label, "unit": m.unit, "formula": m.formula, "reading": m.reading}
                     for k, m in C.MEASURES.items()},
        "populationCaveat": C.POPULATION_WEIGHTING_CAVEAT,
        "sigmaRule": C.sigma_rule_text(),
        "speedFormula": C.SPEED_FORMULA,
        "tileGrid": {s: list(rc) for s, rc in C.TILE_GRID.items()},
        "tileAbbr": dict(C.TILE_ABBR),
        "tileCaption": C.TILE_CAPTION,
        "sectorShares": records(L.load_state_sector_shares()),
        "sectorRlp": records(ST.state_rlp(L.load_state_sector_shares())),
        "reference": {
            "sigma": {"start": years[0], "end": years[-1], "first": sigma.first_value, "last": sigma.last_value,
                      "slope": sigma.slope_per_year, "p": sigma.slope_p, "verdict": sigma.verdict,
                      "n": len(sigma.included_states)},
            "beta": {"slope": beta.fit.slope, "se": beta.fit.se, "p": beta.fit.p, "r2": beta.fit.r_squared,
                     "n": beta.fit.n, "speed": beta.speed, "halfLife": beta.half_life,
                     "seHC1": beta_hc1.fit.se, "pHC1": beta_hc1.fit.p},
        },
    })


# ---------------------------------------------------------------------------
# Housing
# ---------------------------------------------------------------------------

def export_housing() -> None:
    prices = L.load_residex_price_levels()
    index = L.load_residex_index()
    nsdp_cur = L.load_nsdp_current()
    mpce = L.load_hces_urban_mpce()
    city_inc = L.load_city_household_income()
    quarters = list(Hs.sort_quarters(prices.drop_duplicates(subset=["quarter"]))["quarter"])
    price_series = {}
    for city, g in prices.groupby("city"):
        g = Hs.sort_quarters(g)
        price_series[city] = [[q, clean(v), clean(a), clean(b), clean(c)] for q, v, a, b, c in zip(
            g["quarter"], g["composite_price_inr_per_sqft"], g["price_le_60sqm_inr_per_sqft"],
            g["price_60_110sqm_inr_per_sqft"], g["price_gt_110sqm_inr_per_sqft"])]
    idx_series = {}
    for city, g in index.groupby("City"):
        g = Hs.sort_quarters(g.rename(columns={"quarter_raw": "quarter"}))
        idx_series[city] = [[q, clean(v)] for q, v in zip(g["quarter"], g["composite_index"])]
    income_states = {}
    for state, g in nsdp_cur.dropna(subset=["percapita_nsdp_current_prices_inr"]).groupby("state"):
        g = g.sort_values("financial_year")
        income_states[state] = [[fy, float(v)] for fy, v in zip(g["financial_year"], g["percapita_nsdp_current_prices_inr"])]
    ref = Hs.city_affordability(prices, nsdp_cur, "Mumbai")
    ref_r = Hs.relative_price_income_pressure(index, nsdp_cur, "Mumbai")
    ref_s = Hs.stress_index_cross_section(prices, nsdp_cur)
    write("housing", {
        "retrieved": NOW,
        "quarters": quarters,
        "fyOfQuarter": {q: Hs.financial_year_of_quarter(q) for q in sorted(set(quarters) | set(index["quarter_raw"]))},
        "cityToState": dict(Hs.CITY_TO_STATE),
        "prices": price_series,
        "index": idx_series,
        "baseQuarter": Hs.RESIDEX_BASE_QUARTER,
        "sqftPerSqm": Hs.SQFT_PER_SQM,
        "defaultUnitSqm": Hs.DEFAULT_UNIT_SIZE_SQM,
        "nsdpCurrent": income_states,
        "mpce": {r.state_ut: float(r.average_monthly_per_capita_consumption_expenditure_inr)
                 for r in mpce.itertuples() if pd.notna(r.average_monthly_per_capita_consumption_expenditure_inr)},
        "cityIncome": records(city_inc),
        "caveats": dict(Hs.INCOME_PROXY_CAVEATS),
        "rateDisclosure": Hs.RATE_DISCLOSURE,
        "usable": records(L.load_residex_usable_records()),
        "reference": {
            "mumbai": {"quarter": ref.quarter, "unitPrice": ref.unit_price, "income": ref.annual_income_proxy,
                       "pti": ref.price_to_income, "emi": ref.emi_monthly, "emiPct": ref.emi_to_income_pct},
            "rpipiMumbai": {"base": ref_r.base_financial_year, "latest": ref_r.latest_financial_year,
                            "value": ref_r.latest_rpipi},
            "stressTop": records(ref_s.scores.head(3), ["city", "price_to_income", "stress_score_0_100"]),
        },
    })


# ---------------------------------------------------------------------------
# Inequality & financialisation
# ---------------------------------------------------------------------------

def export_inequality() -> None:
    inc = L.load_wil_income_shares()
    wea = L.load_wil_wealth_shares()
    gt = I.group_table(L.load_wil_income_2022(), L.load_wil_wealth_2022())
    gini_i = I.gini_series(inc)
    wdi = wb_snapshot(list(WF.INDICATORS), ["IND"] + list(WB.PEER_COUNTRIES), 1960, datetime.now().year)
    write("inequality", {
        "retrieved": NOW,
        "incomeShares": records(inc),
        "wealthShares": records(wea),
        "vhnwi": records(L.load_wil_vhnwi()),
        "income2022": records(L.load_wil_income_2022()),
        "wealth2022": records(L.load_wil_wealth_2022()),
        "facts": records(L.load_wil_facts()),
        "groupTable": records(gt),
        "riffleCaptions": I.riffle_captions(gt),
        "composition": records(F.composition_table(L.load_paper_a_returns())),
        "aidisHeadline": records(L.load_aidis_debt_headline()),
        "aidisGroups": records(L.load_aidis_author_supplied()),
        "wdiMeta": {c: {"code": c, "label": m.label, "unit": m.unit, "definition": m.definition}
                    for c, m in WF.INDICATORS.items()},
        "accountCodes": list(WF.ACCOUNT_CODES),
        "depthCodes": list(WF.DEPTH_CODES),
        "wdi": wdi,
        "reference": {"giniIncome": records(gini_i.tail(3))},
    })


# ---------------------------------------------------------------------------
# Structural transformation
# ---------------------------------------------------------------------------

def export_structural() -> None:
    countries = ["IND"] + list(WB.PEER_COUNTRIES)
    df = WB.fetch(list(ST.CODES), countries, 1991, datetime.now().year)
    snap = {"series": {}, "countries": {}, "retrieved": NOW, "source": "World Bank WDI API v2 (ILO modelled estimates for employment)"}
    for (code, iso), g in df.dropna(subset=["value"]).groupby(["indicator", "iso3"]):
        g = g.sort_values("year")
        snap["series"].setdefault(code, {})[iso] = [[int(y), float(v)] for y, v in zip(g["year"], g["value"])]
        snap["countries"][iso] = g["country"].iloc[0]
    meta = {c: {"code": c, "label": m.label, "unit": m.unit, **{k: getattr(m, k) for k in ("sector", "kind", "note")
            if hasattr(m, k)}} for c, m in ST.INDICATORS.items()}
    write("structural", {
        "retrieved": NOW,
        "meta": meta,
        "wdi": snap,
        "findings": ST.findings(df, "IND"),
        "stateShares": records(L.load_state_sector_shares()),
        "stateRlp": records(ST.state_rlp(L.load_state_sector_shares())),
    })


# ---------------------------------------------------------------------------
# Macro & world
# ---------------------------------------------------------------------------

def export_macro() -> None:
    wdi = wb_snapshot(list(WB.INDICATORS), ["IND"] + list(WB.PEER_COUNTRIES), 1990, datetime.now().year)
    write("macro", {
        "retrieved": NOW,
        "monthly": records(L.load_macro_monthly()),
        "decisions": records(L.load_rbi_policy_decisions()),
        "calendar": records(L.load_release_calendar()),
        "repoQuarterly": [[d.strftime("%Y-%m-%d"), float(v)] for d, v in zip(L.load_repo_rate()["period"], L.load_repo_rate()["repo_rate"])],
        "wdiMeta": {c: {"code": c, "label": m.label, "unit": m.unit} for c, m in WB.INDICATORS.items()},
        "defaultPeers": list(WB.DEFAULT_PEERS),
        "wdi": wdi,
    })


# ---------------------------------------------------------------------------
# Relationships + regression workbench
# ---------------------------------------------------------------------------

def _var(v) -> dict:
    return {"label": v.label, "short": v.short, "unit": v.unit, "status": v.status, "source": v.source, "period": v.period}


def _pairs(df: pd.DataFrame, key: str) -> list:
    return [[clean(k), clean(v)] for k, v in zip(df[key], df["value"])]


def export_relationships() -> None:
    hyps = []
    for hid in H.HYPOTHESIS_IDS:
        h = H.build(hid, include_tentative=True)
        tent = H.build(hid, include_tentative=False)
        tentative_keys = sorted({clean(k) for k in h.exclude} ^ {clean(k) for k in tent.exclude}, key=str)
        hyps.append({
            "id": h.id, "group": h.group, "question": h.question, "rationale": h.rationale, "kind": h.kind,
            "key": h.key, "obsNoun": h.obs_noun, "x": _var(h.x), "y": _var(h.y),
            "xData": _pairs(h.x_df, h.key), "yData": _pairs(h.y_df, h.key),
            "xTf": h.x_tf, "yTf": h.y_tf, "caveats": list(h.caveats), "caveatNote": h.caveat_note,
            "exclude": {str(clean(k)): v for k, v in tent.exclude.items()},
            "tentativeKeys": tentative_keys, "periodWord": h.period_word, "notes": list(h.notes),
            "usesTentative": tent.uses_tentative or bool(tentative_keys),
        })
    overview = H.overview_table()
    cat = []
    for v in W.catalogue():
        frames = {}
        for p in (v.periods or ("",)):
            fr = v.frame(p)
            key = "state" if v.level == "state" else "year"
            frames[p] = [[clean(k), clean(x)] for k, x in zip(fr[key], fr["value"])]
        cat.append({"id": v.id, "level": v.level, "group": v.group, "label": v.label, "short": v.short,
                    "unit": v.unit, "status": v.status, "source": v.source, "periods": list(v.periods),
                    "defaultPeriod": v.default_period, "tentative": [[clean(k), r] for k, r in v.tentative],
                    "shareGroup": v.share_group, "note": v.note, "frames": frames})
    # Reference: a two-regressor OLS on the state cross-section with HC1 errors.
    ref_ols = None
    try:
        a = {k: x for k, x in next(c for c in cat if c["id"] == "st_unemployment")["frames"]["2023-24"]}
        b = {k: x for k, x in next(c for c in cat if c["id"] == "st_mpce_urban")["frames"]["2023-24"]}
        c_ = next(c for c in cat if c["id"] == "st_nsdp_current")
        cp = c_["defaultPeriod"]
        cc = {k: x for k, x in c_["frames"][cp]}
        keys = sorted(k for k in a if k in b and k in cc and None not in (a[k], b[k], cc[k]))
        data = pd.DataFrame({"y": [a[k] for k in keys], "x1": [b[k] for k in keys], "x2": [cc[k] for k in keys]})
        fit = E.fit_ols(data, "y", ["x1", "x2"], se_type="HC1")
        bp = E.breusch_pagan(fit)
        jb = E.jarque_bera_test(fit)
        ref_ols = {"period": cp, "keys": keys, "params": clean(list(fit.table["coef"])),
                   "bse": clean(list(fit.table["std_err"])), "p": clean(list(fit.table["p"])),
                   "r2": fit.r_squared, "adjR2": fit.adj_r_squared, "f": fit.f_stat, "fP": fit.f_pvalue,
                   "n": fit.n, "bp": [bp.statistic, bp.p_value], "jb": [jb.statistic, jb.p_value],
                   "vif": clean(list(E.vif_table(fit)["vif"])) if "vif" in E.vif_table(fit) else None}
        fit_nr = E.fit_ols(data, "y", ["x1", "x2"])
        ref_ols["bseClassical"] = clean(list(fit_nr.table["std_err"]))
    except Exception as exc:  # noqa: BLE001
        print("reference OLS skipped:", exc)
    write("relationships", {
        "retrieved": NOW,
        "hypotheses": hyps,
        "overview": records(overview),
        "catalogue": cat,
        "levels": dict(W.LEVELS),
        "fyNote": W.FY_NOTE,
        "causationNote": E.CAUSATION_NOTE,
        "caveatText": dict(R.CAVEAT_TEXT),
        "reference": {"ols": ref_ols},
    })


# ---------------------------------------------------------------------------
# Transmission simulator
# ---------------------------------------------------------------------------

def export_transmission() -> None:
    p = T.load_parameters()
    pa, pb = T.defaults(p, "A"), T.defaults(p, "B")
    ref = {}
    for key, sc in T.SCENARIOS.items():
        for regime in (T.OIL_REGIMES if key == "oil" else (T.FULL_PASS_THROUGH,)):
            ref[f"{key}|{regime}"] = [{"id": r.link.id, "value": r.value, "status": r.status}
                                     for r in T.run(key, sc.slider[2], pa, regime)]
    write("transmission", {
        "retrieved": NOW,
        "label": T.HYPOTHETICAL_LABEL,
        "parameters": records(p),
        "specs": {k: {"label": s.label, "scenario": s.scenario, "step": s.step, "isDataInput": s.is_data_input}
                  for k, s in T.PARAMETERS.items()},
        "defaultsA": pa, "defaultsB": pb,
        "scenarios": {k: {"key": s.key, "title": s.title, "shockLabel": s.shock_label, "shockUnit": s.shock_unit,
                          "slider": list(s.slider), "nodes": list(s.nodes),
                          "qualitative": [list(q) for q in s.qualitative]} for k, s in T.SCENARIOS.items()},
        "links": {k: [{"scenario": l.scenario, "id": l.id, "source": l.source, "target": l.target, "label": l.label,
                       "unit": l.unit, "horizon": l.horizon, "params": list(l.params), "equation": l.equation,
                       "assumptions": list(l.assumptions), "regime": l.regime} for l in links]
                  for k, links in T.LINKS.items()},
        "regimes": list(T.OIL_REGIMES),
        "reference": ref,
    })


if __name__ == "__main__":
    for fn in (export_states, export_housing, export_inequality, export_structural, export_macro,
               export_relationships, export_transmission):
        fn()
