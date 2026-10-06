# Methodology

## Research question

1. **Theoretical**: given a simplified open-economy AD/AS system, how do fiscal and monetary policy levers transmit to GDP, inflation, unemployment, the fiscal deficit, public debt and the exchange rate?
2. **Empirical**: has Indian bank financial performance (iBFPI) moved systematically with the RBI repo rate since 2018, and does that relationship differ by rate regime (rising/falling/stable)?

These two questions are answered by two **independent modules** in this repo — the model's output is never dressed up as the empirical module's finding, or vice versa.

## Theoretical framework

Textbook open-economy Keynesian cross (goods-market equilibrium) + expectations-augmented Phillips curve + Okun's law + standard government debt dynamics + a Taylor-rule-style monetary reaction function. Each piece is individually standard in intermediate macroeconomics; combining them into one small simulatable system is this project's contribution, not any single equation.

## Mathematical framework

**Equilibrium output** (see `macro_model.py` docstring for full derivation):

```
Yd = (1-τ)Y
C  = c0 + c1·Yd
I  = i0 - i1·r + i2·invest_confidence
X  = x0 + x1·foreign_demand - x2·exchange_gap
M  = m0 + m1·Y + m2·oil_price/exchange_rate
Y  = C + I + G + X - M
  ⇒  Y* = A / [1 - c1(1-τ) + m1]
```

**Fiscal multiplier**: `dY/dG = 1 / [1 - c1(1-τ) + m1]` — the reciprocal of the denominator above. Import leakage (`m1`) and taxation (`τ`) both shrink it relative to the closed-economy multiplier `1/(1-c1)`.

**Crowding out**: when the "endogenous policy rate" toggle is on, the policy rate follows a Taylor rule `i = r* + π_target + a_π(π-π_target) + a_y·output_gap`. A fiscal expansion that raises `π` and the output gap therefore raises `i`, which lowers `I` via `-i1·r` — the model's crowding-out channel. With the toggle off, the policy rate is fixed by the user and there is no crowding out through this channel (by construction, to make the mechanism's presence/absence explicit rather than implicit).

**Phillips curve**: `π = π_e + κ·output_gap + λ_oil·oil_price_%Δ`.

**Okun's law**: `u = u_natural - okun·output_gap`, floored at zero.

**Debt dynamics**: `b_t = b_{t-1}·(1+i_debt)/(1+g_nominal) - primary_balance_ratio_t`. Debt-to-GDP falls when nominal growth exceeds the interest rate on debt and/or the government runs a primary surplus — the standard `(i-g)` debt-sustainability condition.

**Exchange rate**: `e_t = e_{t-1}·[1 - k·(i_domestic - i_foreign)·0.1]` — a simplified heuristic in the *direction* implied by interest-rate-parity intuition (higher domestic rates attract capital, appreciate the currency), **not** a solved rational-expectations UIP model and not a balance-of-payments model. See "What this model is not" below.

**iBFPI (empirical)**: robust z-score per indicator per bank, `Z* = D·(X - median(X)) / (1.4826·MAD(X))`, averaged equally across five indicators; see `monetary_transmission.py` for the full specification (identical to the India-Wealth-Inequality-Toolkit's banking module, since both descend from the same accompanying research).

## Data

- **Macro simulator**: zero external data; see `docs/DATA_SOURCES.md` for calibration provenance notes.
- **Empirical module**: illustrative synthetic bank panel + an approximated RBI repo-rate path; see `docs/DATA_SOURCES.md`.

## Assumptions

- Annual compounding and one decision period per "year" in the macro simulator (no intra-year dynamics).
- Linear behavioral equations throughout (no explicit non-linearities, e.g. no zero-lower-bound constraint on the policy rate).
- Phillips-curve expected inflation is a fixed parameter, not model-consistent (no rational-expectations loop).
- Independent, additive shocks — the scenario builder changes one input path at a time; the model does not know which combinations of shocks are jointly plausible.

## What this model is not

- Not a forecasting model — it is not fit to Indian GDP/inflation/employment data by any estimation procedure.
- Not a DSGE model — no micro-founded optimization, no explicit expectations formation beyond one fixed parameter.
- Not a balance-of-payments or UIP model — the exchange-rate rule captures a textbook *direction*, not a solved equilibrium.
- Not a replacement for the RBI's or the Ministry of Finance's own models, which incorporate vastly more structure and real-time data.

## Limitations

Six-to-ten-equation models cannot capture: supply-side shocks beyond oil, structural breaks, sudden-stop capital-flow dynamics, heterogeneous agents, sectoral composition, informal-sector dynamics (large in India), or a zero-lower-bound/unconventional-policy regime. The empirical module inherits the limitations documented in the India Wealth Inequality Toolkit's banking methodology (correlation ≠ causation, small rate-regime subsamples, uncorrected autocorrelation, illustrative data pending real bank disclosures).

## Reproducibility

- Every `CalibrationParams` field and every `ScenarioInputs` field is an explicit argument with a stated default — no hidden state.
- `python -m policy_simulator.build_illustrative_data` regenerates the empirical module's bank panel deterministically (seed=42).
- `pytest tests/ -v` checks the macro model against closed-form algebra (e.g. the fiscal multiplier) and qualitative-direction tests (higher rates lower GDP, positive output gap lowers unemployment), and checks the empirical module against manual recomputation.
