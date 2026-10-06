"""Price (and FX) data loading, with an explicit live/synthetic distinction.

**Design**: always attempt a real fetch via `yfinance` first. If that fails
— no network, ticker delisted, rate-limited, exchange not covered by the
provider — fall back to a clearly-labelled **synthetic** price series for
that ticker only, and report the live/synthetic split back to the caller.
The caller (the Streamlit app, a notebook, a test) must surface that split
to the user; nothing in this module silently presents synthetic data as
real.

This two-tier design exists because several of the exchange groups this
project supports (Shanghai in particular) have patchy coverage even when
the network is available, and because this specific demo environment's
network policy blocks outbound requests to Yahoo Finance entirely — see
`docs/DATA_SOURCES.md` for the exact constraint and what to expect when you
run this yourself with normal internet access.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .universe import BY_TICKER, ILLUSTRATIVE_FX_PER_USD, currency_of

# Illustrative per-exchange-group annualized (drift, volatility) used ONLY
# to generate the synthetic fallback series. Order-of-magnitude choices
# loosely consistent with long-run reported equity-market statistics for
# each region; NOT fitted to any specific dataset and NOT a forecast.
SYNTHETIC_DRIFT_VOL: Dict[str, Tuple[float, float]] = {
    "NASDAQ": (0.10, 0.19),
    "NYSE": (0.08, 0.17),
    "NSE": (0.12, 0.22),
    "BSE": (0.12, 0.22),
    "LSE": (0.06, 0.15),
    "JPX": (0.05, 0.17),
    "SSE": (0.06, 0.28),
    "HKEX": (0.07, 0.26),
}


def _seed_from_ticker(ticker: str) -> int:
    """Deterministic seed so the same ticker always gets the same synthetic
    path (reproducibility), without every ticker sharing one seed (which
    would make all synthetic assets perfectly correlated)."""
    return int(hashlib.sha256(ticker.encode()).hexdigest(), 16) % (2 ** 32)


def synthetic_price_series(ticker: str, start: str, end: str) -> pd.Series:
    """Deterministic geometric Brownian motion path for one ticker,
    parameterized by its exchange group's illustrative (drift, vol)."""
    if ticker not in BY_TICKER:
        raise KeyError(f"Unknown ticker: {ticker}")
    asset = BY_TICKER[ticker]
    drift, vol = SYNTHETIC_DRIFT_VOL.get(asset.exchange, (0.08, 0.20))

    dates = pd.bdate_range(start, end)
    n = len(dates)
    if n == 0:
        raise ValueError("start/end produced zero business days.")
    rng = np.random.default_rng(_seed_from_ticker(ticker))
    dt = 1.0 / 252
    shocks = rng.normal((drift - 0.5 * vol ** 2) * dt, vol * np.sqrt(dt), size=n)
    log_price = np.cumsum(shocks)
    price = 100.0 * np.exp(log_price)  # start every synthetic series at an index value of 100
    return pd.Series(price, index=dates, name=ticker)


def fetch_prices_live(tickers: List[str], start: str, end: str) -> Dict[str, pd.Series]:
    """Attempt a real fetch via yfinance. Returns only the tickers that
    succeeded with a non-empty series; never raises for an individual
    ticker failure (the caller decides what to do about gaps)."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    out: Dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if df is not None and not df.empty and "Close" in df.columns:
                series = df["Close"]
                if isinstance(series, pd.DataFrame):  # yfinance sometimes returns a 1-col frame
                    series = series.iloc[:, 0]
                if len(series.dropna()) > 5:
                    out[ticker] = series.dropna()
        except Exception:
            continue  # fall through to synthetic for this ticker
    return out


@dataclass
class LoadResult:
    prices: pd.DataFrame      # wide, one column per ticker, forward-filled, common date index
    status: Dict[str, str]    # ticker -> "live" or "synthetic"


def load_price_history(tickers: List[str], start: str, end: str, allow_live: bool = True) -> LoadResult:
    """Load price history for every ticker, live where possible and
    synthetic (clearly flagged) everywhere else."""
    if not tickers:
        raise ValueError("tickers must be non-empty.")

    live = fetch_prices_live(tickers, start, end) if allow_live else {}
    series_map: Dict[str, pd.Series] = {}
    status: Dict[str, str] = {}
    for t in tickers:
        if t in live:
            series_map[t] = live[t]
            status[t] = "live"
        else:
            series_map[t] = synthetic_price_series(t, start, end)
            status[t] = "synthetic"

    prices = pd.DataFrame(series_map).sort_index().ffill().dropna(how="any")
    if prices.empty:
        raise ValueError("No overlapping price history across the requested tickers.")
    return LoadResult(prices=prices, status=status)


def load_fx_rates(currencies: List[str], start: str, end: str, allow_live: bool = True) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Local-currency-per-USD rate series for each currency (USD itself is
    always 1.0). Attempts a live fetch via the standard Yahoo Finance FX
    ticker convention (`INR=X`, `JPY=X`, ... ; GBP and a few others are
    quoted the other way round, handled below), falling back to a flat
    illustrative snapshot rate.
    """
    status: Dict[str, str] = {}
    dates = pd.bdate_range(start, end)
    cols: Dict[str, pd.Series] = {"USD": pd.Series(1.0, index=dates)}
    status["USD"] = "identity"

    fx_ticker_map = {"INR": "INR=X", "JPY": "JPY=X", "CNY": "CNY=X", "HKD": "HKD=X", "GBP": "GBPUSD=X"}

    for ccy in currencies:
        if ccy == "USD" or ccy in cols:
            continue
        fetched = None
        if allow_live and ccy in fx_ticker_map:
            live = fetch_prices_live([fx_ticker_map[ccy]], start, end)
            if fx_ticker_map[ccy] in live:
                s = live[fx_ticker_map[ccy]].reindex(dates).ffill()
                fetched = (1.0 / s) if ccy == "GBP" else s  # GBPUSD=X is USD-per-GBP; invert to GBP-per-USD
        if fetched is not None:
            cols[ccy] = fetched
            status[ccy] = "live"
        else:
            flat_rate = ILLUSTRATIVE_FX_PER_USD.get(ccy, 1.0)
            cols[ccy] = pd.Series(flat_rate, index=dates)
            status[ccy] = "illustrative_snapshot"

    return pd.DataFrame(cols).ffill(), status


def convert_prices_to_base_currency(
    prices: pd.DataFrame, base_currency: str, fx_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Convert every ticker's local-currency price series into
    `base_currency` using the per-date FX table from `load_fx_rates`.

    `fx_rates` columns are "units of currency per 1 USD." To convert a
    price `P` quoted in currency `C` into `base_currency` `B`:

        P_in_USD = P / fx_rates[C]
        P_in_B   = P_in_USD * fx_rates[B]
    """
    if base_currency not in fx_rates.columns:
        raise KeyError(f"No FX rate loaded for base currency {base_currency!r}.")
    out = {}
    fx_aligned = fx_rates.reindex(prices.index).ffill()
    for ticker in prices.columns:
        ccy = currency_of(ticker)
        p_usd = prices[ticker] / fx_aligned[ccy]
        out[ticker] = p_usd * fx_aligned[base_currency]
    return pd.DataFrame(out)
