# Data dictionary

Field-by-field specification for every dataset consumed by the labs.

## data/processed/bank_panel.csv

Long-form panel: one row per bank per quarter.

| Field | Type | Units | Direction (iBFPI) | Source (real data) | Notes |
| --- | --- | --- | --- | --- | --- |
| `bank` | string | — | — | Bank annual reports | HDFC / ICICI / SBI / Axis / Kotak in this build |
| `period` | date | quarter-end | — | Aligned to fiscal quarter end | ISO date, YYYY-MM-DD |
| `ppnr_to_assets` | float | decimal fraction | +1 | Bank quarterly disclosures | Pre-provision net revenue ÷ average total assets, annualised |
| `cet1_ratio` | float | decimal fraction of RWA | +1 | Basel III Pillar 3 filings | CET1 capital ÷ risk-weighted assets |
| `nco_rate` | float | decimal fraction | −1 | Bank quarterly disclosures | Net charge-offs ÷ average loans, annualised |
| `lcr` | float | ratio (1.30 = 130%) | +1 | Basel III disclosures | Liquidity coverage ratio |
| `unrealised_loss_to_cet1` | float | decimal fraction | −1 | Balance-sheet OCI line ÷ CET1 | AFS book MTM |

**In this build.** Values are illustrative / synthetic (see `data_sources/build_illustrative_data.py`). Every row is deterministically reproducible via `python -m data_sources.build_illustrative_data`.

## data/processed/repo_rate.csv

| Field | Type | Units | Source | Notes |
| --- | --- | --- | --- | --- |
| `period` | date | quarter-end | RBI DBIE | ISO date |
| `repo_rate` | float | % annualised | RBI DBIE | Value effective at quarter-end |

**In this build.** Values approximate the RBI repo-rate history 2018-Q2 through 2024-Q3 at quarter-end, rounded. Replace with the RBI-published series when reproducing.

## Provenance conventions

- Every user-supplied CSV should carry a `source` and `retrieved_at` field where possible.
- When a value is not from an official primary source, flag it in a `provenance` column with one of: `official`, `derived`, `illustrative`, `interpolated`.
- Do not use commercial aggregator prices where an official source exists.

## Refresh cadence

- Repo rate: refresh at each RBI MPC decision; use the rate in effect at quarter-end for panel merging.
- Bank indicators: refresh at each bank's quarterly-earnings release, then re-align to fiscal-quarter end.

## Naming conventions

- All floats are decimal fractions unless labelled `%` or `(1.30 = 130%)`.
- All dates are ISO `YYYY-MM-DD`.
- All monetary values in the wealth module are Indian rupees; nominal unless explicitly labelled *real*.
