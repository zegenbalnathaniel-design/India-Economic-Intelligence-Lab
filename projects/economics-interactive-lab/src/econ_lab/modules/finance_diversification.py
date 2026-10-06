"""A minimal two-asset diversification demo.

For a portfolio split between two assets with weights w1 and w2 = 1-w1,
standard deviations sigma1 and sigma2, and correlation rho between their
returns, portfolio variance is the standard two-asset formula:

    sigma_p^2 = w1^2*sigma1^2 + w2^2*sigma2^2 + 2*w1*w2*rho*sigma1*sigma2

This module exists only to make the *intuition* tangible -- portfolio risk
falls as correlation falls, holding the individual assets' risk fixed --
with a handful of lines of exact algebra. It intentionally does NOT
implement the full Markowitz mean-variance machinery, efficient frontier,
or N-asset optimization; see the `portfolio-optimization-lab` sibling
project for that complete treatment.
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def compute(w1: float, sigma1: float, sigma2: float, rho: float) -> Dict[str, Any]:
    """Compute two-asset portfolio variance/std and the diversification benefit.

    Args:
        w1: Weight on asset 1, 0 <= w1 <= 1 (weight on asset 2 is 1-w1).
        sigma1: Standard deviation (volatility) of asset 1's return. Must be >= 0.
        sigma2: Standard deviation of asset 2's return. Must be >= 0.
        rho: Correlation between the two assets' returns, -1 <= rho <= 1.

    Returns:
        dict with portfolio variance (portfolio_variance), portfolio
        standard deviation (portfolio_std), the weighted-average standard
        deviation you'd get with no diversification benefit at all
        (undiversified_std, i.e. rho=1 case), and the diversification
        benefit (undiversified_std - portfolio_std, which is 0 when rho=1
        and largest when rho=-1).

    Raises:
        ValueError: for weights/volatilities/correlation outside their valid ranges.
    """
    if not (0 <= w1 <= 1):
        raise ValueError("w1 must be between 0 and 1.")
    if sigma1 < 0 or sigma2 < 0:
        raise ValueError("Volatilities cannot be negative.")
    if not (-1 <= rho <= 1):
        raise ValueError("Correlation rho must be between -1 and 1.")

    w2 = 1.0 - w1
    variance = (w1 ** 2) * (sigma1 ** 2) + (w2 ** 2) * (sigma2 ** 2) + 2 * w1 * w2 * rho * sigma1 * sigma2
    variance = max(variance, 0.0)  # guard tiny negative floating-point noise
    portfolio_std = variance ** 0.5
    undiversified_std = w1 * sigma1 + w2 * sigma2  # exactly the rho=1 case
    diversification_benefit = undiversified_std - portfolio_std

    return {
        "w2": w2,
        "portfolio_variance": variance,
        "portfolio_std": portfolio_std,
        "undiversified_std": undiversified_std,
        "diversification_benefit": diversification_benefit,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    w1 = st.slider("Weight on Asset 1", 0.0, 1.0, 0.5, 0.01, key="div_w1")
    col1, col2 = st.columns(2)
    with col1:
        sigma1 = st.slider("Asset 1 volatility (σ1)", 0.0, 50.0, 20.0, 1.0, key="div_s1")
    with col2:
        sigma2 = st.slider("Asset 2 volatility (σ2)", 0.0, 50.0, 30.0, 1.0, key="div_s2")
    rho = st.slider("Correlation between assets (ρ)", -1.0, 1.0, 0.2, 0.05, key="div_rho")
    return {"w1": w1, "sigma1": sigma1, "sigma2": sigma2, "rho": rho}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    rhos = np.linspace(-1, 1, 100)
    w1, s1, s2 = inputs["w1"], inputs["sigma1"], inputs["sigma2"]
    w2 = 1 - w1
    variances = (w1 ** 2) * (s1 ** 2) + (w2 ** 2) * (s2 ** 2) + 2 * w1 * w2 * rhos * s1 * s2
    stds = np.sqrt(np.clip(variances, 0, None))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rhos, y=stds, mode="lines", name="Portfolio std vs. correlation",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=[inputs["rho"]], y=[results["portfolio_std"]], mode="markers",
                              marker=dict(size=12, color="#111827"), name="Current setting"))
    fig.add_hline(y=results["undiversified_std"], line_dash="dash", line_color="#dc2626",
                  annotation_text=f"No-diversification std (ρ=1) = {results['undiversified_std']:.2f}")
    fig.update_layout(xaxis_title="Correlation (ρ)", yaxis_title="Portfolio standard deviation",
                       template="plotly_white", height=440)
    st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Portfolio std", f"{results['portfolio_std']:.2f}")
    m2.metric("Undiversified std (ρ=1)", f"{results['undiversified_std']:.2f}")
    m3.metric("Diversification benefit", f"{results['diversification_benefit']:.2f}")


MODULE = register_module(
    EconModule(
        key="finance_diversification",
        domain="Finance",
        title="Two-Asset Diversification",
        concept=(
            "Combining two assets whose returns don't move in lockstep reduces "
            "portfolio risk below the weighted average of their individual risks -- "
            "the less correlated they are, the bigger the reduction. This module "
            "isolates that intuition with the simplest possible (two-asset) case."
        ),
        equation=r"\sigma_p^2 = w_1^2\sigma_1^2 + w_2^2\sigma_2^2 + 2w_1w_2\rho\,\sigma_1\sigma_2",
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Fix the two weights and volatilities, then slide correlation from +1 "
            "down to -1. Confirm that at ρ=1 the portfolio std exactly equals the "
            "weighted average of the two individual stds (zero diversification "
            "benefit), and that the benefit grows continuously as ρ falls, becoming "
            "largest at ρ=-1."
        ),
        explanation=(
            "At ρ=1 the cross term 2*w1*w2*sigma1*sigma2 is at its algebraic maximum, "
            "and the variance formula factors exactly into (w1*sigma1 + w2*sigma2)^2 -- "
            "so portfolio std equals the simple weighted average, no diversification "
            "benefit. As ρ falls, that cross term shrinks (and goes negative for ρ<0), "
            "pulling portfolio variance below the weighted-average case: combining "
            "imperfectly-correlated assets cancels out some of each other's swings."
        ),
        limitations=(
            "The variance formula is exact algebra for any two assets with the given "
            "weights, volatilities and correlation -- always true by construction. "
            "The specific weights, volatilities and correlation here are illustrative "
            "numbers for the demo, not an estimate for any real pair of assets, and "
            "this module says nothing about expected return, Sharpe ratios, or how to "
            "choose weights optimally. For the full mean-variance optimization problem "
            "across many assets (the efficient frontier, tangency portfolio, Sharpe "
            "ratio maximization), see the `portfolio-optimization-lab` sibling "
            "project; for simulating a real contribution schedule under return "
            "uncertainty, see `sip-monte-carlo`."
        ),
    )
)
