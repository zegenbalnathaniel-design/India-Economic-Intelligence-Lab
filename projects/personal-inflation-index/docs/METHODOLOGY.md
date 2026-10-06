# Methodology

## Research question

**Why can the inflation experienced by an individual household differ from
the official CPI inflation rate?**

Official inflation statistics (like India's Consumer Price Index,
published monthly by MoSPI) summarize price changes across millions of
households into a single national number. That number is a weighted
average built from a basket of goods and a set of expenditure weights
that describe an *average* household. No real household is average: its
basket, its budget shares, and the prices it actually pays all differ
from the national aggregate, sometimes sharply. This project builds the
arithmetic needed to make that gap concrete and explorable, using a
transparent fixed-basket (Laspeyres) index that anyone can recompute with
their own numbers.

## Theoretical framework

A consumer price index tracks the cost, over time, of purchasing a fixed
"basket" of goods and services, relative to the cost of that same basket
in a base period. The basket is described by:

- a set of **categories** (food, housing, transport, etc.), and
- **expenditure weights** `w_i`, the share of total spending a household
  devotes to category `i` in the base period.

Each category also has a **price level** `P_i,t` observed over time
(often itself an aggregate of many sub-items, e.g. "food" bundles rice,
vegetables, pulses, etc. — this project treats each category as a single
price series for simplicity, which a user is free to disaggregate
further).

### The Laspeyres formula

This project implements the **Laspeyres price index**, one of the two
classic bilateral index number formulas (the other being the Paasche
index, which uses *current*-period weights instead):

```
I_t = 100 * sum_i ( w_i * (P_i,t / P_i,0) )
```

- `P_i,0` — category `i`'s price in the base period
- `P_i,t` — category `i`'s price in the current period
- `w_i`   — category `i`'s base-period expenditure weight, normalized so
            that `sum_i w_i = 1`
- `I_t`   — the index value in period `t`, on a base of 100

**Intuition:** `P_i,t / P_i,0` is the price relative for category `i` —
how much more (or less) expensive that category has become since the
base period. The index is simply the expenditure-weighted average of
those price relatives, rescaled to 100. If nothing changed in price,
every relative is 1 and `I_t = 100 * sum_i w_i * 1 = 100`. If everything
doubled in price, `I_t = 200`.

**Derivation / equivalent form.** The Laspeyres index can equivalently be
written as the ratio of two baskets' costs, both evaluated with
base-period *quantities* `Q_i,0`:

```
I_t = 100 * [ sum_i (P_i,t * Q_i,0) ] / [ sum_i (P_i,0 * Q_i,0) ]
```

Since `w_i = (P_i,0 * Q_i,0) / sum_j (P_j,0 * Q_j,0)` by definition, this
is algebraically identical to the weights-and-relatives form above; this
project uses the weights form because household expenditure *shares* are
far easier for a person to estimate than absolute quantities purchased.

### Key assumption: the fixed basket, and substitution bias

The defining feature of a Laspeyres index — and its central limitation —
is that the **basket (the quantities, equivalently the weights) is frozen
at the base period** and never updated as prices move. In reality,
households shift spending away from goods that get relatively more
expensive and toward substitutes that get relatively cheaper. Because the
Laspeyres formula holds quantities fixed, it does not capture that
substitution, and so it **systematically overstates** the true cost-of-
living increase relative to an index that let the basket adjust (like a
Paasche or superlative index). This is known as **substitution bias**,
and it is one of the best-documented phenomena in index number theory
(it is a major reason statistical agencies periodically update CPI
basket weights and sometimes blend formulas).

Two further, related limitations:

- **Basket staleness.** Even without substitution bias, a basket fixed at
  an old base period (e.g. built from a household expenditure survey run
  years earlier) can simply be out of date relative to how people spend
  today — new categories of spending (certain digital services, say)
  may be entirely absent, while categories that have shrunk in importance
  are still weighted as if they hadn't.
- **A single national basket vs. many different households.** Even a
  perfectly up-to-date, substitution-adjusted *national* index describes
  one representative basket. It cannot, by construction, describe the
  basket of any one household, which is the heart of the research
  question below.

## Why household heterogeneity drives a wedge between personal and official inflation

The official CPI's expenditure weights are built from an **average**
across a large, diverse population. Three sources of heterogeneity make
that average a potentially poor description of what any specific
household experiences:

1. **Income-driven differences in budget shares (Engel's Law).** Poorer
   households devote a much larger share of their budget to food and
   other necessities than richer households do, simply because
   necessities do not scale down proportionally with income the way
   discretionary spending does. If food prices rise faster than, say,
   recreation or education prices in a given period, poorer households —
   who are more food-weighted — experience *higher* effective inflation
   than the national average suggests, and vice versa in the opposite
   price-growth scenario. The national CPI weight for food reflects the
   *population-wide* average budget share, which sits between the shares
   of richer and poorer households, so it systematically understates the
   food-price exposure of the poor and overstates it for the rich.

2. **Urban vs. rural consumption patterns and price levels.** Housing
   costs, transport options, and even the prices of identical goods
   differ substantially between urban and rural markets. A national index
   (or even separate urban/rural sub-indices, which MoSPI does publish)
   still averages over within-group variation that a single household
   does not experience as an average — they experience their own local
   prices.

3. **Regional price variation.** India is geographically and
   economically large; prices for the same good can differ by state or
   even by city within a state, due to transport costs, local taxes,
   supply conditions, and market structure. A household's inflation
   experience is tied to its local price trajectory, which can diverge
   from the national aggregate even when national category weights are
   held fixed.

The practical implication: **two households with identical national CPI
exposure numbers can experience very different actual cost-of-living
changes**, purely because of what they buy and where they buy it. A
personal inflation index — built from a household's *own* expenditure
weights and (ideally) prices it actually faces — directly targets this
gap, which this project demonstrates with transparent, user-editable
arithmetic.

## Data — full disclosure (read this before trusting any number here)

**No data shipped with this project is real, officially published CPI
data.** Specifically:

- `src/personal_inflation/example_data.py` contains a set of
  hand-picked, round-number **illustrative example weights**
  (`EXAMPLE_ILLUSTRATIVE_WEIGHTS`) used only to give the basket builder
  and the tests something sensible to start from. They are loosely
  modeled on the *shape* of commonly reported CPI category weight splits
  (food as the largest share, followed by housing, etc.) but are **not**
  MoSPI's published weights and must not be cited as such.
- `data/synthetic_category_price_index.csv` is generated by
  `examples/generate_synthetic_data.py` from a **fixed random seed**
  using simple random-walk-with-drift dynamics per category. It is
  entirely synthetic and contains no real price observations of any
  kind. It exists purely so the methodology (computing and comparing
  indices over time) can be demonstrated end-to-end without the project
  claiming to possess real MoSPI data (which this sandbox cannot fetch).
- The `official_cpi_reference` column in that same CSV is **not** a real
  published CPI series — it is a weighted blend of the synthetic category
  columns, using the same illustrative weights above, meant only to stand
  in for "a comparison series" in the Streamlit app and tests.

See `docs/DATA_SOURCES.md` for exactly where to obtain the real, official
MoSPI CPI series and category weights, and how you would substitute them
into this toolkit.

## Methodology (how the demonstration actually works)

1. A user specifies category weights (via the Streamlit sliders, a Python
   dict, or a CSV upload) — their own real expenditure shares if they
   want a meaningful personal index, or the bundled illustrative example
   weights for a pure demonstration run.
2. A user supplies category prices for two periods (for `laspeyres_index`)
   or a full panel of category prices across many periods (for
   `personal_index_time_series`) — again, either their own real price
   data, or the bundled synthetic series.
3. `laspeyres_index` computes the fixed-basket index value exactly per
   the formula above; `personal_index_time_series` applies it period by
   period against a fixed base period.
4. `compare_to_reference` lines the resulting personal index up against
   any reference series the user supplies (e.g. the synthetic
   `official_cpi_reference` column, or — once a user has it — a real CPI
   series) and reports the point and percentage gap.

At every step above, this is a **demonstration of the methodology**, not
an empirical claim about actual household inflation in India. Treat the
numbers this project produces from its bundled example data exactly as
labeled: illustrative.

## Limitations

- **Substitution bias** (discussed above): the Laspeyres formula
  overstates true cost-of-living change relative to a basket that can
  adjust.
- **Basket staleness**: weights fixed at an old base period drift out of
  date as spending patterns change.
- **Regional and urban/rural variation**: this toolkit treats each
  category as a single national-level price series unless the user
  supplies their own local price data; it has no built-in geographic
  disaggregation.
- **Category granularity**: nine broad categories is a simplification.
  Real expenditure surveys use far more granular item-level baskets; a
  user who wants more precision should subdivide categories themselves
  (e.g. splitting "food" into "cereals", "vegetables", "dairy", ...) —
  the code places no limit on the number or naming of categories.
- **No seasonal adjustment**: the panel index function does no seasonal
  adjustment; a full personal-finance deployment would want to account
  for seasonal price patterns (e.g. in vegetables) before comparing
  month-to-month moves.
- **Single price series per category**: within a category, this toolkit
  does not model substitution between individual items (e.g. between
  rice and wheat within "food") — only across the categories in the
  user's basket, each as a single aggregate price.

## Reproducibility

- `examples/generate_synthetic_data.py` uses a fixed seed
  (`SEED = 20240601`) and pure NumPy random-walk simulation; running it
  again produces a byte-for-byte identical `data/synthetic_category_price_index.csv`.
  This is checked by `tests/test_example_data.py::test_synthetic_generator_is_deterministic`
  and by a test that the checked-in CSV matches what the generator
  currently produces.
- All index-number tests in `tests/test_index.py` include a hand-computed
  worked example (computed independently of the implementation, by hand,
  in the test's docstring) that the function's output is checked against,
  so correctness of the core formula does not rely on the implementation
  checking itself.
