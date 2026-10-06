# india-econ

A small, pip-installable Python package that pulls a handful of Indian economic indicators (GDP, inflation, unemployment, trade, the exchange rate, a policy-adjacent interest rate, government finance, and household finance proxies) into pandas with a couple of lines of code.

## Research Question

Can a small, honestly-scoped Python package make a handful of Indian economic indicators as easy to pull as a few lines of pandas -- without pretending to be a comprehensive data platform, and without hiding from the user whether a given number is real or a clearly-labelled stand-in?

## Why I Built This

Every time I wanted to sanity-check a claim about the Indian economy -- "how much has the rupee moved against the dollar this decade", "what did the fiscal deficit look like before and after a given year" -- I ended up re-writing the same few lines: hit the World Bank API, handle the inevitable timeout or malformed response, reshape the JSON into a Series, and only then get to the actual analysis. `india-econ` packages that boilerplate once, with one honest rule: it tries to fetch real data first, and if it can't, it says so and hands back a synthetic stand-in instead of silently failing or (worse) silently faking something that looks real.

## Economic Theory

A one-line frame for each category this package touches:

- **GDP** -- the broadest single measure of aggregate output; its growth rate is the headline number most "is the economy doing well" conversations start from.
- **Inflation (CPI)** -- the rate at which the general price level erodes purchasing power; central to monetary policy and real-wage analysis.
- **Unemployment** -- the share of the labor force without work but seeking it; a core labor-market slack indicator, though India's informal-sector share makes any single modeled estimate an approximation.
- **Trade (exports/imports)** -- the external balance; the gap between the two feeds directly into the current account and currency pressure.
- **Exchange rate** -- the price of the rupee in dollar terms; it links domestic prices to the rest of the world and is sensitive to both trade and capital flows.
- **Interest rates** -- the price of money; central banks move policy rates to manage inflation and growth, and bank lending rates transmit that policy into the real economy.
- **Government finance** -- the fiscal deficit and public debt load describe how much the government is borrowing now and owes already, both of which constrain future policy space.
- **Household finance** -- savings and credit availability describe how much of national income is set aside versus borrowed against, shaping consumption capacity.

## Methodology

For every indicator, `india-econ`:

1. Attempts a live GET request to the relevant World Bank Open Data indicator endpoint for India (`https://api.worldbank.org/v2/country/IND/indicator/<code>`), with a 10-second timeout.
2. On success, parses the response into a `pandas.Series`/`DataFrame` indexed by year, caches the raw series in memory (keyed by indicator code) so repeat calls don't re-hit the network, and tags the result `status="live"`.
3. On any failure (network error, timeout, malformed response, or the caller explicitly passing `allow_live=False`), generates a deterministic synthetic series instead -- seeded from a hash of the indicator and column name, so it's reproducible, not random noise that differs run to run -- and tags the result `status="synthetic"`.
4. Returns both the data and this status, together with provider/URL/definition/unit/frequency metadata, wrapped in an `IndicatorResult`.

Date filtering (`start`/`end`) happens after the full series is fetched/generated and cached, so asking for a narrower window later doesn't cost another request.

## Data: What's Live vs. Synthetic (full disclosure)

**I tested this honestly rather than assuming it.** In the sandbox this package was built and tested in, an outbound request to `https://api.worldbank.org/...` was blocked by the sandbox's network policy (a proxy-level 403, not a World Bank outage) -- so every test run and example run in that environment actually exercises the **synthetic fallback path**, not a live one. The live-fetch code is fully implemented and has unit tests that mock the HTTP layer to verify both the request shape and the fallback trigger, but I want to be upfront that I could not confirm an end-to-end live pull from this machine. If you run this package somewhere with normal internet access, the live path should work against the World Bank's public, unauthenticated API -- try it and check `result.source` to see which path you actually got.

Either way, every `IndicatorResult` tells you which one happened:

```python
import india_econ as ie

result = ie.gdp()
print(result.source)          # "live" or "synthetic"
print(result.metadata["status"])  # same thing, under the other common name
```

See `docs/DATA_SOURCES.md` for the full source table (one row per indicator: provider, URL, unit, frequency, and status caveats), and `docs/METHODOLOGY.md` for the generation details behind the synthetic fallback.

## Results / Demonstration

```python
>>> import india_econ as ie
>>> result = ie.inflation(start=2015, end=2020)
>>> result.data
year
2015    ...
2016    ...
...
Name: cpi_inflation_pct, dtype: float64
>>> result.source
'synthetic'   # or 'live', depending on network access
```

Run `python examples/demo.py` for a tour of every public function with its live/synthetic status printed alongside the data.

## How It Works

- `india_econ.core.get_indicator()` is the single orchestration function every public indicator function calls; it owns the live-try/synthetic-fallback logic and date filtering.
- `india_econ._worldbank.fetch_indicator_series()` is the only function that ever calls `requests.get`; it's wrapped in `functools.lru_cache` so a given indicator code is fetched at most once per process.
- `india_econ._synthetic.synthetic_series()` generates the deterministic fallback via a seeded `numpy` random walk (optionally mean-reverting, for rate-like series).
- `india_econ._registry` is a single declarative table of every indicator's metadata and synthetic parameters -- it's the source of truth `get_metadata()` and the docs are built from.
- `IndicatorResult` (in `india_econ.core`) wraps the returned `Series`/`DataFrame` together with a metadata dict, and also copies that dict onto the pandas object's `.attrs`, so `result.data.attrs["status"]` works even if you discard the wrapper.

## Installation

This package is **not published on PyPI**. Install it from source, in editable mode, from inside this folder:

```bash
git clone <this-repo-url>
cd projects/india-econ
pip install -e .
```

For running the test suite as well:

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

### CI

`.github/workflows/ci.yml` lives inside this project folder (`projects/india-econ/.github/workflows/ci.yml`). GitHub Actions only ever reads workflow files from a repository's **root** `.github/workflows/` directory, and this project currently lives as a subfolder of a larger monorepo, so this workflow does not run automatically here. It's provided for the day this folder is split out into its own standalone repository (or copied to `.github/workflows/` at a repo root) -- at that point it will run `pip install -e ".[dev]"` and `pytest` on every push and pull request with no changes needed.

## Usage

```python
import india_econ as ie

# Every function takes optional start/end years and an allow_live toggle.
gdp = ie.gdp(start=2010, end=2022)
cpi = ie.inflation()
unemployment = ie.unemployment(start=2018)
trade = ie.trade(end=2021)
fx = ie.exchange_rate()
rates = ie.interest_rates()
fiscal = ie.government_finance()
household = ie.household_finance(allow_live=False)  # force the synthetic path

for result in (gdp, cpi, unemployment, trade, fx, rates, fiscal, household):
    print(result.metadata["indicator"], "->", result.source)

# Static metadata without fetching anything:
print(ie.get_metadata("gdp"))

# Clear exceptions instead of KeyErrors/IndexErrors:
try:
    ie.get_metadata("not_a_real_indicator")
except ie.UnknownIndicatorError as exc:
    print(exc)

try:
    ie.gdp(start=2020, end=2010)
except ie.InvalidDateRangeError as exc:
    print(exc)
```

## Examples

See `examples/demo.py` for a standalone script that calls every public function and prints its data, status, and metadata.

## Limitations

- **Not comprehensive.** This covers eight indicator categories with one or two series each -- a focused, illustrative subset, not a comprehensive Indian economic data platform. It does not cover state-level data, sectoral breakdowns, high-frequency (monthly/quarterly) series, or anything beyond what's listed above.
- **Annual frequency only.** Every series here is annual; the World Bank's open API does not offer the higher-frequency RBI/MOSPI releases this package's indicators are themed around.
- **Proxies, not perfect matches.** `interest_rates()` returns a commercial lending rate, not the RBI's policy repo rate (which isn't in the World Bank's open catalog). `household_finance()` returns economy-wide savings/credit ratios, not household-survey data. Both are documented in `docs/DATA_SOURCES.md`.
- **Synthetic fallback is illustrative, not predictive.** The synthetic series are deterministic random walks shaped to look plausible, not forecasts or estimates of real values -- never use them for actual analysis.
- **In-memory cache only.** The live-fetch cache (`functools.lru_cache`) resets every time you restart your Python process; there's no on-disk cache.

## Future Work

- Add on-disk caching with a TTL, so a live fetch isn't repeated every process restart.
- Add a few more indicator categories (e.g. a sectoral GVA breakdown) if a reliable, unauthenticated live source for them turns up.
- Add a CLI (`india-econ gdp --start 2015`) as a thin wrapper over the existing functions.
- Revisit the `interest_rates()` proxy if a free, keyless source for the RBI repo rate becomes available.

## Sources

- World Bank Open Data / World Development Indicators API: https://api.worldbank.org/v2/ (no API key required)
- Full per-indicator source table: `docs/DATA_SOURCES.md`

## License

MIT. See `LICENSE`.
