# India Economic Data Observatory

A data ingestion, cleaning and validation platform for Indian economic indicators, built so that a synthetic fallback series can never be mistaken for real, officially-sourced data.

## Research Question

Can a single, small pipeline ingest Indian macroeconomic indicators from several genuinely different official sources — each with its own access method and reliability — while making it structurally impossible for a downstream chart or table to present a synthetic fallback value as if it were real data?

## Why I Built This

I kept running into the same problem across my own small data projects: a chart built from a mix of live and placeholder numbers, with nothing in the chart itself telling the reader which is which. Rather than patch that over one more time, I wanted to build the plumbing properly, once, as its own thing — a loader/validator/visualizer stack where "where did this number come from, and can I trust it" is answered by the same object that produced the chart, not by a comment I have to remember to write. India's own statistical landscape is a good test case for this: GDP, prices, labour, fiscal and external-sector data each come from a different agency (MoSPI, RBI, and cross-country aggregators like the World Bank), with genuinely different access methods and genuinely different reliability, which is exactly the kind of mess a provenance-first pipeline needs to survive.

## Economic Theory

- **Growth** (GDP, GDP per capita): the broadest measure of an economy's output and, divided by population, of average material living standards. Current-US$ GDP conflates real output growth with exchange-rate and price-level movements — a rupee depreciation alone can shrink dollar-GDP without any change in real output.
- **Prices** (CPI, WPI): CPI tracks what a representative *consumer* pays; WPI tracks prices at the *wholesale/producer* level. The gap between them (the "WPI-CPI wedge") is itself a standard signal of where inflation pressure is building — producer costs that haven't yet reached the consumer, or vice versa.
- **Labour** (unemployment rate, labour force participation rate): the unemployment rate alone can mislead when participation is falling — people leaving the labour force (discouraged workers, more time in education, caregiving) lower measured unemployment without any underlying improvement, which is why the two are reported together here.
- **Government** (fiscal deficit, government debt): the deficit is a flow (this year's gap between spending and revenue); debt is the accumulated stock. A government can run a persistent deficit while debt-to-GDP still falls, if nominal GDP grows faster than debt — the two series are complements, not substitutes, for judging fiscal sustainability.
- **External sector** (exports, imports, current account, exchange rate): the current account is the net result of trade in goods/services plus income and transfer flows; a persistent deficit must be financed by capital inflows or reserve drawdown, and the exchange rate is both a cause and a consequence of that balance.
- **Financial system** (policy rate, bank credit growth): the central bank's policy rate is the primary lever for transmitting monetary policy into the real economy; bank credit growth is one of the main channels through which that transmission shows up (or fails to), making the two a natural pair to watch together.

## Methodology

Every indicator goes through the same five-step pipeline: **(1)** attempt a real fetch from the indicator's documented official endpoint; **(2)** fall back to a deterministic, seeded synthetic series only if that fails or is disabled; **(3)** validate and clean the result (sort, de-duplicate periods, flag impossible values, forward-fill gaps with an explicit flag); **(4)** cache the cleaned result on disk, keyed so live and synthetic results never collide; **(5)** return the series bundled with a `Metadata` record whose `status` field is always exactly `official` or `illustrative_synthetic` — never implied, never left for the caller to guess. Full detail, including the theoretical rationale for why this matters for cross-source economic data specifically, is in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Data (full disclosure, this specific environment)

Before writing any loader code, I tested a plain `requests.get()` against the World Bank's open, unauthenticated API (`api.worldbank.org`) — the only one of the four documented sources (World Bank, RBI DBIE, MoSPI, IMF IFS) with a real REST/JSON endpoint. **In this sandboxed build environment, it failed**: the request was rejected by the container's own outbound network proxy (`ProxyError` / `403 Forbidden`) before it ever reached World Bank. I did not separately re-probe RBI or MoSPI, since all three sit behind the same proxy.

**Consequence:** as deployed here, every indicator in this app runs its synthetic fallback on every load, because the live attempt never leaves the sandbox — not because the pipeline prefers synthetic data. Two indicators (WPI, the RBI policy rate) are synthetic-only *regardless of network access*, because their real sources (MoSPI, RBI DBIE) don't expose a plain machine-readable API at all — see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the exact probe output and the full per-indicator source table. The other eleven indicators are wired to real World Bank indicator codes and will fetch live, real data the moment this code runs somewhere with ordinary internet access — nothing about the architecture special-cases this sandbox.

## Results / Demonstration

Running `examples/quickstart.py` in this environment loads GDP, the unemployment rate, and the exchange rate and reports, honestly, that all three came back synthetic here (network blocked) — and prints each series' full metadata caption so you can see exactly what it would have said had the fetch succeeded. The Streamlit app's "Browse Indicators" page shows the same thing live, with a green "LIVE / OFFICIAL" badge or an amber "SYNTHETIC / ILLUSTRATIVE" one on every single chart, no exceptions.

## How It Works

```
src/data_observatory/
  metadata.py     Metadata / DataStatus — the provenance record every series carries
  sources.py      real HTTP fetch functions (World Bank JSON API; RBI/MoSPI best-effort probes)
  synthetic.py    deterministic, seeded fallback series generators
  validation.py   sort / de-duplicate / domain-check / forward-fill-with-flag
  cache.py        on-disk CSV cache, keyed by indicator + date range + live/synthetic status
  loaders.py      ties it together: IndicatorSpec registry + load(key, start, end, allow_live)
  viz.py          Plotly chart helpers that render the Metadata caption on every chart
app/
  Home.py, pages/ Streamlit app: browse, compare, and a Methodology & Sources page
```

## Installation

```bash
cd projects/india-economic-data-observatory
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

## Usage

```python
from data_observatory import loaders, viz

frame, meta = loaders.load("gdp", "2000-01-01", "2023-01-01", allow_live=True)
print(meta.caption())          # one-line provenance string
fig = viz.line_chart(frame, meta)
fig.show()
```

Run the Streamlit app:

```bash
streamlit run app/Home.py
```

Run the tests (no network required):

```bash
python3 -m pytest tests/ -q
```

## Examples

- `examples/quickstart.py` — load three indicators across categories, print their metadata, report the live/synthetic split.
- `notebooks/01_quickstart.ipynb` — the same walkthrough as an executed notebook, including the chart with its metadata caption.

## Limitations

- Synthetic fallback series are stochastic-process approximations chosen for plausible shape, not fitted to or copied from real data — never read them as a forecast or as history.
- World Bank's annual series are coarser than India's own monthly/daily official releases (CPI, FX) and are documented as such per indicator, not silently treated as equivalent.
- WPI and the RBI policy rate are synthetic-only today regardless of network access, because their real sources have no plain REST API — see Data, above.
- IMF IFS is documented as a source but not wired into any loader (overlaps substantially with the World Bank series already covered).

## Future Work

- A scripted RBI DBIE export parser (their documented data-extraction flow) to make the policy-rate loader genuinely live.
- A MoSPI bulletin parser (monthly WPI/CPI PDF or Excel releases) for a true WPI series.
- An IMF IFS loader using their API's own dataset/query codes.
- Quarterly-frequency variants for indicators India's own agencies publish more often than annually.

## Sources

World Bank Open Data (`api.worldbank.org`) · RBI Database on Indian Economy (`dbie.rbi.org.in`) · Ministry of Statistics and Programme Implementation (`mospi.gov.in`) · IMF International Financial Statistics. Full per-indicator table in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## License

MIT — see [`LICENSE`](LICENSE).
