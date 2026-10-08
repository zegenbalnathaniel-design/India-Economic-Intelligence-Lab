# Data Registry

Every real dataset in this repository, with full provenance. Status values follow the project's data-integrity system:

- **VERIFIED** — real source data loaded as supplied, no values altered.
- **DERIVED** — calculated from verified source data (formula stated).
- **PARTIAL** — some required data exists but the analysis it would power is incomplete.

Where the exact original source URL and retrieval date could not be independently confirmed from the file alone, this is flagged explicitly — **do not treat an inferred source as confirmed until the provider confirms it.**

---

## `data/raw/real_percapita_nni_timeseries.csv`

| Field | Value |
|---|---|
| Variable | Real per-capita Net National Income (NNI) |
| Geography | All-India |
| Frequency | Annual (financial year) |
| Coverage | 2011–12 to 2024–25 (7 points: 2011-12, 2014-15, 2019-20, 2020-21, 2022-23, 2023-24, 2024-25 — not a continuous annual series, specific years only) |
| Units | ₹ (Indian rupees), constant prices |
| Likely source | MoSPI National Accounts Statistics (NNI at constant prices, per capita) — this is a standard published GoI series | | 
| Source confirmed? | **No — inferred from column naming and figures only.** Please confirm exact MoSPI release/table and retrieval date. |
| Status | **PARTIAL** — real-looking data, source not yet independently confirmed |
| Transformations applied | None — loaded as supplied |

## `data/raw/indicator_summary_hpi_nni.csv`

| Field | Value |
|---|---|
| Variables | RBI all-India House Price Index (start vs. latest), Real per-capita NNI (start vs. latest), Nominal per-capita NNI (start vs. latest) |
| Geography | All-India |
| Frequency | Two-point comparison (not a time series) |
| Coverage | HPI: 2010-11 base (=100) to 2024-25 (~190–193); NNI: 2011-12 to 2024-25 |
| Units | HPI: index (2010-11=100); NNI: ₹ |
| Likely source | RBI (HPI; matches the RBI HPI series you referenced, base year 2010-11 — note this is a different base year from the Q4 2025-26 release you quoted earlier, which uses a 2022-23 base — **these two HPI references use different base years and are not directly comparable without rebasing**); MoSPI National Accounts (NNI) |
| Source confirmed? | **No — inferred.** This looks like a compiled summary table rather than a primary release; please confirm. |
| Status | **PARTIAL** |
| ⚠️ Known issue | Only two points per indicator — cannot build a real time-series chart from this file alone; see `real_percapita_nni_timeseries.csv` for the fuller NNI series |

## `data/raw/india_gdp_growth_cagr.csv`

| Field | Value |
|---|---|
| Variable | India real GDP CAGR |
| Geography | All-India |
| Frequency | Point estimates over three trailing windows |
| Coverage | Latest 10 years (7.8%), latest 5 years (9.0%), latest 3 years (7.4%) — exact end year not stated in the file |
| Source | **World Economics** (stated directly in the file's `source` column) |
| Source type | Private economic-data/analysis provider, **not an official GoI/RBI/MoSPI statistic** — per your own source-priority rules (official > World Bank/IMF > other), this should be visually distinguished from official series, not presented at the same confidence level |
| Status | **VERIFIED** (the file states its own source), but flagged as non-official |
| Transformations applied | None |

## `data/raw/plfs_unemployment_rate_by_state_2023_24.csv`

| Field | Value |
|---|---|
| Variable | Unemployment rate, usual status, age 15+ |
| Geography | 28 Indian states + All-India |
| Frequency | Annual |
| Coverage | 2023-24 only (single cross-section, not a time series) |
| Units | % |
| Likely source | Periodic Labour Force Survey (PLFS) 2023-24 Annual Report, MoSPI/NSSO | 
| Source confirmed? | **No — inferred from filename and standard PLFS methodology.** Please confirm exact PLFS report/table reference. |
| Status | **PARTIAL** — single year only; a divergence/convergence analysis needs multiple years to show a trend, not one cross-section |

## `data/raw/state_gsdp_nsdp_percapita.csv`

| Field | Value |
|---|---|
| Variables | GSDP per capita (current & constant prices), NSDP per capita (current & constant prices) |
| Geography | ~33 Indian states/UTs + All-India |
| Frequency | Annual |
| Coverage | 2023-24 and 2024-25 only (two years) |
| Units | ₹ |
| Likely source | MoSPI State Domestic Product release, or RBI's Handbook of Statistics on Indian States (both compile state Directorate of Economics & Statistics figures) |
| Source confirmed? | **No — inferred.** Please confirm. |
| Status | **PARTIAL** — real state-level cross-section, but only two years; several states have missing cells in 2024-25 (Sikkim, Goa, Gujarat, Andaman & Nicobar, Ladakh, Mizoram, Nagaland, Manipur all have gaps — likely provisional-estimate lags, not errors) |
| ⚠️ Known issue | Two years cannot establish a convergence/divergence **trend** — that needs a longer run (ideally 2010-11 to 2024-25) to see whether lower-income states are closing the gap with higher-income states over time, versus just a snapshot ranking |

---

## What this registry currently supports

- **India Economic Overview**: a real per-capita NNI chart (7 points, 2011-12 to 2024-25), a real GDP CAGR stat panel (flagged as private-provider, not official), a real but low-resolution HPI comparison (2 points, base-year caveat noted).
- **State Economic Divergence Lab**: a real cross-sectional view (one point in time) of GSDP/NSDP per capita and unemployment by state — rankings and current-state dispersion (e.g. a coefficient of variation across states) are legitimate with this data. A true **convergence/divergence trend over time** is not yet supported — that needs the multi-year series requested below.

## Still needed (unchanged from the prior ask, now narrowed)

1. **Multi-year state GSDP/NSDP per capita** (ideally back to 2010-11) — to actually test convergence vs. divergence over time, not just rank one year.
2. **Multi-year PLFS unemployment/LFPR by state** — same reason.
3. **City-level housing prices + household income** for the Housing Intelligence Lab — nothing received yet for this.
4. **Real bank-level BFPI inputs** (PPNR/assets, CET1, NCO rate, LCR, unrealised securities losses/CET1) — the existing panel is still synthetic.
5. Source confirmation (exact release, URL, retrieval date) for the five files above, so each can move from PARTIAL to VERIFIED.
