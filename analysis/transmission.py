"""Macroeconomic transmission simulator: linear, partial-equilibrium chains.

HYPOTHETICAL arithmetic under stated assumptions -- not a forecast and not
an RBI or government projection. Each link multiplies a shock by a
coefficient taken from data/raw/transmission/parameters.csv, where every
non-blank value carries its citation, URL and the wording it came from.
A coefficient that could not be verified is blank (status DATA REQUIRED):
the link that needs it returns `None` with status "needs parameter" and
never a number. Links with no cited coefficient are listed as qualitative.

Four scenarios (shock sign: positive = increase / depreciation):

* policy  -- policy repo rate change, bps
* oil     -- crude oil price change, % versus baseline
* rupee   -- INR depreciation, % rise in rupees per US dollar
* capex   -- public capital expenditure change, % of GDP

Every quantified link is linear in the shock, so a zero shock gives zero
and doubling the shock doubles the effect. The model has no feedback
between links, no dynamics beyond the horizon each source states, and
no general-equilibrium adjustment.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "data" / "raw" / "transmission" / "parameters.csv"

REQUIRED_COLUMNS = ("parameter", "value", "unit", "horizon", "source_citation", "url",
                    "quote_or_context", "verified_via", "status")
PARAM_STATUSES = ("CITED", "DATA REQUIRED")

HYPOTHETICAL_LABEL = ("HYPOTHETICAL — illustrative arithmetic under stated assumptions, "
                      "not an RBI or government forecast")

# Link statuses
QUANTIFIED = "quantified"
NEEDS_PARAMETER = "needs parameter"
QUALITATIVE = "qualitative"
NOT_APPLICABLE = "not applied in this regime"

# Oil regimes
FULL_PASS_THROUGH = "full pass-through to consumers"
GOVT_ABSORBS = "government absorbs the shock"
OIL_REGIMES = (FULL_PASS_THROUGH, GOVT_ABSORBS)

Params = Mapping[str, float | None]


# ---------------------------------------------------------------------------
# Parameters file
# ---------------------------------------------------------------------------
def load_parameters(path: Path | str = PARAMS_PATH) -> pd.DataFrame:
    """The parameters table; blank values stay NaN (never zero)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["value"] = pd.to_numeric(df["value"].replace("", np.nan), errors="coerce")
    if "param_set" not in df.columns:
        df["param_set"] = "A"
    df["param_set"] = df["param_set"].replace("", "A")
    return df


def parameter_problems(df: pd.DataFrame) -> list[str]:
    """Schema and provenance checks: every number must carry a citation."""
    problems = [f"missing column: {c}" for c in REQUIRED_COLUMNS if c not in df.columns]
    if problems:
        return problems
    if df.duplicated(["parameter", "param_set"]).any():
        problems.append("duplicate (parameter, param_set) rows")
    for _, r in df.iterrows():
        name = f"{r['parameter']} [{r['param_set']}]"
        if r["status"] not in PARAM_STATUSES:
            problems.append(f"{name}: unknown status {r['status']!r}")
        has_value = pd.notna(r["value"])
        if has_value:
            for col in ("source_citation", "url", "quote_or_context", "verified_via", "unit", "horizon"):
                if not str(r[col]).strip():
                    problems.append(f"{name}: value without {col}")
            if not str(r["url"]).startswith("http"):
                problems.append(f"{name}: url is not a web address")
            if r["status"] != "CITED":
                problems.append(f"{name}: has a value but status {r['status']!r}")
        elif r["status"] != "DATA REQUIRED":
            problems.append(f"{name}: blank value must have status DATA REQUIRED")
    for key in PARAMETERS:
        if not ((df["parameter"] == key) & (df["param_set"] == "A")).any():
            problems.append(f"{key}: no set-A row in the parameters file")
    for key in df["parameter"].unique():
        if key not in PARAMETERS:
            problems.append(f"{key}: in the file but not used by the model")
    return problems


def defaults(df: pd.DataFrame, param_set: str = "A") -> dict[str, float | None]:
    """Default value per parameter for a set. Set B falls back to set A where
    no alternative cited value exists. Blank -> None."""
    out: dict[str, float | None] = {}
    for key in PARAMETERS:
        row = citation_row(df, key, param_set)
        out[key] = None if row is None or pd.isna(row["value"]) else float(row["value"])
    return out


def citation_row(df: pd.DataFrame, key: str, param_set: str = "A") -> pd.Series | None:
    for s in ([param_set, "A"] if param_set != "A" else ["A"]):
        r = df[(df["parameter"] == key) & (df["param_set"] == s)]
        if not r.empty:
            return r.iloc[0]
    return None


def has_alternative(df: pd.DataFrame, key: str) -> bool:
    return bool(((df["parameter"] == key) & (df["param_set"] == "B")).any())


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParamSpec:
    label: str
    scenario: str
    step: float
    is_data_input: bool = False   # a data input (GDP shares, prices), not a literature coefficient


PARAMETERS: dict[str, ParamSpec] = {
    "repo_to_walr_fresh": ParamSpec("Repo → lending rate on fresh loans (pp per pp)", "policy", 0.01),
    "repo_to_walr_outstanding": ParamSpec("Repo → lending rate on outstanding loans (pp per pp)", "policy", 0.01),
    "repo_to_credit_growth": ParamSpec("Repo → bank credit growth (pp per 100 bps)", "policy", 0.01),
    "real_rate_to_investment_rate": ParamSpec("Real rate → investment / GDP (pp per 100 bps)", "policy", 0.01),
    "real_rate_to_gdp_growth": ParamSpec("Real rate → GDP growth (pp per 100 bps)", "policy", 0.01),
    "policy_to_cpi_cumulative": ParamSpec("Repo → CPI inflation, cumulative (pp per pp)", "policy", 0.01),
    "oil_cpi_bps_per_10pct": ParamSpec("Crude +10% → CPI inflation (bps)", "oil", 1.0),
    "oil_gdp_growth_bps_per_10pct": ParamSpec("Crude +10% → GDP growth (bps)", "oil", 1.0),
    "oil_cad_pct_gdp_per_10usd": ParamSpec("Crude +US$10/bbl → CAD (pp of GDP)", "oil", 0.01),
    "oil_cad_usd_bn_per_10usd": ParamSpec("Crude +US$10/bbl → CAD (US$ bn)", "oil", 0.1),
    "oil_fiscal_pct_gdp_per_10usd": ParamSpec("Crude +US$10/bbl → fiscal deficit if absorbed (pp of GDP)", "oil", 0.01),
    "baseline_crude_usd": ParamSpec("Baseline crude price (US$/bbl)", "oil", 1.0, True),
    "oil_import_share_gdp": ParamSpec("Oil import bill (% of GDP)", "oil", 0.1, True),
    "inr_cpi_bps_per_5pct_depr": ParamSpec("INR −5% → CPI inflation (bps)", "rupee", 1.0),
    "inr_gdp_bps_per_5pct_depr": ParamSpec("INR −5% → GDP growth (bps)", "rupee", 1.0),
    "export_price_elasticity_sr": ParamSpec("Export price elasticity, short run", "rupee", 0.05),
    "export_price_elasticity_lr": ParamSpec("Export price elasticity, long run", "rupee", 0.05),
    "import_price_elasticity_sr": ParamSpec("Import price elasticity, short run", "rupee", 0.05),
    "import_price_elasticity_lr": ParamSpec("Import price elasticity, long run", "rupee", 0.05),
    "exports_gdp": ParamSpec("Exports of goods & services (% of GDP)", "rupee", 0.1, True),
    "imports_gdp": ParamSpec("Imports of goods & services (% of GDP)", "rupee", 0.1, True),
    "capex_multiplier": ParamSpec("Public capex multiplier (₹ GDP per ₹1)", "capex", 0.01),
    "revenue_gdp_ratio": ParamSpec("Government revenue (% of GDP)", "capex", 0.1, True),
}


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    shock_label: str
    shock_unit: str
    slider: tuple[float, float, float, float]   # min, max, default, step
    nodes: tuple[str, ...]                       # diagram nodes, causal order
    qualitative: tuple[tuple[str, str, str], ...]  # (source node, target node, why it is not quantified)


SCENARIOS: dict[str, Scenario] = {
    "policy": Scenario(
        "policy", "Policy-rate shock", "Change in the policy repo rate", "bps", (-250.0, 250.0, 50.0, 25.0),
        ("Policy repo rate", "Lending rate (fresh loans)", "Lending rate (outstanding loans)", "Bank credit growth",
         "Investment / GDP", "Consumption", "GDP growth", "CPI inflation", "Exchange rate & capital flows"),
        (("Lending rate (fresh loans)", "Consumption",
          "No India semi-elasticity of consumption to lending rates was found with a verifiable citation."),
         ("Policy repo rate", "Exchange rate & capital flows",
          "Interest-rate differentials can move portfolio flows and the rupee; no cited coefficient, and RBI FX "
          "intervention breaks any mechanical link."),
         ("Exchange rate & capital flows", "CPI inflation",
          "An appreciation would lower imported inflation (see the rupee scenario), but the size of the rupee move is not modelled."),
         ("Consumption", "GDP growth", "Follows only if the consumption link were quantified.")),
    ),
    "oil": Scenario(
        "oil", "Crude oil price shock", "Change in the crude oil price versus baseline", "%", (-50.0, 100.0, 20.0, 5.0),
        ("Crude oil price", "Oil import bill", "Current account deficit", "CPI inflation", "GDP growth",
         "Fiscal deficit (subsidy / excise)", "Rupee pressure"),
        (("Current account deficit", "Rupee pressure",
          "A wider CAD adds to rupee depreciation pressure; size depends on capital flows and RBI intervention."),
         ("Crude oil price", "Fiscal deficit (subsidy / excise)",
          "Under full pass-through the direct budget cost is nil by construction; in practice excise cuts or subsidies "
          "split the shock between consumers and the budget (only the full-absorption upper bound is cited)."),
         ("CPI inflation", "GDP growth",
          "Second-round effects (wages, expectations, monetary response) are not modelled.")),
    ),
    "rupee": Scenario(
        "rupee", "Rupee depreciation", "INR depreciation (rise in ₹ per US$)", "%", (-10.0, 20.0, 5.0, 1.0),
        ("INR per US$", "Import prices (₹)", "CPI inflation (imported)", "Trade volumes (X, M)",
         "Trade balance (short run)", "Trade balance (long run)", "GDP growth"),
        (("INR per US$", "Trade volumes (X, M)",
          "Most Indian trade is invoiced in US dollars, so export prices in foreign currency may not fall at once; "
          "how far volumes respond depends on price elasticities, for which no India value was verified."),
         ("Import prices (₹)", "Trade volumes (X, M)",
          "Oil, gold and capital goods dominate imports and respond weakly to price in the short run."),),
    ),
    "capex": Scenario(
        "capex", "Public capital expenditure", "Change in public capex", "% of GDP", (-1.0, 2.0, 0.5, 0.1),
        ("Public capex", "Aggregate demand (nominal GDP)", "Fiscal deficit", "Private investment", "Interest rates"),
        (("Public capex", "Private investment",
          "Crowding-in: public infrastructure can raise the return on private capital (complementarity). No cited India "
          "coefficient is used here."),
         ("Fiscal deficit", "Interest rates",
          "Crowding-out: more government borrowing can raise yields and compete for savings; size depends on financing "
          "and monetary conditions."),
         ("Interest rates", "Private investment", "Higher yields would offset part of the crowding-in.")),
    ),
}


@dataclass(frozen=True)
class Link:
    scenario: str
    id: str
    source: str
    target: str
    label: str
    unit: str
    horizon: str          # "short run", "medium run", "long run", "identity"
    params: tuple[str, ...]
    equation: str         # LaTeX
    assumptions: tuple[str, ...]
    regime: str | None = None   # oil links that apply only in one regime


@dataclass
class Result:
    link: Link
    value: float | None
    status: str
    missing: tuple[str, ...] = field(default_factory=tuple)

    def row(self) -> dict:
        return {
            "scenario": self.link.scenario, "link": self.link.id, "from": self.link.source, "to": self.link.target,
            "effect": self.link.label, "value": self.value, "unit": self.link.unit, "horizon": self.link.horizon,
            "status": self.status, "parameters": ", ".join(self.link.params),
            "missing_parameters": ", ".join(self.missing),
        }


def _l(scn, id_, src, tgt, label, unit, horizon, params, eq, assumptions, regime=None) -> Link:
    return Link(scn, id_, src, tgt, label, unit, horizon, tuple(params), eq, tuple(assumptions), regime)


LINKS: dict[str, list[Link]] = {
    "policy": [
        _l("policy", "walr_fresh", "Policy repo rate", "Lending rate (fresh loans)",
           "Δ lending rate on fresh rupee loans (WALR)", "pp", "short run", ["repo_to_walr_fresh"],
           r"\Delta WALR^{fresh} = \beta_{fresh}\,\frac{\Delta repo_{bps}}{100}",
           ["Pass-through ratio of the May 2022–Sep 2023 tightening applies to any shock, up or down.",
            "Linear; no asymmetry between hikes and cuts; liquidity conditions as in that episode."]),
        _l("policy", "walr_outstanding", "Policy repo rate", "Lending rate (outstanding loans)",
           "Δ lending rate on outstanding rupee loans (WALR)", "pp", "short run", ["repo_to_walr_outstanding"],
           r"\Delta WALR^{out} = \beta_{out}\,\frac{\Delta repo_{bps}}{100}",
           ["Same episode ratio; slower than fresh loans because fixed-rate and MCLR-linked loans reset with a lag."]),
        _l("policy", "credit_growth", "Policy repo rate", "Bank credit growth",
           "Δ annualised nominal bank credit growth", "pp", "short run", ["repo_to_credit_growth"],
           r"\Delta g_{credit} = \gamma\,\frac{\Delta repo_{bps}}{100}",
           ["Estimated on 2001–2011 data (pre-EBLR); the source notes the effect weakened after the global financial crisis.",
            "Lag of about seven months; ceteris paribus."]),
        _l("policy", "investment_rate", "Lending rate (fresh loans)", "Investment / GDP",
           "Δ investment rate (investment / GDP)", "pp", "short run",
           ["repo_to_walr_fresh", "real_rate_to_investment_rate"],
           r"\Delta (I/Y) = \delta_I\,\Delta r^{real},\quad \Delta r^{real} \equiv \Delta WALR^{fresh}",
           ["The change in the real interest rate equals the change in the fresh-loan lending rate: inflation "
            "expectations are held fixed (a simulator assumption, not from the source).",
            "Source coefficient is for a 100 bps real-rate change, scaled linearly."]),
        _l("policy", "gdp_growth", "Lending rate (fresh loans)", "GDP growth",
           "Δ real GDP growth (via the real interest rate)", "pp", "short run",
           ["repo_to_walr_fresh", "real_rate_to_gdp_growth"],
           r"\Delta g_{Y} = \delta_Y\,\Delta r^{real},\quad \Delta r^{real} \equiv \Delta WALR^{fresh}",
           ["As for the investment link: inflation expectations held fixed.",
            "Covers the interest-rate channel only, not credit, exchange-rate or expectations channels separately."]),
        _l("policy", "cpi", "Policy repo rate", "CPI inflation",
           "Δ headline CPI inflation (cumulative)", "pp", "medium run", ["policy_to_cpi_cumulative"],
           r"\Delta \pi = \theta\,\frac{\Delta repo_{bps}}{100}",
           ["Ratio from one episode (250 bps tightening, effect to Q2:2024-25) applied linearly to any shock.",
            "Includes all channels the source's model captures; do not add it to the other links."]),
    ],
    "oil": [
        _l("oil", "import_bill_mech", "Crude oil price", "Oil import bill",
           "Δ oil import bill at unchanged volumes", "pp of GDP", "identity", ["oil_import_share_gdp"],
           r"\Delta\left(\tfrac{M_{oil}}{Y}\right) = s_{oil}\,\frac{\Delta p_{oil}\%}{100}",
           ["Mechanical: volumes, the rupee and GDP unchanged (an accounting identity, not a behavioural estimate)."]),
        _l("oil", "cad", "Oil import bill", "Current account deficit",
           "Δ current account deficit as % of GDP (wider = positive)", "pp of GDP", "short run",
           ["baseline_crude_usd", "oil_cad_pct_gdp_per_10usd"],
           r"\Delta CAD/Y = \kappa\,\frac{\Delta p_{\$}}{10},\quad \Delta p_{\$} = p_0\,\frac{\Delta p_{oil}\%}{100}",
           ["Mint Street Memo sensitivity at 2018-19 import volumes and GDP; today's ratio to GDP would differ.",
            "Linear in US$ per barrel; growth does not offset (as the memo finds)."]),
        _l("oil", "cad_usd", "Oil import bill", "Current account deficit",
           "Δ current account deficit in US$ (wider = positive)", "US$ bn", "short run",
           ["baseline_crude_usd", "oil_cad_usd_bn_per_10usd"],
           r"\Delta CAD_{\$bn} = \kappa_{\$}\,\frac{\Delta p_{\$}}{10}",
           ["2018-19 oil import volumes."]),
        _l("oil", "cpi", "Crude oil price", "CPI inflation",
           "Δ headline CPI inflation", "pp", "short run", ["oil_cpi_bps_per_10pct"],
           r"\Delta\pi = \frac{\phi_{bps}}{100}\cdot\frac{\Delta p_{oil}\%}{10}",
           ["Full pass-through to domestic fuel prices (as in the source scenario).",
            "Linear scaling of a 10% scenario to other sizes is a simulator assumption."], FULL_PASS_THROUGH),
        _l("oil", "gdp_growth", "Crude oil price", "GDP growth",
           "Δ real GDP growth", "pp", "short run", ["oil_gdp_growth_bps_per_10pct"],
           r"\Delta g_Y = \frac{\psi_{bps}}{100}\cdot\frac{\Delta p_{oil}\%}{10}",
           ["Full pass-through scenario of the source; linear scaling."], FULL_PASS_THROUGH),
        _l("oil", "fiscal", "Crude oil price", "Fiscal deficit (subsidy / excise)",
           "Δ fiscal deficit, upper bound (full absorption)", "pp of GDP", "short run",
           ["baseline_crude_usd", "oil_fiscal_pct_gdp_per_10usd"],
           r"\Delta FD/Y \le \lambda\,\frac{\Delta p_{\$}}{10}",
           ["Government passes none of the increase to consumers (zero pass-through); the source calls this an upper bound.",
            "2018-19 scale."], GOVT_ABSORBS),
    ],
    "rupee": [
        _l("rupee", "import_prices", "INR per US$", "Import prices (₹)",
           "Δ rupee price of imports", "%", "identity", [],
           r"\Delta p_M^{₹}\% = \Delta e\%",
           ["Import prices fixed in US dollars (dollar invoicing, full pass-through at the border); "
            "a simulator assumption, exact by construction."]),
        _l("rupee", "cpi", "Import prices (₹)", "CPI inflation (imported)",
           "Δ headline CPI inflation", "pp", "short run", ["inr_cpi_bps_per_5pct_depr"],
           r"\Delta\pi = \frac{\rho_{bps}}{100}\cdot\frac{\Delta e\%}{5}",
           ["RBI MPR scenario for a 5% depreciation, scaled linearly; the source finds pass-through is "
            "non-linear and asymmetric, so large shocks are less reliable."]),
        _l("rupee", "gdp_growth", "Trade volumes (X, M)", "GDP growth",
           "Δ real GDP growth (export stimulus)", "pp", "short run", ["inr_gdp_bps_per_5pct_depr"],
           r"\Delta g_Y = \frac{\eta_{bps}}{100}\cdot\frac{\Delta e\%}{5}",
           ["RBI MPR scenario, short-term export stimulus; linear scaling."]),
        _l("rupee", "trade_balance_sr", "Trade volumes (X, M)", "Trade balance (short run)",
           "Δ trade balance, short-run elasticities", "pp of GDP", "short run",
           ["exports_gdp", "imports_gdp", "export_price_elasticity_sr", "import_price_elasticity_sr"],
           r"\Delta\tfrac{TB}{Y} = \tfrac{\Delta e\%}{100}\left[\tfrac{X}{Y}\,\varepsilon_X - \tfrac{M}{Y}\,(1-\varepsilon_M)\right]",
           ["Elasticities approach, first order: export prices fixed in ₹, import prices fixed in US$.",
            "Volumes respond with the stated elasticities; income effects and second-round price effects ignored."]),
        _l("rupee", "trade_balance_lr", "Trade volumes (X, M)", "Trade balance (long run)",
           "Δ trade balance, long-run elasticities", "pp of GDP", "long run",
           ["exports_gdp", "imports_gdp", "export_price_elasticity_lr", "import_price_elasticity_lr"],
           r"\Delta\tfrac{TB}{Y} = \tfrac{\Delta e\%}{100}\left[\tfrac{X}{Y}\,\varepsilon_X^{LR} - \tfrac{M}{Y}\,(1-\varepsilon_M^{LR})\right]",
           ["As the short-run link, with long-run elasticities. Holding the real depreciation constant over the "
            "long run ignores the inflation that erodes it."]),
    ],
    "capex": [
        _l("capex", "demand", "Public capex", "Aggregate demand (nominal GDP)",
           "Δ nominal GDP", "pp of GDP", "short run", ["capex_multiplier"],
           r"\Delta Y / Y = k\cdot \Delta G / Y",
           ["Impact (within-year) multiplier from a structural model for the combined Centre and States.",
            "Same multiplier for any size or sign of change; no supply constraints."]),
        _l("capex", "deficit_gross", "Public capex", "Fiscal deficit",
           "Δ fiscal deficit before revenue feedback", "pp of GDP", "identity", [],
           r"\Delta FD / Y = \Delta G / Y",
           ["Exact identity: extra spending not matched by extra revenue adds one-for-one to the deficit."]),
        _l("capex", "deficit_net", "Aggregate demand (nominal GDP)", "Fiscal deficit",
           "Δ fiscal deficit after revenue feedback", "pp of GDP", "short run",
           ["capex_multiplier", "revenue_gdp_ratio"],
           r"\Delta FD / Y = \Delta G / Y - \tau\,\Delta Y / Y,\quad \tau = \tfrac{\text{revenue}}{Y}",
           ["Revenue rises in proportion to nominal GDP (unit buoyancy), a simulator assumption.",
            "Ignores the change in the GDP denominator of the ratio (first order)."]),
    ],
}


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------
def _get(p: Params, key: str) -> float | None:
    v = p.get(key)
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) else v


def _compute(link: Link, shock: float, p: Params) -> float:
    """Value of one link; all required parameters are known (checked by caller)."""
    g = lambda k: _get(p, k)  # noqa: E731
    s = float(shock)
    if link.scenario == "policy":
        r = s / 100.0
        if link.id == "walr_fresh":
            return g("repo_to_walr_fresh") * r
        if link.id == "walr_outstanding":
            return g("repo_to_walr_outstanding") * r
        if link.id == "credit_growth":
            return g("repo_to_credit_growth") * r
        if link.id == "investment_rate":
            return g("real_rate_to_investment_rate") * g("repo_to_walr_fresh") * r
        if link.id == "gdp_growth":
            return g("real_rate_to_gdp_growth") * g("repo_to_walr_fresh") * r
        if link.id == "cpi":
            return g("policy_to_cpi_cumulative") * r
    if link.scenario == "oil":
        if link.id == "import_bill_mech":
            return g("oil_import_share_gdp") * s / 100.0
        if link.id == "cpi":
            return g("oil_cpi_bps_per_10pct") / 100.0 * s / 10.0
        if link.id == "gdp_growth":
            return g("oil_gdp_growth_bps_per_10pct") / 100.0 * s / 10.0
        d_usd = g("baseline_crude_usd") * s / 100.0
        if link.id == "cad":
            return g("oil_cad_pct_gdp_per_10usd") * d_usd / 10.0
        if link.id == "cad_usd":
            return g("oil_cad_usd_bn_per_10usd") * d_usd / 10.0
        if link.id == "fiscal":
            return g("oil_fiscal_pct_gdp_per_10usd") * d_usd / 10.0
    if link.scenario == "rupee":
        if link.id == "import_prices":
            return s
        if link.id == "cpi":
            return g("inr_cpi_bps_per_5pct_depr") / 100.0 * s / 5.0
        if link.id == "gdp_growth":
            return g("inr_gdp_bps_per_5pct_depr") / 100.0 * s / 5.0
        if link.id in ("trade_balance_sr", "trade_balance_lr"):
            h = "sr" if link.id.endswith("sr") else "lr"
            return trade_balance_change(s, g("exports_gdp"), g("imports_gdp"),
                                        g(f"export_price_elasticity_{h}"), g(f"import_price_elasticity_{h}"))
    if link.scenario == "capex":
        if link.id == "demand":
            return g("capex_multiplier") * s
        if link.id == "deficit_gross":
            return s
        if link.id == "deficit_net":
            return s - g("revenue_gdp_ratio") / 100.0 * g("capex_multiplier") * s
    raise KeyError(f"unknown link {link.scenario}.{link.id}")


def trade_balance_change(depr_pct: float, exports_gdp: float, imports_gdp: float,
                         eps_x: float, eps_m: float) -> float:
    """First-order change in the trade balance (pp of GDP) after a
    depreciation of `depr_pct` %, with export prices fixed in rupees and
    import prices fixed in dollars. Elasticities are absolute values."""
    d = depr_pct / 100.0
    return d * (exports_gdp * eps_x - imports_gdp * (1.0 - eps_m))


def marshall_lerner(eps_x: float | None, eps_m: float | None) -> bool | None:
    """True when |ε_X| + |ε_M| > 1 (from balanced trade a depreciation then
    improves the trade balance); None if either elasticity is missing."""
    if eps_x is None or eps_m is None:
        return None
    return abs(eps_x) + abs(eps_m) > 1.0


def run(scenario: str, shock: float, params: Params, oil_regime: str = FULL_PASS_THROUGH) -> list[Result]:
    """Every quantified link of a scenario for one shock and parameter set."""
    if scenario not in LINKS:
        raise KeyError(f"unknown scenario {scenario!r}")
    out: list[Result] = []
    for link in LINKS[scenario]:
        if link.regime is not None and link.regime != oil_regime:
            out.append(Result(link, None, NOT_APPLICABLE))
            continue
        missing = tuple(k for k in link.params if _get(params, k) is None)
        if missing:
            out.append(Result(link, None, NEEDS_PARAMETER, missing))
            continue
        out.append(Result(link, float(_compute(link, shock, params)) + 0.0, QUANTIFIED))  # +0.0: no "-0.00"
    return out


def results_frame(results: list[Result]) -> pd.DataFrame:
    return pd.DataFrame([r.row() for r in results])


def comparison_table(scenario: str, shock: float, params_a: Params, params_b: Params,
                     oil_regime: str = FULL_PASS_THROUGH) -> pd.DataFrame:
    """Baseline (zero shock) and scenario values for parameter sets A and B."""
    base = run(scenario, 0.0, params_a, oil_regime)
    a = run(scenario, shock, params_a, oil_regime)
    b = run(scenario, shock, params_b, oil_regime)
    rows = []
    for r0, ra, rb in zip(base, a, b):
        rows.append({
            "effect": ra.link.label, "from → to": f"{ra.link.source} → {ra.link.target}",
            "unit": ra.link.unit, "horizon": ra.link.horizon,
            "baseline (no shock)": r0.value,
            "scenario · set A": ra.value, "status A": ra.status,
            "scenario · set B": rb.value, "status B": rb.status,
            "link": ra.link.id,
        })
    return pd.DataFrame(rows)


def format_value(value: float | None, status: str, unit: str) -> str:
    if status == NEEDS_PARAMETER:
        return "needs parameter"
    if status == NOT_APPLICABLE:
        return "not applied"
    if value is None:
        return "—"
    if unit == "%":
        return f"{value:+.2f}%"
    if unit == "US$ bn":
        return f"{value:+.2f} US$ bn"
    return f"{value:+.2f} {unit}"


# ---------------------------------------------------------------------------
# Diagram
# ---------------------------------------------------------------------------
def diagram_edges(scenario: str, results: list[Result]) -> list[dict]:
    """Edges for the causal diagram: one per quantified link (with its
    status) plus the scenario's qualitative links. Duplicate source→target
    pairs (e.g. the CAD in % of GDP and in US$) are merged, keeping the
    best status."""
    rank = {QUANTIFIED: 0, NEEDS_PARAMETER: 1, NOT_APPLICABLE: 2, QUALITATIVE: 3}
    edges: dict[tuple[str, str], dict] = {}
    for r in results:
        key = (r.link.source, r.link.target)
        e = {"source": key[0], "target": key[1], "status": r.status, "label": r.link.label}
        if key not in edges or rank[r.status] < rank[edges[key]["status"]]:
            edges[key] = e
    for src, tgt, why in SCENARIOS[scenario].qualitative:
        edges.setdefault((src, tgt), {"source": src, "target": tgt, "status": QUALITATIVE, "label": why})
    return list(edges.values())


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_payload(scenario: str, shock: float, params_a: Params, params_b: Params, table: pd.DataFrame,
                   oil_regime: str = FULL_PASS_THROUGH, now: datetime | None = None) -> dict:
    """Everything needed to reproduce a run: label, inputs, both parameter
    sets with their citations, and the outputs."""
    table_params = load_parameters()
    used = sorted({k for link in LINKS[scenario] for k in link.params})

    def describe(p: Params, set_name: str) -> list[dict]:
        rows = []
        for k in used:
            row = citation_row(table_params, k, set_name)
            default = None if row is None or pd.isna(row["value"]) else float(row["value"])
            v = _get(p, k)
            rows.append({
                "parameter": k, "value": v, "default_value": default,
                "edited_by_user": v != default,
                "unit": "" if row is None else row["unit"],
                "source_citation": "" if row is None or v != default else row["source_citation"],
                "url": "" if row is None or v != default else row["url"],
                "status": ("USER-SET" if v != default and v is not None else
                           "DATA REQUIRED" if v is None else "CITED"),
            })
        return rows

    sc = SCENARIOS[scenario]
    outputs = table.drop(columns=["link"]).replace({np.nan: None}).to_dict(orient="records")
    return {
        "label": HYPOTHETICAL_LABEL,
        "generated_at_utc": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario": {"key": scenario, "title": sc.title, "shock": float(shock), "shock_unit": sc.shock_unit,
                     "shock_description": sc.shock_label,
                     "oil_regime": oil_regime if scenario == "oil" else None},
        "parameters": {"set_A": describe(params_a, "A"), "set_B": describe(params_b, "B")},
        "outputs": outputs,
        "qualitative_links": [{"from": s, "to": t, "note": w} for s, t, w in sc.qualitative],
        "model": "Linear partial-equilibrium transmission chains; see analysis/transmission.py.",
    }


def export_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_csv(payload: dict) -> str:
    """One flat CSV: header lines with the label and scenario, then the
    outputs, then the parameters used with citations."""
    buf = io.StringIO()
    buf.write(f"# {payload['label']}\n")
    s = payload["scenario"]
    buf.write(f"# scenario: {s['title']}; shock {s['shock']:+g} {s['shock_unit']}"
              f"{'; ' + s['oil_regime'] if s.get('oil_regime') else ''}; generated {payload['generated_at_utc']}\n")
    out = pd.DataFrame(payload["outputs"])
    out.insert(0, "section", "output")
    params = pd.concat([pd.DataFrame(payload["parameters"]["set_A"]).assign(set="A"),
                        pd.DataFrame(payload["parameters"]["set_B"]).assign(set="B")], ignore_index=True)
    params.insert(0, "section", "parameter")
    pd.concat([out, params], ignore_index=True).to_csv(buf, index=False)
    return buf.getvalue()


SCENARIO_KEYS: tuple[str, ...] = tuple(SCENARIOS)
