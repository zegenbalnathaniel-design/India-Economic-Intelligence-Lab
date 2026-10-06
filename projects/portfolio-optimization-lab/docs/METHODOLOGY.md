# Methodology

## Research question

Given a chosen universe of real stocks across multiple global exchanges, what do mean-variance optimization and the Sharpe ratio imply about the minimum-variance and maximum-Sharpe portfolios, and how does the efficient frontier change under realistic constraints (long-only, per-asset weight caps)?

## Theoretical framework: Modern Portfolio Theory

Markowitz (1952) models a portfolio by two numbers: its expected return and its variance. For weights `w` (summing to 1), asset expected-return vector `μ`, and asset covariance matrix `Σ`:

```
E(Rp) = w^T μ
σ_p^2 = w^T Σ w
```

The **Sharpe ratio** (Sharpe, 1966) is the excess return per unit of risk:

```
S(w) = (w^T μ - r_f) / sqrt(w^T Σ w)
```

Every number below is derived from only these three objects — nothing else enters the optimization.

## Mathematical framework: Lagrangian derivations

### 1. Global minimum-variance portfolio

**Problem**: minimize `(1/2) w^T Σ w` subject to `w^T 1 = 1` (fully invested, no return target — just the smallest possible variance).

**Lagrangian**:
```
L(w, λ) = (1/2) w^T Σ w − λ (w^T 1 − 1)
```
**First-order condition** (`∂L/∂w = 0`):
```
Σw − λ1 = 0   ⟹   w = λ Σ^-1 1
```
**Impose the constraint** `1^T w = 1`:
```
λ (1^T Σ^-1 1) = 1   ⟹   λ = 1 / (1^T Σ^-1 1)
```
**Result**:
```
w_mv = Σ^-1 1 / (1^T Σ^-1 1)
```
Implemented in `min_variance_weights_closed_form`. Verified in `tests/test_optimizer.py` against the textbook two-asset inverse-variance-weighting formula and against 200 random feasible perturbations (none of which can lower variance below `w_mv`'s — the empirical signature of a true minimum).

### 2. Maximum-Sharpe (tangency) portfolio

**Key fact**: the Sharpe ratio is unchanged if you scale `w` by any positive constant (it cancels in the ratio). So maximizing `S(w)` subject only to `w^T 1 = 1` is equivalent to first finding the *direction* that maximizes return per unit of variance, then rescaling that direction so the weights sum to 1.

**Equivalent problem**: minimize `(1/2) w^T Σ w` subject to `w^T(μ − r_f 1) = κ` for some fixed excess return `κ` (any positive value — the direction doesn't depend on which one).

**Lagrangian**:
```
L(w, λ) = (1/2) w^T Σ w − λ (w^T(μ − r_f·1) − κ)
```
**First-order condition**:
```
Σw − λ(μ − r_f·1) = 0   ⟹   w ∝ Σ^-1 (μ − r_f·1)
```
**Rescale so the weights form a genuine portfolio** (`1^T w = 1`):
```
w_tan = Σ^-1 (μ − r_f·1) / [1^T Σ^-1 (μ − r_f·1)]
```
Implemented in `tangency_weights_closed_form`. Verified against 500 random budget-constrained portfolios (none achieve a higher Sharpe ratio than `w_tan`) and against the closed-form direction for a 2-asset case.

### 3. The efficient frontier (Merton, 1972)

**Problem**: for a *chosen* target return `r`, minimize `(1/2) w^T Σ w` subject to **two** equality constraints: `w^T μ = r` and `w^T 1 = 1`.

**Lagrangian** (two multipliers, one per constraint):
```
L(w, λ, γ) = (1/2) w^T Σ w − λ(w^T μ − r) − γ(w^T 1 − 1)
```
**First-order condition**:
```
Σw − λμ − γ1 = 0   ⟹   w = Σ^-1(λμ + γ1)
```
Substituting into the two constraints and defining the scalars
```
a = 1^T Σ^-1 1,   b = 1^T Σ^-1 μ,   c = μ^T Σ^-1 μ,   d = ac − b²
```
gives a 2×2 linear system in `(λ, γ)` with solution
```
λ = (a·r − b) / d        γ = (c − b·r) / d
```
so the efficient-frontier weights for target return `r` are
```
w*(r) = Σ^-1 [ (c − b·r)·1 + (a·r − b)·μ ] / d
```
Implemented in `efficient_frontier_closed_form`. The vertex of this frontier (minimum variance point) occurs exactly at the global minimum-variance portfolio from §1 — verified directly in `tests/test_optimizer.py`.

### 4. From Lagrangian to KKT: adding realistic constraints

Sections 1-3 all assume **unlimited short-selling** — the only constraint is the budget constraint, an *equality*, which is exactly the case a Lagrangian solves analytically. The moment you require **long-only** (`w_i ≥ 0`) or a **per-asset weight cap** (`w_i ≤ w_max`), you've added *inequality* constraints, and the Lagrangian generalizes to the **Karush-Kuhn-Tucker (KKT) conditions** — the same first-order logic, but with complementary-slackness conditions on which inequality constraints are "active" (binding) at the optimum. There is no general closed form for which constraints bind, so `min_variance_weights_constrained` and `max_sharpe_weights_constrained` solve the KKT system **numerically** via `scipy.optimize.minimize` (SLSQP, a sequential quadratic programming method built exactly for this: smooth objective, linear/nonlinear equality and inequality constraints).

`tests/test_optimizer.py` verifies that when the bounds are set wide enough to never bind, the numerical KKT solution converges to the closed-form Lagrangian solution — i.e. the general numerical method correctly reduces to the analytic special case.

## Data

- **Expected returns and covariance** (`expected_returns`, `covariance_matrix`): historical daily simple returns, annualized by `× 252` (mean) and `× 252` (covariance) — the standard trading-days-per-year convention. This is a **backward-looking estimate**, not a forward-looking forecast; see Limitations.
- **Price history** (`data_loader.py`): fetched live via `yfinance` where the network allows it; a clearly-labelled **synthetic** geometric-Brownian-motion series is substituted per-ticker wherever a live fetch fails. See `docs/DATA_SOURCES.md` for exactly what happened in any specific run — the Portfolio Builder page's "Data status" panel reports this live/synthetic split explicitly, every time.
- **Currency conversion**: every asset's price series is converted to a user-chosen base currency via `convert_prices_to_base_currency`, using the FX rate at each date (live where available, a flat illustrative snapshot rate otherwise). Mixing un-converted multi-currency price series into one covariance matrix would be a measurement error (currency moves would be misattributed to asset co-movement) — this step exists specifically to avoid that.

## Assumptions

- Returns are assumed stationary over the estimation window (historical mean/covariance are used as if they were the true forward-looking `μ`/`Σ`) — a standard MPT simplification, not a claim that returns are actually stationary.
- No transaction costs, no taxes, no liquidity constraints, no minimum lot sizes.
- The "projected value" chart assumes i.i.d. lognormal returns (geometric Brownian motion) — a simplification; see the SIP Monte Carlo project for a richer simulation treatment.
- FX conversion uses a single daily rate per currency pair; it does not model FX hedging costs or hedged share classes.

## Limitations

- **Estimation error**: historical mean returns are notoriously noisy estimators of future expected returns (far noisier than historical covariance); mean-variance optimization is known to be highly sensitive to this ("optimization amplifies estimation error" — Michaud, 1989). Treat the optimized weights as illustrative of the *method*, not as a recommendation.
- **Non-stationarity**: correlations and volatilities shift across regimes (e.g. rise sharply in crises); a single historical window will not capture this.
- **Historical bias**: using realized returns as a proxy for expected returns assumes the future resembles the past window chosen — survivorship and sample-period selection both bias this.
- **Transaction costs and taxes**: entirely absent from this model; real rebalancing to any of these "optimal" portfolios would incur costs this model does not account for.
- **Model risk**: mean-variance optimization assumes returns are adequately described by their mean and covariance alone (implicitly closest to exact under joint-normality); real asset returns exhibit fat tails and skewness this framework ignores.
- **This is an educational model, not investment advice.**

## Reproducibility

- Every optimizer function takes `mu`/`cov`/`weights` as plain NumPy arrays — no hidden state, no global configuration.
- The synthetic price fallback is seeded deterministically per ticker (`hashlib.sha256(ticker)`); the same ticker and date range always produce the same synthetic series.
- `pytest tests/ -v` checks every closed-form formula against independent algebra (2-asset special cases) and checks the numerical (KKT) solvers against the closed-form (Lagrangian) solutions in the unconstrained limit.
