# India Economic Intelligence Lab

This repository holds two things:

| | |
| --- | --- |
| **`web/`** | **IEIL — the India Economics Intelligence Lab web application.** An interactive research laboratory: two live economic models, a research paper whose central figure is a working instrument, a sourced data explorer and a command palette over the whole lab. React + TypeScript + Vite. See [`web/README.md`](web/README.md). |
| everything else | The original Python / Streamlit computational supplement — the analysis modules, illustrative bank panel and methodology notes the web application grew out of. |

```bash
# the web application
cd web && npm install && npm run dev

# the Python supplement
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```

The two share a subject and a discipline but not a codebase: the web application
reimplements its mathematics in TypeScript so that every model runs in the reader's
browser, with the working shown and the assumptions editable.

---

**An interactive computational economics research portfolio.**

An exploration of how economic theory can be translated into quantitative models, simulations and empirical analysis using Indian economic and financial data. This repository is the computational supplement to two written research papers — it is not a commercial product, a financial-advice platform, or a general economics dashboard.

> I did not build a dashboard to display economic data. I built an interactive computational environment to investigate economic questions from my own research.

---

## What the site does

Two research questions drive every interactive module:

1. **Wealth & inequality.** *How do income, ownership, asset composition and returns on capital influence wealth accumulation and economic mobility in India?* Interactive composition-effect simulator, asset-allocation comparison and r − g explorer.
2. **Banking & monetary policy.** *To what extent did policy rate changes influence bank financial performance during 2018-2024?* Adapts the BFPI methodology from the accompanying JP Morgan / Federal Reserve paper to a five-bank Indian panel (the **iBFPI**), and compares the aggregate iBFPI to the RBI repo rate with a rate-regime split.

---

## Running it locally

```bash
git clone <this repo>
cd india-economic-intelligence-lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m data_sources.build_illustrative_data   # regenerates the shipped CSVs deterministically
streamlit run app/Home.py
```

Runs on Python 3.11+. No API keys, no external services.

---

## Repository structure

```
india-economic-intelligence-lab/
│
├── app/                    Streamlit UI (Home + 6 pages)
│   ├── Home.py
│   ├── components/         theme + shared UI helpers
│   └── pages/              1_Wealth_Inequality_Lab.py ... 6_About.py
│
├── analysis/               Domain logic
│   ├── wealth.py           composition effect, r − g
│   └── banking.py          iBFPI robust z-score, Spearman, regime split
│
├── data/
│   ├── raw/                (empty — user-supplied)
│   ├── processed/          bank_panel.csv, repo_rate.csv
│   └── cache/              (empty — future API-cached pulls)
│
├── data_sources/           Loaders + illustrative-panel builder
├── models/                 (reserved for future extensions)
├── tests/                  Unit tests for analysis modules (pytest)
├── docs/                   Notes on figures and methodology
│
├── README.md
├── methodology.md
├── data_dictionary.md
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Site structure

| Page | Purpose |
| --- | --- |
| Home | Introduction and the three research themes: wealth, banking, method. |
| Wealth & Inequality Lab | Income → wealth framework · composition effect · asset allocation · r − g. |
| Banking & Monetary Policy Lab | iBFPI construction · aggregate & per-bank time series · repo-rate comparison · regime split. |
| Research | The two underlying papers + a conservative evaluation table (SUPPORTS / MIXED / CONTRADICTS / INSUFFICIENT DATA). |
| Methodology | Every formula, every direction coefficient, every assumption — separated into *from the papers* vs *new here*. |
| Data | Source registry with dates, units and retrieval notes. |
| About | Stack, reproducibility, licence, citation. |

---

## Methodologies implemented

- **Composition-effect simulation** — deterministic future-value with annual rebalancing across six asset classes; nominal and real path.
- **r − g on a consistent basis** — Fisher-style deflation before comparison; identity reported, no causal claim.
- **Robust z-score** — `Z* = D · (X − median) / (1.4826 · MAD)`, standardised **per bank** so within-bank history is the reference.
- **iBFPI composite** — equal-weight mean of five standardised indicators (PPNR / assets, CET1, NCO rate, LCR, unrealised losses / CET1).
- **Cross-bank aggregation** — equal or user-weighted mean across banks.
- **Spearman rank correlation** with two-sided p-value.
- **Rate-regime classification** using the three-quarter rolling change in the repo rate (±25bp threshold).

---

## What comes from my research vs what is new here

| Component | Origin | User-editable |
| --- | --- | --- |
| Composition-effect exhibit | **Paper A** | Contribution, horizon, weights, returns, inflation |
| Asset-allocation comparison | New here | Same parameters |
| r − g explorer | Framing from Paper A + literature | r, π, g |
| BFPI robust z-score construction | **Paper B** | Direction coefficients fixed |
| iBFPI (India application) | New here | Bank subset, weighting |
| RBI rate × iBFPI Spearman + regime split | New here | Bank subset, weighting |
| Illustrative bank panel | New here (synthetic) | Replace CSVs to reproduce with real data |

---

## Data sources

Every value on the site is either an author calculation from user-supplied assumptions, or drawn from an official source listed on the Data page. Priority sources: **RBI DBIE**, **RBI Basel III disclosures**, **bank annual reports**, **MOSPI**, **Economic Survey**, **SEBI / NSE / BSE**, **World Bank / IMF / BIS**, **Federal Reserve FRED**.

The MVP ships with an **illustrative synthetic panel** so the methodology can be exercised without API keys. Replace the two CSVs in `data/processed/` with real values to reproduce.

---

## Assumptions

- Long-run nominal returns used as defaults are indicative reference points from historical averages, not forecasts. Every value is editable.
- Household simulations use annual contributions at year-start with annual compounding and optional annual rebalancing.
- Bank indicators are standardised within each bank's own history — cross-bank levels are not directly comparable in absolute terms.
- Fees, taxes and transaction costs are omitted from the wealth-path calculation.
- The regime split uses a fixed ±25bp threshold; alternative thresholds change the labels.

---

## Limitations

- **Correlation is not causation.** No causal identification is implied by any coefficient reported on the site.
- **Historical returns are not future returns.** The composition-effect simulator is deterministic given the assumptions supplied.
- Top-tail wealth is systematically undercovered in most Indian survey data — a Gini computed from surveys should be read with that caveat.
- Small samples: the iBFPI comparison spans ≈26 quarters; regime-conditional correlations are computed on subsets and should be interpreted cautiously.
- Cross-bank accounting differences and structural breaks (IND-AS transition, Covid-era accounting relief) are not adjusted for.
- Autocorrelation in quarterly series inflates effective sample size; Spearman ρ p-values do not correct for this.
- Composite indices are subjective — equal weights are a choice; the direction coefficients are a choice; results depend on both.

---

## Suggested future research directions

- Ingest live RBI DBIE and bank-filing data via a scheduled pull; replace the illustrative panel entirely.
- FOMC / RBI MPC event studies around individual rate decisions (see the JP Morgan paper).
- Bank fixed-effects panel regression of iBFPI on the repo rate with macro controls.
- Sensitivity analysis of the composition-effect module to return-distribution assumptions (Monte Carlo, not deterministic).
- A distributional Gini simulation seeded with household-level ownership rates from the AIDIS / NSS surveys.
- Cross-country replication of the BFPI on other emerging-market bank systems.

---

## License

MIT — see [LICENSE](LICENSE).

## Citation

Please cite the underlying research papers when referring to the methodologies, and this repository when referring to any specific interactive result.
