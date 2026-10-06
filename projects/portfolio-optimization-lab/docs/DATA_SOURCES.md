# Data Sources

## Price data

| Source | Status | Notes |
|---|---|---|
| Yahoo Finance via `yfinance` | **Live, best-effort** | Primary source. Covers US (NYSE/Nasdaq), India (NSE `.NS` / BSE `.BO`), London (`.L`), Tokyo (`.T`), Hong Kong (`.HK`) reasonably well; Shanghai (`.SS`) coverage is patchier even with normal internet access. |
| Deterministic synthetic GBM | **Fallback, clearly labelled** | Used per-ticker whenever the live fetch fails for any reason (no network, delisting, rate limit, provider gap). Seeded by `sha256(ticker)` for reproducibility. See `data_loader.py`. |

**In this specific hosted demo environment**: outbound requests to Yahoo Finance are blocked by the container's network egress policy (confirmed: a direct `yfinance` request here returns a 403 from the proxy). Every price series you see when running this app *in this environment* is therefore synthetic — the app's "Data status" panel says so explicitly on every run, with a per-ticker breakdown. Run this project with normal internet access (your own machine, a CI runner without an egress allowlist, etc.) to get real live-fetched prices; no code change is required — `load_price_history(..., allow_live=True)` will simply start succeeding.

## FX rates

| Source | Status | Notes |
|---|---|---|
| Yahoo Finance FX tickers (`INR=X`, `JPY=X`, `CNY=X`, `HKD=X`, `GBPUSD=X`) | **Live, best-effort** | Same network caveat as above. |
| Flat illustrative snapshot rate | **Fallback, clearly labelled** | `universe.ILLUSTRATIVE_FX_PER_USD` — order-of-magnitude placeholders (e.g. ~83 INR/USD), not live quotes. Used only when the live FX fetch fails, and only for the currency pairs where it fails. |

## Ticker universe

`universe.py`'s `UNIVERSE` list is a hand-picked set of real, well-known, large-cap tickers per exchange group (e.g. Reliance Industries, TCS, HSBC, Toyota, Tencent) — chosen for name recognition and typical data availability, not for any investment merit. Nothing about their inclusion is a recommendation. Add or remove tickers freely; the optimizer does not care which specific names are in the universe.

## What would make this "real"

To turn this project's numbers into a genuine empirical analysis rather than a demonstration:

1. Run it with normal internet access so `yfinance` actually fetches live prices (the Data status panel will confirm this per ticker).
2. Treat the resulting `μ`/`Σ` as a **historical estimate**, not a forecast — see the Limitations section in `docs/METHODOLOGY.md` regarding estimation error.
3. If you need point-in-time accuracy for FX conversion, verify the live FX fetch succeeded (again, visible in the app) rather than relying on the illustrative snapshot.
