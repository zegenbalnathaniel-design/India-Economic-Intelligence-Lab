# Methodology

## Research question

1. How do standard inequality statistics (Gini, Lorenz, percentile shares, Palma ratio) behave on a given distribution, computed transparently and tested against closed-form edge cases?
2. Holding savings behaviour fixed, how much does long-run wealth diverge purely from asset-allocation differences ("composition effect")?

## Theoretical framework

Inequality measurement theory treats a population's income/wealth as a univariate distribution and asks how concentrated it is. No single scalar captures a distribution fully (Atkinson, Sen literature); this toolkit therefore provides several views (point statistics + the Lorenz curve itself) rather than reporting one number.

The composition-effect simulator formalizes a mechanical accounting identity: if wealth is held across `k` asset classes with weights `w_k` (summing to 1) and each class compounds at return `r_k`, portfolio-level growth is the weighted average `r_p = Σ w_k r_k`, which differs across households whenever `w` differs — even with identical income and identical savings rate.

## Mathematical framework

**Gini coefficient** (discrete rank form), for sorted `x_1 <= ... <= x_n`:

```
G = [2 * Σ_{i=1}^{n} i·x_i − (n+1)·Σx_i] / (n · Σx_i)
```

This is algebraically equal to twice the area between the Lorenz curve and the line of equality. Requires `x_i >= 0`.

**Lorenz curve**: plot of cumulative population share `i/n` against cumulative value share `(Σ_{j<=i} x_j) / Σx_j`.

**Percentile share** `[lower, upper]`: `(S(upper) − S(lower)) / S(100)` where `S(p)` is the cumulative value held by the bottom `p`% of units by rank.

**Palma ratio**: `percentile_share(90,100) / percentile_share(0,40)`.

**Concentration ratio (top n)**: share of total value held by the `n` largest-value units (as opposed to a percentile cut — useful for small, discrete populations).

**Composition effect** — household wealth update, contribution `C` at year-start, target weights `w`, per-asset return `r_k`, optional year-end rebalancing to `w`:

```
B_{k,t} = w_k · [B_{k,t-1} + C] · (1 + r_k)       (rebalanced variant: reset to total_t · w_k at year end)
W_t = Σ_k B_{k,t}
```

Real (inflation-adjusted) path: `W_t / (1+π)^t`, using the **Fisher relation** `r_real = (1+r_nom)/(1+π) − 1` throughout (never the linear approximation `r_nom − π`).

**Monte Carlo variant**: annual per-asset returns drawn i.i.d. `Normal(r_k, σ_k)`, assets assumed **independent** (no covariance structure — a deliberate simplification; see the `portfolio-optimization-lab` project for a covariance-aware treatment with real historical data).

## Data

- Inequality functions: no bundled real data. `data/synthetic_household_wealth.csv` is synthetic (see `examples/generate_synthetic_wealth.py`); labeled as such everywhere it is displayed.
- Composition-effect default returns/volatilities (`DEFAULT_NOMINAL_RETURNS`, `DEFAULT_VOLATILITY` in `wealth.py`): illustrative long-run reference points loosely consistent with publicly reported RBI/NSE long-horizon averages. They are defaults a caller is expected to override, not calibrated estimates, and are never presented as forecasts.

## Assumptions

- Inequality functions assume non-negative values and no missing data (NaNs raise rather than being silently dropped — the caller must decide how to handle missingness).
- Composition-effect model: annual compounding, contribution at year start, no fees/taxes/transaction costs, and (in the deterministic variant) no return uncertainty.
- Monte Carlo variant: independent Gaussian annual returns per asset — no fat tails, no cross-asset correlation, no regime-switching.

## Limitations

See the README's Limitations section — reproduced in full for completeness: non-negativity requirement, top-tail underreporting in real survey data, deterministic-model-is-not-a-forecast caveat, and the information loss inherent in any single summary statistic.

## Reproducibility

- `examples/generate_synthetic_wealth.py` is fully deterministic given its `seed` argument (default 42); re-running it reproduces the bundled CSV byte-for-byte.
- All Monte Carlo functions take an explicit `seed` argument; the same seed reproduces the same paths.
- `pytest tests/ -v` exercises every function against closed-form or edge-case expectations (e.g. Gini = (n-1)/n when one unit holds everything).
