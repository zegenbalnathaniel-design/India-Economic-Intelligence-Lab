"""State Economic Divergence — convergence/divergence analytics.

Two standard, textbook techniques from the growth-economics convergence
literature (Barro & Sala-i-Martin), applied to the spliced per-capita NSDP
series in data/raw/rbi_handbook/percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv:

- **Sigma (σ) convergence**: are states' income levels becoming more or
  less dispersed over time? Measured by the cross-sectional coefficient of
  variation (CV) of per-capita income each year. A falling CV means states
  are converging; a rising CV means they are diverging.
- **Beta (β) convergence**: do poorer states grow faster than richer ones?
  Measured by regressing each state's average annual growth rate over the
  period against its initial (log) income level. A negative slope is
  consistent with (unconditional) beta convergence.

Both are purely descriptive statistics of the data provided — neither
implies a causal growth model, and beta convergence in particular is
well known in the literature to be sensitive to which control variables
are (or aren't) included. See docs/methodology for the full caveats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd


def coefficient_of_variation(values) -> float:
    """CV = population std / mean, as a percentage. Returns NaN if the
    mean is zero or fewer than 2 observations are given."""
    x = np.asarray([v for v in values if pd.notna(v)], dtype=float)
    if len(x) < 2 or x.mean() == 0:
        return float("nan")
    return float(np.std(x, ddof=0) / x.mean() * 100.0)


@dataclass
class SigmaConvergenceResult:
    by_year: pd.DataFrame  # columns: financial_year, cv_pct, n_states
    trend_slope_pct_per_year: float
    direction: str  # "converging", "diverging", "no clear trend" or "insufficient data"
    balanced: bool = True
    # States dropped from a balanced panel because they lack a value in at
    # least one year of the input (state -> missing years). Empty when
    # balanced=False or nothing was dropped.
    excluded_states: dict = field(default_factory=dict)


def balanced_panel(nsdp_long: pd.DataFrame, value_col: str = "percapita_nsdp_constant_prices_inr_SPLICED"):
    """Keep only states with a non-blank value in *every* financial year
    present in ``nsdp_long``. Returns (filtered long frame, {excluded state:
    [years with no value]}). Nothing is filled: a state with any gap is
    dropped whole, so the set of states is the same in every year."""
    years = sorted(nsdp_long["financial_year"].unique())
    wide = nsdp_long.pivot_table(index="state", columns="financial_year", values=value_col, aggfunc="first",
                                 dropna=False).reindex(columns=years)
    all_states = sorted(nsdp_long["state"].unique())
    wide = wide.reindex(index=all_states)
    excluded = {}
    for state in all_states:
        missing = [y for y in years if pd.isna(wide.at[state, y])]
        if missing:
            excluded[state] = missing
    keep = [s for s in all_states if s not in excluded]
    return nsdp_long[nsdp_long["state"].isin(keep)], excluded


def sigma_convergence(nsdp_long: pd.DataFrame, value_col: str = "percapita_nsdp_constant_prices_inr_SPLICED",
                      balanced: bool = True) -> SigmaConvergenceResult:
    """Cross-sectional CV of per-capita income for every year present,
    plus a simple linear trend (OLS slope of CV on year index) to
    characterise the overall direction over the sample period.

    ``balanced=True`` (default) first restricts to the states that report
    in every year of the input, so the CV is computed over the *same*
    states each year. With ``balanced=False`` each year uses whichever
    states report that year; when coverage changes (the spliced NSDP
    series has 32 states in 2004-05 but 21 in 2022-23) the trend then
    mixes real changes in dispersion with changes in which states are
    counted, and can even flip sign -- on the full spliced series the
    unbalanced CV trend is slightly negative, the balanced one clearly
    positive.
    """
    excluded: dict = {}
    data = nsdp_long
    if balanced and not nsdp_long.empty:
        data, excluded = balanced_panel(nsdp_long, value_col)
    rows = []
    for year, grp in data.groupby("financial_year"):
        cv = coefficient_of_variation(grp[value_col])
        rows.append({"financial_year": year, "cv_pct": cv, "n_states": grp[value_col].notna().sum()})
    by_year = pd.DataFrame(rows, columns=["financial_year", "cv_pct", "n_states"])
    by_year = by_year[by_year["n_states"] >= 5].sort_values("financial_year").reset_index(drop=True)
    if by_year.empty or by_year["cv_pct"].notna().sum() < 2:
        return SigmaConvergenceResult(by_year=by_year, trend_slope_pct_per_year=float("nan"),
                                      direction="insufficient data", balanced=balanced, excluded_states=excluded)

    valid = by_year.dropna(subset=["cv_pct"])
    t = np.arange(len(valid))
    slope = float(np.polyfit(t, valid["cv_pct"].values, 1)[0])
    if abs(slope) < 0.05:
        direction = "no clear trend"
    elif slope < 0:
        direction = "converging"
    else:
        direction = "diverging"
    return SigmaConvergenceResult(by_year=by_year, trend_slope_pct_per_year=slope, direction=direction,
                                  balanced=balanced, excluded_states=excluded)


@dataclass
class BetaConvergenceResult:
    per_state: pd.DataFrame  # state, initial_value, final_value, avg_annual_growth_pct
    slope: float             # growth rate per unit of log(initial income)
    intercept: float
    r_squared: float
    direction: str           # "consistent with convergence", "consistent with divergence", "no clear relationship"


def beta_convergence(nsdp_long: pd.DataFrame, value_col: str = "percapita_nsdp_constant_prices_inr_SPLICED") -> BetaConvergenceResult:
    """Unconditional beta-convergence regression: average annual growth
    rate (log difference / years) regressed on log(initial income).

    This is the simplest possible specification (no controls) and should
    be read as descriptive, not as a causal growth-determinants model.
    """
    years = sorted(nsdp_long["financial_year"].unique())
    first_year, last_year = years[0], years[-1]
    first_fy_num = int(first_year.split("-")[0])
    last_fy_num = int(last_year.split("-")[0])
    n_years = last_fy_num - first_fy_num

    wide = nsdp_long.pivot_table(index="state", columns="financial_year", values=value_col)
    rows = []
    for state in wide.index:
        v0, v1 = wide.loc[state, first_year], wide.loc[state, last_year]
        if pd.isna(v0) or pd.isna(v1) or v0 <= 0 or v1 <= 0 or n_years <= 0:
            continue
        growth_pct = (np.log(v1) - np.log(v0)) / n_years * 100.0
        rows.append({"state": state, "initial_value": v0, "final_value": v1, "avg_annual_growth_pct": growth_pct})
    per_state = pd.DataFrame(rows)

    if len(per_state) < 5:
        return BetaConvergenceResult(per_state=per_state, slope=float("nan"), intercept=float("nan"),
                                      r_squared=float("nan"), direction="insufficient data")

    x = np.log(per_state["initial_value"].values)
    y = per_state["avg_annual_growth_pct"].values
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    if abs(slope) < 0.5:
        direction = "no clear relationship"
    elif slope < 0:
        direction = "consistent with convergence"
    else:
        direction = "consistent with divergence"
    return BetaConvergenceResult(per_state=per_state, slope=float(slope), intercept=float(intercept),
                                  r_squared=r_squared, direction=direction)


def rank_states_latest(nsdp_long: pd.DataFrame, value_col: str = "percapita_nsdp_constant_prices_inr_SPLICED") -> pd.DataFrame:
    """Latest-year ranking of states by per-capita income, descending."""
    latest_year = sorted(nsdp_long["financial_year"].unique())[-1]
    latest = nsdp_long[nsdp_long["financial_year"] == latest_year].dropna(subset=[value_col]).copy()
    latest = latest.sort_values(value_col, ascending=False).reset_index(drop=True)
    latest["rank"] = np.arange(1, len(latest) + 1)
    return latest[["rank", "state", value_col]].rename(columns={value_col: "percapita_nsdp_inr"})
