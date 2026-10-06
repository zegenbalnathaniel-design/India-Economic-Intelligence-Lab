# Methodology

## Research Question

Can a small set of interactive, mathematically correct modules make standard micro/macro/finance theory tangible rather than diagrammatic? This document gives, for every implemented module, the exact theoretical framework, the governing equations, the assumptions behind them, and what is and is not claimed by their output.

## General Approach

Every module in this project follows the same split:

1. **Theory** -- a general mathematical relationship that is true *by construction* given a stated set of assumptions (e.g. "demand is linear in price"). This part never changes regardless of what numbers a user enters.
2. **Illustrative parameters** -- specific numbers (slopes, intercepts, rates, weights) a user chooses on the app's sliders, solely to produce a concrete, visualizable example. These numbers are not estimates of, or claims about, any real market, economy, or financial product.

No module in this project consumes external data. See the root [`README.md`](../README.md) for the full list of implemented modules and the extensible module architecture (`EconModule` in `src/econ_lab/registry.py`).

---

## Microeconomics

### Demand & Supply Equilibrium (`micro_supply_demand`)

**Framework.** Linear demand and supply in a single market.

```
Qd = a - bP        (b > 0)
Qs = c + dP        (d > 0)
```

**Equilibrium.** Setting Qd = Qs and solving for P:

```
a - bP = c + dP
a - c  = (b+d)P
P* = (a - c) / (b + d)
Q* = a - bP*
```

**Assumptions.** Both curves are exactly linear over the whole relevant range; no third-party effects; the market clears (price adjusts until Qd=Qs).

**Validity.** Requires a > c (so P* > 0) and b, d > 0. Division by (b+d) is always well-defined since b, d > 0.

### Price Elasticity of Demand (`micro_elasticity`)

**Framework.** Point price elasticity of demand, evaluated at a specific point on a linear demand curve Q = a - bP.

```
PED = (dQ/dP) * (P/Q) = -b * (P/Q)
```

**Assumptions.** dQ/dP = -b is exact and constant for a linear curve; elasticity is evaluated at a single point (not the arc/midpoint elasticity between two points).

**Validity.** Requires Q > 0, i.e. 0 <= P < a/b.

### Tax Incidence & Deadweight Loss (`micro_tax_incidence`)

**Framework.** A per-unit tax t creates a wedge between the price consumers pay (Pc) and the price producers receive (Pp = Pc - t).

```
Qd(Pc) = a - b*Pc
Qs(Pp) = c + d*Pp = c + d*(Pc - t)
```

**After-tax equilibrium** (set Qd(Pc) = Qs(Pc - t) and solve for Pc):

```
a - b*Pc = c + d*Pc - d*t
Pc = (a - c + d*t) / (b + d)
Pp = Pc - t
Q  = a - b*Pc
```

**Burden split.** Comparing to the no-tax equilibrium P0 = (a-c)/(b+d):

```
Pc - P0 = t * d / (b + d)     (consumer burden)
P0 - Pp = t * b / (b + d)     (producer burden)
```

These two always sum to exactly t. The side with the *smaller* slope coefficient (relatively less price-responsive, i.e. relatively less elastic) bears the *larger* share -- consistent with the general tax-incidence result that burden falls more heavily on the less elastic side.

**Surplus and deadweight loss** (triangle-area formulas for linear curves):

```
demand price-intercept  = a/b     (price where Qd = 0)
supply price-intercept  = -c/d    (price where Qs = 0)

CS  = 0.5 * (a/b - Pc) * Q
PS  = 0.5 * (Pp - (-c/d)) * Q
DWL = 0.5 * t * (Q0 - Q)
```

**Assumptions.** Linear demand and supply; the tax is a simple per-unit wedge (not ad valorem); no administrative/compliance costs; no behavioral response beyond the price elasticity already captured by the slopes.

**Validity.** Requires t >= 0 and a tax small enough that Q stays positive and Pp stays non-negative.

### Price Ceilings & Floors (`micro_price_controls`)

**Framework.** A legally fixed price Pcontrol, compared with the free-market equilibrium P0 = (a-c)/(b+d).

```
Ceiling (Pcontrol < P0):  shortage = Qd(Pcontrol) - Qs(Pcontrol)
Floor   (Pcontrol > P0):  surplus  = Qs(Pcontrol) - Qd(Pcontrol)
```

Quantity actually transacted is always the smaller ("short side") of Qd and Qs evaluated at the control price. A non-binding control (a ceiling above P0, or a floor below P0) leaves the free-market equilibrium unaffected.

**Assumptions.** Linear demand and supply; perfect enforcement of the control price; no secondary markets.

---

## Macroeconomics

### Aggregate Demand & Aggregate Supply (`macro_ad_as`)

**Framework.** Two linear curves in (output Y, price level P) space -- the same algebra as the single-market model, relabeled, and deliberately much smaller than a full macro simulator.

```
AD: Y = A_d - b_d*P
AS: Y = A_s + b_s*P
```

**Equilibrium.**

```
P* = (A_d - A_s) / (b_d + b_s)
Y* = A_d - b_d*P*
```

A demand shock adds `ad_shift` to A_d; a supply shock adds `as_shift` to A_s. The module reports both the baseline and post-shock equilibrium.

**Assumptions.** Both curves are linear over the displayed range; the model is a single static period with no explicit money market, expectations, or multi-period dynamics.

**Why this is smaller than the sibling policy simulator.** The `india-economic-policy-simulator` project (a sibling in this repository) models fiscal/monetary transmission, a Phillips curve, Okun's law, and debt dynamics across multiple periods. This module intentionally stops at the single-period two-curve diagram, to keep the AD/AS intuition itself front and center.

### Fiscal (Keynesian) Multiplier (`macro_multiplier`)

**Framework.** A constant marginal propensity to consume (MPC = c) means an initial spending injection dG is partly re-spent every round:

```
dY = dG * (1 + c + c^2 + c^3 + ...)
```

This is a geometric series with ratio c (0 <= c < 1), which sums in closed form to:

```
dY = dG / (1 - c)
multiplier = 1 / (1 - MPC)
```

**Assumptions.** Closed economy (no import leakage), no taxes, a constant MPC every round, and enough idle capacity that extra spending translates into extra output rather than purely higher prices.

**Validity.** Requires 0 <= MPC < 1 for the series (and the multiplier) to converge to a finite value.

### Solow-Style Capital Accumulation (`macro_growth`)

**Framework.** Per-worker output follows Cobb-Douglas production f(k) = k^alpha (0 < alpha < 1). Capital per worker accumulates as:

```
k_{t+1} = k_t + s*f(k_t) - delta*k_t
```

where s is the savings/investment rate and delta is the depreciation rate.

**Steady state.** At steady state, investment exactly offsets depreciation: s*k*^alpha = delta*k*. Solving:

```
s*k*^alpha = delta*k*
s/delta = k*^(1-alpha)
k* = (s/delta)^(1/(1-alpha))
y* = k*^alpha
```

**Assumptions.** A single aggregate capital stock and a single aggregate worker/labor input (no population growth or technological progress in this simplified version); Cobb-Douglas production; a constant savings rate and constant depreciation rate.

**Convergence.** Because f(k)=k^alpha is strictly concave while delta*k is linear through the origin, the two cross exactly once for k>0, at k*; the discrete accumulation rule converges to that same k* from any strictly positive starting point k0 (and stays at 0 forever if k0=0, since f(0)=0).

---

## Finance

### Compound Interest & Present Value (`finance_compound_interest`)

**Framework.** Standard time-value-of-money formulas for an initial principal P and/or a stream of equal periodic contributions C, at a constant periodic rate r over n periods.

```
FV_lump    = P * (1+r)^n
FV_annuity = C * [(1+r)^n - 1] / r        (r != 0; ordinary annuity, contributions at period end)
FV_annuity = C * n                         (r = 0)
FV_total   = FV_lump + FV_annuity
PV         = FV_total / (1+r)^n
```

**Assumptions.** A single constant periodic rate for the whole horizon; contributions, if any, occur at the end of each period (ordinary annuity convention); no taxes or fees.

**Validity.** Requires r > -1 and n >= 0.

### Two-Asset Diversification (`finance_diversification`)

**Framework.** Portfolio variance for two assets with weights w1 and w2 = 1-w1, standard deviations sigma1, sigma2, and return correlation rho:

```
sigma_p^2 = w1^2*sigma1^2 + w2^2*sigma2^2 + 2*w1*w2*rho*sigma1*sigma2
```

**Special cases** (used as correctness checks -- see `tests/test_finance_diversification.py`):

- rho = 1: the cross term is maximal and the formula factors exactly into `(w1*sigma1 + w2*sigma2)^2`, i.e. portfolio std equals the simple weighted average -- no diversification benefit.
- rho = -1: the formula becomes `(w1*sigma1 - w2*sigma2)^2`, the minimum possible variance for these weights and volatilities.

**Assumptions.** Only two assets; a single period; no expected-return or optimization layer (this module shows risk reduction only, not risk-adjusted return trade-offs).

**Scope note.** This module deliberately stops at the two-asset variance formula. The `portfolio-optimization-lab` sibling project implements the full N-asset Markowitz mean-variance optimization (minimum-variance portfolio, tangency portfolio, efficient frontier); the `sip-monte-carlo` sibling project simulates a real contribution schedule under return uncertainty.

---

## Methodology (Testing)

Every module above has a corresponding test file under `tests/` that checks its `compute(...)` output against the closed-form formula hand-solved for a specific set of numbers (not merely re-running the same code path), plus edge/invalid-input cases (negative prices, a supply curve that leaves no positive-price equilibrium, a zero elasticity point, an over-sized tax, invalid correlation/weights, etc.). Run `pytest tests/ -v` to reproduce every check.

## Reproducibility

Every module's `compute` function is deterministic (no random sampling anywhere in this project) and depends only on its explicit arguments -- calling it twice with the same inputs always returns identical output. `conftest.py` puts `src/` on `sys.path` so `pytest`, a notebook, or a plain script can all import `econ_lab` identically without installing the package.

## Limitations

See the root [`README.md`](../README.md#limitations) for the full limitations list, including what each domain's modules deliberately leave out relative to the deeper sibling projects in this repository.
