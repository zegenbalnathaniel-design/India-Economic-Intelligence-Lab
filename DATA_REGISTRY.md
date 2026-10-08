# Data Registry

Every real dataset in this repository, with full provenance. Status values:

- **VERIFIED** — real source data, source confirmed.
- **PARTIAL** — real-looking data; source or coverage not fully confirmed.
- **ESTIMATED** — explicitly modelled/interpolated, not reported. Never shown as VERIFIED or DERIVED.
- **SPLICED** — a derived series built by linking two real but methodologically different source series; the exact linking method is documented, not hidden.

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

## Everything from the previous registry entry

(RESIDEX city index 2013-2024/2025-2026, RESIDEX city price levels by unit size, RBI Handbook Table 26 constant-price NSDP 2004-05→2022-23 as originally published in two base-year blocks, bank earnings — reported and ESTIMATED — PLFS unemployment, real per-capita NNI, GDP CAGR) is unchanged; see git history or the files directly in `data/raw/` for the full per-file writeup.

## Still specifically needed

1. **EPWRF/NSS employment-by-sector table** as an actual file (still only cited, not received).
2. **Full 2018-2024 bank panel, all 5 BFPI indicators** (still only 3 recent quarters, 2 indicators).
3. Confirmation of which NSDP current-price vintage is authoritative (old file vs. new screenshot) — optional; I'll keep using the screenshot as current unless told otherwise.
4. The underlying table for the employment-by-sector chart, if you want that series at all.
