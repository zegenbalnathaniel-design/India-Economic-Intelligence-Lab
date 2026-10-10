"""Variable catalogue for the Regression workbench (Economic Relationships Lab).

Every variable is read from a file already in `data/` through
`data_sources.loaders` (directly, or via `analysis.states.build_panel`,
which normalises state names and keeps blank cells as NaN with a note, and
`analysis.regional.beta_convergence` for the one DERIVED growth variable).
Nothing is created, filled or interpolated here. The only operations are
selecting rows/columns, and mapping an Indian financial-year label
"YYYY-YY" to its starting calendar year, the convention the WIL tables use
for the same year (`analysis.hypotheses.WIL_YEAR_NOTE`).

Two geographic levels, and only variables at the same level can be
combined in one model:

- ``state``: a cross-section of states/UTs, key ``state``;
- ``india_annual``: all-India annual time series, key ``year`` (integer).

Deliberately not offered (reported on the page): the quarterly repo-rate /
bank-panel series (ILLUSTRATIVE, synthetic), the monthly macro file (one to
two observations per indicator), World Bank WDI (live API, not a file in
data/), the older-vintage per-capita NSDP columns of
state_gsdp_nsdp_percapita.csv (superseded by the RBI table), and the city
RESIDEX series (a different geographic level).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from analysis import hypotheses as hyp
from analysis import regional, states
from data_sources import loaders

LEVELS: Dict[str, str] = {
    "state": "State cross-section (one observation per state / UT)",
    "india_annual": "All-India annual time series (one observation per year)",
}
LEVEL_KEY = {"state": "state", "india_annual": "year"}
LEVEL_OBS_NOUN = {"state": "states/UTs", "india_annual": "years"}

FY_NOTE = ("Financial year 'YYYY-YY' is keyed to its starting calendar year YYYY, the convention of the WIL "
           "tables: " + hyp.WIL_YEAR_NOTE)
TENTATIVE_C1 = "WIL Table C.1 flags its 2023 row as tentative (excluded unless you include tentative rows)"

NOT_OFFERED: Tuple[Tuple[str, str], ...] = (
    ("Repo rate & bank panel (quarterly)", "bank panel is ILLUSTRATIVE / synthetic — never used for estimation here; "
     "the quarterly repo rate (DERIVED) has no real quarterly partner in this project"),
    ("Monthly macro releases (CPI, IIP, inflation expectations)", "one or two observations per indicator — no series to regress"),
    ("World Bank WDI", "live API, not a file in data/; excluded so every run is reproducible from the repository"),
    ("Per-capita NSDP columns of state_gsdp_nsdp_percapita.csv", "older release vintage of the RBI table already offered"),
    ("NHB RESIDEX city series", "city level — cannot be combined with state or all-India variables"),
)


@dataclass(frozen=True)
class CatalogueVariable:
    id: str
    level: str
    group: str
    label: str
    short: str
    unit: str
    status: str
    source: str
    registry_id: str
    builder: Callable[[str], pd.DataFrame] = field(compare=False, repr=False)
    periods: Tuple[str, ...] = ()          # state level: which year's cross-section
    default_period: str = ""
    tentative: Tuple[Tuple[object, str], ...] = ()
    share_group: str = ""                  # same non-empty group = parts of one total
    note: str = ""

    def frame(self, period: str = "") -> pd.DataFrame:
        """[key, value, note] — values exactly as loaded (NaN kept)."""
        p = period or self.default_period
        if self.periods and p not in self.periods:
            raise ValueError(f"{self.id}: unknown period {p!r}")
        return self.builder(p)

    def period_text(self, period: str = "") -> str:
        p = period or self.default_period
        if self.level == "state":
            return f"FY / survey year {p}" if p else ""
        d = self.frame().dropna(subset=["value"])
        if d.empty:
            return "no observations"
        return f"{int(d['year'].min())}–{int(d['year'].max())} ({len(d)} obs.)"


# ---------------------------------------------------------------------------
# State cross-section
# ---------------------------------------------------------------------------

@lru_cache(maxsize=2)
def _panel() -> pd.DataFrame:
    return states.build_panel()


def _panel_builder(indicator: str) -> Callable[[str], pd.DataFrame]:
    def build(period: str) -> pd.DataFrame:
        p = _panel()
        d = p[(p["indicator"] == indicator) & (p["period"] == period)]
        return pd.DataFrame({"state": d["state"].to_numpy(), "value": d["value"].astype(float).to_numpy(),
                             "note": d["note"].fillna("").to_numpy()})
    return build


def _panel_periods(indicator: str) -> Tuple[str, ...]:
    return tuple(states.periods_for(_panel(), indicator))


@lru_cache(maxsize=2)
def _beta() -> Tuple[pd.DataFrame, str, str]:
    con = loaders.load_nsdp_spliced()
    years = sorted(con["financial_year"].unique())
    per = regional.beta_convergence(con).per_state
    out = pd.DataFrame({"state": [states.normalise_state(s) for s in per["state"]],
                        "value": per["avg_annual_growth_pct"].astype(float).to_numpy(),
                        "note": ""})
    return out, years[0], years[-1]


def _state_vars() -> List[CatalogueVariable]:
    out: List[CatalogueVariable] = []
    cur_p = _panel_periods("nsdp_pc_current_rbi")
    out.append(CatalogueVariable(
        "st_nsdp_current", "state", "Income & output", "Per-capita NSDP, current prices (₹)",
        "per-capita NSDP (current ₹)", "₹", "PARTIAL", hyp.SRC_NSDP_CUR, "rbi_nsdp_current",
        _panel_builder("nsdp_pc_current_rbi"), cur_p, "2023-24" if "2023-24" in cur_p else cur_p[-1],
        note="Delhi and Puducherry held out (unaligned rows); Bihar carries a transcription flag."))
    con_p = _panel_periods("nsdp_pc_constant_spliced")
    out.append(CatalogueVariable(
        "st_nsdp_constant", "state", "Income & output", "Per-capita NSDP, constant prices, spliced (₹)",
        "per-capita NSDP (constant ₹)", "₹", "SPLICED", hyp.SRC_NSDP_CON, "rbi_nsdp_spliced",
        _panel_builder("nsdp_pc_constant_spliced"), con_p, "2021-22" if "2021-22" in con_p else con_p[-1],
        note="Two base years linked by an overlap factor; 2022-23 covers only 21 states."))
    for ind, lab, short in (("gsdp_pc_current_old", "Per-capita GSDP, current prices (₹)", "per-capita GSDP (current ₹)"),
                            ("gsdp_pc_constant_old", "Per-capita GSDP, constant prices (₹)", "per-capita GSDP (constant ₹)")):
        per = _panel_periods(ind)
        out.append(CatalogueVariable(
            f"st_{ind.replace('_old', '')}", "state", "Income & output", lab, short, "₹", "PARTIAL",
            "state_gsdp_nsdp_percapita.csv (earlier upload; source not confirmed) via analysis.states",
            "state_gsdp_nsdp_pc", _panel_builder(ind), per, "2023-24" if "2023-24" in per else per[-1],
            note="Older release vintage; Delhi blanked and Ladakh row excluded as malformed."))
    g, y0, y1 = _beta()
    out.append(CatalogueVariable(
        "st_nsdp_growth", "state", "Income & output",
        f"Average annual growth of per-capita NSDP, constant prices, FY {y0}→{y1} (% / yr)",
        "average annual NSDP growth", "percentage points", "DERIVED",
        "analysis.regional.beta_convergence over " + hyp.SRC_NSDP_CON, "rbi_nsdp_spliced",
        lambda _p, _g=g: _g.copy(), (f"{y0}→{y1}",), f"{y0}→{y1}",
        note="Log growth between the two endpoint years; states missing either endpoint are absent."))
    out.append(CatalogueVariable(
        "st_unemployment", "state", "Labour & consumption", "Unemployment rate, usual status, age 15+ (%)",
        "the PLFS unemployment rate", "percentage points", "PARTIAL", hyp.SRC_PLFS, "plfs_unemployment",
        _panel_builder("plfs_unemployment"), _panel_periods("plfs_unemployment"), "2023-24"))
    out.append(CatalogueVariable(
        "st_mpce_urban", "state", "Labour & consumption", "Urban average MPCE (₹ / person / month)",
        "urban MPCE", "₹ per person per month", "VERIFIED", hyp.SRC_HCES, "hces_mpce",
        _panel_builder("hces_urban_mpce"), _panel_periods("hces_urban_mpce"), "2023-24",
        note="Consumption expenditure, urban only — not income."))
    return out


# ---------------------------------------------------------------------------
# All-India annual time series
# ---------------------------------------------------------------------------

def _year_frame(years, values, notes=None) -> pd.DataFrame:
    return pd.DataFrame({"year": [int(y) for y in years], "value": pd.Series(values, dtype=float).to_numpy(),
                         "note": list(notes) if notes is not None else ""})


def _fy_start(label: str) -> int:
    return int(str(label).split("-")[0])


def _india_vars() -> List[CatalogueVariable]:
    out: List[CatalogueVariable] = []
    groups = {"bottom_50": "Bottom 50%", "middle_40": "Middle 40%", "top_10": "Top 10%",
              "top_1": "Top 1%", "top_0_1": "Top 0.1%"}
    for col, g in groups.items():
        out.append(CatalogueVariable(
            f"in_b1_{col}", "india_annual", "Income concentration (WIL Table B.1)",
            f"{g} share of pre-tax national income (%)", f"the {g} income share", "percentage points",
            "VERIFIED", hyp.SRC_B1, "wil_india",
            lambda _p, c=col: (lambda d: _year_frame(d["year"], d[c]))(loaders.load_wil_income_shares()),
            share_group="wil_b1"))
    for col, g in groups.items():
        def c1(_p, c=col):
            d = loaders.load_wil_wealth_shares()
            notes = ["tentative (authors' flag)" if t else "" for t in d["tentative"].astype(bool)]
            return _year_frame(d["year"], d[c], notes)
        tent = tuple((int(y), TENTATIVE_C1) for y in
                     loaders.load_wil_wealth_shares().query("tentative == True")["year"])
        out.append(CatalogueVariable(
            f"in_c1_{col}", "india_annual", "Wealth concentration (WIL Table C.1)",
            f"{g} share of national wealth (%)", f"the {g} wealth share", "percentage points",
            "VERIFIED", hyp.SRC_C1, "wil_india", c1, tentative=tent, share_group="wil_c1",
            note="Survey years only before 2002 (1961, 1971, 1981, 1991)."))
    for col, lab, short, unit in (
        ("forbes_wealth_pct_nni", "Forbes billionaires' net wealth (% of NNI)", "Forbes billionaire wealth", "percentage points of NNI"),
        ("forbes_count", "Number of Forbes billionaires", "the Forbes billionaire count", "billionaires"),
        ("hurun_wealth_pct_nni", "Hurun rich-list net wealth (% of NNI)", "Hurun rich-list wealth", "percentage points of NNI"),
        ("hurun_count", "Number of Hurun rich-list members", "the Hurun rich-list count", "people"),
    ):
        out.append(CatalogueVariable(
            f"in_c2_{col}", "india_annual", "Top wealth (WIL Table C.2)", lab, short, unit, "VERIFIED",
            hyp.SRC_C2, "wil_india",
            lambda _p, c=col: (lambda d: _year_frame(d["year"], d[c]))(loaders.load_wil_vhnwi()),
            note="Hurun published only in some years." if col.startswith("hurun") else ""))
    sectors = {
        "gross_capital_formation_total": "total (all sectors)",
        "public_nonfinancial_corp": "public non-financial corporations",
        "private_nonfinancial_corp": "private non-financial corporations",
        "public_financial_corp": "public financial corporations",
        "private_financial_corp": "private financial corporations",
        "general_government": "general government",
        "households_incl_npish": "households (incl. NPISH)",
    }
    for sec, lab in sectors.items():
        def gcf(_p, s=sec):
            d = loaders.load_gross_capital_formation()
            d = d[d["sector"] == s]
            return _year_frame([_fy_start(y) for y in d["year"]], d["gross_capital_formation_inr_crore"],
                               [f"FY {y}" for y in d["year"]])
        out.append(CatalogueVariable(
            f"in_gcf_{sec}", "india_annual", "Investment (RBI Handbook GCF)",
            f"Gross capital formation, {lab} (₹ crore, current prices)", f"GCF of {lab}", "₹ crore", "PARTIAL",
            hyp.SRC_GCF, "rbi_gcf_sector", gcf, share_group="gcf", note="Nominal (current prices). " + FY_NOTE))

    def nni(_p):
        d = loaders.load_real_percapita_nni()
        return _year_frame([_fy_start(y) for y in d["financial_year"]], d["real_percapita_nni_inr"],
                           [f"FY {y}" for y in d["financial_year"]])
    out.append(CatalogueVariable(
        "in_real_pc_nni", "india_annual", "Income level", "Real per-capita NNI (₹, constant prices)",
        "real per-capita NNI", "₹", "PARTIAL", hyp.SRC_NNI, "real_pc_nni", nni,
        note="Only seven non-consecutive financial years. " + FY_NOTE))
    return out


@lru_cache(maxsize=2)
def _catalogue() -> Tuple[CatalogueVariable, ...]:
    return tuple(_state_vars() + _india_vars())


def catalogue(level: Optional[str] = None) -> List[CatalogueVariable]:
    cat = list(_catalogue())
    return [v for v in cat if level is None or v.level == level]


def get(var_id: str) -> CatalogueVariable:
    for v in _catalogue():
        if v.id == var_id:
            return v
    raise KeyError(var_id)


def catalogue_table(level: Optional[str] = None) -> pd.DataFrame:
    """One row per variable (and, at state level, per available period)
    with the number of non-missing observations."""
    rows = []
    for v in catalogue(level):
        periods = v.periods or ("",)
        for p in periods:
            d = v.frame(p)
            obs = d.dropna(subset=["value"])
            if v.level == "state":
                cover = p
            else:
                cover = f"{int(obs['year'].min())}–{int(obs['year'].max())}" if not obs.empty else "—"
            rows.append({"level": LEVELS[v.level].split(" (")[0], "group": v.group, "id": v.id,
                         "variable": v.label, "period / coverage": cover, "n (non-missing)": int(len(obs)),
                         "missing rows": int(d["value"].isna().sum()),
                         "tentative rows": len(v.tentative), "status": v.status, "unit": v.unit})
    return pd.DataFrame(rows)
