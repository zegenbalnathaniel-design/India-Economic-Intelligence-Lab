"""A simple Solow-style capital-accumulation growth model.

Per-worker output follows a Cobb-Douglas production function f(k) = k^alpha
(0 < alpha < 1), with capital per worker k accumulating according to:

    k_{t+1} = k_t + s * f(k_t) - delta * k_t
            = k_t + s * k_t^alpha - delta * k_t

where s is the savings rate (share of output reinvested) and delta is the
depreciation rate. The capital stock converges to a steady state k* where
investment exactly offsets depreciation, s*f(k*) = delta*k*:

    k* = (s / delta) ** (1 / (1 - alpha))

This closed form for k* is always true given this production function and
accumulation rule; s, delta, alpha and the starting capital k0 are
illustrative, user-chosen numbers for the demo.
"""

from __future__ import annotations

from typing import Any, Dict, List

from econ_lab.registry import EconModule, register_module


def _next_capital(k: float, s: float, delta: float, alpha: float) -> float:
    return k + s * (k ** alpha) - delta * k


def compute(s: float, delta: float, alpha: float, k0: float, periods: int = 50) -> Dict[str, Any]:
    """Simulate a Solow-style capital-accumulation path and its steady state.

    Args:
        s: Savings/investment rate, share of output reinvested. Must satisfy 0 < s < 1.
        delta: Depreciation rate. Must satisfy 0 < delta < 1.
        alpha: Capital's output elasticity in f(k)=k^alpha. Must satisfy 0 < alpha < 1.
        k0: Starting capital per worker. Must be >= 0.
        periods: Number of periods to simulate. Must be >= 1.

    Returns:
        dict with the steady-state capital (k_star), steady-state output
        (y_star = k_star**alpha), the simulated capital path (length
        periods+1, including k0), and the output path (k_t**alpha for each
        k_t on the path).

    Raises:
        ValueError: for parameters outside their valid ranges.
    """
    if not (0 < s < 1):
        raise ValueError("Savings rate s must satisfy 0 < s < 1.")
    if not (0 < delta < 1):
        raise ValueError("Depreciation rate delta must satisfy 0 < delta < 1.")
    if not (0 < alpha < 1):
        raise ValueError("Capital elasticity alpha must satisfy 0 < alpha < 1.")
    if k0 < 0:
        raise ValueError("Starting capital k0 cannot be negative.")
    if periods < 1:
        raise ValueError("periods must be at least 1.")

    k_star = (s / delta) ** (1.0 / (1.0 - alpha))
    y_star = k_star ** alpha

    capital_path: List[float] = [k0]
    k = k0
    for _ in range(periods):
        k = max(_next_capital(k, s, delta, alpha), 0.0)
        capital_path.append(k)
    output_path = [k ** alpha if k > 0 else 0.0 for k in capital_path]

    return {
        "k_star": k_star,
        "y_star": y_star,
        "capital_path": capital_path,
        "output_path": output_path,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    col1, col2 = st.columns(2)
    with col1:
        s = st.slider("Savings rate s", 0.05, 0.6, 0.25, 0.01, key="growth_s")
        delta = st.slider("Depreciation rate δ", 0.02, 0.3, 0.08, 0.01, key="growth_delta")
    with col2:
        alpha = st.slider("Capital elasticity α", 0.1, 0.8, 0.33, 0.01, key="growth_alpha")
        k0 = st.slider("Starting capital per worker k0", 0.0, 20.0, 1.0, 0.5, key="growth_k0")
    periods = st.slider("Periods to simulate", 10, 200, 60, 5, key="growth_periods")
    return {"s": s, "delta": delta, "alpha": alpha, "k0": k0, "periods": periods}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import plotly.graph_objects as go
    import streamlit as st

    t = list(range(len(results["capital_path"])))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=results["capital_path"], mode="lines", name="Capital per worker k_t",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=t, y=results["output_path"], mode="lines", name="Output per worker y_t",
                              line=dict(color="#16a34a", width=3)))
    fig.add_hline(y=results["k_star"], line_dash="dash", line_color="#2563eb",
                  annotation_text=f"k* = {results['k_star']:.2f}")
    fig.add_hline(y=results["y_star"], line_dash="dash", line_color="#16a34a",
                  annotation_text=f"y* = {results['y_star']:.2f}")
    fig.update_layout(xaxis_title="Period", yaxis_title="Per-worker level",
                       template="plotly_white", height=460, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

    m1, m2 = st.columns(2)
    m1.metric("Steady-state capital k*", f"{results['k_star']:.2f}")
    m2.metric("Steady-state output y*", f"{results['y_star']:.2f}")


MODULE = register_module(
    EconModule(
        key="macro_growth",
        domain="Macroeconomics",
        title="Solow-Style Capital Accumulation",
        concept=(
            "Each period, a fraction of output is saved and invested, adding to the "
            "capital stock; capital also wears out (depreciates) each period. "
            "Capital per worker accumulates until investment exactly offsets "
            "depreciation -- a steady state that any starting point converges toward."
        ),
        equation=(
            r"k_{t+1}=k_t+s\,k_t^{\alpha}-\delta k_t \qquad "
            r"k^{*}=\left(\dfrac{s}{\delta}\right)^{\frac{1}{1-\alpha}}"
        ),
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Start two runs from very different k0 (e.g. 0.5 and 15) with identical "
            "s, delta, alpha, and watch both paths converge to the *same* k* -- the "
            "steady state depends only on s, delta, alpha, not on the starting point. "
            "Then raise the savings rate s and see k* (and y*) rise."
        ),
        explanation=(
            "Investment per worker is s*k^alpha; depreciation is delta*k. When "
            "investment exceeds depreciation, capital grows; when depreciation "
            "exceeds investment, capital shrinks. The two curves cross exactly once "
            "for k>0 (because k^alpha is concave while delta*k is a straight line "
            "through the origin), at the closed-form k* above -- which is why the "
            "simulated path, run far enough, converges to that same number regardless "
            "of k0."
        ),
        limitations=(
            "The steady-state formula k*=(s/delta)^(1/(1-alpha)) is an exact "
            "consequence of this particular accumulation rule and Cobb-Douglas "
            "production function -- always true given those assumptions. It ignores "
            "population growth, technological progress, and any distinction between "
            "physical and human capital. s, delta, alpha, and k0 are illustrative, "
            "user-chosen numbers for this demo, not calibrated to any real economy's "
            "growth accounting."
        ),
    )
)
