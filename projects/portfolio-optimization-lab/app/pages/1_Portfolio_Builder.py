from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio_lab import optimizer as opt
from portfolio_lab.data_loader import load_price_history, load_fx_rates, convert_prices_to_base_currency
from portfolio_lab.universe import UNIVERSE, EXCHANGE_GROUPS, currency_of

st.set_page_config(page_title="Portfolio Builder", page_icon="🧮", layout="wide")
st.title("🧮 Portfolio Builder")

st.sidebar.header("1. Choose your markets")
all_exchanges = sorted(set(a.exchange for a in UNIVERSE), key=lambda e: list(EXCHANGE_GROUPS).index(e))
chosen_exchanges = st.sidebar.multiselect(
    "Exchanges", all_exchanges, default=all_exchanges,
    format_func=lambda e: f"{e} — {EXCHANGE_GROUPS[e]}",
)
candidate_tickers = [a.ticker for a in UNIVERSE if a.exchange in chosen_exchanges]

st.sidebar.header("2. Choose your stocks")
default_pick = candidate_tickers[:6] if len(candidate_tickers) >= 6 else candidate_tickers
tickers = st.sidebar.multiselect("Tickers", candidate_tickers, default=default_pick)

st.sidebar.header("3. Investment")
initial_investment = st.sidebar.number_input("Initial investment", 1_000.0, 100_000_000.0, 100_000.0, step=1_000.0)
base_currency = st.sidebar.selectbox("Base currency", ["USD", "INR", "GBP", "JPY", "CNY", "HKD"], index=0)
rf = st.sidebar.slider("Risk-free rate (%)", 0.0, 10.0, 4.0) / 100

st.sidebar.header("4. Constraints")
long_only = st.sidebar.checkbox("Long-only (no short-selling)", value=True)
max_weight = st.sidebar.slider("Max weight per asset", 0.1, 1.0, 1.0 if not long_only else 0.5)

st.sidebar.header("5. History window")
years_back = st.sidebar.slider("Years of history", 1, 10, 3)
end = date.today()
start = end - timedelta(days=365 * years_back)

if len(tickers) < 2:
    st.warning("Pick at least 2 tickers in the sidebar to build a portfolio.")
    st.stop()

with st.spinner("Loading price history..."):
    result = load_price_history(tickers, start.isoformat(), end.isoformat(), allow_live=True)
    currencies_needed = sorted(set(currency_of(t) for t in tickers) | {base_currency})
    fx_rates, fx_status = load_fx_rates(currencies_needed, start.isoformat(), end.isoformat(), allow_live=True)
    prices_base = convert_prices_to_base_currency(result.prices, base_currency, fx_rates)

st.subheader("Data status")
status_df = pd.DataFrame(
    [{"ticker": t, "exchange": next(a.exchange for a in UNIVERSE if a.ticker == t),
      "currency": currency_of(t), "price_source": result.status[t]} for t in tickers]
)
n_live = (status_df["price_source"] == "live").sum()
if n_live == 0:
    st.warning(
        f"⚠️ All {len(tickers)} tickers are using **synthetic** price data (no live fetch succeeded — "
        "this is expected in this hosted demo environment, whose network policy blocks Yahoo Finance; "
        "run this app with normal internet access to get live prices). See docs/DATA_SOURCES.md."
    )
else:
    st.success(f"{n_live} / {len(tickers)} tickers using live price data; the rest are synthetic fallback.")
st.dataframe(status_df, use_container_width=True, hide_index=True)

mu = opt.expected_returns(prices_base)[tickers]
cov = opt.covariance_matrix(prices_base)[tickers].loc[tickers]

constraints = opt.Constraints(long_only=long_only, max_weight=max_weight, min_weight=0.0 if long_only else -max_weight)

try:
    if long_only or max_weight < 1.0:
        w_minvar = opt.min_variance_weights_constrained(mu.values, cov.values, constraints)
        w_maxsharpe = opt.max_sharpe_weights_constrained(mu.values, cov.values, rf, constraints)
    else:
        w_minvar = opt.min_variance_weights_closed_form(cov.values)
        w_maxsharpe = opt.tangency_weights_closed_form(mu.values, cov.values, rf)
except RuntimeError as exc:
    st.error(f"Optimization failed: {exc}")
    st.stop()

st.session_state["portfolio_lab"] = {
    "tickers": tickers, "mu": mu, "cov": cov, "w_minvar": w_minvar, "w_maxsharpe": w_maxsharpe,
    "rf": rf, "base_currency": base_currency, "initial_investment": initial_investment,
    "constraints": constraints, "exchanges": {t: next(a.exchange for a in UNIVERSE if a.ticker == t) for t in tickers},
}

tab_minvar, tab_maxsharpe = st.tabs(["Minimum-Variance Portfolio", "Maximum-Sharpe (Tangency) Portfolio"])

for tab, w, label in [(tab_minvar, w_minvar, "Minimum-variance"), (tab_maxsharpe, w_maxsharpe, "Maximum-Sharpe")]:
    with tab:
        ret = opt.portfolio_return(w, mu.values)
        vol = opt.portfolio_volatility(w, cov.values)
        sharpe = opt.sharpe_ratio(w, mu.values, cov.values, rf)
        c1, c2, c3 = st.columns(3)
        c1.metric("Expected annual return", f"{ret:.1%}")
        c2.metric("Annual volatility", f"{vol:.1%}")
        c3.metric("Sharpe ratio", f"{sharpe:.2f}")

        alloc = opt.allocate_investment(w, tickers, initial_investment)
        alloc_df = pd.DataFrame({"ticker": tickers, "weight": w, f"amount ({base_currency})": alloc.values})
        fig = go.Figure(go.Pie(labels=alloc_df["ticker"], values=np.maximum(alloc_df["weight"], 0), hole=0.45))
        fig.update_layout(title=f"{label} portfolio allocation", height=380)
        col_a, col_b = st.columns([1, 1])
        col_a.plotly_chart(fig, use_container_width=True)
        col_b.dataframe(alloc_df.style.format({"weight": "{:.1%}", f"amount ({base_currency})": "{:,.0f}"}), use_container_width=True, hide_index=True)

        proj = opt.project_portfolio_value(initial_investment, ret, vol, years=10)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=proj["year"], y=proj["p90"], line=dict(width=0), showlegend=False))
        fig2.add_trace(go.Scatter(x=proj["year"], y=proj["p10"], fill="tonexty", line=dict(width=0), name="10th-90th percentile band"))
        fig2.add_trace(go.Scatter(x=proj["year"], y=proj["expected"], name="Expected path", line=dict(color="black")))
        fig2.update_layout(title=f"Projected value over 10 years ({label}) — analytic, not a Monte Carlo", height=380,
                            xaxis_title="Years", yaxis_title=f"Value ({base_currency})")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "This is a **lognormal projection** from the stated expected return/volatility — "
            "a mechanical implication, not a forecast. See the SIP Monte Carlo project in this "
            "portfolio for a simulation-based treatment with explicit contribution/fee/inflation modelling."
        )

st.divider()
st.caption(
    "Weights for both portfolios are stored in session state for the Efficient Frontier and "
    "Correlation Network pages — visit those next to see the full picture."
)
