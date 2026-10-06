# Economics Interactive Lab

An interactive, open-source teaching platform that turns standard microeconomics, macroeconomics, and finance diagrams into small, mathematically correct models you can actually experiment with.

## Research Question

Can a small set of interactive, mathematically correct modules make standard micro/macro/finance theory tangible rather than diagrammatic?

## Why I Built This

I kept noticing the same gap between how economics is taught and how it's understood: a textbook shows one static supply-and-demand diagram, states that a tax wedge "splits based on elasticity," and moves on. The algebra behind that claim is simple, but almost nobody who reads the diagram ever actually drags a slider and watches the split change in front of them. I wanted a lab, not a textbook page -- a place where every curve you see is backed by a real formula, every number is something *you* chose, and every module tells you plainly which part is eternal mathematics and which part is just today's illustrative input.

## Economic Theory

**Microeconomics**
- **Demand & supply equilibrium**: linear curves `Qd = a - bP`, `Qs = c + dP`, solved algebraically for `P*`, `Q*`.
- **Price elasticity of demand**: the exact point-elasticity formula `PED = (dQ/dP)(P/Q)`.
- **Tax incidence**: a per-unit tax wedge between consumer and producer price, with the burden split exactly by the two curves' relative slopes, plus consumer surplus / producer surplus / deadweight loss from the standard triangle-area formulas.
- **Price ceilings & floors**: the resulting shortage or surplus quantity when a legal price diverges from the market-clearing price.

**Macroeconomics**
- **Aggregate demand / aggregate supply**: a deliberately small two-linear-curve diagram in (output, price level) space, with one-off demand and supply shocks.
- **Fiscal (Keynesian) multiplier**: the simple closed-economy multiplier `1/(1-MPC)`, derived from summing the geometric series of spending rounds.
- **Solow-style growth**: capital-per-worker accumulation `k_{t+1} = k_t + s·k_t^α - δ·k_t` and its closed-form steady state.

**Finance** (kept introductory -- see *Future Work* and the sibling projects below for depth)
- **Compound interest & present value**: the standard lump-sum and ordinary-annuity future-value formulas, and present value as their inverse.
- **Two-asset diversification**: the two-asset portfolio-variance formula, showing risk fall as correlation falls.

## Methodology

Every equation, parameter, and assumption behind each module is written out in full in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Data

This project uses **no external data**. Every module is a closed-form or simulated toy model whose inputs are numbers you choose on sliders for the purpose of the demonstration -- never estimates of, or claims about, any real market, economy, or financial instrument. Where a module states a result (an equilibrium price, a multiplier, a deadweight loss), that result is a mathematically exact consequence of the equation and the numbers you picked, not an empirical finding.

## Results / Demonstration

Run the app (see *Installation*/*Usage* below) and open any module page. Each page follows the same sequence: concept, equation, interactive controls, a live chart, a specific experiment to try, a plain-English explanation, and the module's limitations. For example, on the Tax Incidence page, fixing the tax amount and making demand flatter (less price-responsive) relative to supply visibly shifts a larger share of the tax burden onto consumers -- exactly as the closed-form burden-split formula `d/(b+d)` predicts.

## How It Works

The project is built around one extensible abstraction, `EconModule` (in `src/econ_lab/registry.py`):

```
EconModule(
    key, domain, title,
    concept,                # markdown explanation
    equation,                # the math, as LaTeX
    compute,                 # pure-Python function -- the real math, no UI
    render_controls,         # Streamlit widgets -> kwargs for compute()
    render_visualization,    # Streamlit/Plotly chart from inputs + results
    experiment, explanation, limitations,
)
```

A module calls `register_module(EconModule(...))` once, at import time, to add itself to a global registry. The Streamlit app and the test suite never import a specific module file by name -- they discover every module purely through `econ_lab.registry.all_modules()` / `modules_by_domain()`. That means a future contributor adds a brand-new module by creating **one new file** under `src/econ_lab/modules/`, adding **one import line** to `src/econ_lab/modules/__init__.py`, and (optionally) **one thin page file** under `app/pages/` -- no existing file needs to change.

Because `compute` is plain Python with no Streamlit dependency, every module's math is independently callable and testable from a script, a notebook, or `pytest` -- see `notebooks/01_modules_from_scratch.ipynb` for examples that never touch the UI at all.

```
src/econ_lab/
├── registry.py          # the EconModule dataclass + register_module() + the registry
└── modules/
    ├── micro_supply_demand.py
    ├── micro_elasticity.py
    ├── micro_tax_incidence.py
    ├── micro_price_controls.py
    ├── macro_ad_as.py
    ├── macro_multiplier.py
    ├── macro_growth.py
    ├── finance_compound_interest.py
    └── finance_diversification.py
app/
├── Home.py               # overview / navigation page
├── common.py             # render_module_page(): the shared concept->...->limitations layout
└── pages/                # one thin page per module, built on common.render_module_page
```

## Installation

```bash
git clone <this repo>
cd economics-interactive-lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the app:

```bash
streamlit run app/Home.py
```

Use a module's math directly, with no UI at all:

```python
from econ_lab.registry import get_module

module = get_module("micro_tax_incidence")
result = module.run(a=100.0, b=2.0, c=10.0, d=1.5, tax=10.0)
print(result["consumer_burden_share"], result["deadweight_loss"])
```

Run the tests:

```bash
pytest tests/ -v
```

## Examples

See `notebooks/01_modules_from_scratch.ipynb` for a walkthrough of several modules' pure math (equilibrium, elasticity, the multiplier, compound interest) called directly, without Streamlit.

## Limitations

- This is a **teaching lab of toy models**, not an empirical or forecasting tool. Every equation is exactly true given its assumptions (linear curves, a constant MPC, a constant periodic rate, a fixed correlation); every input number is illustrative and chosen for the demo, never an estimate of a real market, economy, or asset.
- The microeconomics modules assume perfectly linear demand and supply over the whole displayed range; real curves are rarely linear everywhere, and these modules ignore income effects, substitutes/complements, and dynamic adjustment speed to a new equilibrium.
- The macro modules are intentionally *small*: the AD/AS module has no money market or expectations, and the fiscal multiplier module is the closed-economy case with no tax or import leakage and no interest-rate response. See the `india-economic-policy-simulator` sibling project for a considerably richer macro model (open-economy multiplier, monetary transmission, Phillips curve, debt dynamics).
- The finance modules are deliberately introductory: compound interest/PV assumes a constant periodic rate, and the diversification demo covers only the two-asset case with no expected-return or optimization layer. See the `portfolio-optimization-lab` sibling project for full Markowitz mean-variance optimization and the `sip-monte-carlo` sibling project for simulating contribution schedules under return uncertainty.
- The Solow-style growth module ignores population growth, technological progress, and the distinction between physical and human capital.

## Future Work

Modules from a larger wishlist not yet implemented:

- **Microeconomics**: monopoly pricing and the markup/deadweight-loss comparison to perfect competition; externalities and Pigouvian taxes/subsidies; a simple public-goods/free-rider demo; a basic game-theory module (prisoner's dilemma payoff matrix with Nash equilibrium).
- **Macroeconomics**: a simple IS-LM diagram; an open-economy exchange-rate module; a basic Phillips-curve/inflation-expectations module distinct from the sibling policy simulator's fuller version.
- **Finance**: bond pricing and duration; a simple options payoff diagram (calls/puts at expiry); a basic CAPM/beta illustration.
- A "compare two scenarios side by side" view generalized across every module, not just the AD/AS and tax-incidence pages that currently show it implicitly.

## Sources

This project uses no external data sources. The equations implemented are standard results from introductory microeconomics, macroeconomics, and finance (linear supply-and-demand, point elasticity, tax-incidence and surplus/deadweight-loss geometry, AD/AS, the Keynesian multiplier, the Solow growth model, and standard time-value-of-money and two-asset portfolio-variance formulas), as commonly presented in undergraduate economics and finance textbooks.

## License

MIT -- see [`LICENSE`](LICENSE).
