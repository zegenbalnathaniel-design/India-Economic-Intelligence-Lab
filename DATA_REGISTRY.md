# Data Registry

Every real dataset in this repository, with full provenance. Status values:

- **VERIFIED** — real source data, source confirmed.
- **PARTIAL** — real-looking data; source or coverage not fully confirmed.
- **ESTIMATED** — explicitly modelled/interpolated, not reported. Never shown as VERIFIED or DERIVED.
- **SPLICED** — a derived series built by linking two real but methodologically different source series; the exact linking method is documented, not hidden.
- **DERIVED** — a transparent calculation (a ratio, index, percentile rescaling, average, etc.) over one or more VERIFIED/PARTIAL real series. The formula and every input series are documented; nothing in a DERIVED value is estimated, interpolated, or assumed — only computed. (Introduced for RPIPI and the ICHASI cross-section stress score; see "ICHASI / RPIPI" below.)

---

## Methodology decisions made directly (not left open)

These three were explicitly delegated back to me rather than asked as open questions. Here's what was decided and why — all reversible, all documented:

**1. NSDP base-year splice (2004-05 base vs. 2011-12 base series).** Computed via **overlap-year linking**: both series publish values for 2011-12 through 2014-15, so for each state I took `link_factor = mean(new_base_value / old_base_value)` across those 4 overlap years, then multiplied every pre-2011-12 old-base value by that state's factor. This is the standard technique statistical agencies use to splice a rebased series (not an invented method). Link factors ranged ~1.3x–2.2x across states (expected — base-year price-level differences, not an error). Output: `percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv`, with a `method` column on every row stating whether that value is "as published" or "old-base × link factor." Factors themselves are in `nsdp_splice_link_factors.csv` for audit.

**2. City income proxy for the Housing Lab.** No city-level household income data exists anywhere in what's been provided. Decision: **use the city's state per-capita NSDP** (now available 2004-05→2024-25, current and constant prices) as the income denominator, with each of the 50 RESIDEX cities mapped to its state. This will be stated as an explicit modelling assumption everywhere it's used in the Housing Lab (methodology page, chart captions, "how was this calculated" expansions) — never presented as true city-level income, since it will systematically overstate affordability in expensive metros relative to their state average.

**3. NHB RESIDEX base quarter.** Inferred directly from the data you supplied, not assumed: in the 2013-2024 composite-index file, **35 of 50 cities read exactly 100, and 41 read 99-101, at Mar-2018** — no other quarter comes remotely close (next-highest is Jun-2018 with 12 cities at exactly 100). The base is therefore **Mar-2018 (Q4 FY2017-18) = 100**, stated with this evidence in the index files' documentation rather than asserted from memory.

---

## New from your screenshots (transcribed, not re-derived from the CSVs)

### `data/raw/rbi_handbook/nsdp_current_prices_by_state_2011_12_to_2024_25.csv`

Per-capita NSDP, **current** prices (distinct from the constant-price series above), 32 states, 2011-12→2024-25. Transcribed directly from your `dbie.rbihub.in/handbook/per-capita-net-state-domestic-product-state-wise-at-current-prices` screenshot. Status: **PARTIAL** (AI-vision transcription of a screenshot, not a machine-read file — treat as a close approximation, not pixel-perfect).

**⚠️ Important finding, not resolved automatically:** cross-checking this against the `state_gsdp_nsdp_percapita.csv` file from your earlier upload turned up a *systematic* discrepancy, not random transcription noise: for ~20 states both 2024-25 and 2023-24 values differ by a small, consistent margin (e.g. Telangana 2024-25: 3,87,623 in the old file vs. 3,79,751 here, Tamil Nadu: 3,61,619 vs. 3,58,027) — about 1-2% apart, not wildly off. For 6 states (Bihar, Jharkhand, UP, Kerala, Arunachal Pradesh, Tripura) the old file has a 2024-25 value where this transcription shows a blank/dash. That pattern (small consistent offset + a cluster of newly-blank cells) looks like **two different release vintages of the same published series** (e.g. Provisional vs. First Revised Estimates), not an error in either source. I'm treating this screenshot — directly observed, dated, URL-confirmed — as the current record going forward; the older file is kept, not deleted, with this conflict flagged in both places. If you know which vintage is authoritative, say so and I'll mark the other superseded.

Two states (**Delhi, Puducherry**) had ambiguous column counts in the screenshot (13 values where 14 were expected) — rather than guess which column was missing, these are in a separate `nsdp_current_prices_delhi_puducherry_UNALIGNED.csv` file, unmerged, needing a re-check against the source.

**Also fixed**: the Delhi row in `state_gsdp_nsdp_percapita.csv` was genuinely malformed CSV (9 values crammed into 8 columns — a pre-existing bug from how that file was originally built, not something introduced today). Blanked rather than guessed at realignment; same caveat applies.

### `data/raw/rbi_handbook/institutional_sector_gross_capital_formation_2011_12_to_2023_24.csv`

Gross capital formation at current prices by institutional sector (public/private non-financial corporations, public/private financial corporations, general government, households incl. NPISH), ₹ crore, 2011-12→2023-24. Transcribed from your `dbie.rbihub.in/handbook/institutional-sector-wise-gross-capital-formation-at-current-prices` screenshot — this table was small and unambiguous (13 years × 7 columns, no gaps), low transcription risk. Status: **PARTIAL** (same AI-vision-transcription caveat, but high confidence given no missing/ambiguous cells).

### Employment chart — explicitly NOT extracted

Your third screenshot ("Employment in public and organised private sectors over time," 1970-71→2023-24) is a **line chart with no visible data labels**. Reading precise annual figures off pixel positions on a chart would mean inventing precision that isn't actually there — exactly what your rules forbid. I did not transcribe this one. If you want this series, I need the underlying table (a RBI Handbook table number, a CSV/Excel export, or a zoomed screenshot of a data table rather than the rendered chart).

---

## New: NHB RESIDEX data-quality coverage and MoSPI HCES urban MPCE

### `data/raw/nhb_residex/assessment_price_usable_records_quarterly.csv`

NHB RESIDEX Assessment-Prices HPI **data-quality coverage**: for each quarter from Jun-2017
through Jun-2026, how many phase-1 city residential-apartment records existed vs. how many were
"usable" for the index (68-93% of records, varying by quarter). Source column: "NHB RESIDEX
Usable Records". Status: **VERIFIED** (directly supplied primary statistic).

**Exact caveat from the source file (every row), carried verbatim into the loader docstring
(`data_sources.loaders.load_residex_usable_records`) and into the UI (Housing Lab, section A
expander):** *"This is data-quality coverage, not city HPI index values."* — i.e. this file is
**not** a price series and must never be plotted or read as one; it describes the quality of the
administrative data behind the real composite-index/price-level files already in this registry,
not a new price or affordability metric.

Geography: national (not city-level — the counts are totals across phase-1 cities, not broken
out by city). Frequency: quarterly. Units: record counts and a usable-percent (68-93% range).

### `data/raw/hces/state_ut_urban_mpce_2023_24.csv`

MoSPI Household Consumption Expenditure Survey (HCES) 2023-24, Statement 7: **average monthly
per-capita consumption expenditure (MPCE)**, urban sector, by state/UT — a single cross-section
(survey year 2023-24 only, no time series). Source: "MoSPI HCES 2023-24 Statement 7". Status:
**VERIFIED** (directly supplied primary statistic).

**Exact caveat from the source file (every row), carried verbatim into the loader docstring
(`data_sources.loaders.load_hces_urban_mpce`), into `analysis.housing.INCOME_PROXY_CAVEATS["mpce"]`,
and into the UI (Housing Lab, section B toggle):** *"Use only as an urban state/UT consumption
proxy; do not label as city household income."* This is **consumption expenditure, not income**,
and **state/UT-level, not city-level**.

Geography: state/UT (32 states/UTs + All-India). Frequency: single cross-section, survey year
2023-24. Units: ₹/month per capita.

**How it's used**: `analysis/housing.py`'s `city_affordability()` / `affordability_across_cities()`
now accept an additive `income_source` parameter (`"nsdp"`, the default and original behaviour, or
`"mpce"`) plus an optional `mpce_urban` DataFrame — this is a **second, alternative** income proxy
alongside the pre-existing state-NSDP proxy, not a replacement; both carry their own explicit
caveat (`INCOME_PROXY_CAVEATS`) threaded into every result and into the Housing Lab UI. Because
MPCE is a single 2023-24 cross-section, it **cannot** be used for the RPIPI time series below —
only for the cross-sectional price-to-income ranking, EMI calculator, and ICHASI stress score.

---

## ICHASI / RPIPI (new analysis, `analysis/housing.py`)

The user supplied a full methodology spec for an "India City Housing Affordability Stress Index"
(ICHASI, 0-100, percentile-clipped) and a fallback "Relative Price-to-Income Pressure Index"
(RPIPI). Only the parts honestly computable from real data **already in this repository** were
built — nothing here reconstructs a mortgage-rate history or a city benchmark price level that
doesn't exist (see "Still specifically needed" below).

**`relative_price_income_pressure()` (RPIPI)** — status **DERIVED**. Pure time series:
`RPIPI_c,t = 100 × (HPI_c,t/HPI_c,0) / (Y_c,t/Y_c,0)`, using the real RESIDEX **composite index**
(`load_residex_index()`, 2013-2024) for price and the real state NSDP time series
(`load_nsdp_current()`, or `load_nsdp_spliced()` via the `income_value_col` parameter) for income,
via `CITY_TO_STATE`. Base period `0` = the earliest financial year both series cover for that
city (not one fixed calendar year for every city). The quarterly index is averaged within each
Indian financial year (April-March) to align it with the annual income series — a documented,
transparent calculation, not an estimate. 100 = price and income grew equally since the base
period; >100 = price outpaced income; <100 = income outpaced price. No benchmark price level or
rate assumption is needed for this function — the repo already has real absolute RESIDEX price
levels and a real composite index, so the spec's "Step 1: standardise via a benchmark HPI ratio"
is unnecessary here.

Sample real value computed and sanity-checked while building this: **Mumbai, base FY2013-14 = 100,
latest FY2024-25 RPIPI ≈ 57.7** — i.e. Maharashtra's per-capita NSDP (current prices) grew
considerably faster (≈147%, ₹1,25,261 → ₹3,09,340) than Mumbai's RESIDEX composite index (≈42.5%,
79.25 → 112.99) over that window, so by this measure income outpaced price for Mumbai, not the
reverse. Read this as a real, computed finding from the two source series, not an assumption.

**`stress_index_cross_section()` (ICHASI fallback)** — status **DERIVED**. A percentile-clipped
0-100 affordability stress score **across cities at one quarter** (not over time), reusing
`city_affordability()`/`price_to_income_ratio()` with the user-supplied annual mortgage rate,
tenure and down-payment — exactly the sliders already on the Housing Lab page, not a historical
rate series. Each city's price-to-income ratio is clipped to the [5th, 95th] percentile of the
comparison set, then rescaled linearly to 0-100, so one extreme-outlier city cannot compress
every other city's score toward zero. Explicitly labelled, in both the docstring and the UI
(`RATE_DISCLOSURE`), as using **one representative, currently-selected rate**, not an observed
historical lender panel — a stated simplification given what data exists, not a disguised
fabrication.

Both ship with dataclass results (`RpipiResult`, `StressIndexResult`, matching the
`SigmaConvergenceResult`/`BetaConvergenceResult` pattern in `analysis/regional.py`) and tests in
`tests/test_housing.py` (base-period normalisation, known-value formula checks, percentile-clip
behaviour against an injected extreme outlier, and insufficient-data handling).

---

## World Inequality Lab, India (`data/raw/wil/`, Wealth Lab section W) — VERIFIED

Source: Bharti, Chancel, Piketty & Somanchi (2024), *Income and Wealth Inequality in India, 1922-2023:
The Rise of the Billionaire Raj*, WIL Working Paper 2024/09 (PDF supplied by the author). Tables were
extracted from the PDF's text layer by `scripts/extract_wil_tables.py` — no number retyped by hand — and
Tables 2–3 were compared against the rendered page (printed p. 40).

| File | Paper table | Coverage |
|---|---|---|
| `table2_income_2022_23.csv` | Table 2 (p. 40) | adults, income share, threshold, average income, ratio to average — Average … Top 0.001% |
| `table3_wealth_2022_23.csv` | Table 3 (p. 40) | same for net wealth |
| `tableB1_income_shares_1951_2022.csv` | Table B.1 (pp. 70–71) | Bottom 50 / Middle 40 / Top 10 / Top 1 / Top 0.1 income shares, every year |
| `tableC1_wealth_shares_1961_2023.csv` | Table C.1 (p. 76) | wealth shares: 1961, 1971, 1981, 1991 (survey years), 2002–2023; `tentative` = 2023 (authors' note) |
| `tableC2_vhnwi_1988_2022.csv` | Table C.2 (p. 77) | Forbes billionaire count and wealth % NNI; Hurun count and % NNI (blank where '*') |
| `long_run_facts.csv` | text | growth rates, wealth-income ratio, pre-1951 top 1% shares; each row has a qualifier and section |

Derived in `analysis/inequality.py` (formula shown on the page): Upper middle P90–P99 = Top 10% − Top 1%.
**Bottom 10% and Lower middle (P10–P50) are DATA REQUIRED** — the paper does not split the bottom half.

Checks (`tests/test_inequality.py`): Bottom 50 + Middle 40 + Top 10 = 100 ± 0.1 in every year of B.1 and
C.1; Top 0.1 ≤ Top 1 ≤ Top 10 everywhere; the 2022 rows of B.1/C.1 equal Tables 2/3. **In-paper
inconsistency:** Middle 40% average income ₹1,65,273 implies 28.2% of income against the printed 27.3%
(0.9 pp); other groups agree within 0.2 pp. The Bottom 50% wealth threshold (−₹4.1 crore) is a single AIDIS
outlier, per the paper's note.

The earlier user-supplied summary (`distribution_2022_23.csv`, `wealth_shares_1961_2022_23.csv`) was
removed. It mixed Table 3 with the tentative 2023 row of C.1 (Top 10% wealth 64.6% and Top 0.1% 29.0% are
2023 values; 2022-23 is 65.0% and 29.7%) and had several approximate or wrong figures — listed on the page
under "What changed from the earlier summary".

## New loader: `load_real_percapita_nni()` (Economic Relationships Lab) — PARTIAL

No new data. `data_sources.loaders.load_real_percapita_nni()` reads the existing
`data/raw/real_percapita_nni_timeseries.csv` (all-India real per-capita NNI, ₹ at constant prices,
status **PARTIAL** since the first registry entry: source inferred as MoSPI National Accounts, not
confirmed). The only processing is display-format parsing — `'2011–12'` → `'2011-12'` and
`'₹63,462'` → `63462` — with the published cells kept alongside (`financial_year_as_published`,
`value_as_published`). The file has seven non-consecutive financial years (2011-12, 2014-15,
2019-20, 2020-21, 2022-23, 2023-24, 2024-25); missing years stay missing.

Used only by the Relationships Lab hypothesis "real per-capita NNI vs Top 10% income share"
(`analysis/hypotheses.py`), which matches financial year Y-(Y+1) to WIL calendar year Y (the
paper's Table 2, labelled 2022-23, equals the 2022 row of Table B.1). Five years overlap, and only
one consecutive-year change exists, so the page reports n = 5 and marks the first-difference
check as not computable rather than bridging the gaps.

## New: latest monthly releases (`data/raw/macro_monthly/`, Macro & World "Now" section)

- `india_macro_monthly.csv` — CPI (Aug 2026, base 2024=100, provisional), IIP (Aug 2026 quick estimates,
  **base 2022-23=100** — the 2011-12 base in the supplied note is outdated), RBI household
  inflation-expectations survey (Sep and Jul 2026 rounds). Each row has `status`, `base`, `release_type`,
  `release_date` and `source`.
- `rbi_policy_decisions.csv` — dated RBI policy-rate decisions. One so far: 7 Oct 2026, +25 bp to 5.50%
  (SDF 5.25%, MSF/Bank Rate 5.75%). Daily and monthly tables are **built** from decisions in
  `analysis/macro_monthly.py`; days before the first loaded decision stay blank, and monthly averages
  appear only for complete months.
- `release_calendar.csv` — scheduled releases (CPI for Sep 2026 on 12 Oct 2026). Never an observed value.

Status: **VERIFIED** for CPI (MoSPI press release on PIB surfaced by web search, 9 Oct 2026); **PARTIAL**
for IIP, the policy decision and the survey (confirmed by several reports quoting the official release; the
primary documents were not opened — the sandbox cannot reach mospi.gov.in or rbi.org.in). The August CPI
release date (stated as 2 Oct 2026) is not confirmed and is left blank.

## New: live World Bank WDI provider (`data_sources/worldbank.py`, page 12)

Nothing is stored in the repository. The India Macro & World page calls the World Bank API v2
(`api.worldbank.org/v2`, no key, no environment variable) for 12 annual indicators (real GDP growth,
GDP per capita PPP, CPI inflation, ILO-modelled unemployment, current account % GDP, total reserves,
official exchange rate, trade / exports / imports % GDP, central-government debt % GDP, Gini) for India
and up to six peers. Status of every value: **VERIFIED at source** (World Bank's published value), shown
with the API's `lastupdated` date and the UTC retrieval time.

- **No fallback.** Any failure (timeout, network, HTTP, API error message, schema mismatch) shows
  *DATA UNAVAILABLE* and no numbers; partial results are never shown. Successful responses are cached 6 h.
- `null` stays missing (gaps in lines, "no data" in cards).
- These are harmonised series and can differ from MOSPI/RBI headline releases (unemployment is ILO
  modelled, not PLFS; central-government debt excludes states).
- **Not verified live from the build sandbox**, which has no route to the World Bank. Parsing is tested
  against the documented schema (`tests/test_worldbank.py`); the first live check happens on deploy.

## Everything from the previous registry entry

(RESIDEX city index 2013-2024/2025-2026, RESIDEX city price levels by unit size, RBI Handbook Table 26 constant-price NSDP 2004-05→2022-23 as originally published in two base-year blocks, bank earnings — reported and ESTIMATED — PLFS unemployment, real per-capita NNI, GDP CAGR) is unchanged; see git history or the files directly in `data/raw/` for the full per-file writeup.

## Still specifically needed

1. **EPWRF/NSS employment-by-sector table** as an actual file (still only cited, not received).
2. **Full 2018-2024 bank panel, all 5 BFPI indicators** (still only 3 recent quarters, 2 indicators).
3. Confirmation of which NSDP current-price vintage is authoritative (old file vs. new screenshot) — optional; I'll keep using the screenshot as current unless told otherwise.
4. The underlying table for the employment-by-sector chart, if you want that series at all.
5. **Mortgage-rate-history dataset.** No such dataset has been supplied or built — the ICHASI
   cross-section (`analysis.housing.stress_index_cross_section`) uses one representative,
   currently-selected rate instead (see `RATE_DISCLOSURE` in that module and section E of the
   Housing Lab page), and that is the honest ceiling on what can be shown until this arrives. The
   user specified, in detail, exactly how a proper version should be built — this is recorded
   here as a **specification for future data collection**, not data in hand, and nothing in this
   codebase computes a historical rate series from it or from any other assumption.

   **Required structure** — a fixed lender panel, with one row per (lender, product, observation
   date), carrying these fields:
   - `lender`
   - `product_definition`
   - `posted_floating_rate` (or a `min_rate`/`max_rate` range)
   - `observation_date`
   - `borrower_profile` / `slab` (e.g. salaried vs. self-employed, loan-amount slab, credit-score
     band — whatever segmentation the lender publishes the rate against)
   - `min_rate`, `max_rate`, `representative_midpoint_rate`
   - `is_standard_rate` (a flag distinguishing the lender's standard/headline rate from a
     promotional or segment-specific one)

   **Required aggregation** — an unweighted mean across lenders, per year:
   `r_t = (1/N_t) × Σ_b r_b,t` (sum over lenders `b` observed in year `t`, `N_t` lenders that
   year).

   **Required disclosure label**, to use verbatim on any chart, table or UI copy once/if this
   dataset ever arrives — do not paraphrase it:

   > "Representative advertised floating home-loan rate, fixed lender panel; not an official
   > volume-weighted average rate paid by all mortgage borrowers."

   **Explicitly NOT used as data**: the user separately mentioned a "contextual, non-statistical"
   10.5%→7.35% range spanning 2015-2026. They were explicit that this is not a real series, and
   it has **not** been used anywhere in this codebase as if it were one — no function in
   `analysis/housing.py` reconstructs a historical rate from it or from any other assumption.
