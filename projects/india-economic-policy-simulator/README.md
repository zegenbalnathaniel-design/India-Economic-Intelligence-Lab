# India Economic Policy Simulator

An interactive, pedagogical macroeconomic simulator for exploring Indian fiscal and monetary policy trade-offs, paired with an empirical bank-performance/repo-rate transmission analysis.

## Research Question

What can a simplified computational model teach us about the trade-offs involved in Indian fiscal and monetary policy — and separately, what does the actual data show about how bank financial performance has moved with the RBI repo rate since 2018?

## Why I Built This

Macroeconomic transmission mechanisms (fiscal multipliers, crowding out, the Phillips curve, debt dynamics) are usually taught as static diagrams. I wanted a small system I could actually run — vary one input, hold others fixed, and watch the transmission happen across every tracked variable at once — while keeping the empirical question (what actually happened to bank performance as rates moved) clearly separate from the theoretical model.

## Economic Theory

- **Aggregate demand / open-economy multiplier**: `Y = C + I + G + X − M`, with the fiscal multiplier `dY/dG = 1/[1 − c₁(1−τ) + m₁]` shrinking as import leakage or the tax rate rises.
- **Monetary transmission / crowding out**: policy rate → real rate → investment; an optional Taylor-rule reaction function lets fiscal expansion raise rates endogenously, crowding out investment.
- **Phillips curve**: inflation responds to the output gap and an oil cost-push term.
- **Okun's law**: unemployment falls with a positive output gap.
- **Debt dynamics**: the standard law of motion `b_t = b_{t-1}·(1+i)/(1+g) − primary_balance_ratio_t`.
- **iBFPI (empirical)**: a robust-z-score composite of five bank financial indicators, correlated against the repo rate — adapted from the author's accompanying research.

## Methodology

Full equations, parameters and derivations: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Data

- The macro simulator uses **no external data** — it is a closed system of equations with illustrative, overridable calibration parameters (see `CalibrationParams` in `macro_model.py`). These are *not* econometric estimates.
- The empirical module uses an **illustrative synthetic** bank panel (`data/processed/bank_panel.csv`) and an approximate RBI repo-rate series — see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for what's real, what's illustrative, and where to get the real series.

## Results / Demonstration

This is a **demonstration**, not a forecast or an empirical finding about the Indian economy: running the scenario builder shows what the model's equations imply under chosen inputs. The empirical module's correlation output, by contrast, is a real (if small-sample) statistical result — on illustrative data until real bank disclosures are substituted in.

## How It Works

```
src/policy_simulator/
├── macro_model.py            # the AD/AS-style simulator (theory)
├── monetary_transmission.py  # iBFPI construction (empirical)
├── data_loaders.py           # loads the illustrative bank panel / repo rate
└── build_illustrative_data.py
```

## Installation

```bash
git clone <this repo>
cd india-economic-policy-simulator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```python
from policy_simulator.macro_model import CalibrationParams, ScenarioInputs, constant_path, compare_scenarios

params = CalibrationParams()
baseline = constant_path(ScenarioInputs(), years=8)
shock = constant_path(ScenarioInputs(government_spending=30.0), years=8)
result = compare_scenarios(baseline, shock, params)
print(result[["period", "gdp_baseline", "gdp_shock", "gdp_delta"]])
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

See `app/pages/1_Scenario_Builder.py` for a full baseline-vs-shock walkthrough with every input exposed as a slider.

## Limitations

- This is a **teaching model** — six to ten equations calibrated by hand, not estimated from Indian time series. Treat every output as "what this model's assumptions imply," never as a GDP/inflation forecast.
- The exchange-rate update rule is a simplified heuristic (direction-only), not a rigorous uncovered-interest-parity or balance-of-payments model.
- No explicit expectations formation beyond a fixed `expected_inflation` parameter — no forward-looking rational-expectations channel.
- The empirical module's correlations do not correct for autocorrelation in a quarterly series and are not causal estimates; see `docs/METHODOLOGY.md`.
- Regime classification (rising/falling/stable rates) uses an arbitrary ±25bp threshold — results are sensitive to this choice.

## Future Work

- Sensitivity-analysis panel (tornado chart) ranking which parameter most moves a given output.
- A simple VAR or local-projections estimate on real Indian macro time series, kept as a clearly-separate empirical complement to the theoretical model.
- Stochastic shocks (Monte Carlo over the macro model) to show a distribution of outcomes rather than one path.

## Sources

- RBI Database on Indian Economy (DBIE) — repo rate history: https://dbie.rbi.org.in
- MoSPI — GDP, inflation aggregates (for calibration context, not estimation).
- Author's accompanying research on wealth accumulation in India (BFPI methodology adaptation).

## License

MIT — see [`LICENSE`](LICENSE).
