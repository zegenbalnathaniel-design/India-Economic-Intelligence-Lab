# Data Sources

## Bundled with this repository

| Source | Provider | Status | URL pattern | Definition | Unit | Frequency | Date coverage | Transformations | Limitations |
|---|---|---|---|---|---|---|---|---|---|
| `data/synthetic_city_housing_baseline.csv` | Generated locally by `examples/generate_synthetic_city_housing.py` | **SYNTHETIC — not real data** | n/a (local script) | Illustrative per-city house price and household income, anchored to hand-picked relative-ordering constants (`INCOME_MULTIPLIER`, `PRICE_TO_INCOME_ANCHOR`) plus seeded Gaussian noise | INR | One static snapshot (no time dimension) | n/a | Deterministic, seeded (seed=2024) generation; rounded to nearest 1,000 | Numbers are illustrative scaffolding only; only the broad relative ordering across cities is meant to echo commonly-reported qualitative patterns — do not treat any value as a real statistic |

This is the **only** data file this project ships. It exists solely so the affordability metrics and the Streamlit app have something runnable out of the box. Every place it is displayed (README, app banners, this file) says SYNTHETIC.

## Where to get real data for a future version (not used here)

This sandbox has no outbound network access to real-estate listing sites, house-price indices, or household-survey portals, so none of the sources below were fetched or used to build anything in this repository. They are listed as a roadmap for a future version that would ingest real data.

| Source | Provider | What it has | URL pattern | Frequency |
|---|---|---|---|---|
| RBI House Price Index (HPI) | Reserve Bank of India, Database on Indian Economy (DBIE) | Quarterly city-level residential property price index for ~10 major Indian cities | dbie.rbi.org.in | Quarterly |
| NHB RESIDEX | National Housing Bank | City-level housing price index, broader city coverage than RBI HPI | nhb.org.in | Quarterly |
| Knight Frank India research reports | Knight Frank | Published city-level housing price and affordability commentary (price-to-income, EMI-to-income) for major metros | knightfrank.co.in | Periodic (published reports) |
| Periodic Labour Force Survey (PLFS) | MoSPI (Ministry of Statistics and Programme Implementation) | Household income/consumption-adjacent microdata, usable as an income proxy at state/city-class level | mospi.gov.in | Annual |
| All-India Debt and Investment Survey (AIDIS) | NSSO | Household assets, liabilities, and borrowing for housing | mospi.gov.in | Periodic (roughly decennial) |
| Ministry of Housing and Urban Affairs (MoHUA) data | Government of India | Urban housing stock, affordable-housing scheme data (PMAY), urbanization statistics | mohua.gov.in | Periodic |

For any dataset actually brought in, record (as in the table above): **source, provider, URL, exact definition, unit, frequency, date coverage, transformations applied, and known limitations.**

## Limitations of available real data generally

- RBI HPI and NHB RESIDEX cover a limited set of major cities and are index numbers (base-year = 100), not absolute prices — converting them into an absolute price-to-income ratio requires anchoring to a base-year price from another source.
- Household income data in India is patchier than consumption data (PLFS and NSSO rounds measure consumption/expenditure more reliably than income); using consumption as an income proxy understates true affordability stress for savings-constrained households.
- None of these sources report a ready-made household-level price-to-income or EMI-to-income ratio — computing one requires combining a price series with an income series collected by a different agency, on a different geography, at a different frequency, which introduces real methodological risk (see README Limitations).
- Informal-sector income and self-built/informal housing are underrepresented in all of the sources above, which mostly reflect the formal, bank-financed segment of the market that this tool's EMI/LTV framing is built around anyway.
