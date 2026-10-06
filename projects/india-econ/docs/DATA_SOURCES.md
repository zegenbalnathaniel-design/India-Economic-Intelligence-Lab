# Data Sources

## Network probe (full disclosure)

Before writing any fetch code, I tested a real unauthenticated request against the World Bank API from the sandbox this package was built in:

```python
requests.get(
    "https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD?format=json&per_page=5",
    timeout=10,
)
```

**Result: it failed.** The request was blocked at the sandbox's outbound proxy with a `403 Forbidden` on the proxy tunnel itself (`ProxyError: Unable to connect to proxy ... Tunnel connection failed: 403 Forbidden`), not a World Bank-side error. That means this is a sandbox network policy restriction, not evidence the World Bank API is unreachable in general. Every example and test run in this sandbox therefore exercises the **synthetic fallback path**, which is why the live-fetch code's correctness is verified with mocked HTTP responses (`tests/test_live_and_caching.py`) rather than a real end-to-end call from this machine.

If you install and run this package somewhere with normal outbound internet access, try `india_econ.gdp().source` -- it should read `"live"`.

## Per-indicator source table

| Function | World Bank indicator code(s) | Provider | URL | Definition | Unit | Frequency | Coverage | Transformations | Limitations | Status in this sandbox |
|---|---|---|---|---|---|---|---|---|---|---|
| `gdp()` | `NY.GDP.MKTP.CD` | World Bank Open Data (WDI) | `https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD` | GDP at current market prices | current US$ | annual | World Bank's full available history for India | `gdp_growth_pct` derived locally via `pct_change() * 100` on the level series | Level in nominal (not inflation-adjusted) US$; a single exchange-rate conversion can shift year-to-year comparisons | synthetic (live blocked in sandbox) |
| `inflation()` | `FP.CPI.TOTL.ZG` | World Bank Open Data (WDI) | `https://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL.ZG` | Consumer price inflation, annual % | % per year | annual | World Bank's full available history for India | none | CPI basket methodology has changed over India's history; not directly comparable to RBI's own CPI release in every period | synthetic |
| `unemployment()` | `SL.UEM.TOTL.ZS` | World Bank Open Data (ILO modeled estimate) | `https://api.worldbank.org/v2/country/IND/indicator/SL.UEM.TOTL.ZS` | Unemployment, % of total labor force (modeled ILO estimate) | % of labor force | annual | World Bank's full available history for India | none | A modeled estimate, not a direct national labor-force-survey figure; India's large informal sector makes any single unemployment number approximate | synthetic |
| `trade()` | `NE.EXP.GNFS.CD`, `NE.IMP.GNFS.CD` | World Bank Open Data (WDI) | `https://api.worldbank.org/v2/country/IND/indicator/NE.EXP.GNFS.CD` / `.../NE.IMP.GNFS.CD` | Exports / imports of goods and services | current US$ | annual | World Bank's full available history for India | none (two series merged into one DataFrame by year) | Balance-of-payments basis; does not break out goods vs. services or by trading partner | synthetic |
| `exchange_rate()` | `PA.NUS.FCRF` | World Bank Open Data (IMF IFS) | `https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF` | Official exchange rate, period average | INR per USD | annual | World Bank's full available history for India | none | Annual average only -- no intra-year volatility; not the same as a spot/closing rate | synthetic |
| `interest_rates()` | `FR.INR.LEND` | World Bank Open Data (WDI) | `https://api.worldbank.org/v2/country/IND/indicator/FR.INR.LEND` | Commercial bank lending interest rate | % per year | annual | World Bank's full available history for India | none | **Proxy, not the RBI policy repo rate** -- the World Bank's open, keyless API does not publish the repo rate directly; this is the closest available open series | synthetic |
| `government_finance()` | `GC.BAL.CASH.GD.ZS`, `GC.DOD.TOTL.GD.ZS` | World Bank Open Data (WDI / IMF GFS) | `https://api.worldbank.org/v2/country/IND/indicator/GC.BAL.CASH.GD.ZS` / `.../GC.DOD.TOTL.GD.ZS` | Central government cash surplus/deficit (% GDP, negative = deficit); central government debt (% GDP) | % of GDP | annual | World Bank's full available history for India | none | Central government only (not general government / state-level); cash basis, which can differ from accrual-basis fiscal deficit figures India's budget documents quote | synthetic |
| `household_finance()` | `NY.GNS.ICTR.ZS`, `FS.AST.PRVT.GD.ZS` | World Bank Open Data (WDI) | `https://api.worldbank.org/v2/country/IND/indicator/NY.GNS.ICTR.ZS` / `.../FS.AST.PRVT.GD.ZS` | Gross domestic savings (% GDP); domestic credit to private sector by banks (% GDP) | % of GDP | annual | World Bank's full available history for India | none | **Proxies, not household-survey data** -- both are economy-wide ratios, not a household balance-sheet series, since no such open series exists in this API | synthetic |

"Status in this sandbox" reflects the network probe above, not a property of the package: on a machine with normal internet access, any of these would be expected to read `"live"` on success and only fall back to `"synthetic"` on an actual fetch failure.

## Synthetic fallback generation

Not a data source in the usual sense, but documented for transparency: when a live fetch fails (or `allow_live=False` is passed), `india_econ._synthetic.synthetic_series()` generates a deterministic series using `numpy.random.default_rng`, seeded from a SHA-256 hash of the indicator and column name. Series either drift at a fixed rate with noise, or mean-revert toward a long-run level with noise (used for rate-like indicators such as inflation or interest rates), using parameters defined per-column in `india_econ._registry.REGISTRY`. These values are illustrative only and are always tagged `status="synthetic"`.
