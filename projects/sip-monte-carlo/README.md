# SIP & Wealth Accumulation Monte Carlo Simulator

A Monte Carlo simulator for Indian SIP (systematic investment plan) wealth
accumulation, modeling growing monthly contributions, fees, and inflation
to show the full *distribution* of outcomes under stated assumptions —
never a single "expected" number, and never a forecast.

## Research Question

Most SIP calculators show you one number: "invest ₹15,000/month for 20
years at 12% and you'll have ₹X." That number is a deterministic
compound-interest projection, and it quietly hides two things that matter
enormously in practice:

1. **Volatility isn't free, even if the average return stays the same.**
   Because compounding is multiplicative, a more volatile path with the
   same *arithmetic mean* return typically lands you at a *lower* final
   wealth than a steadier path — a well-known but under-communicated fact
   called variance drag / the arithmetic–geometric mean gap.
2. **The order of good and bad years matters**, not just how many of each
   there were, whenever you're adding money regularly (sequence-of-returns
   risk).

This project asks: given a parameterized set of assumptions (return,
volatility, fees, inflation, contribution growth), what does the *entire
distribution* of 20-year SIP outcomes actually look like — and how much of
its spread comes from each of these two effects?

## Why I Built This

Every SIP pitch deck I've seen shows a single smooth exponential curve.
That curve is correct arithmetic, and it is also a very incomplete picture
of what investors should expect. I wanted a tool that makes the *spread*
of outcomes — not just the midpoint — the main event, and that makes
volatility drag and sequence risk something you can see directly on a
chart rather than take on faith from a paragraph of prose. This sits
alongside the other quantitative-finance and economics projects in this
portfolio as the "what does uncertainty actually do to a long-horizon
plan" piece.

## Economic Theory

- **Growing annuity future value.** The deterministic core generalizes the
  standard compound-interest SIP formula to annually-stepping
  contributions, an initial lump sum, and a continuous fee drag — with an
  exact closed-form solution (see Methodology).
- **The arithmetic–geometric mean gap (volatility drag).** For a
  multiplicative compounding process, the typical (geometric-mean) growth
  rate is below the arithmetic mean by roughly `volatility² / 2`. Two SIPs
  with identical *average* annual returns but different volatility will,
  more often than not, leave the more volatile one at lower *typical*
  (median) wealth — even though its *average* (mean) wealth may be similar
  or even slightly higher, pulled up by a longer right tail.
- **Sequence-of-returns risk.** Holding the exact multiset of annual
  returns fixed, the *order* in which they occur changes the final wealth
  whenever there are ongoing contributions, because later returns apply to
  a larger accumulated base than earlier ones.
- **The real/nominal distinction.** Returns compound in nominal terms;
  purchasing power is what nominal wealth is worth after inflation. The
  two are kept conceptually and computationally separate throughout.

## Methodology

Full derivations, exact equations, and stated assumptions are in
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md). In brief:

1. Monthly returns are drawn from a lognormal distribution whose *annual*
   mean and volatility are moment-matched to the user's inputs exactly,
   then decomposed into 12 independent monthly draws (an exact, not
   approximate, decomposition).
2. Fees are a continuous drag subtracted from the monthly growth rate.
3. Contributions step up once per year by a chosen growth rate and are
   added at the end of each month, after that month's return is applied.
4. At zero volatility, the simulator reduces to — and is numerically
   verified against — the exact closed-form future value of a growing
   annuity.
5. Nominal wealth at every time step is deflated by the stated inflation
   rate to produce a parallel real-wealth series.
6. Percentiles (p10/p25/p50/p75/p90) and the mean of wealth are recorded
   at *every* month across all simulated paths, not just at the end.

**This produces a distribution, never a forecast.** Every output —
every chart, every percentile, every probability — describes "what
happens across many randomly-generated paths under the assumptions you
chose," not a prediction of what will happen to any real investment, and
none of it is investment advice.

## Data

**This project uses no external data.** It is a purely parameterized
numerical simulation: you supply assumptions (expected return, volatility,
fees, inflation, contribution growth), and the simulator shows you the
distribution of outcomes those assumptions imply. There is nothing to
fetch, nothing to calibrate against a historical index, and nothing that
could go stale.

The sliders ship with illustrative default values, clearly labeled as such
and overridable on every single one:

| Assumption | Illustrative default | Not a forecast of... |
|---|---|---|
| Expected annual return | 12%/year | any specific index, fund, or asset class |
| Annual volatility | 18%/year | any specific index's historical standard deviation |
| Annual fee / expense ratio drag | 1.0%/year | any specific fund's actual expense ratio |
| Annual inflation | 5%/year | India's actual future CPI inflation |
| Contribution step-up | 5%/year | your actual future income growth |

Change any of these in the sidebar; the entire distribution recomputes.

## Results / Demonstration

Running the simulator with the illustrative defaults (₹15,000/month,
20-year horizon, 12% expected return, 18% volatility, 5% contribution
step-up, 1% fee drag, 5% inflation, 5,000 paths) produces a wide fan of
outcomes, not a single number — open the app to see the live chart. Two
properties hold up under the model (and are enforced by the test suite,
not just asserted in prose):

- **Volatility drag is visible and directional.** At 25-year horizon,
  12% expected return, holding the mean fixed, raising volatility from 5%
  to 30% pulls the *median* final value down sharply while the *mean*
  stays roughly flat (or drifts slightly up, from lognormal skew) —
  exactly the arithmetic/geometric mean gap described above.
- **Fees compound against you.** Raising the fee assumption from 0.5% to
  2.5%/year, holding everything else fixed, strictly lowers both the mean
  and the median final value over a 20-year horizon.

The **Sequence of Returns Risk** page shows a small worked example: the
same eight annual returns, same arithmetic mean, run forward and in
reverse order over the same contribution stream — producing two different
final values from numbers that average out identically.

## How It Works

- `src/sip_monte_carlo/closed_form.py` — exact deterministic growing-annuity
  future value, used as a correctness reference.
- `src/sip_monte_carlo/engine.py` — the Monte Carlo engine: lognormal
  monthly return model, fee drag, growing contributions, inflation
  deflation, percentile paths, and target-probability queries.
- `src/sip_monte_carlo/sequence_risk.py` — the standalone
  sequence-of-returns-risk demonstration (forward vs. reversed return
  order).
- `app/Home.py` + `app/pages/` — the Streamlit app: sliders for every
  input, a percentile fan chart, a probability-of-target metric, a
  dedicated sequence-of-returns-risk page, and a methodology page.
- `tests/` — pytest suite covering the required correctness properties
  (see Limitations/Future Work and `docs/METHODOLOGY.md`), edge cases, and
  invalid-input handling.
- `notebooks/01_sip_walkthrough.ipynb` — a full worked example (₹15,000/
  month for 20 years) including the sequence-of-returns demo.

## Installation

```bash
cd projects/sip-monte-carlo
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
# or, for an editable install of just the package:
pip install -e .
```

Requires Python ≥ 3.10.

## Usage

**Run the Streamlit app:**

```bash
streamlit run app/Home.py
```

**Use the engine directly in Python:**

```python
from sip_monte_carlo.engine import run_simulation

result = run_simulation(
    monthly_contribution=15_000,
    duration_years=20,
    expected_annual_return=0.12,
    annual_volatility=0.18,
    annual_inflation=0.05,
    contribution_growth_rate=0.05,
    annual_fee_rate=0.01,
    n_paths=5_000,
    seed=42,
)
print(result.final_summary())
print("P(reach ₹1 crore):", result.probability_of_reaching(10_000_000))
```

**Run the tests:**

```bash
python3 -m pytest tests/ -q
```

## Examples

See `notebooks/01_sip_walkthrough.ipynb` for a complete walkthrough:
running the simulator, reading the percentile summary, computing the
probability of reaching a target corpus, and reproducing the
sequence-of-returns-risk demonstration. The notebook is also where to look
for ready-to-adapt code if you want to script a batch of scenario
comparisons outside the Streamlit app.

## Limitations

- Returns are i.i.d. lognormal by assumption — no autocorrelation, regime
  switching, fat tails beyond what lognormal already implies, or modeling
  of real historical market cycles.
- All parameters (return, volatility, fees, inflation, contribution
  growth) are held constant across the simulated horizon.
- Fees are a single flat annual rate; Indian tax treatment (STCG/LTCG on
  equity mutual funds, etc.) is not modeled.
- The sequence-of-returns demonstration uses a small, hand-picked set of
  returns for pedagogical clarity, not a simulation of realistic return
  sequences.
- No external data source is used or needed; nothing here is calibrated to
  any real fund, index, or historical period.

## Future Work

- Add a bootstrap/historical-block-resampling mode (optional, clearly
  labeled) as an alternative to the i.i.d. lognormal assumption, for users
  who want to see sequence effects drawn from real historical blocks
  rather than hand-picked examples.
- Model Indian capital-gains tax treatment as an optional drag on
  realized/final returns.
- Allow correlated, multi-fund portfolios (feeding into glide-path /
  asset-allocation-over-time scenarios) rather than a single blended
  return/volatility assumption.
- Add a goal-based "required monthly SIP" solver: given a target corpus and
  horizon, back out the contribution needed to hit it with a chosen
  probability.

## Sources

This project does not use external data sources — see
[Data](#data) above. The formulas implemented (growing annuity future
value, lognormal moment matching, the arithmetic–geometric mean
relationship, sequence-of-returns risk) are standard results in
quantitative finance and actuarial mathematics; derivations are worked out
from first principles in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)
rather than cited from any single textbook.

## License

MIT — see [`LICENSE`](LICENSE).
