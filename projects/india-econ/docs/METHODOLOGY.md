# Methodology

## Research Question

Can a small, honestly-scoped Python package make a handful of Indian economic indicators as easy to pull as a few lines of pandas -- without claiming comprehensive coverage, and while making the live-vs-synthetic status of every value visible in code, not just in prose?

## Theory

See the README's "Economic Theory" section for a one-line frame per indicator category (GDP, inflation, unemployment, trade, exchange rate, interest rates, government finance, household finance). This package is a data-access layer, not a modeling library, so the economic theory involved is in choosing *which* series are reasonable proxies for each category, not in any estimation method.

## Data

Primary (attempted) source: the World Bank's Open Data / World Development Indicators API (`https://api.worldbank.org/v2/country/IND/indicator/<code>`), which is public and requires no API key. Full per-indicator source table: `docs/DATA_SOURCES.md`.

Fallback source: a deterministic synthetic series generated locally, used only when the live fetch fails or is explicitly disabled (`allow_live=False`). It is never presented as real data -- every result carries `status="synthetic"` when this path is used.

## Assumptions

- **Country scope**: all live indicator codes are queried for India (`IND`) specifically; the package does not support other countries.
- **Annual frequency**: every indicator here is annual. The World Bank's open API does not carry the higher-frequency (monthly/quarterly) releases that India's own statistical agencies (RBI, MOSPI) publish for some of these series.
- **Proxy series where no direct open series exists**: `interest_rates()` uses a commercial bank lending rate (`FR.INR.LEND`) as a stand-in for a policy rate, since the RBI's repo rate is not in the World Bank's open catalog. `household_finance()` uses gross domestic savings and private-sector credit (both economy-wide, % of GDP) as stand-ins for household-level savings/credit, since no household-survey series is available through this API. Both are flagged in the relevant function's docstring and in `docs/DATA_SOURCES.md`.
- **Full-history caching**: a live fetch pulls each indicator code's *entire* available history once per process (not re-fetched for different `start`/`end` windows), then filters locally. This trades a slightly larger first request for guaranteeing repeat calls never hit the network again.

## Methodology (what the code actually does)

1. A caller calls a public function, e.g. `india_econ.gdp(start=2015, end=2020)`.
2. `india_econ.core.get_indicator()` looks up the indicator's `IndicatorSpec` in the registry (`india_econ._registry`), raising `UnknownIndicatorError` for a bad name, and validates `start <= end`, raising `InvalidDateRangeError` otherwise.
3. If `allow_live` is `True` (the default), it calls `india_econ._worldbank.fetch_indicator_series()` for each World Bank indicator code the spec lists. That function is wrapped in `functools.lru_cache`, keyed by indicator code, so repeat calls for the same code never re-hit the network.
4. If that succeeds, the series are assembled into a `pandas.Series`/`DataFrame` indexed by year, and (for GDP specifically) a growth-rate column is derived locally via `pct_change()`. Status is set to `"live"`.
5. If it fails for any reason (`DataFetchError` -- network error, timeout, malformed response) or `allow_live=False` was passed, a synthetic series is generated instead by `india_econ._synthetic.synthetic_series()`: a `numpy.random.default_rng` seeded from a SHA-256 hash of the indicator and column name produces a reproducible random walk (optionally pulled toward a long-run mean, for rate-like series). Status is set to `"synthetic"`.
6. The result is filtered to the requested `start`/`end` window and wrapped in an `IndicatorResult`, which carries both the data and a metadata dict (including `status`/`source`), and also copies that metadata onto the pandas object's `.attrs`.

## Limitations

- Annual-only, India-only, eight indicator categories with one or two series each -- see the README's "Limitations" section for the full list.
- The synthetic fallback is illustrative, not a forecast or an estimate of the true value -- it exists purely so the package degrades gracefully rather than failing outright or (worse) silently serving fabricated-but-labelled-as-real numbers.
- No on-disk caching: the `lru_cache` layer only lives for the duration of one Python process.

## Reproducibility

- Synthetic series are fully deterministic: the same indicator/column name always seeds the same `numpy` generator, so `gdp(allow_live=False)` returns identical numbers on every machine and every run (verified in `tests/test_public_api.py::test_synthetic_data_is_deterministic_across_calls`).
- The live path's caching and fallback behavior are both covered by tests that mock `requests.get` (`tests/test_live_and_caching.py`), so they do not depend on this sandbox's actual network access to verify correctness.
- To reproduce the test suite: `pip install -e ".[dev]"` then `pytest tests/ -q` from `projects/india-econ/`.
