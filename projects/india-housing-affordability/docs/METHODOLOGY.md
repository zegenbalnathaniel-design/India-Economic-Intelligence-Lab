# Methodology

## Research question

How affordable is home ownership for a given household, under explicit financing assumptions — and how does that affordability change over a multi-year horizon if house prices, incomes, and mortgage rates move at different assumed rates? This is framed as a **methodology demonstration using synthetic city baselines**, not an empirical measurement of Indian housing markets (no real city-level price/income data is bundled or accessible in this environment — see `DATA_SOURCES.md`).

## Theoretical framework

No single ratio captures housing affordability. The main candidates each capture one dimension and miss others:

- **Price-to-income ratio (PIR)** captures the up-front burden of home ownership but ignores financing terms entirely — a buyer with a 30-year loan at 6% and a buyer with a 10-year loan at 12% face very different monthly burdens at the *same* PIR.
- **EMI-to-income ratio** captures the recurring cash-flow burden but says nothing about the down payment hurdle, which can be binding even when the EMI itself is affordable (credit-constrained households can be priced out well before they are income-constrained).
- **Loan-to-value (LTV)** describes leverage and regulatory risk exposure, not affordability per se.
- None of these ratios account for *why* prices or incomes are what they are: urbanization and land-supply constraints, credit availability and underwriting standards, interest-rate cycles, income growth, and speculative demand all shift the underlying price and income paths that feed every ratio above. A full treatment of affordability would need a structural model of housing supply and demand — this project does not attempt that; it only computes transparent ratios on top of inputs the caller supplies or on the bundled synthetic baseline.

This is why the toolkit exposes several metrics side by side (see README "Economic Theory") rather than collapsing affordability into one number.

## Mathematical framework

### EMI (Equated Monthly Instalment) — standard amortizing-loan annuity formula

For a loan of principal `P`, monthly interest rate `r = annual_rate / 12`, and `n = years * 12` monthly instalments:

```
EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
```

**Derivation.** The present value of `n` equal instalments of size `EMI`, discounted at the periodic rate `r`, must equal the amount borrowed:

```
P = EMI * Σ_{t=1}^{n} (1 + r)^{-t} = EMI * [1 - (1+r)^{-n}] / r
```

Solving for `EMI`:

```
EMI = P * r / [1 - (1+r)^{-n}] = P * r * (1+r)^n / [(1+r)^n - 1]
```

**Zero-rate edge case.** At `r = 0` the formula is `0/0`. The limit as `r -> 0` (by L'Hopital or by first principles — `n` equal instalments with no interest) is `EMI = P / n`, which is what `emi()` returns explicitly for `annual_interest_rate == 0` rather than evaluating the indeterminate form.

### Total interest and interest burden

```
total_interest = EMI * n - P
interest_burden_ratio = total_interest / (total_interest + P)
```

Interest burden rises with the rate and, holding the rate fixed, rises with tenure — a longer loan leaves more principal outstanding for longer, so a larger share of every rupee repaid is interest even though the EMI itself is smaller.

### Price-to-income, mortgage-payment-to-income, loan-to-value

```
price_to_income        = house_price / annual_income
mortgage_payment_to_income = EMI_monthly / monthly_income
loan_to_value           = loan_amount / house_price
```

All three are plain ratios of caller-supplied quantities; no model is involved.

### Years to save a down payment (static version)

```
years_to_save = target_down_payment / annual_savings
```

A deliberately simple straight-line model: no return on the savings pot, no growth in the target. The scenario projector (below) relaxes both simplifications.

### Scenario projection

Given a scenario's assumed house-price growth `g_p`, income growth `g_y`, mortgage rate `m` (all held constant across the horizon in this version), savings rate `s`, down-payment fraction `d`, and a starting house price `P_0` and income `Y_0`, for year `t = 1 .. horizon`:

```
P_t = P_0 * (1 + g_p)^t
Y_t = Y_0 * (1 + g_y)^t
down_payment_target_t = d * P_t
cumulative_savings_t  = Σ_{k=1}^{t} s * Y_k
```

"Years to afford the down payment" is the smallest `t` such that `cumulative_savings_t >= down_payment_target_t`. The EMI and EMI-to-income columns in the same table are computed **as if** the household purchased at year `t`'s price, financing `(1-d) * P_t` over the configured loan tenure at rate `m` — they describe affordability-at-purchase in each hypothetical year, not one household's actual amortization path (a household that actually buys in year 3 does not also "buy" in year 7; the table shows all years for comparison).

**This is a deterministic, assumption-driven projection, not a forecast.** Three standard scenarios (conservative / baseline / optimistic) are provided as different assumption sets; the projector make no claim that any of them is more likely than another for any real city.

## Data

- **No real city-level housing-price or household-income data is bundled or fetched.** This sandbox has no outbound access to real-estate or income-survey data sources.
- `data/synthetic_city_housing_baseline.csv` is produced by `examples/generate_synthetic_city_housing.py`, a deterministic, seeded (seed=2024) generator. Per-city "income multiplier" and "price-to-income anchor" constants in that script are hand-picked to echo widely-reported, qualitative relative orderings (Mumbai and Delhi NCR least affordable, Kolkata and Ahmedabad relatively more affordable, among these eight cities) — they are **not** fitted to, or sourced from, any real statistic. Every number in the CSV is explicitly tagged `data_status = "SYNTHETIC"`.
- See `DATA_SOURCES.md` for where real data for a future version could be obtained.

## Assumptions

- EMI/amortization: fixed-rate loan, monthly compounding, no fees, no prepayment, no taxes.
- Scenario projector: constant growth rates and constant mortgage rate within a scenario (no cycles, no rate resets); savings rate applied to gross income with no consumption floor; down payment target recomputed each year against that year's house price (i.e. it assumes the household has not yet bought).
- `affordability_summary`'s default savings-rate assumption (20% of income) when the caller does not supply one is illustrative, not a claim about actual Indian household savings behaviour.

## Limitations

See the README's Limitations section for the full list. In summary: synthetic data only; no structural housing-supply/demand model; constant-rate scenario assumptions; no transaction costs, taxes, or maintenance costs; no regional cost-of-living adjustment to currency units; EMI model assumes a textbook fixed-rate amortizing loan (real-world loans vary — floating rates, part-prepayment, step-up EMIs, etc.).

## Reproducibility

- `examples/generate_synthetic_city_housing.py` is fully deterministic given `SEED` (default 2024); re-running it reproduces `data/synthetic_city_housing_baseline.csv` byte-for-byte.
- `STANDARD_SCENARIOS` in `scenarios.py` are fixed, named constants — not randomly generated — so scenario outputs are deterministic given the caller's starting inputs.
- `pytest tests/ -v` exercises every metric against hand-computed closed-form values and documented edge cases (0% interest, 100%/0% down payment, 1-year and 30-year tenures, invalid/negative inputs).
