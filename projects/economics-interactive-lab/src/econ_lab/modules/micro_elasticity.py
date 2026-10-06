"""Price elasticity of demand (point elasticity).

For a linear demand curve Q = a - b*P, the point elasticity of demand at
price P is the exact derivative-based formula:

    PED = (dQ/dP) * (P/Q) = -b * (P / Q)

This is always true for a linear demand curve (dQ/dP = -b is constant by
construction); only the chosen a, b, and the price point at which it is
evaluated are illustrative choices.
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def compute(a: float, b: float, price: float) -> Dict[str, Any]:
    """Compute point price elasticity of demand for linear demand Q = a - b*P.

    Args:
        a: Demand intercept. Must be > 0.
        b: Demand slope magnitude (dQ/dP = -b). Must be > 0.
        price: The price at which to evaluate elasticity. Must satisfy
            0 <= price < a/b so quantity is strictly positive.

    Returns:
        dict with quantity at that price, the point elasticity, and a
        qualitative label ("elastic", "inelastic", "unit elastic").

    Raises:
        ValueError: for non-positive slope/intercept, a negative price,
            or a price that drives quantity to zero or below (elasticity
            is undefined there).
    """
    if a <= 0 or b <= 0:
        raise ValueError("Demand intercept a and slope b must both be positive.")
    if price < 0:
        raise ValueError("Price cannot be negative.")

    quantity = a - b * price
    if quantity <= 0:
        raise ValueError(
            "Price is at or above the demand curve's choke price (quantity <= 0); "
            "elasticity is undefined there."
        )

    elasticity = -b * (price / quantity)
    magnitude = abs(elasticity)
    if magnitude > 1:
        label = "elastic"
    elif magnitude < 1:
        label = "inelastic"
    else:
        label = "unit elastic"

    return {
        "quantity": quantity,
        "elasticity": elasticity,
        "label": label,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    st.markdown("**Demand:** Q = a − b·P")
    a = st.slider("Demand intercept a", 10.0, 200.0, 100.0, 1.0, key="ped_a")
    b = st.slider("Demand slope b", 0.1, 10.0, 2.0, 0.1, key="ped_b")
    max_price = max(a / b - 0.01, 0.01)
    price = st.slider("Price at which to evaluate elasticity", 0.0, float(max_price),
                       float(max_price) / 2, 0.1, key="ped_price")
    return {"a": a, "b": b, "price": price}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    a, b, price = inputs["a"], inputs["b"], inputs["price"]
    prices = np.linspace(0, a / b, 200)
    quantities = a - b * prices

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quantities, y=prices, mode="lines", name="Demand",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=[results["quantity"]], y=[price], mode="markers",
                              marker=dict(size=12, color="#111827"),
                              name=f"Evaluation point (PED={results['elasticity']:.2f})"))
    fig.update_layout(xaxis_title="Quantity", yaxis_title="Price",
                       template="plotly_white", height=420,
                       legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    m1, m2 = st.columns(2)
    m1.metric("Point elasticity (PED)", f"{results['elasticity']:.3f}")
    m2.metric("Classification", results["label"].replace("_", " ").title())


MODULE = register_module(
    EconModule(
        key="micro_elasticity",
        domain="Microeconomics",
        title="Price Elasticity of Demand",
        concept=(
            "Elasticity measures how sensitive quantity demanded is to a price "
            "change, in percentage terms, at a specific point on the demand curve -- "
            "unlike the slope, it doesn't depend on the units price and quantity are "
            "measured in."
        ),
        equation=r"\text{PED} = \frac{dQ}{dP}\cdot\frac{P}{Q} = -b\cdot\frac{P}{Q} \quad \text{for } Q=a-bP",
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "With a and b fixed, drag the evaluation price from near zero toward "
            "the choke price (a/b). Notice that |PED| rises continuously along a "
            "straight-line demand curve even though the slope b never changes -- "
            "elasticity is a point property, not a curve-wide constant."
        ),
        explanation=(
            "Because Q=a-bP is linear, dQ/dP = -b everywhere, a constant. But "
            "elasticity rescales that slope by P/Q, which changes continuously as "
            "you move along the line. Near P=0, P/Q is tiny, so PED is close to 0 "
            "(inelastic). As P approaches the choke price a/b, Q shrinks toward 0 and "
            "P/Q blows up, so PED becomes very large in magnitude (elastic)."
        ),
        limitations=(
            "The formula PED = -b(P/Q) is an exact consequence of a linear demand "
            "curve; it is not an empirical elasticity estimate. The intercept a, "
            "slope b, and evaluation price are illustrative numbers chosen for the "
            "demo. Real goods' demand curves are rarely exactly linear across their "
            "whole price range, and this point-elasticity formula (as opposed to the "
            "midpoint/arc elasticity formula) is only exact for infinitesimally small "
            "price changes."
        ),
    )
)
