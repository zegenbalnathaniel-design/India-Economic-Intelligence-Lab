"""Price ceilings and price floors: shortage and surplus quantities.

Demand: Qd = a - b*P
Supply: Qs = c + d*P
Free-market equilibrium: P0 = (a-c)/(b+d), Q0 = a - b*P0

A binding **price ceiling** Pc < P0 caps the price below equilibrium.
Quantity actually transacted is the lesser of the two sides, which at a
below-equilibrium price is quantity supplied:

    Q_transacted = min(Qd(Pc), Qs(Pc)) = Qs(Pc)   [since Pc < P0]
    shortage     = Qd(Pc) - Qs(Pc)

A binding **price floor** Pf > P0 sets a minimum price above equilibrium.
Quantity transacted is again the lesser side, now quantity demanded:

    Q_transacted = min(Qd(Pf), Qs(Pf)) = Qd(Pf)   [since Pf > P0]
    surplus      = Qs(Pf) - Qd(Pf)

If the control price is not actually binding (ceiling above P0, or floor
below P0), the free-market equilibrium prevails and shortage/surplus is 0.
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def compute(a: float, b: float, c: float, d: float, control_price: float, control_type: str) -> Dict[str, Any]:
    """Compute the effect of a price ceiling or floor on a linear market.

    Args:
        a: Demand intercept. Must be > 0.
        b: Demand slope magnitude. Must be > 0.
        c: Supply intercept. Must be >= 0.
        d: Supply slope. Must be > 0.
        control_price: The legally set price. Must be >= 0.
        control_type: Either "ceiling" (a maximum legal price) or
            "floor" (a minimum legal price).

    Returns:
        dict with the free-market equilibrium (p0, q0), quantity demanded
        and supplied at the control price, whether the control is binding,
        the quantity actually transacted, and the shortage or surplus
        (whichever applies; the other is 0).

    Raises:
        ValueError: for invalid slopes/intercepts, a negative control
            price, or an unrecognized control_type.
    """
    if b <= 0 or d <= 0:
        raise ValueError("Demand slope b and supply slope d must both be positive.")
    if a <= 0:
        raise ValueError("Demand intercept a must be positive.")
    if c < 0:
        raise ValueError("Supply intercept c cannot be negative.")
    if control_price < 0:
        raise ValueError("Control price cannot be negative.")
    if control_type not in ("ceiling", "floor"):
        raise ValueError('control_type must be "ceiling" or "floor".')

    p0 = (a - c) / (b + d)
    if p0 < 0:
        raise ValueError("No positive-price equilibrium exists for these curves (a must exceed c).")
    q0 = a - b * p0

    qd_at_control = max(a - b * control_price, 0.0)
    qs_at_control = max(c + d * control_price, 0.0)

    if control_type == "ceiling":
        binding = control_price < p0
        if binding:
            transacted = min(qd_at_control, qs_at_control)
            shortage = qd_at_control - qs_at_control
            surplus = 0.0
        else:
            transacted, shortage, surplus = q0, 0.0, 0.0
    else:  # floor
        binding = control_price > p0
        if binding:
            transacted = min(qd_at_control, qs_at_control)
            surplus = qs_at_control - qd_at_control
            shortage = 0.0
        else:
            transacted, shortage, surplus = q0, 0.0, 0.0

    return {
        "p0": p0,
        "q0": q0,
        "qd_at_control": qd_at_control,
        "qs_at_control": qs_at_control,
        "binding": binding,
        "transacted": transacted,
        "shortage": shortage,
        "surplus": surplus,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    st.markdown("**Demand:** Qd = a − b·P &nbsp;&nbsp; **Supply:** Qs = c + d·P")
    col1, col2 = st.columns(2)
    with col1:
        a = st.slider("Demand intercept a", 10.0, 200.0, 100.0, 1.0, key="pc_a")
        b = st.slider("Demand slope b", 0.1, 10.0, 2.0, 0.1, key="pc_b")
    with col2:
        c = st.slider("Supply intercept c", 0.0, 100.0, 10.0, 1.0, key="pc_c")
        d = st.slider("Supply slope d", 0.1, 10.0, 1.5, 0.1, key="pc_d")
    control_type = st.radio("Control type", ["ceiling", "floor"], key="pc_type",
                             help="Ceiling = maximum legal price (e.g. rent control). "
                                  "Floor = minimum legal price (e.g. minimum wage).")
    control_price = st.slider("Control price", 0.0, 100.0, 20.0, 1.0, key="pc_price")
    return {"a": a, "b": b, "c": c, "d": d, "control_price": control_price, "control_type": control_type}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    a, b, c, d = inputs["a"], inputs["b"], inputs["c"], inputs["d"]
    p_max = max(results["p0"], inputs["control_price"]) * 1.4 + 1
    prices = np.linspace(0, p_max, 200)
    demand_q = a - b * prices
    supply_q = c + d * prices

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=demand_q, y=prices, mode="lines", name="Demand",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=supply_q, y=prices, mode="lines", name="Supply",
                              line=dict(color="#dc2626", width=3)))
    fig.add_trace(go.Scatter(x=[results["q0"]], y=[results["p0"]], mode="markers",
                              marker=dict(size=10, color="gray"), name="Free-market equilibrium"))
    fig.add_hline(y=inputs["control_price"], line_dash="dash", line_color="#111827",
                  annotation_text=f"{inputs['control_type'].title()} = {inputs['control_price']:.1f}")
    if results["binding"]:
        fig.add_trace(go.Scatter(x=[results["qd_at_control"]], y=[inputs["control_price"]],
                                  mode="markers", marker=dict(size=10, color="#16a34a"), name="Qd at control"))
        fig.add_trace(go.Scatter(x=[results["qs_at_control"]], y=[inputs["control_price"]],
                                  mode="markers", marker=dict(size=10, color="#ea580c"), name="Qs at control"))
    fig.update_layout(xaxis_title="Quantity", yaxis_title="Price", template="plotly_white",
                       height=460, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

    if not results["binding"]:
        st.info("This control price is not binding -- the free market equilibrium already satisfies it.")
    elif results["shortage"] > 0:
        st.error(f"Shortage: {results['shortage']:.2f} units (quantity demanded exceeds quantity supplied).")
    else:
        st.warning(f"Surplus: {results['surplus']:.2f} units (quantity supplied exceeds quantity demanded).")


MODULE = register_module(
    EconModule(
        key="micro_price_controls",
        domain="Microeconomics",
        title="Price Ceilings & Floors",
        concept=(
            "Governments sometimes cap prices (ceilings, e.g. rent control) or set a "
            "minimum (floors, e.g. a minimum wage). When the control price differs "
            "from the market-clearing price, the quantity actually bought and sold is "
            "limited by the *short* side of the market, creating a shortage or surplus."
        ),
        equation=(
            r"\text{Ceiling } P_c < P_0: \ \text{shortage}=Q_d(P_c)-Q_s(P_c) \qquad "
            r"\text{Floor } P_f > P_0: \ \text{surplus}=Q_s(P_f)-Q_d(P_f)"
        ),
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Start with a non-binding control (ceiling above P0, or floor below P0) "
            "and confirm shortage/surplus is zero. Then cross the equilibrium price -- "
            "note the shortage or surplus appears immediately and grows the further "
            "the control price is pushed from equilibrium."
        ),
        explanation=(
            "A price ceiling below equilibrium makes sellers unwilling to supply as "
            "much as buyers want at that price -- a shortage, sized exactly by the gap "
            "between Qd and Qs evaluated at the ceiling price. A price floor above "
            "equilibrium does the reverse: sellers want to offer more than buyers want "
            "to buy at that price -- a surplus. Either way, only the smaller quantity "
            "(the 'short side') actually gets transacted."
        ),
        limitations=(
            "The shortage/surplus formulas are exact given linear demand and supply -- "
            "always true by construction for this curve shape. The slopes, intercepts "
            "and control price are illustrative numbers chosen for the demo, not "
            "estimates from any real regulated market. This module does not model "
            "secondary effects of controls (black markets, quality degradation, queuing "
            "costs, or how long until the market `unwinds` toward a new equilibrium)."
        ),
    )
)
