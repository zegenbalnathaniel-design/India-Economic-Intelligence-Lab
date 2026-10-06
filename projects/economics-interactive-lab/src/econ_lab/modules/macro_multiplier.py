"""The simple closed-economy fiscal (Keynesian) multiplier.

With a constant marginal propensity to consume (MPC = c), an initial
government-spending injection dG ripples through the economy: the first
round of spending becomes someone's income, a fraction c of which is
re-spent, a fraction c of *that* is re-spent, and so on -- an infinite
geometric series:

    dY = dG * (1 + c + c^2 + c^3 + ...) = dG / (1 - c)      for 0 <= c < 1

so the closed-economy multiplier is exactly:

    multiplier = 1 / (1 - MPC)
    dY         = multiplier * dG

This module is deliberately the simple closed-economy textbook version
(no taxes, no imports, no endogenous interest-rate response) -- see the
`india-economic-policy-simulator` sibling project for the open-economy
multiplier `1/[1-c(1-tau)+m]` with crowding-out effects.
"""

from __future__ import annotations

from typing import Any, Dict, List

from econ_lab.registry import EconModule, register_module


def compute(mpc: float, delta_g: float, rounds: int = 10) -> Dict[str, Any]:
    """Compute the closed-economy fiscal multiplier and spending-round path.

    Args:
        mpc: Marginal propensity to consume, 0 <= mpc < 1.
        delta_g: The initial government spending injection (can be negative
            for a cut).
        rounds: Number of finite spending rounds to display in the
            round-by-round path (does not affect the closed-form multiplier).
            Must be >= 1.

    Returns:
        dict with the multiplier, the implied total change in output
        (delta_y), the per-round spending amounts, and the cumulative sum
        after each round (which converges toward delta_y).

    Raises:
        ValueError: if mpc is not in [0, 1), or rounds < 1.
    """
    if not (0 <= mpc < 1):
        raise ValueError("MPC must satisfy 0 <= MPC < 1 for the multiplier to be finite.")
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    multiplier = 1.0 / (1.0 - mpc)
    delta_y = multiplier * delta_g

    round_spending: List[float] = [delta_g * (mpc ** i) for i in range(rounds)]
    cumulative: List[float] = []
    running = 0.0
    for amount in round_spending:
        running += amount
        cumulative.append(running)

    return {
        "multiplier": multiplier,
        "delta_y": delta_y,
        "round_spending": round_spending,
        "cumulative": cumulative,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    mpc = st.slider("Marginal propensity to consume (MPC)", 0.0, 0.95, 0.75, 0.01, key="mult_mpc")
    delta_g = st.slider("Government spending injection (ΔG)", -100.0, 100.0, 50.0, 5.0, key="mult_dg")
    rounds = st.slider("Spending rounds to display", 3, 30, 12, 1, key="mult_rounds")
    return {"mpc": mpc, "delta_g": delta_g, "rounds": rounds}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import plotly.graph_objects as go
    import streamlit as st

    rounds = list(range(1, len(results["round_spending"]) + 1))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rounds, y=results["round_spending"], name="Spending this round",
                          marker_color="#2563eb"))
    fig.add_trace(go.Scatter(x=rounds, y=results["cumulative"], name="Cumulative ΔY so far",
                              mode="lines+markers", line=dict(color="#111827", width=3)))
    fig.add_hline(y=results["delta_y"], line_dash="dash", line_color="#dc2626",
                  annotation_text=f"Multiplier limit ΔY = {results['delta_y']:.1f}")
    fig.update_layout(xaxis_title="Spending round", yaxis_title="Amount",
                       template="plotly_white", height=440, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

    m1, m2 = st.columns(2)
    m1.metric("Multiplier = 1/(1-MPC)", f"{results['multiplier']:.2f}x")
    m2.metric("Total ΔOutput", f"{results['delta_y']:+.2f}")


MODULE = register_module(
    EconModule(
        key="macro_multiplier",
        domain="Macroeconomics",
        title="Fiscal (Keynesian) Multiplier",
        concept=(
            "Government spending doesn't just add to output once -- it becomes "
            "someone's income, part of which gets re-spent, becoming someone else's "
            "income, and so on. In the simplest closed economy with a constant "
            "marginal propensity to consume, this chain sums to a clean multiple of "
            "the original injection."
        ),
        equation=r"\Delta Y = \Delta G\,(1+c+c^2+\cdots) = \frac{\Delta G}{1-c} \quad\Rightarrow\quad \text{multiplier}=\frac{1}{1-\text{MPC}}",
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Keep ΔG fixed and raise MPC from 0.5 toward 0.95. Watch the multiplier "
            "climb steeply as MPC approaches 1 -- and notice in the round-by-round "
            "chart that the bars shrink more slowly each round, taking many more "
            "rounds to approach the eventual multiplier limit."
        ),
        explanation=(
            "Each spending round is dG * MPC^round -- a geometric sequence that "
            "shrinks every round because MPC < 1. The sum of the whole infinite "
            "sequence is the standard geometric-series formula dG/(1-MPC), which is "
            "exactly the multiplier. The chart's running cumulative sum should visibly "
            "converge toward that closed-form limit as more rounds are added."
        ),
        limitations=(
            "The formula 1/(1-MPC) is an exact result of summing a geometric series -- "
            "always true given a constant MPC and no leakages. It is also the "
            "*simplest possible* version: no taxes, no import leakage, no price or "
            "interest-rate response, and no supply constraints (it implicitly assumes "
            "idle capacity can absorb the extra output). MPC and ΔG are illustrative, "
            "user-chosen numbers. For a richer open-economy multiplier with tax and "
            "import leakage and monetary crowding-out, see the "
            "`india-economic-policy-simulator` sibling project."
        ),
    )
)
