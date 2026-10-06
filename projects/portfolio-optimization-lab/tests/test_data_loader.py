"""Unit tests for portfolio_lab.data_loader — focused on the synthetic
fallback path and FX conversion arithmetic (network calls to yfinance are
not exercised in CI; `allow_live=False` is used throughout)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from portfolio_lab import data_loader as dl
from portfolio_lab.universe import UNIVERSE


def test_synthetic_series_deterministic_given_same_ticker():
    s1 = dl.synthetic_price_series("AAPL", "2023-01-01", "2023-06-30")
    s2 = dl.synthetic_price_series("AAPL", "2023-01-01", "2023-06-30")
    assert np.allclose(s1.values, s2.values)


def test_synthetic_series_different_tickers_not_identical():
    s1 = dl.synthetic_price_series("AAPL", "2023-01-01", "2023-06-30")
    s2 = dl.synthetic_price_series("MSFT", "2023-01-01", "2023-06-30")
    assert not np.allclose(s1.values, s2.values)


def test_synthetic_series_rejects_unknown_ticker():
    with pytest.raises(KeyError):
        dl.synthetic_price_series("NOT_A_REAL_TICKER", "2023-01-01", "2023-06-30")


def test_load_price_history_falls_back_to_synthetic_without_network():
    tickers = ["AAPL", "RELIANCE.NS", "7203.T"]
    result = dl.load_price_history(tickers, "2023-01-01", "2023-06-30", allow_live=False)
    assert set(result.status.values()) == {"synthetic"}
    assert list(result.prices.columns) == tickers
    assert len(result.prices) > 0


def test_load_price_history_rejects_empty_ticker_list():
    with pytest.raises(ValueError):
        dl.load_price_history([], "2023-01-01", "2023-06-30")


def test_all_universe_tickers_produce_synthetic_series():
    for asset in UNIVERSE:
        s = dl.synthetic_price_series(asset.ticker, "2023-01-01", "2023-03-31")
        assert len(s) > 0
        assert (s > 0).all()


def test_fx_rates_identity_for_usd():
    fx, status = dl.load_fx_rates(["USD", "INR"], "2023-01-01", "2023-03-31", allow_live=False)
    assert (fx["USD"] == 1.0).all()
    assert status["USD"] == "identity"
    assert status["INR"] == "illustrative_snapshot"


def test_convert_prices_to_base_currency_identity_when_already_base():
    dates = pd.bdate_range("2023-01-01", periods=5)
    prices = pd.DataFrame({"AAPL": [100, 101, 102, 103, 104]}, index=dates)
    fx = pd.DataFrame({"USD": [1.0] * 5}, index=dates)
    converted = dl.convert_prices_to_base_currency(prices, "USD", fx)
    assert np.allclose(converted["AAPL"].values, prices["AAPL"].values)


def test_convert_prices_to_base_currency_scales_correctly():
    dates = pd.bdate_range("2023-01-01", periods=3)
    # RELIANCE.NS is INR-denominated; convert to USD at a flat 83 INR/USD.
    prices = pd.DataFrame({"RELIANCE.NS": [830.0, 831.0, 829.0]}, index=dates)
    fx = pd.DataFrame({"USD": [1.0] * 3, "INR": [83.0] * 3}, index=dates)
    converted = dl.convert_prices_to_base_currency(prices, "USD", fx)
    assert math.isclose(converted["RELIANCE.NS"].iloc[0], 830.0 / 83.0)
