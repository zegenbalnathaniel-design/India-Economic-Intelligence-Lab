"""portfolio_lab — Modern Portfolio Theory, implemented from scratch.

Expected return, covariance, Sharpe ratio, the minimum-variance and
maximum-Sharpe portfolios (derived via Lagrange multipliers), and the
efficient frontier, over a configurable multi-exchange stock universe
(US, India NSE/BSE, London, Tokyo, Shanghai, Hong Kong).

**Educational tool — not investment advice.** See docs/METHODOLOGY.md for
every formula and docs/DATA_SOURCES.md for exactly which data is live vs.
synthetic in any given run.
"""
from .optimizer import (
    expected_returns,
    covariance_matrix,
    portfolio_return,
    portfolio_variance,
    portfolio_volatility,
    sharpe_ratio,
    min_variance_weights_closed_form,
    tangency_weights_closed_form,
    efficient_frontier_closed_form,
    Constraints,
    min_variance_weights_constrained,
    max_sharpe_weights_constrained,
    efficient_frontier_constrained,
    allocate_investment,
    project_portfolio_value,
)

__all__ = [
    "expected_returns",
    "covariance_matrix",
    "portfolio_return",
    "portfolio_variance",
    "portfolio_volatility",
    "sharpe_ratio",
    "min_variance_weights_closed_form",
    "tangency_weights_closed_form",
    "efficient_frontier_closed_form",
    "Constraints",
    "min_variance_weights_constrained",
    "max_sharpe_weights_constrained",
    "efficient_frontier_constrained",
    "allocate_investment",
    "project_portfolio_value",
]

__version__ = "0.1.0"
