# India Economic Intelligence Lab

A portfolio of nine independent, open-source computational projects exploring economics, finance, education and Indian economic data.

I build open-source computational projects exploring economics, finance, education, and Indian economic data. Each project below is self-contained — its own README, license, tests, methodology and (where relevant) Streamlit app — but they share a common thread: using data and computation to make economic questions understandable, rather than just asserted.

## The nine projects

| # | Project | What it does |
|---|---|---|
| 1 | [`india-economic-policy-simulator`](projects/india-economic-policy-simulator/) | A pedagogical fiscal/monetary policy simulator (open-economy fiscal multiplier, Phillips curve, Okun's law, debt dynamics, crowding out) plus an empirical bank-performance/repo-rate transmission analysis (iBFPI). |
| 2 | [`india-wealth-inequality-toolkit`](projects/india-wealth-inequality-toolkit/) | A reusable Gini / Lorenz curve / percentile-share / Palma-ratio inequality toolkit, plus the household wealth-composition simulator from the author's research on wealth accumulation in India. |
| 3 | [`india-housing-affordability`](projects/india-housing-affordability/) | Price-to-income, EMI, loan-to-value and down-payment-burden metrics across major Indian cities, with conservative/baseline/optimistic scenario comparison. |
| 4 | [`portfolio-optimization-lab`](projects/portfolio-optimization-lab/) | Modern Portfolio Theory from scratch: Sharpe ratios, the minimum-variance and maximum-Sharpe portfolios derived via Lagrange multipliers, and the efficient frontier, over a configurable six-exchange global stock universe (US, India NSE/BSE, London, Tokyo, Shanghai, Hong Kong) — including a 3D frontier and a 3D correlation-network view. |
| 5 | [`sip-monte-carlo`](projects/sip-monte-carlo/) | A Monte Carlo simulator for systematic-investment-plan wealth accumulation: percentile fan charts, probability of reaching a target, sequence-of-returns risk, fees and inflation. |
| 6 | [`personal-inflation-index`](projects/personal-inflation-index/) | Build your own household consumption basket and compute a personalized Laspeyres inflation index, compared against an illustrative CPI-style basket. |
| 7 | [`economics-interactive-lab`](projects/economics-interactive-lab/) | An extensible interactive economics-education platform — micro (supply/demand, elasticity, tax incidence), macro (AD/AS, multipliers, growth) and finance (compound interest, diversification) modules, each with its own concept, equation, controls, visualization, experiment and limitations. |
| 8 | [`india-economic-data-observatory`](projects/india-economic-data-observatory/) | A data ingestion/cleaning/validation pipeline for Indian economic indicators (growth, prices, labour, government, external sector, financial system), with standardized metadata and reusable visualization functions. |
| 9 | [`india-econ`](projects/india-econ/) | A genuinely pip-installable Python package exposing a clean API (`gdp()`, `inflation()`, `unemployment()`, `trade()`, ...) for a focused, honestly-scoped subset of Indian economic data. |

See [`docs/PORTFOLIO_BUILD_ORDER.md`](docs/PORTFOLIO_BUILD_ORDER.md) for the recommended order to read/build these in, and why.

## How this portfolio is organized

This is a **monorepo of independent projects**, not one integrated application. Every project under `projects/` has its own:

```
README.md          — research question, theory, methodology, usage, limitations
LICENSE             — MIT
pyproject.toml      — installable package metadata
requirements.txt
src/<package>/      — the actual implementation
tests/              — pytest, checked against closed-form math wherever possible
docs/METHODOLOGY.md — full derivations and assumptions
docs/DATA_SOURCES.md — where real data would come from, and what's synthetic in the meantime
notebooks/          — a runnable walkthrough
app/                — a Streamlit interface, where the project calls for one
```

Nothing imports across project folders — each one clones, installs and runs on its own.

## Conceptual relationships

Although independent, the projects form a loose pipeline, each feeding ideas (not code) into the next:

```
India Economic Data Observatory
      ↓
India Economic Policy Simulator
      ↓
India Housing Affordability
      ↓
Personal Inflation Index
      ↓
India Wealth Inequality Toolkit
      ↓
Portfolio Optimization Lab
      ↓
SIP Monte Carlo
      ↓
Economics Interactive Lab
      ↓
India Econ Python Package
```

The shared theme: using data and computation to make economic questions understandable.

## A note on data and rigor

Every project in this portfolio distinguishes **Theory** (what economic theory predicts), **Data** (what real data shows, where available), **Model** (what a computational model assumes), **Simulation** (what happens under stated hypothetical assumptions) and **Empirical result** (what is actually observed). Where real, authoritative data (RBI, MoSPI, World Bank, IMF) isn't accessible in a given environment, every project ships a clearly-labelled **synthetic** or **illustrative** fallback instead — never presented as a real finding. Each project's `docs/DATA_SOURCES.md` says exactly which is which, and where to get the real thing.

None of this is investment advice, a policy recommendation, or a forecast. These are educational, computational projects for exploring how economic theory, data and simulation relate to each other.

## License

Each project carries its own MIT license (see the corresponding `LICENSE` file inside each `projects/*/` folder).
