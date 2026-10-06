"""Monte Carlo engine for SIP (systematic investment plan) wealth accumulation.

IMPORTANT FRAMING: everything this module produces is the *distribution of
outcomes implied by a set of stated, user-overridable assumptions*. None of
it is a forecast, a guarantee, or investment advice. Real markets do not
hand out i.i.d. lognormal returns on schedule; this is a tool for reasoning
about uncertainty under a model, not a prediction machine.

Mechanics
---------
The simulation runs month by month for ``duration_years * 12`` months:

1. Monthly gross returns are drawn from a lognormal distribution whose
   *annual* mean and volatility are moment-matched to the user's
   ``expected_annual_return`` and ``annual_volatility`` (see
   :func:`lognormal_monthly_params`). Monthly log-returns are i.i.d. draws
   from ``Normal(mu_log / 12, sigma_log**2 / 12)`` -- an exact
   decomposition, because a sum of 12 independent draws from this monthly
   normal is itself ``Normal(mu_log, sigma_log**2)``, the annual
   log-return distribution implied by the annual assumptions.
2. Fees are a continuous drag on the log-return: ``annual_fee_rate / 12``
   is subtracted from every monthly log-return, so a higher expense ratio
   shaves compounding growth every single month, compounding against the
   investor exactly like a negative return would.
3. Each month, the existing balance grows by that month's return, then
   that month's contribution is added (ordinary-annuity convention -- see
   :mod:`sip_monte_carlo.closed_form` for why this convention is chosen:
   it is the one that has an exact, checkable closed form).
4. Contributions step up once per year by ``contribution_growth_rate``
   (e.g., a 10%/year raise applied to the SIP amount).
5. At the end, nominal wealth at every month is deflated by
   ``(1 + annual_inflation) ** (month / 12)`` to get real (inflation
   adjusted) wealth at that same month.

The result carries the full cross-sectional percentile path over time
(for a "fan chart"), not just final-value statistics, because the
*shape* of the uncertainty over time is itself the point.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np
import pandas as pd

#: Percentiles (in percent) reported throughout this module.
PERCENTILES = (10, 25, 50, 75, 90)


def lognormal_monthly_params(
    expected_annual_return: float, annual_volatility: float
) -> tuple[float, float]:
    """Moment-match an annual arithmetic mean/volatility to a monthly
    lognormal log-return distribution.

    We model the annual *simple* gross return as lognormal: if the annual
    simple return is ``R = exp(Z) - 1`` with ``Z ~ Normal(mu_log,
    sigma_log**2)``, then matching ``E[R] = expected_annual_return`` and
    ``Std[R] = annual_volatility`` gives

        sigma_log**2 = ln(1 + annual_volatility**2 / (1 + expected_annual_return)**2)
        mu_log       = ln(1 + expected_annual_return) - sigma_log**2 / 2

    Because sums of independent normals are normal, drawing 12 i.i.d.
    monthly log-returns from ``Normal(mu_log/12, sigma_log**2/12)`` and
    summing them reproduces ``Normal(mu_log, sigma_log**2)`` exactly for
    the annual log-return -- so the monthly simulation is an exact,
    not approximate, decomposition of the stated annual assumptions.

    Parameters
    ----------
    expected_annual_return:
        Illustrative arithmetic mean annual return (e.g. ``0.12`` for a
        12% assumption). This is a user-chosen *assumption*, not an
        empirical estimate.
    annual_volatility:
        Illustrative annual standard deviation of returns. Must be
        ``>= 0``.

    Returns
    -------
    (mu_log, sigma_log): the annual lognormal location and scale.
    """
    if annual_volatility < 0:
        raise ValueError("annual_volatility must be non-negative.")
    if expected_annual_return <= -1:
        raise ValueError("expected_annual_return must be greater than -100%.")

    gross = 1.0 + expected_annual_return
    if annual_volatility == 0:
        return float(np.log(gross)), 0.0

    sigma_log_sq = np.log(1.0 + (annual_volatility**2) / (gross**2))
    mu_log = np.log(gross) - sigma_log_sq / 2.0
    return float(mu_log), float(np.sqrt(sigma_log_sq))


def net_monthly_rate(
    expected_annual_return: float,
    annual_fee_rate: float,
    annual_volatility: float = 0.0,
) -> float:
    """The deterministic (zero-volatility) net monthly compounding rate.

    This is the monthly rate the simulation reduces to when
    ``annual_volatility == 0``: the annual lognormal mean log-return,
    minus the annual fee drag, split evenly across 12 months, exponentiated.
    Used both by the engine's deterministic path and by tests that check
    the engine against the exact closed form.
    """
    if annual_fee_rate < 0:
        raise ValueError("annual_fee_rate must be non-negative.")
    mu_log, _ = lognormal_monthly_params(expected_annual_return, annual_volatility)
    monthly_log_return = mu_log / 12.0 - annual_fee_rate / 12.0
    return float(np.exp(monthly_log_return) - 1.0)


def _validate_inputs(
    monthly_contribution: float,
    duration_years: int,
    annual_volatility: float,
    annual_inflation: float,
    contribution_growth_rate: float,
    initial_capital: float,
    annual_fee_rate: float,
    n_paths: int,
) -> None:
    if monthly_contribution < 0:
        raise ValueError("monthly_contribution must be non-negative.")
    if duration_years <= 0:
        raise ValueError("duration_years must be positive.")
    if annual_volatility < 0:
        raise ValueError("annual_volatility must be non-negative.")
    if annual_inflation <= -1:
        raise ValueError("annual_inflation must be greater than -100%.")
    if contribution_growth_rate <= -1:
        raise ValueError("contribution_growth_rate must be greater than -100%.")
    if initial_capital < 0:
        raise ValueError("initial_capital must be non-negative.")
    if annual_fee_rate < 0:
        raise ValueError("annual_fee_rate must be non-negative.")
    if n_paths <= 0:
        raise ValueError("n_paths must be positive.")


@dataclass
class SimulationResult:
    """Container for a full SIP Monte Carlo run.

    All "paths" arrays run over ``months`` (length ``N + 1``, including
    month 0). Final-value arrays run over simulated paths (length
    ``n_paths``).
    """

    months: np.ndarray  # shape (N+1,): 0, 1, ..., N
    years: np.ndarray  # shape (N+1,): months / 12
    nominal_paths_percentiles: Dict[int, np.ndarray]  # percentile -> array (N+1,)
    real_paths_percentiles: Dict[int, np.ndarray]
    mean_nominal_path: np.ndarray  # shape (N+1,)
    mean_real_path: np.ndarray
    nominal_final: np.ndarray  # shape (n_paths,) final nominal wealth per path
    real_final: np.ndarray
    total_contributed: float
    inputs: dict = field(default_factory=dict)

    def final_summary(self) -> pd.DataFrame:
        """Mean/median/percentile summary of nominal and real final wealth."""
        rows = []
        rows.append(("mean", float(np.mean(self.nominal_final)), float(np.mean(self.real_final))))
        for p in PERCENTILES:
            rows.append((
                f"p{p}",
                float(np.percentile(self.nominal_final, p)),
                float(np.percentile(self.real_final, p)),
            ))
        df = pd.DataFrame(rows, columns=["statistic", "nominal", "real"])
        return df.set_index("statistic")

    def probability_of_reaching(self, target: float, use_real: bool = False) -> float:
        """Empirical fraction of simulated paths whose final wealth meets
        or exceeds ``target``.

        This is a description of the simulated distribution under the
        stated assumptions, not a probability of any real-world event.
        """
        if target < 0:
            raise ValueError("target must be non-negative.")
        values = self.real_final if use_real else self.nominal_final
        return float(np.mean(values >= target))

    def percentile_dataframe(self, real: bool = False) -> pd.DataFrame:
        """Full time series of percentile bands, for fan charts."""
        source = self.real_paths_percentiles if real else self.nominal_paths_percentiles
        data = {f"p{p}": source[p] for p in PERCENTILES}
        data["mean"] = self.mean_real_path if real else self.mean_nominal_path
        data["year"] = self.years
        data["month"] = self.months
        return pd.DataFrame(data)


def run_simulation(
    monthly_contribution: float,
    duration_years: int,
    expected_annual_return: float = 0.12,
    annual_volatility: float = 0.18,
    annual_inflation: float = 0.05,
    contribution_growth_rate: float = 0.0,
    initial_capital: float = 0.0,
    annual_fee_rate: float = 0.0,
    n_paths: int = 2000,
    seed: int | None = 42,
) -> SimulationResult:
    """Run the SIP Monte Carlo simulation and return the full result.

    Every return/volatility/fee/inflation/growth number here is an
    *illustrative, user-chosen assumption*. The output describes "what
    happens under these assumptions, across many random draws" -- it is a
    distribution, never a forecast of what will actually happen to any
    real portfolio.

    Parameters
    ----------
    monthly_contribution:
        SIP amount contributed at the end of each month during year 0 (the
        first year); see ``contribution_growth_rate``. Must be ``>= 0``.
    duration_years:
        Investment horizon in whole years. Must be ``> 0``.
    expected_annual_return:
        Illustrative arithmetic mean annual nominal return assumption
        (e.g. 0.12 = 12%/year). Override freely; this is not a forecast.
    annual_volatility:
        Illustrative annual standard deviation of returns (e.g. 0.18 =
        18%/year). Set to 0 to get the deterministic compound-interest
        case exactly.
    annual_inflation:
        Illustrative annual inflation rate used only to deflate nominal
        results into real (today's-rupee) terms. Does not affect the
        nominal simulation itself.
    contribution_growth_rate:
        Fractional step-up applied to the monthly contribution once per
        year (e.g. 0.1 = contribution rises 10% every year).
    initial_capital:
        Lump sum already invested at time zero. Must be ``>= 0``.
    annual_fee_rate:
        Expense-ratio-style annual drag subtracted continuously from the
        growth rate every month (e.g. 0.01 = 1%/year in fees). Must be
        ``>= 0``.
    n_paths:
        Number of independent simulated paths. Must be ``> 0``.
    seed:
        Random seed. The same seed with otherwise identical inputs
        reproduces byte-identical output.

    Returns
    -------
    SimulationResult
    """
    _validate_inputs(
        monthly_contribution,
        duration_years,
        annual_volatility,
        annual_inflation,
        contribution_growth_rate,
        initial_capital,
        annual_fee_rate,
        n_paths,
    )

    n_months = 12 * duration_years
    mu_log, sigma_log = lognormal_monthly_params(expected_annual_return, annual_volatility)
    monthly_mean_log = mu_log / 12.0 - annual_fee_rate / 12.0
    monthly_std_log = sigma_log / np.sqrt(12.0)

    rng = np.random.default_rng(seed)

    if monthly_std_log == 0.0:
        # Deterministic case: every path is identical. Still draw through the
        # RNG machinery conceptually, but there is no randomness to apply.
        log_returns = np.full((n_paths, n_months), monthly_mean_log, dtype=float)
    else:
        log_returns = rng.normal(
            loc=monthly_mean_log, scale=monthly_std_log, size=(n_paths, n_months)
        )
    monthly_factors = np.exp(log_returns)  # shape (n_paths, n_months)

    # Contributions: step up once per year (year index k = t // 12, 0-indexed).
    month_idx = np.arange(n_months)
    year_idx = month_idx // 12
    contributions = monthly_contribution * (1.0 + contribution_growth_rate) ** year_idx

    total_contributed = float(np.sum(contributions))

    # Month-by-month balance evolution, vectorized across paths:
    # balance_t = balance_{t-1} * factor_t + contribution_t  (ordinary annuity convention)
    balances = np.empty((n_paths, n_months + 1), dtype=float)
    balances[:, 0] = initial_capital
    for t in range(n_months):
        balances[:, t + 1] = balances[:, t] * monthly_factors[:, t] + contributions[t]

    months = np.arange(n_months + 1)
    years = months / 12.0

    nominal_percentiles = {
        p: np.percentile(balances, p, axis=0) for p in PERCENTILES
    }
    mean_nominal_path = np.mean(balances, axis=0)

    deflator = (1.0 + annual_inflation) ** years
    real_balances = balances / deflator
    real_percentiles = {p: np.percentile(real_balances, p, axis=0) for p in PERCENTILES}
    mean_real_path = np.mean(real_balances, axis=0)

    return SimulationResult(
        months=months,
        years=years,
        nominal_paths_percentiles=nominal_percentiles,
        real_paths_percentiles=real_percentiles,
        mean_nominal_path=mean_nominal_path,
        mean_real_path=mean_real_path,
        nominal_final=balances[:, -1].copy(),
        real_final=real_balances[:, -1].copy(),
        total_contributed=total_contributed,
        inputs={
            "monthly_contribution": monthly_contribution,
            "duration_years": duration_years,
            "expected_annual_return": expected_annual_return,
            "annual_volatility": annual_volatility,
            "annual_inflation": annual_inflation,
            "contribution_growth_rate": contribution_growth_rate,
            "initial_capital": initial_capital,
            "annual_fee_rate": annual_fee_rate,
            "n_paths": n_paths,
            "seed": seed,
        },
    )
