"""Hypothesis library for the Economic Relationships Lab.

Each entry pairs two variables that already exist in this repository
(loaded only through `data_sources.loaders`) with a question, a one-line
economic rationale, the data status of each side, a source line naming the
table/file, default transforms and the caveat codes that drive the
auto-generated analysis text (`analysis.relationships.analysis_sentences`).

Nothing here creates, fills, interpolates or edits a value. The only
operations are: selecting columns/rows from a loaded table, mapping a
financial-year label to the calendar year the WIL tables use for the same
year (see `WIL_YEAR_NOTE`), mapping cities to their state with the same
documented `analysis.housing.CITY_TO_STATE` table the Housing Lab uses,
averaging a quarterly series within complete financial years
(`relationships.quarterly_to_financial_year`), and the growth-rate
calculation already in `analysis.regional.beta_convergence`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from analysis import housing, regional
from analysis import relationships as rel
from data_sources import loaders

# --------------------------------------------------------------------------
# Shared constants
# --------------------------------------------------------------------------

AGGREGATES = {
    "India": "national aggregate row (PLFS), not a state",
    "All-India": "national aggregate row (HCES), not a state",
}

TENTATIVE_REASON = ("2023 row of WIL Table C.1 is flagged tentative by the authors — excluded by default "
                    "(tick 'Include tentative 2023 wealth row' to add it)")

WIL_YEAR_NOTE = ("WIL year Y is matched to India's financial year Y-(Y+1): the paper's Table 2, "
                 "labelled 2022-23, equals the 2022 row of Table B.1 (checked in tests/test_inequality.py).")

SRC_B1 = "WIL Working Paper 2024/09, Table B.1 (data/raw/wil/tableB1_income_shares_1951_2022.csv)"
SRC_C1 = "WIL Working Paper 2024/09, Table C.1 (data/raw/wil/tableC1_wealth_shares_1961_2023.csv)"
SRC_C2 = "WIL Working Paper 2024/09, Table C.2 (data/raw/wil/tableC2_vhnwi_1988_2022.csv)"
SRC_NSDP_CUR = "RBI Handbook, per-capita NSDP at current prices (rbi_handbook/nsdp_current_prices_by_state_2011_12_to_2024_25.csv)"
SRC_NSDP_CON = "RBI Handbook Table 26, spliced (rbi_handbook/percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv)"
SRC_PLFS = "PLFS 2023-24, MoSPI (data/raw/plfs_unemployment_rate_by_state_2023_24.csv)"
SRC_HCES = "MoSPI HCES 2023-24 Statement 7 (data/raw/hces/state_ut_urban_mpce_2023_24.csv)"
SRC_NNI = "Real per-capita NNI, all-India (data/raw/real_percapita_nni_timeseries.csv; source inferred as MoSPI NAS)"
SRC_GCF = ("RBI Handbook, institutional-sector gross capital formation at current prices "
           "(rbi_handbook/institutional_sector_gross_capital_formation_2011_12_to_2023_24.csv)")
SRC_RESIDEX = "NHB RESIDEX city price levels (nhb_residex/city_price_levels_by_unit_size_2013_2024.csv)"


@dataclass(frozen=True)
class VarSpec:
    label: str        # full axis / table label
    short: str        # short name used in sentences
    unit: str         # unit of one raw value, for the slope sentence
    status: str       # VERIFIED / PARTIAL / SPLICED / DERIVED / ILLUSTRATIVE
    source: str
    period: str


@dataclass
class Hypothesis:
    id: str
    group: str
    question: str
    rationale: str
    kind: str                     # "cross_section" or "time_series"
    key: str                      # join key column
    obs_noun: str                 # "states", "years", ...
    x: VarSpec
    y: VarSpec
    x_df: pd.DataFrame            # [key, "value"]
    y_df: pd.DataFrame            # [key, "value"]
    x_tf: str = "none"
    y_tf: str = "none"
    caveats: Tuple[str, ...] = ()
    caveat_note: str = ""
    exclude: Dict[object, str] = field(default_factory=dict)
    period_word: str = "year"
    notes: List[str] = field(default_factory=list)
    uses_tentative: bool = False
    existing: bool = False        # one of the three original presets

    @property
    def is_ts(self) -> bool:
        return self.kind == "time_series"

    @property
    def status_text(self) -> str:
        return f"X: {self.x.status} · Y: {self.y.status}"

    @property
    def source_line(self) -> str:
        return f"X — {self.x.source}. Y — {self.y.source}."


# Catalogue order and the question shown in the selector (kept here so the
# selector does not need to build every hypothesis).
QUESTIONS: Dict[str, str] = {
    # Original presets (cross-section of states)
    "inc_unemp": "Is higher per-capita income associated with lower unemployment?",
    "inc_mpce": "Do richer states have higher urban consumption?",
    "beta": "Did initially poorer states grow faster? (initial income vs growth)",
    # New: income and wealth concentration (WIL)
    "wil_top1_income_vs_wealth": "Do income and wealth concentration at the top move together?",
    "wil_billionaires_vs_top1_wealth": "Does billionaire wealth track the Top 1% wealth share?",
    "wil_billionaires_vs_top01_wealth": "Does billionaire wealth track the Top 0.1% wealth share?",
    "wil_billionaires_vs_top1_income": "Do years with more billionaire wealth have a higher Top 1% income share?",
    "wil_bottom50_vs_top10_income": "When the Top 10% income share rises, does the Bottom 50% share fall? (mechanical-link example)",
    "wil_top1_vs_bottom50_wealth": "Do gains in the Top 1% wealth share come with a smaller Bottom 50% share?",
    "wil_forbes_vs_hurun": "Do the two rich lists (Forbes, Hurun) agree on billionaire wealth?",
    # New: growth and investment
    "nni_vs_top10_income": "Has rising real per-capita income coincided with rising Top 10% income share?",
    "gcf_public_vs_private": "Does public-corporate investment move with private-corporate investment (crowding in)?",
    # New: states and cities
    "mpce_vs_unemployment": "Do states with higher urban consumption have higher or lower unemployment?",
    "growth_vs_mpce": "Did faster-growing states end up with higher urban consumption?",
    "city_price_vs_state_mpce": "Are house prices higher in cities whose states consume more?",
}
GROUPS: Dict[str, str] = {
    "inc_unemp": "States", "inc_mpce": "States", "beta": "States",
    "wil_top1_income_vs_wealth": "Inequality (WIL)", "wil_billionaires_vs_top1_wealth": "Inequality (WIL)",
    "wil_billionaires_vs_top01_wealth": "Inequality (WIL)", "wil_billionaires_vs_top1_income": "Inequality (WIL)",
    "wil_bottom50_vs_top10_income": "Inequality (WIL)", "wil_top1_vs_bottom50_wealth": "Inequality (WIL)",
    "wil_forbes_vs_hurun": "Inequality (WIL)",
    "nni_vs_top10_income": "Growth & investment", "gcf_public_vs_private": "Growth & investment",
    "mpce_vs_unemployment": "States", "growth_vs_mpce": "States", "city_price_vs_state_mpce": "Cities & housing",
}
HYPOTHESIS_IDS: List[str] = list(QUESTIONS)
NEW_IDS: List[str] = [h for h in HYPOTHESIS_IDS if h not in ("inc_unemp", "inc_mpce", "beta")]

# Hypotheses that read WIL Table C.1, where the 2023 row is tentative.
TENTATIVE_IDS = {"wil_top1_income_vs_wealth", "wil_billionaires_vs_top1_wealth",
                 "wil_billionaires_vs_top01_wealth", "wil_top1_vs_bottom50_wealth"}


# --------------------------------------------------------------------------
# Variable builders (each returns [key, "value"] from a loader, untouched)
# --------------------------------------------------------------------------

def _col(df: pd.DataFrame, key: str, col: str) -> pd.DataFrame:
    return df[[key, col]].rename(columns={col: "value"}).reset_index(drop=True)


def _b1(col: str) -> pd.DataFrame:
    return _col(loaders.load_wil_income_shares(), "year", col)


def _c1(col: str) -> pd.DataFrame:
    return _col(loaders.load_wil_wealth_shares(), "year", col)


def _c2(col: str) -> pd.DataFrame:
    return _col(loaders.load_wil_vhnwi(), "year", col)


def _years(df: pd.DataFrame) -> str:
    d = df.dropna(subset=["value"])
    if d.empty:
        return "no observations"
    return f"{d.iloc[:, 0].min()}–{d.iloc[:, 0].max()} ({len(d)} obs.)"


def _share(label: str, short: str, src: str, df: pd.DataFrame) -> VarSpec:
    """A WIL group share (% of national income or wealth), VERIFIED."""
    return VarSpec(label, short, "percentage points", "VERIFIED", src, _years(df))


def _tentative_exclude(include_tentative: bool) -> Dict[object, str]:
    return {} if include_tentative else {2023: TENTATIVE_REASON}


def _nsdp_current(year: str) -> pd.DataFrame:
    d = loaders.load_nsdp_current()
    return _col(d[d["financial_year"] == year], "state", "percapita_nsdp_current_prices_inr")


def _mpce() -> pd.DataFrame:
    return _col(loaders.load_hces_urban_mpce().rename(columns={"state_ut": "state"}), "state",
                "average_monthly_per_capita_consumption_expenditure_inr")


def _unemp() -> pd.DataFrame:
    return _col(loaders.load_unemployment_by_state(), "state", "unemployment_rate_usual_status_15plus_2023_24")


def _beta_growth() -> Tuple[pd.DataFrame, str, str]:
    con = loaders.load_nsdp_spliced()
    years = sorted(con["financial_year"].unique())
    beta = regional.beta_convergence(con)
    per = beta.per_state[["state", "avg_annual_growth_pct"]].rename(columns={"avg_annual_growth_pct": "value"})
    return per, years[0], years[-1]


V_NSDP_CUR_2324 = VarSpec("Per-capita NSDP, current prices, FY 2023-24 (₹)", "per-capita NSDP (current ₹)",
                          "₹", "PARTIAL", SRC_NSDP_CUR, "FY 2023-24")
V_MPCE = VarSpec("Urban average MPCE, 2023-24 (₹ / person / month)", "urban MPCE", "₹ per person per month",
                 "VERIFIED", SRC_HCES, "HCES survey year 2023-24")
V_UNEMP = VarSpec("Unemployment rate, usual status, age 15+, 2023-24 (%)", "the PLFS unemployment rate",
                  "percentage points", "PARTIAL", SRC_PLFS, "PLFS survey year 2023-24")


def build(hid: str, *, include_tentative: bool = False) -> Hypothesis:
    """Build one hypothesis from the loaders. `include_tentative` adds the
    2023 row of WIL Table C.1 (excluded and reported by default)."""
    if hid not in QUESTIONS:
        raise KeyError(hid)
    q, g = QUESTIONS[hid], GROUPS[hid]
    tent = _tentative_exclude(include_tentative)

    if hid == "inc_unemp":
        return Hypothesis(
            hid, g, q,
            "Okun-type reasoning: richer state economies may generate more jobs — but educated, "
            "higher-income states can also show higher open (search) unemployment.",
            "cross_section", "state", "states", V_NSDP_CUR_2324, V_UNEMP,
            _nsdp_current("2023-24"), _unemp(), exclude=dict(AGGREGATES), existing=True,
            caveat_note="NSDP is a financial-year output measure; PLFS is a survey-year labour measure",
        )
    if hid == "inc_mpce":
        return Hypothesis(
            hid, g, q,
            "Consumption should rise with income produced in the state, though not one-for-one "
            "(savings, remittances, and output that accrues to non-residents).",
            "cross_section", "state", "states", V_NSDP_CUR_2324, V_MPCE,
            _nsdp_current("2023-24"), _mpce(), x_tf="log", y_tf="log", caveats=("proxy",),
            exclude=dict(AGGREGATES), existing=True,
            caveat_note="NSDP measures output produced in the state; MPCE is urban household consumption only",
        )
    if hid == "beta":
        g_df, y0, y1 = _beta_growth()
        con = loaders.load_nsdp_spliced()
        init = _col(con[con["financial_year"] == y0], "state", "percapita_nsdp_constant_prices_inr_SPLICED")
        return Hypothesis(
            hid, g, q,
            "Neoclassical growth theory predicts catch-up (beta convergence): poorer economies grow "
            "faster because capital earns higher returns where it is scarce.",
            "cross_section", "state", "states",
            VarSpec(f"Per-capita NSDP, constant prices spliced, FY {y0} (₹)", "initial per-capita NSDP",
                    "₹", "SPLICED", SRC_NSDP_CON, f"FY {y0}"),
            VarSpec(f"Average annual growth of per-capita NSDP, FY {y0}→{y1} (% / yr)", "average annual growth",
                    "percentage points", "DERIVED", "analysis.regional.beta_convergence over " + SRC_NSDP_CON,
                    f"FY {y0}→{y1}"),
            init, g_df, x_tf="log", caveats=("shared_term",), existing=True,
            caveat_note="growth is computed from the same initial value, so measurement error in it biases toward finding convergence",
        )

    if hid == "wil_top1_income_vs_wealth":
        x, y = _b1("top_1"), _c1("top_1")
        return Hypothesis(
            hid, g, q,
            "High incomes are saved and turned into wealth, and wealth yields capital income — so the "
            "two kinds of concentration should reinforce each other over time.",
            "time_series", "year", "years",
            _share("Top 1% share of pre-tax national income (%)", "the Top 1% income share", SRC_B1, x),
            _share("Top 1% share of national wealth (%)", "the Top 1% wealth share", SRC_C1, y),
            x, y, caveats=("shared_inputs",), exclude=tent, uses_tentative=True,
            caveat_note="before 2002 the wealth series exists only for the survey years 1961, 1971, 1981 and 1991, so first differences use 2002–2022",
        )
    if hid in ("wil_billionaires_vs_top1_wealth", "wil_billionaires_vs_top01_wealth"):
        col = "top_1" if hid.endswith("top1_wealth") else "top_0_1"
        grp = "Top 1%" if col == "top_1" else "Top 0.1%"
        x, y = _c2("forbes_wealth_pct_nni"), _c1(col)
        return Hypothesis(
            hid, g, q,
            f"Billionaires sit inside the {grp}; if their fortunes drive top-end wealth, the two series "
            "should rise and fall together.",
            "time_series", "year", "years",
            VarSpec("Forbes billionaires' net wealth (% of NNI)", "Forbes billionaire wealth",
                    "percentage points of NNI", "VERIFIED", SRC_C2, _years(x)),
            _share(f"{grp} share of national wealth (%)", f"the {grp} wealth share", SRC_C1, y),
            x, y, caveats=("shared_inputs",), exclude=tent, uses_tentative=True,
            caveat_note="the paper's top-wealth estimates may draw on the same rich-list information, and billionaire wealth is valued at volatile market prices",
        )
    if hid == "wil_billionaires_vs_top1_income":
        x, y = _c2("forbes_wealth_pct_nni"), _b1("top_1")
        return Hypothesis(
            hid, g, q,
            "Large fortunes generate dividends, capital gains and business income at the very top, "
            "so billionaire wealth and top income shares could rise together.",
            "time_series", "year", "years",
            VarSpec("Forbes billionaires' net wealth (% of NNI)", "Forbes billionaire wealth",
                    "percentage points of NNI", "VERIFIED", SRC_C2, _years(x)),
            _share("Top 1% share of pre-tax national income (%)", "the Top 1% income share", SRC_B1, y),
            x, y,
            caveat_note="billionaire wealth is valued at market prices, so asset-price swings (2007→2009 in this table) move it far more than income shares",
        )
    if hid == "wil_bottom50_vs_top10_income":
        x, y = _b1("top_10"), _b1("bottom_50")
        return Hypothesis(
            hid, g, q,
            "Teaching example: a rising top share has to come from someone — but because the three "
            "group shares add up to 100%, a negative correlation is partly guaranteed by arithmetic.",
            "time_series", "year", "years",
            _share("Top 10% share of pre-tax national income (%)", "the Top 10% income share", SRC_B1, x),
            _share("Bottom 50% share of pre-tax national income (%)", "the Bottom 50% income share", SRC_B1, y),
            x, y, caveats=("mechanical",),
            caveat_note="Bottom 50% + Middle 40% + Top 10% = 100 in every year of Table B.1, so only the Middle 40% can absorb a change without moving the other two",
        )
    if hid == "wil_top1_vs_bottom50_wealth":
        x, y = _c1("top_1"), _c1("bottom_50")
        return Hypothesis(
            hid, g, q,
            "If wealth concentration at the top comes at the expense of the poorest half (rather than "
            "the middle 40%), the two shares should move in opposite directions.",
            "time_series", "year", "years",
            _share("Top 1% share of national wealth (%)", "the Top 1% wealth share", SRC_C1, x),
            _share("Bottom 50% share of national wealth (%)", "the Bottom 50% wealth share", SRC_C1, y),
            x, y, caveats=("partly_mechanical",), exclude=tent, uses_tentative=True,
            caveat_note="the two groups are not complements (the Middle 40% and P90–P99 sit between them), so the link is only partly mechanical",
        )
    if hid == "wil_forbes_vs_hurun":
        v = loaders.load_wil_vhnwi()
        x, y = _col(v, "year", "forbes_wealth_pct_nni"), _col(v, "year", "hurun_wealth_pct_nni")
        return Hypothesis(
            hid, g, q,
            "Two independent rich lists measuring similar people should broadly agree; if they do not, "
            "top-wealth estimates built on them inherit that uncertainty.",
            "time_series", "year", "years",
            VarSpec("Forbes billionaires' net wealth (% of NNI)", "Forbes wealth",
                    "percentage points of NNI", "VERIFIED", SRC_C2, _years(x)),
            VarSpec("Hurun rich-list net wealth (% of NNI)", "Hurun wealth",
                    "percentage points of NNI", "VERIFIED", SRC_C2, _years(y)),
            x, y, caveats=("measurement",),
            caveat_note="Hurun lists far more people than Forbes (e.g. 1,103 vs 162 in 2022) and is published only in some years",
        )
    if hid == "nni_vs_top10_income":
        nni = loaders.load_real_percapita_nni()
        x = pd.DataFrame({"year": nni["financial_year"].str[:4].astype(int),
                          "value": nni["real_percapita_nni_inr"].astype(float)})
        y = _b1("top_10")
        return Hypothesis(
            hid, g, q,
            "Kuznets-style question: does faster average income growth go with a larger share "
            "accruing to the top decile?",
            "time_series", "year", "years",
            VarSpec("Real per-capita NNI (₹, constant prices)", "real per-capita NNI", "₹", "PARTIAL", SRC_NNI,
                    "FY " + ", ".join(nni["financial_year"])),
            _share("Top 10% share of pre-tax national income (%)", "the Top 10% income share", SRC_B1, y),
            x, y, x_tf="log",
            caveat_note="the NNI file has only seven non-consecutive financial years, so almost no year-on-year changes exist",
            notes=[WIL_YEAR_NOTE + " The NNI financial year 2011-12 is therefore matched to WIL year 2011, and so on."],
        )
    if hid == "gcf_public_vs_private":
        gcf = loaders.load_gross_capital_formation()
        pub = gcf[gcf["sector"] == "public_nonfinancial_corp"]
        prv = gcf[gcf["sector"] == "private_nonfinancial_corp"]
        x = _col(pub.rename(columns={"year": "financial_year"}), "financial_year", "gross_capital_formation_inr_crore")
        y = _col(prv.rename(columns={"year": "financial_year"}), "financial_year", "gross_capital_formation_inr_crore")
        per = f"FY {x['financial_year'].min()}→{x['financial_year'].max()}"
        return Hypothesis(
            hid, g, q,
            "Public investment can crowd private investment in (infrastructure raises private returns) "
            "or out (competition for savings) — the sign of co-movement is the first clue.",
            "time_series", "financial_year", "financial years",
            VarSpec("GCF, public non-financial corporations (₹ crore, current prices)", "public-corporate GCF",
                    "₹ crore", "PARTIAL", SRC_GCF, per),
            VarSpec("GCF, private non-financial corporations (₹ crore, current prices)", "private-corporate GCF",
                    "₹ crore", "PARTIAL", SRC_GCF, per),
            x, y, x_tf="log", y_tf="log", caveats=("nominal",),
            caveat_note="the first-difference (growth) result strips out most of that shared nominal trend",
        )
    if hid == "mpce_vs_unemployment":
        return Hypothesis(
            hid, g, q,
            "Richer, more educated states can afford longer job search, so open unemployment may be "
            "higher where living standards are higher — the opposite of the naive expectation.",
            "cross_section", "state", "states", V_MPCE, V_UNEMP, _mpce(), _unemp(),
            caveats=("proxy",), exclude=dict(AGGREGATES),
            caveat_note="MPCE here is urban-only while the PLFS rate covers rural and urban residents together",
        )
    if hid == "growth_vs_mpce":
        g_df, y0, y1 = _beta_growth()
        return Hypothesis(
            hid, g, q,
            "Sustained growth should cumulate into higher living standards, so faster-growing states "
            "might show higher consumption at the end of the period.",
            "cross_section", "state", "states",
            VarSpec(f"Average annual growth of per-capita NSDP, FY {y0}→{y1} (% / yr)", "average annual NSDP growth",
                    "percentage points", "DERIVED", "analysis.regional.beta_convergence over " + SRC_NSDP_CON,
                    f"FY {y0}→{y1}"),
            V_MPCE, g_df, _mpce(), exclude=dict(AGGREGATES), caveats=("proxy",),
            caveat_note="the end-of-period consumption level also depends on where each state started, which growth alone ignores",
        )
    if hid == "city_price_vs_state_mpce":
        lv = loaders.load_residex_price_levels()
        rows, dropped_fy = [], 0
        for city, d in lv.groupby("city"):
            fy = rel.quarterly_to_financial_year(d, "quarter", "composite_price_inr_per_sqft",
                                                 housing.financial_year_of_quarter)
            hit = fy.data[fy.data["financial_year"] == "2023-24"]
            rows.append({"city": city, "value": float(hit["value"].iloc[0]) if not hit.empty else np.nan})
            dropped_fy += int(hit.empty)
        y = pd.DataFrame(rows, columns=["city", "value"])
        mp = _mpce().set_index("state")["value"]
        x = pd.DataFrame({"city": y["city"],
                          "value": [mp.get(housing.CITY_TO_STATE.get(c), np.nan) for c in y["city"]]})
        per_state = pd.Series([housing.CITY_TO_STATE.get(c) for c in y["city"]]).value_counts()
        top_state, top_n = per_state.index[0], int(per_state.iloc[0])
        return Hypothesis(
            hid, g, q,
            "Housing is priced off local purchasing power, so cities in higher-consumption states "
            "should command higher prices per square metre.",
            "cross_section", "city", "cities",
            VarSpec("Urban average MPCE of the city's state, 2023-24 (₹ / person / month)", "state urban MPCE",
                    "₹ per person per month", "VERIFIED", SRC_HCES + " via analysis.housing.CITY_TO_STATE",
                    "HCES survey year 2023-24"),
            VarSpec("RESIDEX composite price, FY 2023-24 average of 4 quarters (₹ / sq ft)", "city house price",
                    "₹ per sq ft", "PARTIAL", SRC_RESIDEX, "FY 2023-24 (Jun-2023 to Mar-2024)"),
            x, y, caveats=("repeated_values", "proxy"),
            caveat_note=f"{top_n} of the cities are in {top_state} and share its single MPCE value; state consumption is not city income",
        )
    raise KeyError(hid)  # pragma: no cover


# --------------------------------------------------------------------------
# Evaluation (used by the overview table and the tests)
# --------------------------------------------------------------------------

@dataclass
class Evaluation:
    hypothesis: Hypothesis
    aligned: rel.AlignmentResult
    data: pd.DataFrame                    # transformed analysis sample (levels)
    corr: rel.CorrelationSummary
    verdict: rel.Verdict
    diff: Optional[rel.DifferencedPair] = None
    diff_corr: Optional[rel.CorrelationSummary] = None
    diff_verdict: Optional[rel.Verdict] = None
    outcome: str = ""


def evaluate(h: Hypothesis) -> Evaluation:
    """Align, apply the default transforms, and compute the levels (and,
    for time series, first-difference) correlations."""
    aligned = rel.align_observations(h.x_df, h.y_df, h.key, "value", "value",
                                     x_label=h.x.short, y_label=h.y.short, exclude=h.exclude)
    tp = rel.transform_pair(aligned, h.x_tf, h.y_tf)
    corr = rel.correlations(tp.data["x"], tp.data["y"])
    ev = Evaluation(h, aligned, tp.data, corr, rel.verdict(corr))
    if h.is_ts:
        ev.diff = rel.first_differences(tp.data, h.key)
        ev.diff_corr = rel.correlations(ev.diff.data["x"], ev.diff.data["y"])
        ev.diff_verdict = rel.verdict(ev.diff_corr)
        ev.outcome = rel.differencing_outcome(ev.verdict, ev.diff_verdict)
    return ev


def overview_table(*, include_tentative: bool = False, ids: Optional[List[str]] = None) -> pd.DataFrame:
    """One row per hypothesis, computed live from the loaders."""
    rows = []
    for hid in ids or HYPOTHESIS_IDS:
        ev = evaluate(build(hid, include_tentative=include_tentative))
        h, v = ev.hypothesis, ev.verdict
        rows.append({
            "id": hid,
            "Group": h.group,
            "Hypothesis": h.question,
            "Type": "time series" if h.is_ts else "cross-section",
            "n": v.n,
            "Spearman ρ": v.rho,
            "p-value": v.p,
            "Verdict": v.label + ("" if v.significant or not v.computable else " (n.s.)"),
            "First-diff ρ (n)": (f"{ev.diff_verdict.rho:.2f} (n = {ev.diff_verdict.n})"
                                 if h.is_ts and ev.diff_verdict.computable
                                 else (f"n/a (n = {ev.diff_verdict.n})" if h.is_ts else "—")),
            "Survives differencing?": ev.outcome.replace("_", " ") if h.is_ts else "—",
            "Data status": h.status_text,
        })
    return pd.DataFrame(rows)
