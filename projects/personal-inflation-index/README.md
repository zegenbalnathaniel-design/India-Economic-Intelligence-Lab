# Personal Inflation Index

A toolkit and Streamlit app for building your own household spending basket and computing a personalized Laspeyres-style inflation index, so you can see how it can diverge from a single national CPI figure.

## Research Question

**Why can the inflation experienced by an individual differ from official CPI inflation?**

A national Consumer Price Index summarizes price changes across millions of households into one number, built from one basket and one set of expenditure weights describing an "average" household. No real household is average. This project makes that gap concrete: it lets you plug in your own category weights and prices (or illustrative example data) and computes a transparent, fixed-basket index you can directly compare against a reference series.

## Why I Built This

I kept running into the same disconnect: the headline CPI print would say inflation was mild, yet the categories I actually spend the most on — rent, transport, school and medical costs — felt like they'd moved a lot more than that. That gap isn't a contradiction or a conspiracy; it's what you'd expect once you take seriously that a national index is an average over very different households. I wanted a small, honest tool that makes the *mechanism* behind that gap visible and computable, using nothing more exotic than the same fixed-basket index formula statistical agencies themselves use — applied to a basket that's actually mine (or, for anyone trying it out, a clearly labeled example basket) instead of the nation's.

## Economic Theory

A consumer price index tracks the cost of a fixed basket of goods over time relative to a base period. Three ingredients define it: **categories** of spending, **expenditure weights** (the share of a budget each category gets in the base period), and each category's **price level** over time. The classic **Laspeyres index** freezes the basket's quantities (equivalently, its weights) at the base period and lets only prices move — this is simple, transparent, and exactly reproducible, but it means the index cannot capture consumers substituting away from goods that get relatively more expensive, a well-known limitation called **substitution bias**.

Crucially, **household heterogeneity** — differences in income (poorer households spend a much larger budget share on necessities like food, per Engel's Law), urban vs. rural living, and regional price variation — means that even a perfectly computed national average index describes no single household exactly. Two households can face the very same published CPI figure while experiencing very different actual cost-of-living changes, purely because of what they buy and where. See `docs/METHODOLOGY.md` for the full derivation and economic reasoning.

## Methodology

This project implements the textbook fixed-basket Laspeyres formula:

```
I_t = 100 * sum_i( w_i * (P_i,t / P_i,0) )
```

where `w_i` are normalized base-period expenditure weights, `P_i,0` is a category's base-period price, and `P_i,t` is its current-period price. An unchanged basket scores exactly 100.0 by construction. The core module also provides a time-series version (computing the index across every period in a price panel) and a comparison function (computing the point and percentage gap against a reference series). Full derivation, assumptions, and limitations: `docs/METHODOLOGY.md`.

## Data

**No data shipped with this project is real, officially published CPI data.** This project was built without internet access to MoSPI's publications, and the choice made here is to be explicit about that rather than present placeholder numbers as fact:

- `src/personal_inflation/example_data.py` contains `EXAMPLE_ILLUSTRATIVE_WEIGHTS` — hand-picked, round-number **illustrative example weights**, loosely shaped like commonly reported CPI category splits but **not** MoSPI's published weights.
- `data/synthetic_category_price_index.csv` is **entirely synthetic**: a deterministic, seeded random-walk simulation (see `examples/generate_synthetic_data.py`, seed `20240601`), regenerable byte-for-byte from that script. It contains no real price observations.
- The `official_cpi_reference` column in that same file is **not** a real CPI series — it is a weighted blend of the synthetic category columns, used only to give the comparison feature something to plot against.

See `docs/DATA_SOURCES.md` for exactly where to obtain the real, official MoSPI CPI series and category weights (with the standard source/provider/URL/definition/unit/frequency/coverage/transformations/limitations table), and treat any specific official number you recall as "commonly reported, requires independent verification against the current MoSPI publication" unless you have the primary document in front of you.

## Results / Demonstration

Using the bundled illustrative weights and synthetic price panel, `notebooks/01_building_a_personal_index.ipynb` walks through computing a personal index over a simulated 5-year monthly panel and shows two different hypothetical household baskets (food-heavy vs. education-heavy) diverging differently from the same comparison series — purely as a result of different expenditure weights applied to the same underlying price moves. **This is a demonstration of the methodology, not an empirical finding about real Indian household inflation.** The Streamlit app lets you reproduce the same exercise interactively with your own weights and, optionally, your own uploaded price data.

## How It Works

1. `src/personal_inflation/index.py` implements `laspeyres_index` (two-period), `personal_index_time_series` (a full panel over time), and `compare_to_reference` (gap vs. a reference series), plus `normalize_weights` and clear, tested error handling for missing prices, negative/zero prices, and unnormalized weights.
2. `examples/generate_synthetic_data.py` deterministically generates `data/synthetic_category_price_index.csv`.
3. The Streamlit app (`app/Home.py` + `app/pages/1_Basket_Builder.py`) wraps the same functions in a basket-builder UI: sliders that renormalize to 100%, a choice between the bundled synthetic series or your own CSV upload, and a chart comparing your personal index to the comparison series.
4. `tests/` verifies the formula against hand-computed examples, the "unchanged basket = 100" invariant, weight normalization, the "faster-growing category weighted more heavily yields a higher index" property, and invalid-input handling.

## Installation

```bash
cd projects/personal-inflation-index
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

Or, as an installable package (editable):

```bash
pip install -e .
```

## Usage

**As a library:**

```python
from personal_inflation.index import laspeyres_index

weights = {"food": 0.5, "housing": 0.3, "transport": 0.2}
base_prices = {"food": 100.0, "housing": 200.0, "transport": 50.0}
current_prices = {"food": 110.0, "housing": 220.0, "transport": 40.0}

laspeyres_index(base_prices, current_prices, weights)  # -> 104.0
```

**The Streamlit app:**

```bash
streamlit run app/Home.py
```

Then open the "Basket Builder" page from the sidebar, adjust the weight sliders, and either use the bundled synthetic example series or upload your own CSV of category prices over time.

**Regenerating the synthetic demo data:**

```bash
python3 examples/generate_synthetic_data.py
```

**Running the tests:**

```bash
python3 -m pytest tests/ -q
```

## Examples

See `notebooks/01_building_a_personal_index.ipynb` for a full worked walkthrough: a hand-verified sanity check, loading the synthetic panel, computing a personal index over time, comparing it to the illustrative reference series, and contrasting two differently-weighted hypothetical households.

## Limitations

- **Substitution bias**: the Laspeyres formula cannot capture consumers substituting away from relatively more expensive categories, so it tends to overstate true cost-of-living increases relative to an index that lets the basket adjust.
- **Basket staleness**: weights fixed at an old base period go out of date as real spending patterns shift.
- **No geographic disaggregation**: each category is a single price series; there's no built-in urban/rural or state-level breakdown (a user would need to supply their own local price data).
- **Category granularity**: nine broad categories is a simplification; users can split categories further themselves.
- **No seasonal adjustment** in the time-series function.
- **All bundled weights and prices are illustrative/synthetic**, not empirical findings (see Data, above).

## Future Work

- Support importing real MoSPI sub-group CPI series (once obtained per `docs/DATA_SOURCES.md`) as a genuine comparison series, with explicit provenance metadata attached to every uploaded series.
- Add a Paasche and/or Fisher (superlative) index option alongside Laspeyres, to let users directly see the size of substitution bias in their own basket.
- Let users split categories into sub-items with their own weights and prices, rather than treating each top-level category as a single price series.
- Add regional/urban-rural price-series support so a user could compare "my basket at my local prices" against "my basket at the national-average price series" as a second, independent source of divergence.

## Sources

- Statistics Ministry (MoSPI), Government of India — official CPI publications: https://mospi.gov.in/ (see `docs/DATA_SOURCES.md` for the full sourcing table; no MoSPI data is bundled with this repository).
- Laspeyres, Paasche, and index-number theory generally — standard treatment in any introductory price-statistics or index-number-theory reference; not reproduced verbatim here, summarized in `docs/METHODOLOGY.md`.

## License

MIT — see `LICENSE`.
