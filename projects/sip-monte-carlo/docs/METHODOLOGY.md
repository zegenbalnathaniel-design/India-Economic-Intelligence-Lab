# Methodology

## Research question

Given a monthly SIP (systematic investment plan) contribution that grows
over time, under a *stated set of assumptions* about expected returns,
return volatility, fees and inflation — **what does the full distribution
of possible outcomes look like**, not just the single "average-case"
projection most SIP calculators show? And specifically: how much of that
distribution's spread comes from (a) uncertainty about the average return,
versus (b) the mechanical fact that compounding with volatility is not the
same as compounding at a fixed rate equal to the average?

This is a methodology/simulation question, not an empirical or predictive
one. No historical return data is fitted, estimated, or used anywhere in
this project — see [Data](../README.md#data) in the README.

## Theoretical framework

### Compound interest with a growing annuity (the deterministic baseline)

The textbook SIP calculation assumes a constant monthly rate `r` and a
constant monthly contribution `C`, and computes the future value of an
*ordinary annuity*:

```
FV = C * [(1 + r)^n - 1] / r
```

This project generalizes that baseline in three ways that most SIP
calculators skip:

1. **Growing contributions.** The SIP amount steps up once a year by a
   `contribution_growth_rate` (e.g., "I'll raise my SIP by 10% every year
   as my salary grows").
2. **An initial lump sum**, compounding alongside the contributions.
3. **Fees**, applied as a continuous drag on the compounding rate.

The exact closed form for this generalized, but still *deterministic*,
case is derived and implemented in `src/sip_monte_carlo/closed_form.py`.
For year block `k` (0-indexed), the twelve monthly contributions of size

```
C_k = monthly_contribution * (1 + contribution_growth_rate)^k
```

accumulate to `C_k * FVA_12(r)` by the end of that year, where
`FVA_12(r) = [(1+r)^12 - 1] / r` is the future-value-of-annuity factor for
12 level monthly payments (limit `12` as `r -> 0`). That lump sum then
compounds forward for the remaining months to the end of the horizon.
Summing over all `T` years and adding the compounded initial capital gives
the exact future value:

```
FV = V0 * (1+r)^(12T) + sum_{k=0}^{T-1} C_k * FVA_12(r) * (1+r)^(12(T-1-k))
```

This closed form is what the Monte Carlo engine is checked against when
volatility is set to zero (`tests/test_engine.py::
test_zero_volatility_matches_closed_form_*`). A simulator that cannot
reproduce ordinary compound interest exactly in the no-uncertainty case is
not trustworthy when uncertainty is turned on, so this check is treated as
load-bearing, not optional.

### Returns as a lognormal process

Once volatility is turned on, annual simple returns are modeled as
lognormal: the annual gross return is `R = exp(Z) - 1` with
`Z ~ Normal(mu_log, sigma_log^2)`. Matching the first two moments to the
user's `expected_annual_return` (arithmetic mean) and `annual_volatility`
(standard deviation of the simple return) gives:

```
sigma_log^2 = ln(1 + annual_volatility^2 / (1 + expected_annual_return)^2)
mu_log      = ln(1 + expected_annual_return) - sigma_log^2 / 2
```

Because sums of independent normal variables are normal, the engine draws
12 independent monthly log-returns from `Normal(mu_log/12, sigma_log^2/12)`
per path. Summing any 12 of them reproduces `Normal(mu_log, sigma_log^2)`
exactly — so the monthly simulation is an *exact* decomposition of the
stated annual assumptions, not an approximation glued together from an
arbitrary monthly distribution.

Fees are folded in by subtracting `annual_fee_rate / 12` from every
monthly log-return — a continuous drag, consistent with how an ongoing
expense ratio actually erodes a fund's NAV growth every day the fund
exists, not just once a year.

### Volatility drag: the arithmetic–geometric mean gap

For a lognormal (or any multiplicative) compounding process, the typical
("median") compounding rate converges to the **geometric mean**, which is
systematically below the **arithmetic mean** whenever volatility is
positive:

```
geometric mean (continuous approx.)  ≈  arithmetic mean − volatility^2 / 2
```

This is a mechanical, not psychological, fact about multiplying random
factors together — it has nothing to do with market pessimism or risk
aversion. Two investment options with the *same* arithmetic mean return
but different volatility will, more often than not, leave a long-horizon
investor at *different* typical wealth levels: the more volatile option's
median path falls further below its mean. The Monte Carlo engine
demonstrates this directly: holding `expected_annual_return` fixed and
raising `annual_volatility` lowers the **median** final value while
leaving the **mean** roughly flat (or even slightly higher, because the
right tail of a lognormal distribution gets longer as volatility rises —
a few extreme winners pull the average up even as the typical path does
worse). See `tests/test_engine.py::
test_higher_volatility_does_not_increase_median_final_value`.

### Sequence-of-returns risk

Sequence-of-returns risk is a related but distinct phenomenon: *holding
the exact set of annual returns fixed*, the *order* in which they occur
changes the final wealth whenever there are ongoing cash flows (regular
contributions here; regular withdrawals in a decumulation/retirement
context). This is implemented and tested independently of the main
engine, in `src/sip_monte_carlo/sequence_risk.py`, using a small, explicit,
user-editable set of annual returns run forward and in reverse. Reversing
a list does not change its arithmetic mean, so any difference in the two
final values is attributable purely to ordering, not to average return.

Mechanically: a return that lands late in the horizon is multiplied
against a much larger accumulated base (built up by years of prior
contributions) than the same return would be if it landed early. The
engine's own month-by-month Monte Carlo already samples many different
implicit "sequences" across its simulated paths — the dedicated module
isolates the effect in a controlled, minimal example for teaching
purposes.

### Inflation adjustment

Inflation plays no role in the nominal simulation itself — it is applied
once, after the fact, purely to re-express results in constant
(today's-rupee) purchasing power:

```
real_wealth(t) = nominal_wealth(t) / (1 + annual_inflation)^(t / 12)
```

where `t` is the month index. This keeps "what grows the money" (returns,
contributions, fees) cleanly separate from "what the money is worth"
(inflation), per the Theory/Model/Simulation separation this project
follows throughout.

## Assumptions (stated explicitly)

- Annual returns are i.i.d. lognormal, with no autocorrelation, no regime
  switching, and no modeling of real historical market cycles, crashes, or
  recoveries. This is a deliberate simplification, not a claim that real
  markets behave this way.
- Volatility, expected return, fees, inflation and contribution growth are
  all held *constant* across the simulated horizon (no time-varying
  parameters, no glide paths, no changing asset allocation over time).
- Contributions step up once per year (a discrete, annual, not monthly,
  growth schedule), and are added at the end of each month, after that
  month's return is applied (the "ordinary annuity" convention).
- Fees are modeled as a constant, continuous annual drag (`annual_fee_rate
  / 12` subtracted from every monthly log-return) — a reasonable
  approximation of an expense ratio, not a model of transaction costs,
  taxes, exit loads, or any India-specific fee structure.
- Inflation is a single constant rate used only to deflate nominal results
  into real terms; it is not drawn stochastically and does not feed back
  into the nominal return assumption (i.e., `expected_annual_return` is
  already assumed nominal, not real).
- All assumptions (return, volatility, fees, inflation, growth) are
  illustrative defaults that the user is expected to override; none of
  them are fitted to, or claimed to represent, any real fund, index, or
  historical period.

## Methodology (how the simulation is run)

1. Validate inputs (see `src/sip_monte_carlo/engine.py::_validate_inputs`);
   raise `ValueError` on anything economically nonsensical (negative
   duration, negative contribution, non-positive path count, etc.).
2. Moment-match the stated annual return/volatility assumptions to a
   lognormal annual distribution, then decompose it into independent
   monthly log-return draws (exact, not approximate — see above).
3. Draw `n_paths × n_months` i.i.d. monthly log-returns with NumPy's
   `default_rng(seed)` (or skip the draw entirely when volatility is zero,
   since the outcome is then deterministic).
4. Step the balance forward month by month for every path simultaneously
   (vectorized), adding the appropriate year's contribution at the end of
   each month.
5. Record the cross-sectional percentiles (p10, p25, p50, p75, p90) and
   mean of nominal wealth at *every* month, not just the final one, to
   support the fan chart.
6. Deflate every recorded value by the inflation factor appropriate to
   its month to get the parallel real-wealth series.
7. Report final-value statistics and, given a user-supplied target corpus,
   the empirical fraction of simulated paths whose final nominal (or real)
   wealth meets or exceeds it.

## Limitations

- No real market data, no backtesting, no calibration to historical
  Indian (or any) asset class returns. See the README's Data and
  Limitations sections.
- Returns are assumed independent month to month; no fat tails beyond what
  the lognormal distribution itself produces, no jump risk, no
  correlation with inflation or interest rates.
- The sequence-of-returns demonstration uses a small, hand-picked set of
  returns for clarity; it is a teaching example, not a simulation of "most
  likely" real-world sequences.
- Fees are a single flat annual rate; no distinction between expense
  ratio, transaction costs, exit load, or tax drag (e.g., Indian LTCG/STCG
  treatment on equity mutual funds is not modeled).
- Contribution growth is a single constant annual rate; no modeling of
  income interruptions, contribution pauses, or lump-sum withdrawals mid
  horizon.

## Reproducibility

Every simulation run accepts an explicit `seed`. For fixed inputs
(including `seed`), `run_simulation(...)` is deterministic and
reproducible byte-for-byte — verified in
`tests/test_engine.py::test_same_seed_reproducible`. No other source of
randomness (wall-clock time, OS entropy, etc.) is used anywhere in the
package; `numpy.random.default_rng(seed)` is the sole source of
randomness, instantiated fresh inside each call to `run_simulation`.
