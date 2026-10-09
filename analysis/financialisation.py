"""Inequality and financialisation: pure calculations for the
Inequality & Financialisation Lab.

Inputs are only (a) the World Inequality Lab tables already in the project
(Bharti, Chancel, Piketty & Somanchi 2024, Tables B.1 and C.1), (b) Table 1
of the author's Paper A (household asset composition, RBI 2017; returns
1991-2021) and (c) World Bank WDI series fetched live by the page. Nothing
here fetches, stores or fills data:

* missing years stay missing -- no interpolation, no carrying forward;
* comparisons use overlapping years only, and report how many there are;
* every correlation comes with its n and is described, not interpreted
  causally;
* findings text is assembled only from values computed here; when an input
  is unavailable the text says so instead of producing a number.
"""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np
import pandas as pd

from analysis import inequality

# ---------------------------------------------------------------------------
# A. Lorenz curves and concentration from the WIL group shares
# ---------------------------------------------------------------------------
LORENZ_BREAKS = (0.0, 0.5, 0.9, 0.99, 0.999, 1.0)


def lorenz_table(series: pd.DataFrame, years) -> pd.DataFrame:
    """Lorenz points for the requested `years` of Table B.1 or C.1.

    Columns: year, pop_share, cum_share (both 0-1), tentative. The points
    sit at P0, P50, P90, P99, P99.9 and P100 -- the breakpoints implied by
    the published Bottom 50% / Middle 40% / Top 1% / Top 0.1% shares
    (Top 10% follows from the partition). Joining them with straight lines
    is the piecewise-linear curve whose Gini is `inequality.gini_lower_bound`.
    Years not in the table raise KeyError (never filled).
    """
    s = series.set_index("year")
    rows = []
    for y in years:
        if y not in s.index:
            raise KeyError(f"year {y} not in the table")
        r = s.loc[y]
        pts = inequality.lorenz_points(r["bottom_50"], r["middle_40"], r["top_1"], r["top_0_1"])
        tent = bool(r["tentative"]) if "tentative" in s.columns else False
        rows += [{"year": int(y), "pop_share": x, "cum_share": c, "tentative": tent} for x, c in pts]
    return pd.DataFrame(rows, columns=["year", "pop_share", "cum_share", "tentative"])


def partition_gap(series: pd.DataFrame) -> pd.DataFrame:
    """Bottom 50 + Middle 40 + Top 10 minus 100, per year (rounding in the
    printed table). Large gaps would mean the Lorenz points are unreliable."""
    out = series[["year"]].copy()
    out["sum_minus_100_pp"] = (series["bottom_50"] + series["middle_40"] + series["top_10"] - 100).round(2)
    return out


def concentration_compare(income: pd.DataFrame, wealth: pd.DataFrame) -> pd.DataFrame:
    """Income vs wealth concentration in the years both tables report.

    Columns: year, income_/wealth_ top_10, top_1, bottom_50, gini_lb,
    wealth_tentative, and wealth-minus-income gaps for Top 10% share and Gini.
    """
    gi = inequality.gini_series(income).set_index("year")["gini_lower_bound"]
    gw = inequality.gini_series(wealth).set_index("year")["gini_lower_bound"]
    i, w = income.set_index("year"), wealth.set_index("year")
    years = sorted(set(i.index) & set(w.index))
    rows = []
    for y in years:
        rows.append({
            "year": int(y),
            "income_top_10": float(i.loc[y, "top_10"]), "wealth_top_10": float(w.loc[y, "top_10"]),
            "income_top_1": float(i.loc[y, "top_1"]), "wealth_top_1": float(w.loc[y, "top_1"]),
            "income_bottom_50": float(i.loc[y, "bottom_50"]), "wealth_bottom_50": float(w.loc[y, "bottom_50"]),
            "income_gini_lb": float(gi.loc[y]), "wealth_gini_lb": float(gw.loc[y]),
            "wealth_tentative": bool(w.loc[y, "tentative"]) if "tentative" in w.columns else False,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["top_10_gap_pp"] = (out["wealth_top_10"] - out["income_top_10"]).round(1)
        out["gini_gap"] = out["wealth_gini_lb"] - out["income_gini_lb"]
    return out


# ---------------------------------------------------------------------------
# B. Household asset composition (Paper A Table 1)
# ---------------------------------------------------------------------------
COMPOSITION_ORDER = ["Residential property", "Gold", "Durable goods", "Financial assets"]


def composition_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Aggregate household asset composition from Paper A Table 1.

    The paper gives one 5% share for financial assets (deposits + listed
    equity combined) and a return for each part, so the financial row keeps
    the share once and lists both returns. Durable goods have a negative
    return with no figure: `return_pct` is NaN and `return_text` says
    'negative' -- never 0.
    """
    t = returns.set_index("asset")

    def ret(asset):
        v = t.loc[asset, "nominal_return_1991_2021_pct"]
        return float(v) if pd.notna(v) else math.nan

    fin_share = t.loc["Financial assets: deposits", "share_of_household_assets_pct"]
    rows = [
        {"asset": "Residential property", "share_pct": float(t.loc["Residential property", "share_of_household_assets_pct"]),
         "return_pct": ret("Residential property"), "return_text": f"{ret('Residential property'):.1f}% (stated)"},
        {"asset": "Gold", "share_pct": float(t.loc["Gold", "share_of_household_assets_pct"]),
         "return_pct": ret("Gold"), "return_text": f"{ret('Gold'):.1f}% (stated)"},
        {"asset": "Durable goods", "share_pct": float(t.loc["Durable goods", "share_of_household_assets_pct"]),
         "return_pct": math.nan, "return_text": "negative (no figure given)"},
        {"asset": "Financial assets", "share_pct": float(fin_share), "return_pct": math.nan,
         "return_text": (f"deposits {ret('Financial assets: deposits'):.1f}% (midpoint of stated 6–7%); "
                         f"listed equity {ret('Financial assets: listed equity'):.1f}% (stated); split of the "
                         f"{float(fin_share):g}% between them not given")},
    ]
    return pd.DataFrame(rows, columns=["asset", "share_pct", "return_pct", "return_text"])


def composition_sum(comp: pd.DataFrame) -> float:
    return float(comp["share_pct"].sum())


def portfolio_return_bounds(returns: pd.DataFrame) -> dict[str, float]:
    """Bounds on the weighted nominal return of the representative household
    portfolio, as Paper A builds it (durables excluded, weights renormalised
    over property + gold + financial assets).

    Because the paper does not split the 5% financial share between deposits
    and equity, the weighted return can only be bounded: all-deposits gives
    the lower bound, all-equity the upper. Also returns the paper's stated
    figure for comparison. DERIVED from the printed Table 1 values only.
    """
    t = returns.set_index("asset")
    sp, sg = (float(t.loc[a, "share_of_household_assets_pct"]) for a in ("Residential property", "Gold"))
    sf = float(t.loc["Financial assets: deposits", "share_of_household_assets_pct"])
    rp, rg = (float(t.loc[a, "nominal_return_1991_2021_pct"]) for a in ("Residential property", "Gold"))
    rd = float(t.loc["Financial assets: deposits", "nominal_return_1991_2021_pct"])
    re_ = float(t.loc["Financial assets: listed equity", "nominal_return_1991_2021_pct"])
    w = sp + sg + sf
    stated = t.loc["Representative household portfolio", "nominal_return_1991_2021_pct"]
    return {
        "weight_base_pct": w,
        "lower_all_deposits": (sp * rp + sg * rg + sf * rd) / w,
        "upper_all_equity": (sp * rp + sg * rg + sf * re_) / w,
        "stated": float(stated) if pd.notna(stated) else math.nan,
    }


# ---------------------------------------------------------------------------
# C/D. WDI series helpers
# ---------------------------------------------------------------------------
def wdi_series(frame: pd.DataFrame | None, code: str, iso3: str = "IND") -> pd.Series:
    """Year -> value for one code and country, non-missing only (empty
    Series when the frame is None/empty). Never fills gaps."""
    if frame is None or frame.empty:
        return pd.Series(dtype="float64", name=code)
    s = frame[(frame["indicator"] == code) & (frame["iso3"] == iso3)].dropna(subset=["value"])
    return pd.Series(s["value"].to_numpy(dtype="float64"), index=s["year"].astype(int).to_numpy(),
                     name=code).sort_index()


def change_summary(s: pd.Series) -> dict | None:
    """First and latest non-missing observation and the change between them
    (in the series' own unit). None with fewer than two observations."""
    s = s.dropna().sort_index()
    if len(s) < 2:
        return None
    return {"first_year": int(s.index[0]), "first": float(s.iloc[0]),
            "last_year": int(s.index[-1]), "last": float(s.iloc[-1]),
            "change": float(s.iloc[-1] - s.iloc[0]), "n_obs": int(len(s))}


def participation_gap(richest_60: pd.Series, poorest_40: pd.Series) -> pd.DataFrame:
    """Richest-60% minus poorest-40% account ownership (pp), only in years
    where both are reported."""
    df = pd.concat({"richest_60": richest_60, "poorest_40": poorest_40}, axis=1).dropna()
    df.index.name = "year"
    df = df.reset_index()
    df["gap_pp"] = df["richest_60"] - df["poorest_40"]
    df["year"] = df["year"].astype(int)
    return df[["year", "richest_60", "poorest_40", "gap_pp"]]


# ---------------------------------------------------------------------------
# E. Aligning two indicators
# ---------------------------------------------------------------------------
def align_two(a: pd.Series, b: pd.Series, start: int, end: int,
              names: tuple[str, str] = ("a", "b")) -> pd.DataFrame:
    """Outer-join two year-indexed series over [start, end].

    Columns: year, <name a>, <name b>, both_observed. Years where either is
    missing stay missing -- nothing is interpolated or carried forward.
    """
    na, nb = names
    if na == nb:
        nb = f"{nb} (2)"
    df = pd.concat({na: a.dropna(), nb: b.dropna()}, axis=1)
    df = df[(df.index >= start) & (df.index <= end)].sort_index()
    df.index.name = "year"
    df = df.reset_index()
    df["year"] = df["year"].astype(int)
    df["both_observed"] = df[na].notna() & df[nb].notna()
    return df


def pearson(aligned: pd.DataFrame, min_n: int = 5) -> dict | None:
    """Pearson correlation of the two value columns over years where both
    are observed. None when fewer than `min_n` pairs or either is constant.
    Descriptive only: two trending series correlate whether or not they are
    related."""
    cols = [c for c in aligned.columns if c not in ("year", "both_observed")]
    both = aligned[aligned["both_observed"]]
    if len(both) < min_n:
        return None
    x, y = both[cols[0]].to_numpy(float), both[cols[1]].to_numpy(float)
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    return {"r": float(np.corrcoef(x, y)[0, 1]), "n": int(len(both)),
            "first_year": int(both["year"].min()), "last_year": int(both["year"].max())}


def first_differences(aligned: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year changes of both series, kept only where the two years
    are consecutive and both series are observed in both years (no change
    is computed across a gap)."""
    cols = [c for c in aligned.columns if c not in ("year", "both_observed")]
    both = aligned[aligned["both_observed"]].sort_values("year").reset_index(drop=True)
    rows = []
    for prev, cur in zip(both.itertuples(index=False), both.iloc[1:].itertuples(index=False)):
        if cur.year - prev.year == 1:
            rows.append({"year": int(cur.year), cols[0]: cur[1] - prev[1], cols[1]: cur[2] - prev[2]})
    out = pd.DataFrame(rows, columns=["year", *cols])
    out["both_observed"] = True
    return out


def overlap_change(aligned: pd.DataFrame) -> dict | None:
    """Change in each series between the first and last year in which BOTH
    are observed. None with fewer than two such years."""
    cols = [c for c in aligned.columns if c not in ("year", "both_observed")]
    both = aligned[aligned["both_observed"]].sort_values("year")
    if len(both) < 2:
        return None
    f, l = both.iloc[0], both.iloc[-1]
    return {"first_year": int(f["year"]), "last_year": int(l["year"]), "n_common": int(len(both)),
            "a_first": float(f[cols[0]]), "a_last": float(l[cols[0]]), "a_change": float(l[cols[0]] - f[cols[0]]),
            "b_first": float(f[cols[1]]), "b_last": float(l[cols[1]]), "b_change": float(l[cols[1]] - f[cols[1]])}


def wil_catalogue(income: pd.DataFrame, wealth: pd.DataFrame, vhnwi: pd.DataFrame | None = None,
                  include_tentative: bool = False) -> dict[str, dict]:
    """Year-indexed WIL series offered for comparison.

    {label: {"series": pd.Series, "unit": str, "source": str}}. The 2023
    wealth row (tentative per the authors) is excluded unless asked for.
    """
    out: dict[str, dict] = {}
    w = wealth if include_tentative or "tentative" not in wealth.columns else wealth[~wealth["tentative"].astype(bool)]
    for col, name in inequality.SERIES.items():
        out[f"WIL income share · {name}"] = {
            "series": income.set_index("year")[col].astype(float), "unit": "% of pre-tax national income",
            "source": "WIL Table B.1"}
    for col, name in inequality.SERIES.items():
        out[f"WIL wealth share · {name}"] = {
            "series": w.set_index("year")[col].astype(float), "unit": "% of net wealth",
            "source": "WIL Table C.1"}
    gi = inequality.gini_series(income).set_index("year")["gini_lower_bound"]
    gw = inequality.gini_series(w).set_index("year")["gini_lower_bound"]
    out["WIL income Gini (lower bound, derived)"] = {"series": gi, "unit": "Gini, 0–1",
                                                     "source": "Derived from WIL Table B.1"}
    out["WIL wealth Gini (lower bound, derived)"] = {"series": gw, "unit": "Gini, 0–1",
                                                     "source": "Derived from WIL Table C.1"}
    if vhnwi is not None and not vhnwi.empty:
        v = vhnwi.set_index("year")
        out["Forbes billionaires' wealth, % of NNI"] = {
            "series": v["forbes_wealth_pct_nni"].dropna().astype(float), "unit": "% of net national income",
            "source": "WIL Table C.2"}
    return out


# ---------------------------------------------------------------------------
# F. Deterministic findings
# ---------------------------------------------------------------------------
FINDING_SECTIONS = ("Observed facts", "Statistical results", "Interpretation",
                    "Hypotheses requiring further testing")


def _pp(x: float) -> str:
    return f"{x:+.1f} pp"


def build_findings(
    income: pd.DataFrame,
    wealth: pd.DataFrame,
    comp: pd.DataFrame,
    *,
    account: Mapping[str, pd.Series] | None = None,
    market_vs_top1: Mapping | None = None,
    wdi_status: str = "DATA UNAVAILABLE",
) -> dict[str, list[str]]:
    """Findings text in four sections, built only from the inputs.

    `account` maps "total", "poorest_40", "richest_60" to WDI series (may be
    empty). `market_vs_top1` is {"change": overlap_change(...) or None,
    "corr": pearson(...) or None, "corr_diff": pearson(first_differences)
    or None} for market cap (a) vs WIL Top 1% wealth share (b). When WDI
    inputs are missing, the text states `wdi_status` instead of a number.
    """
    f: dict[str, list[str]] = {k: [] for k in FINDING_SECTIONS}
    obs, stat, interp, hyp = (f[k] for k in FINDING_SECTIONS)

    # --- WIL income / wealth ---------------------------------------------
    inc, wl = income.sort_values("year"), wealth.sort_values("year")
    firm_w = wl[~wl["tentative"].astype(bool)] if "tentative" in wl.columns else wl
    i0, i1 = inc.iloc[0], inc.iloc[-1]
    w0, w1 = firm_w.iloc[0], firm_w.iloc[-1]
    obs.append(f"Top 10% share of pre-tax national income: {i0['top_10']:.1f}% in {int(i0['year'])}, "
               f"{i1['top_10']:.1f}% in {int(i1['year'])}; Bottom 50%: {i0['bottom_50']:.1f}% → "
               f"{i1['bottom_50']:.1f}% (WIL Table B.1).")
    obs.append(f"Top 1% share of net wealth: {w0['top_1']:.1f}% in {int(w0['year'])}, {w1['top_1']:.1f}% in "
               f"{int(w1['year'])}; Top 10%: {w0['top_10']:.1f}% → {w1['top_10']:.1f}% (WIL Table C.1).")
    if "tentative" in wl.columns and wl["tentative"].astype(bool).any():
        t = wl[wl["tentative"].astype(bool)].iloc[-1]
        obs.append(f"The {int(t['year'])} wealth row is marked tentative by the authors (Top 1%: "
                   f"{t['top_1']:.1f}%); it is excluded from the comparisons below.")

    gi = inequality.gini_series(inc).set_index("year")["gini_lower_bound"]
    gw = inequality.gini_series(firm_w).set_index("year")["gini_lower_bound"]
    stat.append(f"Lower-bound income Gini (piecewise-linear Lorenz through the published shares): "
                f"{gi.iloc[0]:.3f} in {int(gi.index[0])} → {gi.iloc[-1]:.3f} in {int(gi.index[-1])} "
                f"({gi.iloc[-1] - gi.iloc[0]:+.3f}); lowest {gi.min():.3f} in {int(gi.idxmin())}.")
    stat.append(f"Lower-bound wealth Gini: {gw.iloc[0]:.3f} in {int(gw.index[0])} → {gw.iloc[-1]:.3f} in "
                f"{int(gw.index[-1])} ({gw.iloc[-1] - gw.iloc[0]:+.3f}).")
    cc = concentration_compare(inc, firm_w)
    if not cc.empty:
        n_more = int((cc["gini_gap"] > 0).sum())
        stat.append(f"Wealth Gini exceeds income Gini in {n_more} of {len(cc)} years both tables report "
                    f"({int(cc['year'].min())}–{int(cc['year'].max())}).")
        if n_more == len(cc):
            interp.append("Wealth is more concentrated than income in every year both series cover. This "
                          "describes the pattern; on its own it does not identify the mechanism (inheritance, "
                          "saving rates and asset returns can all produce it).")
    if i1["top_10"] > i0["top_10"] and w1["top_1"] > w0["top_1"]:
        interp.append(f"Both income and wealth at the top are more concentrated at the end of the WIL "
                      f"series than at the start. These are distributional national-accounts estimates "
                      f"the authors describe as a lower bound on concentration.")

    # --- Paper A composition ----------------------------------------------
    c = comp.set_index("asset")["share_pct"]
    obs.append(f"Average household assets (RBI 2017, via Paper A Table 1): residential property "
               f"{c['Residential property']:g}%, gold {c['Gold']:g}%, durable goods {c['Durable goods']:g}%, "
               f"financial assets {c['Financial assets']:g}% — an aggregate, not a breakdown by household group.")
    hyp.append(f"Financial assets are {c['Financial assets']:g}% of household assets on average, but an average "
               "cannot show who holds them. Hypothesis: financial-asset holdings are concentrated in the top "
               "wealth groups, so equity-market gains accrue mainly to them. Test: asset composition by "
               "asset-holding class from the NSS 77th round AIDIS (DATA REQUIRED).")

    # --- Account ownership -------------------------------------------------
    account = account or {}
    tot = change_summary(account.get("total", pd.Series(dtype=float)))
    if tot is None:
        obs.append(f"Account ownership (Global Findex): {wdi_status} — fewer than two survey years available "
                   "on this run.")
    else:
        obs.append(f"Account ownership, adults 15+ (Global Findex): {tot['first']:.1f}% in {tot['first_year']}, "
                   f"{tot['last']:.1f}% in {tot['last_year']} ({_pp(tot['change'])}, {tot['n_obs']} survey years).")
    gap = participation_gap(account.get("richest_60", pd.Series(dtype=float)),
                            account.get("poorest_40", pd.Series(dtype=float)))
    if len(gap) >= 2:
        g0, g1 = gap.iloc[0], gap.iloc[-1]
        stat.append(f"Richest-60% minus poorest-40% account-ownership gap: {g0['gap_pp']:.1f} pp in "
                    f"{int(g0['year'])} → {g1['gap_pp']:.1f} pp in {int(g1['year'])} "
                    f"({_pp(g1['gap_pp'] - g0['gap_pp'])}).")
        if tot is None:
            interp.append("The poorest-40% gap can be read from the chart, but without the all-adult series "
                          "this run cannot say whether overall participation rose.")
        elif tot["change"] > 0 and g1["gap_pp"] < g0["gap_pp"]:
            interp.append("By the one measure available — having an account — participation broadened: "
                          "ownership rose and the gap between the poorest 40% and richest 60% narrowed. "
                          "This says nothing about balances held, account use, or ownership of "
                          "market-linked assets.")
        else:
            interp.append(f"Account ownership changed by {_pp(tot['change'])} and the poorest-40% gap by "
                          f"{_pp(g1['gap_pp'] - g0['gap_pp'])}: not both a rise and a narrowing, so this "
                          "measure does not show unambiguous broadening.")
    else:
        stat.append(f"Poorest-40% vs richest-60% account-ownership gap: {wdi_status} — needs both series "
                    "in at least two survey years.")

    # --- Market cap vs Top 1% wealth --------------------------------------
    mv = market_vs_top1 or {}
    ch, corr, corr_d = mv.get("change"), mv.get("corr"), mv.get("corr_diff")
    if ch is None:
        stat.append(f"Market capitalisation vs Top 1% wealth share: {wdi_status} — fewer than two overlapping "
                    "years.")
    else:
        stat.append(f"Over the {ch['n_common']} years both are observed ({ch['first_year']}–{ch['last_year']}), "
                    f"market capitalisation moved {ch['a_first']:.1f}% → {ch['a_last']:.1f}% of GDP "
                    f"({_pp(ch['a_change'])}) and the WIL Top 1% wealth share {ch['b_first']:.1f}% → "
                    f"{ch['b_last']:.1f}% ({_pp(ch['b_change'])}).")
        if corr is not None:
            stat.append(f"Correlation of levels: r = {corr['r']:.2f} (n = {corr['n']}); "
                        + (f"of year-on-year changes: r = {corr_d['r']:.2f} (n = {corr_d['n']})."
                           if corr_d is not None else "year-on-year changes: not computable (fewer than 5 "
                           "consecutive-year pairs, or no variation)."))
        if ch["a_change"] > 0 and ch["b_change"] > 0:
            interp.append("Aggregate equity-market expansion coincided with a rising Top 1% wealth share. "
                          "That timing is consistent with — but does not show — market gains accruing "
                          "disproportionately to the top; correlation between two trending aggregates is "
                          "not evidence of a causal or distributional link.")
        elif ch["a_change"] > 0:
            interp.append("Market capitalisation rose while the Top 1% wealth share did not, over the "
                          "overlapping years — aggregate expansion alone does not reveal who gained.")
        hyp.append("Rising market capitalisation raises measured top wealth shares mainly through price "
                   "revaluation of concentrated holdings. Test: ownership of listed equity by wealth group "
                   "(AIDIS microdata, or depository holdings by holder size — DATA REQUIRED).")
    hyp.append("Wider account ownership has not translated into wider ownership of market-linked assets. "
               "Test: unique-investor counts (not demat accounts or folios) by income/wealth group — "
               "DATA REQUIRED; aggregate AMFI/NSDL/CDSL counts cannot answer it.")
    return f
