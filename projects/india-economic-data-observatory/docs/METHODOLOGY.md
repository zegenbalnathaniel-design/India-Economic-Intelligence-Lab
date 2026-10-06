# Methodology

## Research question

Can a single, small, self-contained pipeline ingest Indian macroeconomic
indicators from several genuinely different official sources — each with
its own access method, update cadence, and reliability — while making it
*structurally impossible* for a downstream chart or table to present a
synthetic fallback value as if it were real, officially-sourced data?

## Theoretical framework: why standardized metadata and validation matter here

Cross-source economic data work has a well-known failure mode: a chart
built from several indicators quietly mixes provenance — some numbers
real, some interpolated, some from a different base year or methodology —
and nothing in the chart tells the reader which parts to trust. This
project treats that as a *design* problem, not just a data-quality
footnote:

- **Provenance as a first-class, typed field, not a comment.** Every
  series this package returns is paired with a `Metadata` record whose
  `status` field is one of exactly two values (`official` /
  `illustrative_synthetic`) — there is no third, ambiguous state, and no
  code path that can return a series without one. See
  `src/data_observatory/metadata.py`.
- **"Attempt real, fail to synthetic, always label" as the only loading
  path.** There is no separate "demo mode" with different code; the
  fallback is the same code path a real network outage would hit in
  production. See `src/data_observatory/loaders.py`.
- **Validation as a visible pass, not a silent cleanup.** Forward-filling
  a gap is a real methodological choice (it assumes "no new information"
  rather than, say, linear interpolation) and readers should be able to
  see exactly which points were touched by it. See
  `src/data_observatory/validation.py`.

## Data

Four official sources are documented and targeted: World Bank Open Data
(the only one with a plain unauthenticated REST/JSON API), RBI's Database
on Indian Economy, MoSPI, and IMF International Financial Statistics (see
`docs/DATA_SOURCES.md` for which are actually wired into a loader and
why). This environment's own live-fetch probe against the World Bank API
**failed** at the outbound network proxy — see `docs/DATA_SOURCES.md` for
the exact error and what that does and does not imply about the pipeline
itself.

## Assumptions

- World Bank's annual indicator series are an acceptable (if coarser)
  stand-in for several indicators whose "true" Indian source (MoSPI, RBI)
  publishes at finer granularity (monthly CPI, daily FX) — documented per
  indicator in `docs/DATA_SOURCES.md`, never silently assumed equivalent.
- The synthetic fallback's drift/volatility/mean-reversion parameters are
  illustrative order-of-magnitude choices, not fitted to or copied from
  any real dataset, and the series they produce must never be read as a
  forecast or as real history.
- Forward-filling (rather than interpolating or dropping) is the
  documented missing-data policy project-wide, chosen because it never
  uses future information and is simple to reason about and to flag.

## Methodology (the pipeline, step by step)

1. **Attempt live fetch** (`sources.py`) against the indicator's real
   official endpoint, if `allow_live=True` and the indicator has one with
   a parseable API (World Bank). For RBI/MoSPI, a genuine HTTP GET is
   still attempted against the real portal URL, but is not expected to
   yield a parseable series (see `docs/DATA_SOURCES.md`).
2. **Fall back to synthetic** (`synthetic.py`) if the live attempt
   returned nothing usable, or was skipped. Synthetic generation is
   seeded deterministically from the indicator's key, so re-running the
   pipeline with no live access reproduces byte-identical output.
3. **Validate and clean** (`validation.py`): sort by date, de-duplicate
   periods (latest wins), flag and null out any value outside the
   indicator's documented domain, forward-fill gaps, and flag every
   forward-filled point.
4. **Cache** (`cache.py`) the cleaned result to an on-disk CSV keyed by
   indicator + date range + live/synthetic status, so a cached synthetic
   result is never served back as if it were live or vice versa.
5. **Return** `(frame, metadata)` with `metadata.status` set honestly —
   this is the only field any UI or notebook is allowed to trust for
   deciding how to present the series.

## Limitations

- The synthetic fallback is a stochastic-process approximation, not a
  model of the Indian economy; its shape is plausible but not
  evidence of anything.
- World Bank's annual series cannot substitute for the finer-grained
  official releases (monthly CPI/WPI, daily FX, event-driven policy rate)
  for any analysis that needs that granularity.
- RBI DBIE and MoSPI integrations are probe-only today (see
  `docs/DATA_SOURCES.md`); WPI and the policy rate are always synthetic
  until a scripted bulletin/export parser is built for them.
- This sandbox's own network policy could not be worked around; the
  "attempt live" code path is real but untested against an actually
  reachable World Bank endpoint in this specific run.

## Reproducibility

- Synthetic series are seeded from `sha256(indicator_key)` — identical
  inputs always produce identical output (see
  `tests/test_synthetic.py::test_level_series_deterministic_reproducibility`
  and the bounded-series equivalent).
- The full pipeline (loaders, validation, caching, metadata, viz) has a
  pytest suite that runs with no network access
  (`cd projects/india-economic-data-observatory && python3 -m pytest tests/ -q`)
  and exercises both the synthetic-fallback path and a mocked live-fetch
  success/failure path for each.
- `conftest.py` at the project root puts `src/` on `sys.path` so the
  package imports cleanly for tests, the app, notebooks, and the example
  script without an editable install.
