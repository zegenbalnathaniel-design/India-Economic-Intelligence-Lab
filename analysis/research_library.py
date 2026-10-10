"""Research library: investigations computed live from the project's data.

Each investigation returns an `Investigation` with the eight parts the
library promises — question, motivation, data (evidence-ledger ids),
method, results (tables), findings, limitations and further questions.
Findings are generated only from computed values and are kept in four
separate lists:

* facts           — observed values, read straight from the data
* statistics      — test results (coefficients, p-values, n)
* interpretation  — cautious reading; never causal
* hypotheses      — what would need further testing, and with what data

Nothing here plots; the Research Library page draws the charts from
`charts` specs so this module stays testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from analysis import convergence as conv, housing, inequality, regional, wealth
from data_sources import loaders


@dataclass
class Investigation:
    id: str
    title: str
    question: str
    motivation: str
    data: list[str]                      # evidence-ledger ids
    method: str
    tables: dict[str, pd.DataFrame]
    facts: list[str]
    statistics: list[str]
    interpretation: list[str]
    hypotheses: list[str]
    limitations: list[str]
    further_questions: list[str]
    charts: list[dict] = field(default_factory=list)  # {"table","x","y","kind","title"}
    settings: dict = field(default_factory=dict)


def _strength(rho: float) -> str:
    a = abs(rho)
    return "strong" if a >= 0.6 else "moderate" if a >= 0.3 else "weak"


# ---------------------------------------------------------------------------
def balanced_sigma(nsdp: pd.DataFrame, col: str) -> dict:
    """CV across the states present in every year (so the comparison is
    like-for-like), with an OLS trend and a reading of it."""
    wide = nsdp.pivot_table(index="financial_year", columns="state", values=col).dropna(axis=1)
    cv = wide.std(axis=1, ddof=0) / wide.mean(axis=1) * 100
    t = np.arange(len(cv))
    lr = stats.linregress(t, cv.to_numpy())
    reading = ("no clear trend" if lr.pvalue >= 0.05 else
               "falling dispersion (σ-convergence)" if lr.slope < 0 else "rising dispersion (σ-divergence)")
    return {"table": pd.DataFrame({"financial_year": cv.index, "cv_pct": cv.values, "n_states": wide.shape[1]}),
            "n_states": wide.shape[1], "first_year": cv.index[0], "last_year": cv.index[-1],
            "first_cv": float(cv.iloc[0]), "last_cv": float(cv.iloc[-1]),
            "slope": float(lr.slope), "p": float(lr.pvalue), "reading": reading}


def _peak_sentence(sigma_table: pd.DataFrame) -> str:
    """Where the dispersion series peaked, so a linear trend is not read as
    a steady rise."""
    t = sigma_table.reset_index(drop=True)
    i = int(t["cv_pct"].idxmax())
    peak, last = t.loc[i], t.iloc[-1]
    if i == len(t) - 1:
        return f"The balanced-panel CV is at its highest in the latest year, {peak['financial_year']}."
    return (f"The balanced-panel CV peaked at {peak['cv_pct']:.1f}% in {peak['financial_year']} and was "
            f"{last['cv_pct']:.1f}% in {last['financial_year']}: the overall trend is upward, but not steady.")


def convergence() -> Investigation:
    nsdp = loaders.load_nsdp_spliced()
    col = "percapita_nsdp_constant_prices_inr_SPLICED"
    sig = regional.sigma_convergence(nsdp, value_col=col, balanced=False)
    beta = regional.beta_convergence(nsdp, value_col=col)
    ps = beta.per_state.dropna(subset=["initial_value", "avg_annual_growth_pct"])
    lr = stats.linregress(np.log(ps["initial_value"]), ps["avg_annual_growth_pct"])
    by = sig.by_year.dropna(subset=["cv_pct"])
    first, last = by.iloc[0], by.iloc[-1]
    bal = balanced_sigma(nsdp, col)
    fast = ps.sort_values("avg_annual_growth_pct", ascending=False)
    years = sorted(nsdp["financial_year"].unique())
    rob = conv.sigma_robustness(nsdp, value_col=col)
    rob_tab = rob.assign(measure=rob["measure"].map(lambda m: conv.MEASURES[m].label))
    alt = rob[rob["panel"].str.startswith("all states")]
    facts = [
        f"Balanced panel ({bal['n_states']} states with data in every year): the coefficient of variation of "
        f"real per-capita NSDP was {bal['first_cv']:.1f}% in {bal['first_year']} and {bal['last_cv']:.1f}% in "
        f"{bal['last_year']}.",
        _peak_sentence(bal["table"]),
        f"All available states: {first['cv_pct']:.1f}% ({int(first['n_states'])} states, {first['financial_year']}) "
        f"vs {last['cv_pct']:.1f}% ({int(last['n_states'])} states, {last['financial_year']}) — not like-for-like, "
        "because coverage changes.",
        f"Fastest average real growth, {years[0]}→{years[-1]}: {fast.iloc[0]['state']} "
        f"({fast.iloc[0]['avg_annual_growth_pct']:.2f}% a year); slowest: {fast.iloc[-1]['state']} "
        f"({fast.iloc[-1]['avg_annual_growth_pct']:.2f}% a year).",
    ]
    if not alt.empty:
        rising = alt[alt["verdict"] == "rising"]["measure"].map(lambda m: conv.MEASURES[m].label).tolist()
        other = alt[alt["verdict"] != "rising"]
        facts.append(
            f"Robustness: keeping all {int(alt['n_states'].iloc[0])} states but ending in {alt['end'].iloc[0]}, "
            f"{len(rising)} of {len(alt)} dispersion measures rise ({', '.join(rising) or 'none'})"
            + ("; " + ", ".join(f"{conv.MEASURES[m].label} is {v}" for m, v in zip(other['measure'], other['verdict']))
               if len(other) else "") + ".")
    statistics = [
        f"σ trend, balanced panel: {bal['slope']:+.2f} percentage points of CV a year (OLS on year, "
        f"p = {bal['p']:.3f}) — {bal['reading']}.",
        f"β regression (n = {len(ps)}): slope {lr.slope:+.3f} (SE {lr.stderr:.3f}, p = {lr.pvalue:.3f}), "
        f"R² = {lr.rvalue**2:.3f}.",
    ]
    if lr.pvalue < 0.05:
        interp = [f"Poorer states grew {'faster' if lr.slope < 0 else 'slower'} on average — a pattern "
                  f"{'consistent with β-convergence' if lr.slope < 0 else 'of divergence'} over this window. "
                  "It describes the data; it does not show why."]
    else:
        interp = ["There is no statistically clear relationship between a state's starting income and its "
                  "later growth over this window: the data do not show poorer states catching up."]
    interp.append("The balanced panel drops the states without data in the last year, several of them "
                  "high-income; the robustness check shows which measures keep the same reading when they "
                  "are included.")
    interp.append("σ and β answer different questions: dispersion can stay flat even when some poor states "
                  "grow fast, if others fall behind.")
    return Investigation(
        id="convergence", title="Interstate economic convergence",
        question="Are poorer Indian states catching up with richer ones in real income per person?",
        motivation="If growth is faster where incomes are lower, regional gaps narrow over time; if not, "
                   "national growth can coexist with widening regional inequality.",
        data=["rbi_nsdp_spliced", "rbi_nsdp_constant"],
        method="σ-convergence: coefficient of variation of real per-capita NSDP across the states observed in "
               "every year (balanced panel), with an OLS trend. β-convergence: OLS of average annual growth over the whole window on log "
               "initial income (one observation per state).",
        tables={"sigma": bal["table"], "sigma_robustness": rob_tab,
                "beta": ps[["state", "initial_value", "final_value", "avg_annual_growth_pct"]]
                .sort_values("avg_annual_growth_pct", ascending=False)},
        facts=facts, statistics=statistics, interpretation=interp,
        hypotheses=["Whether services specialisation explains the fastest growers needs state GVA by sector "
                    "(DATA REQUIRED).",
                    "Population-weighted dispersion may differ from the unweighted CV used here (state "
                    "population series: DATA REQUIRED)."],
        limitations=["The coefficient of variation is sensitive to a few very high-income states; the SD of log "
                     "income, Gini and P90/P10 are reported alongside it.",
                     "NSDP per capita, not GSDP; constant prices spliced across the 2004-05 and 2011-12 bases.",
                     "Unweighted across states: a small state counts as much as Uttar Pradesh.",
                     "Migration, price-level differences and boundary changes (e.g. J&K, Telangana) affect comparisons."],
        further_questions=["Did convergence differ before and after 2011-12?",
                           "Is there club convergence among the richer coastal states?"],
        charts=[{"table": "sigma", "x": "financial_year", "y": "cv_pct", "kind": "line",
                 "title": "Cross-state dispersion (CV, %) of real per-capita NSDP — balanced panel"},
                {"table": "beta", "x": "state", "y": "avg_annual_growth_pct", "kind": "bar",
                 "title": "Average annual real growth by state"}],
        settings={"value_col": col, "window": f"{years[0]} to {years[-1]}"},
    )


# ---------------------------------------------------------------------------
def concentration() -> Investigation:
    b1, c1 = loaders.load_wil_income_shares(), loaders.load_wil_wealth_shares()
    c1f = c1[~c1["tentative"]]
    ib, wb = b1.set_index("year"), c1f.set_index("year")
    gi = inequality.gini_series(b1).set_index("year")["gini_lower_bound"]
    gw = inequality.gini_series(c1f).set_index("year")["gini_lower_bound"]
    m = b1.merge(c1f, on="year", suffixes=("_inc", "_wea"))
    rho, p = stats.spearmanr(m["top_1_inc"], m["top_1_wea"])
    low_year = int(ib["top_1"].idxmin())
    facts = [
        f"Top 1% income share: {ib.loc[1951, 'top_1']:.1f}% (1951), lowest {ib.loc[low_year, 'top_1']:.1f}% "
        f"({low_year}), {ib.loc[2022, 'top_1']:.1f}% (2022).",
        f"Bottom 50% income share: {ib.loc[1980, 'bottom_50']:.1f}% (1980) → {ib.loc[2022, 'bottom_50']:.1f}% (2022).",
        f"Top 10% wealth share: {wb.loc[1961, 'top_10']:.1f}% (1961) → {wb.loc[2022, 'top_10']:.1f}% (2022); "
        f"Top 1%: {wb.loc[1961, 'top_1']:.1f}% → {wb.loc[2022, 'top_1']:.1f}%.",
    ]
    statistics = [
        f"Gini lower bound from the group shares — income: {gi.loc[1982]:.2f} (1982) → {gi.loc[2022]:.2f} (2022); "
        f"wealth: {gw.loc[1961]:.2f} (1961) → {gw.loc[2022]:.2f} (2022).",
        f"Top 1% income share vs Top 1% wealth share across the {len(m)} years both exist: Spearman "
        f"ρ = {rho:.2f} (p = {p:.1e}) — a {_strength(rho)} {'positive' if rho > 0 else 'negative'} association.",
    ]
    return Investigation(
        id="concentration", title="Income and wealth concentration since independence",
        question="How have income and wealth concentration in India changed, and do they move together?",
        motivation="Income flows feed wealth stocks; if top income shares and top wealth shares rise together, "
                   "the two reinforce each other.",
        data=["wil_india"],
        method="Shares from WIL Tables B.1 (income, annual 1951-2022) and C.1 (wealth, 1961-2022; tentative "
               "2023 excluded). Gini from a piecewise-linear Lorenz curve through five published points "
               "(a lower bound). Spearman correlation on years present in both series.",
        tables={"income": b1, "wealth": c1f, "gini": pd.DataFrame({"year": gi.index, "income_gini_lb": gi.values})},
        facts=facts, statistics=statistics,
        interpretation=["Concentration fell from independence to the early 1980s and has risen since; income and "
                        "wealth concentration have moved together, as the WIL authors also report.",
                        "Both series trend upward over 2002-2022, so part of the correlation in levels reflects "
                        "the shared trend — see the Relationships Lab for first differences."],
        hypotheses=["Rising top wealth shares are linked to the growth of billionaire wealth (C.2) — testable "
                    "with year-on-year changes, but n is small.",
                    "Recent bottom/middle shares are the least certain (no comparable consumption survey after "
                    "2011-12)."],
        limitations=["WIL estimates are a lower bound by the authors' own account.",
                     "Wealth before 2002 rests on four survey years only.",
                     "The Gini here ignores within-group inequality."],
        further_questions=["Did concentration rise faster after 2014-15, as the paper suggests for wealth?",
                           "How does consumption inequality (HCES) compare with WIL income inequality?"],
        charts=[{"table": "income", "x": "year", "y": ["bottom_50", "middle_40", "top_10", "top_1"], "kind": "line",
                 "title": "Pre-tax national income shares, % (WIL Table B.1)"},
                {"table": "wealth", "x": "year", "y": ["bottom_50", "middle_40", "top_10", "top_1"], "kind": "line",
                 "title": "Net wealth shares, % (WIL Table C.1)"}],
        settings={"exclude_tentative_2023": True},
    )


def _rg_reading(rmg: pd.DataFrame, band: float = 0.005) -> str:
    """Classify each asset's real return as above, about equal to (±0.5 pts)
    or below g."""
    above = rmg[rmg["r_minus_g"] > band]["asset"].tolist()
    equal = rmg[rmg["r_minus_g"].abs() <= band]["asset"].tolist()
    below = rmg[rmg["r_minus_g"] < -band]["asset"].tolist()
    parts = []
    if above:
        parts.append(f"above g: {', '.join(above)}")
    if equal:
        parts.append(f"about equal to g (within ±0.5 pts): {', '.join(equal)}")
    if below:
        parts.append(f"below g: {', '.join(below)}")
    return ("Real returns — " + "; ".join(parts) + ". The typical household portfolio earns below growth while "
            "equity roughly keeps pace: return heterogeneity rather than a general r > g.")


# ---------------------------------------------------------------------------
def composition_effect(inflation: float = 0.065, g_real: float = 0.065) -> Investigation:
    r = loaders.load_paper_a_returns().set_index("asset")["nominal_return_1991_2021_pct"] / 100
    assets = {"Listed equity": r["Financial assets: listed equity"], "Residential property": r["Residential property"],
              "Gold": r["Gold"], "Typical household portfolio": r["Representative household portfolio"],
              "Bank deposits": r["Financial assets: deposits"]}
    rank = wealth.allocation_ranking(assets, 100000, 30, inflation)
    rmg = wealth.real_minus_g(assets, inflation, g_real)
    facts_ = loaders.load_wil_facts().set_index(["metric", "period"])["value"]
    excess = wealth.implied_excess_growth(facts_[("Wealth-to-income ratio", "1995")],
                                          facts_[("Wealth-to-income ratio", "2022")], 27)
    top, typ = rank.iloc[0], rank.set_index("allocation").loc["Typical household portfolio"]
    return Investigation(
        id="composition", title="Composition effect and return heterogeneity",
        question="Do identical savers end up unequal because of what they own, and does India show r > g?",
        motivation="If households save the same but hold different assets, wealth gaps open without any "
                   "difference in thrift — a mechanism separate from income inequality.",
        data=["paper_a", "wil_india"],
        method="Future value of ₹1 lakh saved at the end of each year for 30 years at each asset's 1991-2021 "
               f"nominal return (Paper A, Table 1). Real returns at π = {inflation:.1%}; compared with g = {g_real:.1%}.",
        tables={"ranking": rank, "real_vs_g": rmg},
        facts=[f"{top['allocation']} reaches ₹{top['final_nominal']/1e7:.2f} crore; the typical household portfolio "
               f"₹{typ['final_nominal']/1e7:.2f} crore — {top['final_nominal']/typ['final_nominal']:.1f}× from the same "
               "₹30 lakh saved.",
               f"National wealth rose from {facts_[('Wealth-to-income ratio', '1995')]:.2f}× to "
               f"{facts_[('Wealth-to-income ratio', '2022')]:.2f}× national income, 1995-2022 (WIL)."],
        statistics=[f"Real return minus g at these settings: " + "; ".join(
            f"{a} {d*100:+.1f} pts" for a, d in zip(rmg["asset"], rmg["r_minus_g"])) + ".",
            f"Wealth grew about {excess*100:.1f}% a year faster than income over 1995-2022 (derived)."],
        interpretation=[_rg_reading(rmg)],
        hypotheses=["Equity and business ownership is concentrated at the top, so the composition effect widens "
                    "wealth gaps — testing it needs asset holdings by wealth group (AIDIS: DATA REQUIRED)."],
        limitations=["Thirty-year historical averages; no volatility, costs or taxes; housing's rent saving ignored.",
                     "Single representative households, not a distribution."],
        further_questions=["How much of the Top 10%'s wealth share rise reflects asset prices vs saving?"],
        charts=[{"table": "ranking", "x": "allocation", "y": "final_nominal", "kind": "bar",
                 "title": "Final wealth after 30 years of ₹1 lakh a year (₹, nominal)"}],
        settings={"inflation": inflation, "g_real": g_real, "contribution": 100000, "years": 30},
    )


# ---------------------------------------------------------------------------
def housing_affordability() -> Investigation:
    ci = loaders.load_city_household_income()
    aff = housing.affordability_across_cities(loaders.load_residex_price_levels(), loaders.load_nsdp_current(),
                                              city_income=ci, income_source="city")
    pi = aff["price_to_income"].dropna()
    over5 = aff[aff["price_to_income"] > 5]
    top = aff.iloc[0]
    flagged = ci[ci["cross_check"].str.startswith(("conflict", "coverage conflicts", "not separately"))]["residex_city"]
    return Investigation(
        id="housing", title="Housing price pressure across cities",
        question="How many years of household income does a home cost across Indian cities?",
        motivation="Price-to-income is the simplest affordability gauge; dispersion across cities shows where "
                   "housing stress concentrates.",
        data=["nhb_residex", "city_household_income"],
        method=f"Price of a {housing.DEFAULT_UNIT_SIZE_SQM:.0f} sq. m. (carpet) home — RESIDEX price per sq. ft, "
               "latest quarter, × size in sq. ft — ÷ the city's average annual household income (PRICE & Tata "
               "Sons). Only cities with both are compared.",
        tables={"cities": aff[["city", "state", "quarter", "price_to_income", "emi_to_income_pct"]]},
        facts=[f"Across {len(pi)} cities the median price-to-income ratio is {pi.median():.1f}× "
               f"(range {pi.min():.1f}× to {pi.max():.1f}×); highest: {top['city']} ({top['price_to_income']:.1f}×).",
               f"{len(over5)} cities exceed 5×" + (": " + ", ".join(over5['city'].head(8)) if len(over5) else "") + "."],
        statistics=[f"Interquartile range {pi.quantile(.25):.1f}×–{pi.quantile(.75):.1f}×; median EMI "
                    f"{aff['emi_to_income_pct'].median():.0f}% of income at 8.5% over 20 years with 20% down."],
        interpretation=["Average household income is pulled up by high earners, so a typical household faces a "
                        "higher ratio than shown — read the ranking, not the level, as the robust part."],
        hypotheses=["Ratios computed with a median household income would be higher and might reorder cities "
                    "(median incomes by city: DATA REQUIRED)."],
        limitations=["Income figures supplied by the author; some conflict with, or are not separately reported in, "
                     "press coverage of the report"
                     + (f" ({', '.join(flagged)})" if len(flagged) else "") + ".",
                     "RESIDEX assessment prices (Sep-2024) and 2025-26 income estimates are not the same year."],
        further_questions=["Has price pressure risen faster than income since 2013? (Housing Lab, RPIPI)"],
        charts=[{"table": "cities", "x": "city", "y": "price_to_income", "kind": "bar",
                 "title": "Price-to-income ratio by city (average household income)"}],
        settings={"unit_size_sqm": housing.DEFAULT_UNIT_SIZE_SQM, "income_source": "city"},
    )


# ---------------------------------------------------------------------------
def financialisation() -> Investigation:
    v, c1 = loaders.load_wil_vhnwi(), loaders.load_wil_wealth_shares()
    m = v.merge(c1[~c1["tentative"]], on="year")
    rho, p = stats.spearmanr(m["forbes_wealth_pct_nni"], m["top_0_1"])
    d = m.sort_values("year")[["year", "forbes_wealth_pct_nni", "top_0_1"]].diff().dropna()
    cons = d[(m.sort_values("year")["year"].diff() == 1).iloc[1:].values]
    rho_d, p_d = stats.spearmanr(cons["forbes_wealth_pct_nni"], cons["top_0_1"]) if len(cons) > 3 else (np.nan, np.nan)
    shares = loaders.load_paper_a_returns().set_index("asset")["share_of_household_assets_pct"].dropna()
    return Investigation(
        id="financialisation", title="Financialisation and household wealth (what the data can and cannot say)",
        question="Is the growth of financial wealth broad-based, or concentrated at the very top?",
        motivation="Booming markets and rising investor numbers are often read as inclusive wealth creation; "
                   "that needs evidence on who owns the assets.",
        data=["wil_india", "paper_a"],
        method="Spearman correlation between Forbes billionaire wealth (% of NNI, WIL Table C.2) and the Top 0.1% "
               "wealth share (Table C.1), in levels and in year-on-year changes over consecutive years.",
        tables={"aligned": m[["year", "forbes_count", "forbes_wealth_pct_nni", "top_0_1", "top_1"]]},
        facts=[f"Household assets (RBI 2017, Paper A Table 1): " + ", ".join(
                   f"{SHARE_LABELS.get(a, a)} {s:.0f}%" for a, s in shares.items()) + ".",
               f"Forbes billionaire wealth: {v.set_index('year').loc[1991, 'forbes_wealth_pct_nni']:.1f}% of NNI (1991) → "
               f"{v.set_index('year').loc[2022, 'forbes_wealth_pct_nni']:.1f}% (2022)."],
        statistics=[f"Levels: ρ = {rho:.2f} (p = {p:.1e}, n = {len(m)}).",
                    (f"Year-on-year changes: ρ = {rho_d:.2f} (p = {p_d:.3f}, n = {len(cons)})."
                     if not np.isnan(rho_d) else "Too few consecutive years for a change-based test.")],
        interpretation=["Wealth at the very top has tracked billionaire wealth; nothing in these series shows the "
                        "gains spreading down the distribution."],
        hypotheses=["Mutual fund folios, SIP inflows and demat accounts are not in the project (AMFI/NSDL/CDSL: "
                    "DATA REQUIRED); even with them, folios and demat accounts are not unique investors, and SIP "
                    "inflows do not show how wealth is distributed."],
        limitations=["Aggregate composition only — no breakdown by household group (AIDIS 77th round: DATA REQUIRED).",
                     "Billionaire lists and WIL top shares are not independent: WIL uses rich lists for the top tail."],
        further_questions=["What share of equity is held by the Top 10% of households?"],
        charts=[{"table": "aligned", "x": "year", "y": ["forbes_wealth_pct_nni", "top_0_1"], "kind": "line",
                 "title": "Billionaire wealth (% NNI) and Top 0.1% wealth share (%)"}],
        settings={"exclude_tentative_2023": True},
    )


SHARE_LABELS = {"Financial assets: deposits": "financial assets (deposits + equity)",
                "Residential property": "residential property", "Gold": "gold", "Durable goods": "durable goods"}

INVESTIGATIONS = {
    "convergence": convergence,
    "concentration": concentration,
    "composition": composition_effect,
    "housing": housing_affordability,
    "financialisation": financialisation,
}

NOT_YET_POSSIBLE = [
    ("State-level productivity differences", "State GVA by sector (RBI Handbook / MoSPI) and PLFS state employment by industry."),
    ("Manufacturing and employment", "Uses the World Bank series in the Structural Transformation Lab (live only); a "
     "reproducible offline version needs ASI / PLFS manufacturing tables."),
    ("Public expenditure and growth", "State budget data — RBI 'State Finances: A Study of Budgets' capital outlay by state."),
    ("Human capital and regional development", "State education / health indicators (e.g. UDISE+, NFHS) or a "
     "subnational HDI (Global Data Lab)."),
]
