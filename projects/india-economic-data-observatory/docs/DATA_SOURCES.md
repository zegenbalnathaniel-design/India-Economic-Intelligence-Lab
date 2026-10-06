# Data Sources

## Network probe result (read this first)

Before writing any loader code, I tested a plain, unauthenticated
`requests.get()` against the World Bank's open REST API:

```python
import requests
requests.get(
    "https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD?format=json&per_page=5",
    timeout=10,
)
```

**Result in this specific sandboxed environment: it failed.** The exact
error was:

```
ProxyError: HTTPSConnectionPool(host='api.worldbank.org', port=443): Max retries
exceeded with url: /v2/country/IND/indicator/NY.GDP.MKTP.CD?format=json&per_page=5
(Caused by ProxyError('Unable to connect to proxy', OSError('Tunnel connection
failed: 403 Forbidden')))
```

That is a rejection at this container's own outbound egress proxy, before
the request ever reached World Bank's servers — not a World Bank outage
and not an API-format problem. I did not separately re-probe RBI's DBIE
portal or MoSPI's site, since both sit behind the same proxy and the
World Bank API (a plain machine-readable REST endpoint) was already the
most tractable of the three to begin with.

**Practical consequence:** as deployed in this exact sandbox, every
indicator loader below runs its synthetic fallback path on every call,
because the live attempt is blocked before it starts — not because the
pipeline is faked to prefer synthetic data. Nothing about `loaders.py`
special-cases this environment. Run the same code with `allow_live=True`
on a machine with ordinary internet access and the World Bank–backed
indicators (everything below except WPI and the policy rate) will fetch
real data and the returned `Metadata.status` will read `official`.

## Source table

| Indicator | Provider | Source / series | URL | Definition | Unit | Frequency | Date coverage attempted | Transformations | Limitations |
|---|---|---|---|---|---|---|---|---|---|
| GDP | World Bank | World Development Indicators, `NY.GDP.MKTP.CD` | https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD | GDP at purchaser's prices, current US$ | current US$ | annual | as requested | none beyond WB's own conversion | current-US$ mixes real growth with FX/price effects |
| GDP per capita | World Bank | World Development Indicators, `NY.GDP.PCAP.CD` | https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.PCAP.CD | GDP ÷ midyear population, current US$ | current US$ per person | annual | as requested | none | does not adjust for PPP/cost-of-living |
| CPI inflation | World Bank | World Development Indicators, `FP.CPI.TOTL.ZG` | https://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL.ZG | Annual % change in consumer price index | % | annual | as requested | none | annual, not MoSPI's monthly official CPI basket/base-year |
| WPI inflation | MoSPI | Wholesale Price Index bulletins | https://www.mospi.gov.in/ | Annual % change in producer/wholesale price level | % | annual (official release: monthly) | as requested | none | MoSPI publishes WPI as PDF/Excel bulletins, no plain REST/JSON API; this loader performs a real best-effort GET against mospi.gov.in but cannot parse a true series from it — **illustrative-only** |
| Unemployment rate | World Bank | ILO modeled estimate via WDI, `SL.UEM.TOTL.ZS` | https://api.worldbank.org/v2/country/IND/indicator/SL.UEM.TOTL.ZS | Share of labour force without work, seeking work | % of labour force | annual | as requested | none | ILO-modeled, not India's own PLFS rate directly |
| Labour force participation rate | World Bank | ILO modeled estimate via WDI, `SL.TLF.ACTI.ZS` | https://api.worldbank.org/v2/country/IND/indicator/SL.TLF.ACTI.ZS | Share of population 15+ economically active | % of population 15+ | annual | as requested | none | ILO-modeled; India's measured LFPR is sensitive to survey design |
| Fiscal balance | World Bank | World Development Indicators, `GC.BAL.CASH.GD.ZS` | https://api.worldbank.org/v2/country/IND/indicator/GC.BAL.CASH.GD.ZS | Central govt cash surplus/deficit, % of GDP | % of GDP | annual | as requested | none | central government only; differs from India's Budget "fiscal deficit" (gross-borrowing basis) |
| Government debt | World Bank | World Development Indicators, `GC.DOD.TOTL.GD.ZS` | https://api.worldbank.org/v2/country/IND/indicator/GC.DOD.TOTL.GD.ZS | Central govt outstanding debt, % of GDP | % of GDP | annual | as requested | none | central government only; excludes state-government debt |
| Exports | World Bank | World Development Indicators, `NE.EXP.GNFS.CD` | https://api.worldbank.org/v2/country/IND/indicator/NE.EXP.GNFS.CD | Goods & services exports, current US$ | current US$ | annual | as requested | none | BoP basis; mixes volume and price/FX effects |
| Imports | World Bank | World Development Indicators, `NE.IMP.GNFS.CD` | https://api.worldbank.org/v2/country/IND/indicator/NE.IMP.GNFS.CD | Goods & services imports, current US$ | current US$ | annual | as requested | none | BoP basis; mixes volume and price/FX effects |
| Current account balance | World Bank | World Development Indicators, `BN.CAB.XOKA.GD.ZS` | https://api.worldbank.org/v2/country/IND/indicator/BN.CAB.XOKA.GD.ZS | Net exports + net income + net transfers, % of GDP | % of GDP | annual | as requested | none | annual only; hides within-year volatility |
| Exchange rate | World Bank | World Development Indicators, `PA.NUS.FCRF` | https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF | Period-average official rate, INR per US$ | INR per US$ | annual | as requested | none | annual average, not a daily spot rate |
| Policy interest rate | RBI | Database on Indian Economy (DBIE), repo rate | https://dbie.rbi.org.in/ | RBI's benchmark repo rate | % | event-driven (MPC meetings) | as requested | none | DBIE is an interactive BI portal with no stable JSON API; real HTTP GET attempted, cannot parse a series — **illustrative-only** |
| Bank credit growth | World Bank | World Development Indicators, `FS.AST.PRVT.GD.ZS` (derived) | https://api.worldbank.org/v2/country/IND/indicator/FS.AST.PRVT.GD.ZS | YoY change in domestic credit to private sector, % of GDP | p.p. of GDP, YoY change | annual | as requested | first difference (YoY) applied after fetch | proxy for credit growth, not RBI's direct non-food-credit growth rate |

## Why the two non-World-Bank indicators (WPI, policy rate) are architected differently

RBI's Database on Indian Economy and MoSPI's statistics portal are the
correct, real, official sources for WPI and the repo rate respectively —
but neither exposes a plain, unauthenticated, versioned JSON REST API the
way World Bank does. Both are primarily interactive BI-tool front ends
(DBIE) or report-publishing sites (MoSPI) intended for a human clicking
through a UI or downloading a PDF/Excel bulletin, not for a stateless
`GET` from a script.

Rather than silently skip the "attempt live first" step for these two, each
loader still performs a genuine `requests.get()` against the documented
real URL (`sources.probe_rbi_dbie`, `sources.probe_mospi`) — so the
architecture is honest about having tried — but neither function attempts
to scrape a time series out of an HTML BI-portal page, since that would be
far too brittle to be a "real fetch" in any meaningful sense. Both series
are therefore always `illustrative_synthetic` today. A real integration
would need DBIE's documented data-extraction/export flow or a scripted
MoSPI bulletin parser, which is listed under Future Work in the README.

## IMF International Financial Statistics

IMF IFS (https://www.imf.org/en/Data) is the fourth source this project
documents per its design brief, but is not wired into any loader: IFS
requires either the IMF's own API with its own query DSL and dataset
codes, or a manual data-portal export, and overlaps substantially with the
World Bank series already covered. It is listed here for completeness and
as a natural extension point (see README → Future Work).
