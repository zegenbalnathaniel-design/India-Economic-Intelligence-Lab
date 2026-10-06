"""Linear demand & supply equilibrium.

Demand:  Qd = a - b*P   (b > 0: quantity demanded falls as price rises)
Supply:  Qs = c + d*P   (d > 0: quantity supplied rises as price rises)

Setting Qd = Qs and solving for P gives the closed-form equilibrium:

    P* = (a - c) / (b + d)
    Q* = a - b*P*          (equivalently c + d*P*)

This is the textbook linear supply-and-demand model. The equation above is
always true given linear curves; the slopes/intercepts (a, b, c, d) below
are illustrative numbers the user chooses for this demo, not estimates of
any real market.
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def compute(a: float, b: float, c: float, d: float) -> Dict[str, Any]:
    """Solve for the linear demand/supply equilibrium.

    Args:
        a: Demand intercept (quantity demanded at price 0). Must be > 0.
        b: Demand slope magnitude, Qd = a - b*P. Must be > 0.
        c: Supply intercept (quantity supplied at price 0). Must be >= 0.
        d: Supply slope, Qs = c + d*P. Must be > 0.

    Returns:
        dict with p_star, q_star, demand price-intercept (a/b), and the
        supply price-intercept (-c/d, i.e. the minimum price at which any
        quantity is supplied).

    Raises:
        ValueError: for non-positive slopes, a negative intercept, or a
            configuration where no positive-price equilibrium exists
            (demand curve entirely below the supply curve).
    """
    if b <= 0 or d <= 0:
        raise ValueError("Demand slope b and supply slope d must both be positive.")
    if a <= 0:
        raise ValueError("Demand intercept a must be positive.")
    if c < 0:
        raise ValueError("Supply intercept c cannot be negative.")

    p_star = (a - c) / (b + d)
    if p_star < 0:
        raise ValueError(
            "No positive-price equilibrium: at P=0 supply already exceeds demand "
            "(check that a > c)."
        )
    q_star = a - b * p_star

    return {
        "p_star": p_star,
        "q_star": q_star,
        "demand_price_intercept": a / b,
        "supply_price_intercept": -c / d,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    st.markdown("**Demand:** Qd = a − b·P &nbsp;&nbsp; **Supply:** Qs = c + d·P")
    col1, col2 = st.columns(2)
    with col1:
        a = st.slider("Demand intercept a", 10.0, 200.0, 100.0, 1.0)
        b = st.slider("Demand slope b", 0.1, 10.0, 2.0, 0.1)
    with col2:
        c = st.slider("Supply intercept c", 0.0, 100.0, 10.0, 1.0)
        d = st.slider("Supply slope d", 0.1, 10.0, 1.5, 0.1)
    return {"a": a, "b": b, "c": c, "d": d}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    a, b, c, d = inputs["a"], inputs["b"], inputs["c"], inputs["d"]
    p_star, q_star = results["p_star"], results["q_star"]

    p_max = max(results["demand_price_intercept"], p_star) * 1.15
    prices = np.linspace(0, p_max, 200)
    demand_q = a - b * prices
    supply_q = c + d * prices

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=demand_q, y=prices, mode="lines", name="Demand",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=supply_q, y=prices, mode="lines", name="Supply",
                              line=dict(color="#dc2626", width=3)))
    fig.add_trace(go.Scatter(x=[q_star], y=[p_star], mode="markers",
                              marker=dict(size=12, color="#111827"),
                              name=f"Equilibrium (Q*={q_star:.1f}, P*={p_star:.2f})"))
    fig.add_shape(type="line", x0=0, x1=q_star, y0=p_star, y1=p_star,
                  line=dict(color="gray", dash="dot"))
    fig.add_shape(type="line", x0=q_star, x1=q_star, y0=0, y1=p_star,
                  line=dict(color="gray", dash="dot"))
    fig.update_layout(
        xaxis_title="Quantity", yaxis_title="Price",
        template="plotly_white", height=460,
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)
    m1, m2 = st.columns(2)
    m1.metric("Equilibrium price P*", f"{p_star:.2f}")
    m2.metric("Equilibrium quantity Q*", f"{q_star:.2f}")


MODULE = register_module(
    EconModule(
        key="micro_supply_demand",
        domain="Microeconomics",
        title="Demand & Supply Equilibrium",
        concept=(
            "A market clears where the quantity buyers want to purchase equals the "
            "quantity sellers want to offer. With straight-line demand and supply "
            "curves, that single intersection point has an exact algebraic solution."
        ),
        equation=(
            r"Q_d = a - bP \qquad Q_s = c + dP \qquad "
            r"P^{*} = \dfrac{a-c}{b+d}, \quad Q^{*} = a - bP^{*}"
        ),
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Hold supply fixed and raise the demand slope b (making demand more "
            "price-responsive). Then shift the demand intercept a by the same "
            "amount each time and compare how much P* moves at a small b versus "
            "a large b."
        ),
        explanation=(
            "The demand curve slopes down because, by assumption, people buy less "
            "at a higher price (b>0). The supply curve slopes up because sellers are "
            "willing to offer more at a higher price (d>0). The market-clearing price "
            "P* is where the two lines cross; plugging the two linear equations into "
            "each other and solving for P gives the closed form above exactly -- no "
            "approximation involved."
        ),
        limitations=(
            "The equation P* = (a-c)/(b+d) is always true for any linear Qd=a-bP and "
            "Qs=c+dP -- that part is pure algebra. The specific values of a, b, c, d "
            "you choose on the sliders are illustrative numbers picked for this demo, "
            "not estimates of any real good's demand or supply. Real-world demand and "
            "supply are rarely exactly linear over their whole range, and this module "
            "ignores income effects, substitutes, and dynamic adjustment to equilibrium."
        ),
    )
)
