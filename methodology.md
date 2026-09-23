# Methodology

The authoritative write-up of every formula and assumption used on the site. This document is the reference; the in-app Methodology page is a shorter presentation of the same content.

## 1. Wealth accumulation — future value with rebalancing

A household contributes a constant amount `C` at the **start** of each year for `T` years, split across six asset classes by target allocation `w`. Each asset `k` compounds at nominal return `r_k`. When rebalancing is on (default), holdings are reset to `w` at each year-end.

Update rule for asset `k`:

    B_{k,t} = w_k · [ B_{k,t-1} + C ] · (1 + r_k)

with optional year-end reset to `total_t · w_k`. Portfolio-level nominal wealth is `W_t = Σ_k B_{k,t}` and the real path is `W_t / (1+π)^t` with `π` the assumed constant inflation.

Weighted portfolio return: `r_p = Σ_k w_k · r_k`. Real weighted return: `(1 + r_p) / (1 + π) − 1`.

**Assumptions.** Deterministic returns, no fees or taxes, no transaction costs, no correlation between asset returns.

## 2. Real vs nominal returns

Fisher approximation used throughout:

    r_real = (1 + r_nom) / (1 + π) − 1

Not the linear shortcut `r_nom − π`, which is inaccurate outside small-`π` regimes.

## 3. r − g

`r` and `g` **must be measured on the same basis.** The r − g explorer converts nominal `r` to real using the Fisher relation, then compares to real growth `g_real`. Comparing nominal `r` with real `g` overstates the gap and is a common source of error.

The identity `r > g` implies capital's share of national income tends to rise relative to labour income; it does **not** imply that inequality of individuals must rise. Distributional outcomes also depend on savings rates by wealth level, bequests, and the composition of wealth across the distribution — none of these are inside the identity.

## 4. Gini coefficient

Where used, the Gini is computed from sorted individual wealth levels using the trapezoidal Lorenz-curve formula. The MVP does not run a distributional Gini — the composition-effect module is deterministic for a single household.

## 5. iBFPI — India Bank Financial Performance Index

Adapted from the BFPI methodology in the accompanying JP Morgan / Fed-rate research paper.

### 5.1 Robust z-score per indicator per bank

For indicator `X_k` on bank `i` at time `t`, and direction coefficient `D_k`:

    Z*_{k,it} = D_k · (X_{k,it} − median_i(X_k)) / (1.4826 · MAD_i(X_k))

- The scale constant `1.4826` makes MAD consistent with the standard deviation of a normal distribution.
- Standardisation is done **within each bank's own history**, so a value is comparable to that bank's own baseline.
- `D_k = +1` if a higher raw value indicates better performance, `−1` otherwise.

### 5.2 Composite

Equal-weighted mean of the five standardised indicators:

    iBFPI_{it} = (1/5) · Σ_k Z*_{k,it}

Equal weights are a choice — a common one, and the same as in the JP Morgan paper. Alternative weightings should be justified explicitly.

### 5.3 Cross-bank aggregation

Default aggregation is an equal-weighted mean across banks. Optional asset-weighted mean is provided (marked illustrative — replace weights with real balance-sheet totals to reproduce).

### 5.4 Indicators, direction, interpretation

| Indicator | Direction D | Interpretation |
| --- | --- | --- |
| PPNR / Assets | +1 | Core earnings power |
| CET1 Ratio | +1 | Capital adequacy |
| Net Charge-Off Rate | −1 | Realised credit losses |
| Liquidity Coverage Ratio | +1 | Short-run liquidity |
| Unrealised Securities Losses / CET1 | −1 | MTM stress on AFS book |

## 6. Spearman rank correlation

A rank-based correlation that captures monotonic association without assuming linearity or normality. Used here for the iBFPI × repo-rate relation. The reported p-value is a two-sided test of H₀: ρ = 0 and does **not** correct for autocorrelation of the quarterly series. Correlation is not causation — an event study or panel regression is needed for causal statements.

## 7. Rate-regime classification

Regimes are classified from the three-quarter rolling change in the repo rate:

    Δ₃ r_t = Σ_{s=t-2}^{t} (r_s − r_{s-1})

    Δ₃ r_t > +25bp  →  rising
    Δ₃ r_t < −25bp  →  falling
    otherwise        →  stable

The threshold is a modelling choice; results are sensitive to it. The regime-split correlations use the same Spearman ρ within the subsample and inherit the same limitations.

## 8. Provenance — from the papers vs new here

| Component | Origin |
| --- | --- |
| Composition-effect exhibit | Paper A |
| Robust z-score / BFPI formula | Paper B |
| Direction coefficients (5 indicators) | Paper B |
| Asset-allocation comparison as an interactive module | New here |
| r − g explorer | Framing from Paper A + literature, module is new |
| iBFPI applied to Indian panel | New here |
| Rate-regime split (±25bp on Δ₃ rate) | New here |
| Illustrative synthetic panel | New here |

## 9. Assumptions the visitor edits (never hard-coded)

- Annual contribution, horizon, allocation weights, per-asset nominal returns, inflation
- r, π, g in the r − g module
- Bank subset and aggregation weighting in the Banking Lab

## 10. Assumptions hard-coded (documented, would-be-editable in a follow-up)

- Annual compounding, annual contribution timing
- Direction coefficients for the five iBFPI indicators (fixed)
- Regime threshold (±25bp on three-quarter change)
- MAD scale constant (1.4826)

## 11. Known limitations

Correlation ≠ causation · small samples for rate-regime subsets · top-tail wealth undercoverage in Indian surveys · asset valuation uncertainty (property, gold marks-to-market) · historical returns ≠ future returns · structural breaks (Covid, IND-AS transition) · data revisions · cross-bank accounting differences · autocorrelation not corrected in Spearman p-values · composite-index subjectivity (weights and directions are choices) · deterministic returns in the composition-effect model.
