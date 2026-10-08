# Data Registry

Every real dataset in this repository, with full provenance. Status values:

- **VERIFIED** — real source data, source confirmed (either self-stated in the file or confirmed against an independently-matched official table).
- **PARTIAL** — looks like real data; exact source release/URL/retrieval date not yet independently confirmed, or coverage is too limited (too few years/points) for the analysis it would power.
- **ESTIMATED** — explicitly not reported/observed data; modelled or interpolated. Must never be displayed as VERIFIED or DERIVED.

---

## State / regional economic data

### `data/raw/rbi_handbook/percapita_nsdp_constant_prices_2004_05_to_2022_23.csv`

| Field | Value |
|---|---|
| Variable | Per-capita Net State Domestic Product (NSDP), constant prices |
| Geography | 37 states/UTs |
| Frequency | Annual |
| Coverage | 2004-05 to 2022-23 — **but two different base years**: 2004-05 base (2004-05 → 2014-15) and 2011-12 base (2011-12 → 2022-23), with a 4-year overlap (2011-12 to 2014-15) |
| Units | ₹ |
| Source | RBI Handbook of Statistics on Indian States, Table 26 — confirmed from the uploaded workbook's own sheet titles/headers (`T_26(i)`–`(iv)`, "TABLE 26: PER CAPITA NET STATE DOMESTIC PRODUCT (Constant Prices)") |
| Status | **VERIFIED** (source self-identifies in the file) |
| Transformation | Wide-to-long reshape of 4 sheets (one per base-year/period block) into one tidy table; `-` cells (no data published for that state/year) converted to null. Script: `data_sources/ingest_uploaded_sources.py` |
| ⚠️ Known issue | **The two base-year series are not directly comparable without rebasing.** A naive concatenation would imply a false continuous trend across 2011-12. The 4-year overlap (2011-12–2014-15) is present in *both* series, which means a standard overlap-linking (splice) factor *can* be computed if you want one continuous series — but this hasn't been done yet; right now the two eras are kept distinct via the `base_year` column. Tell me if you want them spliced, and I'll compute and document the linking factor rather than silently merging them. |

### `data/raw/state_gsdp_nsdp_percapita.csv` (from your earlier upload)

Unchanged from before, now **upgraded to VERIFIED**: the exact figures (Bihar ₹76,490; Telangana ₹4,27,730; Karnataka ₹4,21,858 for 2024-25) match the dbie.rbihub.in screenshot you sent, which is itself sourced from the same RBI Handbook of Statistics on Indian States, confirming this file's provenance. Covers 2023-24 and 2024-25 only — the file above now extends the same metric (constant-price NSDP per capita) back to 2004-05, closing most of the gap.

### `data/raw/plfs_unemployment_rate_by_state_2023_24.csv`, `data/raw/real_percapita_nni_timeseries.csv`, `data/raw/india_gdp_growth_cagr.csv`, `data/raw/indicator_summary_hpi_nni.csv`

Unchanged — see prior registry entries below.

---

## Housing — NHB RESIDEX (National Housing Bank Residential Price Index)

### `data/raw/nhb_residex/city_composite_index_2013_2024.csv`

| Field | Value |
|---|---|
| Variable | Composite housing price index |
| Geography | 50 cities (Ahmedabad, Bengaluru, Mumbai, Delhi, Chennai, Pune, Hyderabad, Kolkata + 42 others — full list in the file) |
| Frequency | Quarterly |
| Coverage | Jun-2013 to Sep-2024 (46 quarters) |
| Units | Index (base period not stated in the uploaded file — index values cross 100 around 2018-19 for most cities, consistent with NHB RESIDEX's known 2017-18 base, but **not confirmed from the file itself** — flag this to NHB RESIDEX's published base-year documentation before treating "100" as a specific base quarter) |
| Source | National Housing Bank RESIDEX — confirmed from the uploaded file's own column structure (city × quarter composite index), matching NHB RESIDEX's published format |
| Status | **PARTIAL** (real NHB data, base-year/methodology note needs confirming) |
| Transformation | HTML table (file was `.xls` but is actually an HTML export) parsed with `pandas.read_html`, de-duplicated (source file repeats the table twice), wide-to-long reshape |

### `data/raw/nhb_residex/city_composite_index_2025_2026.csv`

Same series, most recent 5 quarters (Jun-2025 to Jun-2026), 50 cities. Same status/caveats as above.

### `data/raw/nhb_residex/city_price_levels_by_unit_size_2013_2024.csv`

| Field | Value |
|---|---|
| Variables | Actual price level in ₹/sq.m. — composite, and by three unit-size tiers (≤60 sq.m., 60–110 sq.m., >110 sq.m.) |
| Geography | Same 50 cities |
| Frequency | Quarterly, Jun-2013 to Sep-2024 |
| Source | NHB RESIDEX |
| Status | **PARTIAL** (real data; same base-year caveat doesn't apply here since these are absolute price levels, not an index — this file is actually stronger evidence-wise than the index files) |
| **This is the single most valuable file for the Housing Intelligence Lab** — real, city-level, ₹/sq.m. price levels over an 11-year run. Pairing this with income data lets P/I be computed directly rather than proxied through an index. |

**Still needed for Housing Lab**: city-level (not state-level) household income. NSDP per capita by state is a usable proxy but will overstate affordability in expensive metros (where incomes concentrate) relative to the state average — this needs to be stated explicitly as a modelling assumption in the Housing methodology, never presented as true city-level income.

---

## Banking — iBFPI inputs

### `data/raw/bank_earnings/bank_earnings_reported_q2fy25_to_q2fy26.csv`

| Field | Value |
|---|---|
| Variables | NII, non-interest income, operating profit, provisions, PAT, total assets, NIM, ROA, CET1, CAR, LCR |
| Banks | HDFC Bank, ICICI Bank, SBI, Axis Bank |
| Frequency | Quarterly |
| Coverage | Q2 FY2025, Q1 FY2026, Q2 FY2026 (3 quarters only) |
| Status | **VERIFIED** (quarterly disclosures — treat as real reported figures) |
| Coverage gaps | Several cells are blank per bank/quarter (e.g. SBI has no NII breakdown some quarters, Axis is missing NII in Q2FY25) — real disclosures are not uniform across banks; this is expected, not an error |
| ⚠️ For iBFPI specifically | Only 2 of the 5 BFPI indicators are consistently present (CET1, LCR for some bank-quarters); no PPNR/assets, no net charge-off rate, no unrealised-securities-losses/CET1. **Not sufficient alone to replace the synthetic panel.** Also only 3 quarters — the existing iBFPI methodology needs the 2018-2024 run to match the repo-rate regime-split analysis. |

### `data/raw/bank_earnings/bank_earnings_ESTIMATED_2019q1_2025q1.csv`

**⚠️ This file is NOT verified or reported data.** Its own `data_status` column says `estimated_from_annual` and its own `notes` column states: *"Quarterly PAT distributed from annual anchor at Q1/Q2/Q3/Q4 = 22%/23%/26%/29%; NII, operating profit and assets are ratio/base-growth estimates; not reported."*

| Field | Value |
|---|---|
| Status | **ESTIMATED — must never be displayed as VERIFIED, DERIVED, or used to compute a "real" iBFPI result.** Per your own rules, this is closer to the SYNTHETIC/illustrative category than real data, despite covering real banks and plausible figures. |
| Possible legitimate use | Clearly labelled as a *model estimate* for a **Scenario/What-if context only** (e.g. "if quarterly figures followed a typical seasonal distribution of annual results, they would look like this") — never in a results panel that claims to show actual bank performance. |

---

(All other entries from the prior registry — `real_percapita_nni_timeseries.csv`, `indicator_summary_hpi_nni.csv`, `india_gdp_growth_cagr.csv`, `plfs_unemployment_rate_by_state_2023_24.csv` — unchanged; see git history for the original writeup.)

## What this registry now supports

- **State Economic Divergence Lab**: a real, 2004-05→2024-25 per-capita income series by state (with the base-year splice decision pending), a real one-year unemployment snapshot, and a real sectoral-employment narrative *if* you also send the EPWRF/NSS-round employment-by-sector table (still not received as a file — only cited in your research).
- **Housing Intelligence Lab**: real city-level housing price levels (2013-2024, 50 cities) — genuinely strong. Income side still needs either city-level data or an explicit, documented state-proxy assumption.
- **Banking Lab**: 3 real quarters for 4 banks, covering 2 of 5 BFPI indicators — not enough to replace the synthetic 2018-2024 panel yet. The estimated file must stay out of any "real result."

## Still specifically needed

1. **Decision**: splice the two NSDP base-year series (I compute and document the linking factor) or keep them as two visually separate eras?
2. **City-level household income** (or explicit approval to proxy with state NSDP per capita, clearly labelled as an assumption).
3. **EPWRF/NSS-round state-wise employment-by-sector table** as an actual file — your research identified where it lives, not the data itself.
4. **Full 2018-2024 bank panel** with all 5 BFPI indicators, if you want to replace the synthetic iBFPI panel — the two files received don't cover this.
5. NHB RESIDEX's documented base-year/base-quarter (to label the index files precisely, e.g. "2017-18 = 100") — a one-line confirmation, not a new dataset.
