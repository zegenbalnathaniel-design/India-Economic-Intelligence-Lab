# Open Portfolio Optimization Laboratory

Modern Portfolio Theory implemented from scratch — expected return, covariance, Sharpe ratios, and the minimum-variance and maximum-Sharpe portfolios derived via Lagrange multipliers — over a configurable universe spanning six global exchange groups.

## Research Question

Given a user-chosen set of real stocks across the US, India, London, Tokyo, Shanghai and Hong Kong, what do mean-variance optimization and the Sharpe ratio imply about the minimum-variance and maximum-Sharpe portfolios, and how does the efficient frontier change under realistic long-only / weight-cap constraints?

## Why I Built This

Most "portfolio optimizer" demos either hide the math behind a library call or restrict themselves to a handful of US tickers. I wanted every formula — the minimum-variance weights, the tangency portfolio, the efficient frontier itself — derived on the page via Lagrange multipliers (and, where constraints make that impossible, solved numerically via the KKT generalization), over a genuinely multi-market universe with real currency conversion, not a toy example.

## Economic / Financial Theory

- **Modern Portfolio Theory** (Markowitz, 1952): a portfolio is characterized by `E(Rp) = w^T μ` and `σ_p^2 = w^T Σ w`.
- **Sharpe ratio** (Sharpe, 1966): `(w^T μ - r_f) / σ_p` — excess return per unit of risk.
- **Lagrangian optimization**: the minimum-variance portfolio, the tangency (maximum-Sharpe) portfolio, and the full efficient frontier all have closed-form solutions when the only constraint is the budget constraint (`w^T 1 = 1`) — because that's an equality constraint, which is exactly what a Lagrangian solves analytically. Full derivations for each are in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).
- **KKT conditions**: long-only and weight-cap constraints are inequalities; the Lagrangian generalizes to the Karush-Kuhn-Tucker conditions, solved here numerically via `scipy.optimize.minimize` (SLSQP).

## Methodology

Full mathematical derivations: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Data

Live price data via `yfinance` where network access allows it, with a clearly-labelled **synthetic** (deterministic geometric Brownian motion) fallback per ticker wherever it doesn't — see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). **In the specific hosted environment this was authored in, Yahoo Finance is network-blocked, so every series in that environment is synthetic** — the app states this explicitly every time; run it with normal internet access for live data.

## Results / Demonstration

This is a **demonstration of the method**, not a real investment analysis, unless/until run with live network access against current prices — and even then, the Limitations section applies (estimation error, non-stationarity, no transaction costs). **Educational tool — not investment advice.**

## How It Works

```
src/portfolio_lab/
├── optimizer.py     # MPT core: returns, covariance, Sharpe, min-variance & tangency (Lagrangian), frontier, constrained (KKT) variants
├── data_loader.py   # live yfinance fetch with per-ticker synthetic fallback; FX conversion
├── network3d.py      # classical MDS 3D layout of the correlation matrix
└── universe.py       # the six-exchange-group ticker universe
```

Three Streamlit pages beyond the builder: a **3D efficient frontier** (return × volatility × Sharpe, built with Plotly), a **3D correlation network** (a Three.js scene driven by a classical-MDS embedding of the correlation matrix — not a decorative layout), and the full methodology.

## Installation

```bash
git clone <this repo>
cd portfolio-optimization-lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```python
from portfolio_lab import optimizer as opt
from portfolio_lab.data_loader import load_price_history

result = load_price_history(["AAPL", "RELIANCE.NS", "7203.T"], "2021-01-01", "2024-01-01")
mu = opt.expected_returns(result.prices)
cov = opt.covariance_matrix(result.prices)

w_minvar = opt.min_variance_weights_closed_form(cov.values)
w_tangency = opt.tangency_weights_closed_form(mu.values, cov.values, rf=0.04)
print("Min-variance Sharpe:", opt.sharpe_ratio(w_minvar, mu.values, cov.values, rf=0.04))
print("Tangency Sharpe:", opt.sharpe_ratio(w_tangency, mu.values, cov.values, rf=0.04))
```

Run the app:

```bash
streamlit run app/Home.py
```

Run the tests:

```bash
pytest tests/ -v
```

## Examples

See `notebooks/01_mpt_from_scratch.ipynb` for a from-scratch walkthrough of every formula against a small synthetic example, and the Streamlit app for the full interactive experience (multi-exchange picker, initial-investment allocator, 3D frontier, 3D correlation network).

## Limitations

- Mean-variance optimization is highly sensitive to estimation error in `μ` (much more than in `Σ`) — treat optimized weights as illustrative of the method, not a recommendation.
- No transaction costs, taxes, or liquidity constraints.
- Historical covariance is not guaranteed to persist (correlations shift sharply in crises).
- The "projected value" chart assumes i.i.d. lognormal returns — see the `sip-monte-carlo` project in this portfolio for explicit simulation with contributions, fees and inflation.
- FX conversion uses one daily rate per currency pair and does not model hedging.
- **This is an educational tool, not investment advice.**

## Future Work

- Black-Litterman blending of a market-equilibrium prior with user views, to address estimation error directly.
- Resampled/bootstrapped efficient frontiers (Michaud resampling) to visualize estimation uncertainty on the frontier itself.
- Transaction-cost-aware rebalancing between two chosen portfolios.

## Sources

- Markowitz, H. (1952). *Portfolio Selection.* The Journal of Finance.
- Sharpe, W.F. (1966). *Mutual Fund Performance.* The Journal of Business.
- Merton, R.C. (1972). *An Analytic Derivation of the Efficient Portfolio Frontier.* Journal of Financial and Quantitative Economics.
- Michaud, R.O. (1989). *The Markowitz Optimization Enigma: Is Optimized Optimal?* Financial Analysts Journal.
- Torgerson, W.S. (1952). *Multidimensional scaling: I. Theory and method.* Psychometrika.

## License

MIT — see [`LICENSE`](LICENSE).
