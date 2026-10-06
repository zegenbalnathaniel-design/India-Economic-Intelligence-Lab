"""The configurable asset universe: real tickers across six exchange
groups, with the currency each one actually trades in. This module only
declares *identifiers* (ticker, name, exchange, currency) — no prices, no
returns. Price history is fetched (or, failing that, synthetically
generated) by `data_loader.py`.

Ticker suffix conventions (as used by most market-data providers,
including Yahoo Finance / `yfinance`, which `data_loader.py` uses when it
can reach the network):

- US — NYSE / Nasdaq: no suffix (e.g. `AAPL`)
- India — NSE: `.NS` suffix (e.g. `RELIANCE.NS`)
- India — BSE: `.BO` suffix (e.g. `ICICIBANK.BO`)
- UK — London Stock Exchange: `.L` suffix (e.g. `HSBA.L`)
- Japan — Japan Exchange Group (Tokyo): `.T` suffix (e.g. `7203.T`)
- China — Shanghai Stock Exchange: `.SS` suffix (e.g. `600519.SS`)
- Hong Kong — Hong Kong Exchanges: `.HK` suffix (e.g. `0700.HK`)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    exchange: str
    currency: str


UNIVERSE: List[Asset] = [
    # United States — NYSE / Nasdaq (USD)
    Asset("AAPL", "Apple Inc.", "NASDAQ", "USD"),
    Asset("MSFT", "Microsoft Corp.", "NASDAQ", "USD"),
    Asset("JPM", "JPMorgan Chase & Co.", "NYSE", "USD"),
    Asset("JNJ", "Johnson & Johnson", "NYSE", "USD"),
    Asset("XOM", "Exxon Mobil Corp.", "NYSE", "USD"),
    Asset("PG", "Procter & Gamble Co.", "NYSE", "USD"),
    # India — NSE (INR)
    Asset("RELIANCE.NS", "Reliance Industries", "NSE", "INR"),
    Asset("TCS.NS", "Tata Consultancy Services", "NSE", "INR"),
    Asset("HDFCBANK.NS", "HDFC Bank", "NSE", "INR"),
    Asset("INFY.NS", "Infosys", "NSE", "INR"),
    # India — BSE (INR)
    Asset("ICICIBANK.BO", "ICICI Bank", "BSE", "INR"),
    Asset("ITC.BO", "ITC Ltd.", "BSE", "INR"),
    # United Kingdom — London Stock Exchange (GBP)
    Asset("HSBA.L", "HSBC Holdings", "LSE", "GBP"),
    Asset("ULVR.L", "Unilever", "LSE", "GBP"),
    Asset("AZN.L", "AstraZeneca", "LSE", "GBP"),
    Asset("BP.L", "BP plc", "LSE", "GBP"),
    # Japan — Japan Exchange Group / Tokyo (JPY)
    Asset("7203.T", "Toyota Motor Corp.", "JPX", "JPY"),
    Asset("6758.T", "Sony Group Corp.", "JPX", "JPY"),
    Asset("9984.T", "SoftBank Group Corp.", "JPX", "JPY"),
    # China — Shanghai Stock Exchange (CNY)
    Asset("600519.SS", "Kweichow Moutai", "SSE", "CNY"),
    Asset("601398.SS", "Industrial & Commercial Bank of China", "SSE", "CNY"),
    # Hong Kong — Hong Kong Exchanges (HKD)
    Asset("0700.HK", "Tencent Holdings", "HKEX", "HKD"),
    Asset("9988.HK", "Alibaba Group", "HKEX", "HKD"),
    Asset("0005.HK", "HSBC Holdings (HK listing)", "HKEX", "HKD"),
]

BY_TICKER: Dict[str, Asset] = {a.ticker: a for a in UNIVERSE}

EXCHANGE_GROUPS: Dict[str, str] = {
    "NASDAQ": "United States (NYSE & Nasdaq)",
    "NYSE": "United States (NYSE & Nasdaq)",
    "NSE": "India (NSE)",
    "BSE": "India (BSE)",
    "LSE": "London Stock Exchange",
    "JPX": "Japan Exchange Group",
    "SSE": "Shanghai Stock Exchange",
    "HKEX": "Hong Kong Exchanges",
}

# Illustrative / approximate FX snapshot: units of local currency per 1 USD.
# Used ONLY as a fallback when a live FX series cannot be fetched (see
# data_loader.py) — never presented as a live quote. Order of magnitude
# matters far more than precision for a teaching tool's currency
# normalization step.
ILLUSTRATIVE_FX_PER_USD: Dict[str, float] = {
    "USD": 1.0,
    "INR": 83.0,
    "GBP": 0.79,
    "JPY": 150.0,
    "CNY": 7.2,
    "HKD": 7.8,
}


def tickers_for_exchanges(exchanges: List[str]) -> List[str]:
    return [a.ticker for a in UNIVERSE if a.exchange in exchanges]


def currency_of(ticker: str) -> str:
    if ticker not in BY_TICKER:
        raise KeyError(f"Unknown ticker: {ticker}. Add it to UNIVERSE in universe.py first.")
    return BY_TICKER[ticker].currency
