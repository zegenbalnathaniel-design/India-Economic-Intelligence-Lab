"""Per-unit tax incidence, surplus, and deadweight loss.

Demand: Qd = a - b*Pc   (Pc = price paid by consumers)
Supply: Qs = c + d*Pp   (Pp = price received by producers = Pc - t)

A per-unit tax t wedges the price consumers pay above the price producers
receive. Substituting Pp = Pc - t into market clearing (Qd = Qs) and
solving gives closed-form after-tax prices and quantity:

    Pc  = (a - c + d*t) / (b + d)
    Pp  = Pc - t
    Q   = a - b*Pc

Compared with the no-tax equilibrium P0 = (a-c)/(b+d), Q0 = a - b*P0, the
tax wedge splits between consumers and producers in exact proportion to
the *other side's* slope:

    consumer burden = Pc - P0 = t * d / (b + d)
    producer burden = P0 - Pp = t * b / (b + d)

(consumer share + producer share of the wedge always sum to exactly t).

Consumer surplus (CS), producer surplus (PS) and deadweight loss (DWL) use
the usual triangle-area formulas for linear curves:

    CS  = 0.5 * (P_demand_intercept - Pc) * Q
    PS  = 0.5 * (Pp - P_supply_intercept) * Q
    DWL = 0.5 * t * (Q0 - Q)

where P_demand_intercept = a/b (price where Qd=0) and
P_supply_intercept = -c/d (price where Qs=0).
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def compute(a: float, b: float, c: float, d: float, tax: float) -> Dict[str, Any]:
    """Compute per-unit tax incidence, surplus, and deadweight loss.

    Args:
        a: Demand intercept. Must be > 0.
        b: Demand slope magnitude, Qd = a - b*Pc. Must be > 0.
        c: Supply intercept, Qs = c + d*Pp. Must be >= 0.
        d: Supply slope. Must be > 0.
        tax: Per-unit tax levied between consumer and producer price. Must be >= 0.

    Returns:
        dict with the no-tax equilibrium (p0, q0), the after-tax consumer
        price (p_consumer), producer price (p_producer), after-tax
        quantity (q_tax), the consumer/producer burden split, tax revenue,
        consumer surplus, producer surplus, and deadweight loss.

    Raises:
        ValueError: for non-positive slopes, non-positive demand intercept,
            a negative supply intercept, a negative tax, or a tax so large
            it pushes quantity to zero or below.
    """
    if b <= 0 or d <= 0:
        raise ValueError("Demand slope b and supply slope d must both be positive.")
    if a <= 0:
        raise ValueError("Demand intercept a must be positive.")
    if c < 0:
        raise ValueError("Supply intercept c cannot be negative.")
    if tax < 0:
        raise ValueError("Tax must be non-negative.")

    p0 = (a - c) / (b + d)
    if p0 < 0:
        raise ValueError("No positive-price equilibrium exists for these curves (a must exceed c).")
    q0 = a - b * p0

    p_consumer = (a - c + d * tax) / (b + d)
    p_producer = p_consumer - tax
    q_tax = a - b * p_consumer

    if q_tax <= 0 or p_producer < 0:
        raise ValueError("Tax is too large relative to these curves: after-tax quantity hits zero.")

    consumer_burden = p_consumer - p0
    producer_burden = p0 - p_producer

    demand_intercept_price = a / b
    supply_intercept_price = -c / d

    consumer_surplus = 0.5 * (demand_intercept_price - p_consumer) * q_tax
    producer_surplus = 0.5 * (p_producer - supply_intercept_price) * q_tax
    tax_revenue = tax * q_tax
    deadweight_loss = 0.5 * tax * (q0 - q_tax)

    return {
        "p0": p0,
        "q0": q0,
        "p_consumer": p_consumer,
        "p_producer": p_producer,
        "q_tax": q_tax,
        "consumer_burden": consumer_burden,
        "producer_burden": producer_burden,
        "consumer_burden_share": consumer_burden / tax if tax > 0 else float("nan"),
        "producer_burden_share": producer_burden / tax if tax > 0 else float("nan"),
        "tax_revenue": tax_revenue,
        "consumer_surplus": consumer_surplus,
        "producer_surplus": producer_surplus,
        "deadweight_loss": deadweight_loss,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    st.markdown("**Demand:** Qd = a − b·P_consumer &nbsp;&nbsp; **Supply:** Qs = c + d·P_producer")
    col1, col2 = st.columns(2)
    with col1:
        a = st.slider("Demand intercept a", 10.0, 200.0, 100.0, 1.0, key="tax_a")
        b = st.slider("Demand slope b", 0.1, 10.0, 2.0, 0.1, key="tax_b")
    with col2:
        c = st.slider("Supply intercept c", 0.0, 100.0, 10.0, 1.0, key="tax_c")
        d = st.slider("Supply slope d", 0.1, 10.0, 1.5, 0.1, key="tax_d")
    tax = st.slider("Per-unit tax t", 0.0, 20.0, 5.0, 0.5, key="tax_t")
    return {"a": a, "b": b, "c": c, "d": d, "tax": tax}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    a, b, c, d = inputs["a"], inputs["b"], inputs["c"], inputs["d"]
    p_max = results["p0"] * 1.6 + inputs["tax"]
    prices = np.linspace(0, p_max, 200)
    demand_q = a - b * prices
    supply_q = c + d * prices

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=demand_q, y=prices, mode="lines", name="Demand",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=supply_q, y=prices, mode="lines", name="Supply",
                              line=dict(color="#dc2626", width=3)))
    fig.add_trace(go.Scatter(x=[results["q0"]], y=[results["p0"]], mode="markers",
                              marker=dict(size=10, color="gray"), name="No-tax equilibrium"))
    fig.add_trace(go.Scatter(x=[results["q_tax"], results["q_tax"]],
                              y=[results["p_producer"], results["p_consumer"]],
                              mode="lines+markers", line=dict(color="#111827", dash="dash"),
                              marker=dict(size=10),
                              name="Tax wedge (P_consumer above, P_producer below)"))
    fig.update_layout(xaxis_title="Quantity", yaxis_title="Price", template="plotly_white",
                       height=460, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Consumer price", f"{results['p_consumer']:.2f}")
    m2.metric("Producer price", f"{results['p_producer']:.2f}")
    m3.metric("Tax revenue", f"{results['tax_revenue']:.2f}")
    m4.metric("Deadweight loss", f"{results['deadweight_loss']:.2f}")
    st.caption(
        f"Consumers bear {results['consumer_burden_share']*100:.1f}% of the per-unit tax, "
        f"producers bear {results['producer_burden_share']*100:.1f}% "
        f"(consumer surplus {results['consumer_surplus']:.2f}, "
        f"producer surplus {results['producer_surplus']:.2f})."
    )


MODULE = register_module(
    EconModule(
        key="micro_tax_incidence",
        domain="Microeconomics",
        title="Tax Incidence & Deadweight Loss",
        concept=(
            "A per-unit tax drives a wedge between the price buyers pay and the "
            "price sellers receive. Who actually bears the burden depends on the "
            "relative steepness (elasticity) of demand and supply, not on who writes "
            "the check to the tax authority."
        ),
        equation=(
            r"P_{consumer} = \frac{a-c+dt}{b+d}, \quad P_{producer}=P_{consumer}-t \quad "
            r"\text{burden}_{consumer} = t\cdot\frac{d}{b+d}, \quad "
            r"\text{burden}_{producer} = t\cdot\frac{b}{b+d}"
        ),
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Fix the tax amount and the supply curve, then make demand much steeper "
            "(raise a, lower b so the curve is nearly vertical in spirit) versus much "
            "flatter. Watch the consumer burden share move toward 100% as demand "
            "becomes less price-responsive relative to supply."
        ),
        explanation=(
            "The tax doesn't change the underlying demand or supply relationships -- "
            "it changes which price each side effectively faces. Solving the two "
            "linear equations with the wedge Pp = Pc - t gives an exact after-tax "
            "price and quantity. The consumer and producer surplus triangles and the "
            "deadweight-loss triangle are then computed from the standard geometric "
            "area formulas for straight-line demand and supply."
        ),
        limitations=(
            "The burden-split and DWL formulas above are exact for linear demand and "
            "supply -- that is pure algebra and geometry, always true for this curve "
            "shape. The specific intercepts, slopes, and tax size are illustrative "
            "numbers for this demo, not estimates of any real tax or market. Real "
            "demand/supply curves are rarely perfectly linear, and this module ignores "
            "general-equilibrium effects, tax administration costs, and behavioral "
            "responses beyond the simple price elasticity captured by the slopes."
        ),
    )
)
