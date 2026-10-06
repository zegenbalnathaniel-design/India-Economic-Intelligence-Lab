"""A deliberately small aggregate demand / aggregate supply diagram.

This module is intentionally much simpler than a full macro simulator: two
straight lines in (output, price level) space, with an optional one-off
shift applied to each. It is meant to make the textbook AD/AS *diagram*
interactive, not to model monetary transmission, inflation dynamics, or
multi-period adjustment -- see the `india-economic-policy-simulator`
sibling project for a much richer macro model.

Aggregate demand:  Y = A_d - b_d * P     (slopes down: higher prices lower
                                           real spending)
Aggregate supply:  Y = A_s + b_s * P     (slopes up: higher prices call
                                           forth more output, short run)

where A_d and A_s are the demand/supply intercepts, which can each be
shifted by a demand shock (ad_shift) or a supply shock (as_shift) -- e.g.
a fiscal expansion shifts AD right (ad_shift > 0), an oil-price spike
shifts AS left (as_shift < 0).

Equilibrium (by the same algebra as linear demand & supply):

    P* = (A_d - A_s) / (b_d + b_s)
    Y* = A_d - b_d * P*
"""

from __future__ import annotations

from typing import Any, Dict

from econ_lab.registry import EconModule, register_module


def _equilibrium(ad_intercept: float, ad_slope: float, as_intercept: float, as_slope: float) -> Dict[str, float]:
    if ad_slope <= 0 or as_slope <= 0:
        raise ValueError("AD slope and AS slope must both be positive.")
    p_star = (ad_intercept - as_intercept) / (ad_slope + as_slope)
    y_star = ad_intercept - ad_slope * p_star
    return {"p_star": p_star, "y_star": y_star}


def compute(
    ad_intercept: float,
    ad_slope: float,
    as_intercept: float,
    as_slope: float,
    ad_shift: float = 0.0,
    as_shift: float = 0.0,
) -> Dict[str, Any]:
    """Compute the baseline and post-shock AD/AS equilibrium.

    Args:
        ad_intercept: Baseline AD intercept (AD curve: Y = ad_intercept - ad_slope*P).
        ad_slope: AD slope magnitude. Must be > 0.
        as_intercept: Baseline AS intercept (AS curve: Y = as_intercept + as_slope*P).
        as_slope: AS slope. Must be > 0.
        ad_shift: One-off shift added to ad_intercept (e.g. a fiscal/monetary
            demand shock). Positive = expansionary.
        as_shift: One-off shift added to as_intercept (e.g. a supply/cost shock).
            Positive = favorable supply shock.

    Returns:
        dict with the baseline equilibrium (p0, y0), the shocked
        equilibrium (p1, y1), and the resulting change in output and price
        level (delta_y, delta_p).

    Raises:
        ValueError: for non-positive slopes or an equilibrium price below zero.
    """
    baseline = _equilibrium(ad_intercept, ad_slope, as_intercept, as_slope)
    shocked = _equilibrium(ad_intercept + ad_shift, ad_slope, as_intercept + as_shift, as_slope)

    if baseline["p_star"] < 0 or shocked["p_star"] < 0:
        raise ValueError("These parameters imply a negative equilibrium price level.")

    return {
        "p0": baseline["p_star"],
        "y0": baseline["y_star"],
        "p1": shocked["p_star"],
        "y1": shocked["y_star"],
        "delta_y": shocked["y_star"] - baseline["y_star"],
        "delta_p": shocked["p_star"] - baseline["p_star"],
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    st.markdown("**AD:** Y = A_d − b_d·P &nbsp;&nbsp; **AS:** Y = A_s + b_s·P")
    col1, col2 = st.columns(2)
    with col1:
        ad_intercept = st.slider("AD intercept A_d", 100.0, 500.0, 300.0, 5.0, key="adas_adi")
        ad_slope = st.slider("AD slope b_d", 0.5, 10.0, 3.0, 0.5, key="adas_ads")
        ad_shift = st.slider("Demand shock (ad_shift)", -100.0, 100.0, 20.0, 5.0, key="adas_adshift",
                              help="e.g. a fiscal/monetary expansion shifts AD right (+).")
    with col2:
        as_intercept = st.slider("AS intercept A_s", 0.0, 300.0, 50.0, 5.0, key="adas_asi")
        as_slope = st.slider("AS slope b_s", 0.5, 10.0, 2.0, 0.5, key="adas_ass")
        as_shift = st.slider("Supply shock (as_shift)", -100.0, 100.0, 0.0, 5.0, key="adas_asshift",
                              help="e.g. an oil-price spike shifts AS left (-).")
    return {
        "ad_intercept": ad_intercept, "ad_slope": ad_slope,
        "as_intercept": as_intercept, "as_slope": as_slope,
        "ad_shift": ad_shift, "as_shift": as_shift,
    }


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import numpy as np
    import plotly.graph_objects as go
    import streamlit as st

    p_max = max(results["p0"], results["p1"]) * 1.6 + 1
    prices = np.linspace(0, p_max, 200)

    ad0 = inputs["ad_intercept"] - inputs["ad_slope"] * prices
    as0 = inputs["as_intercept"] + inputs["as_slope"] * prices
    ad1 = (inputs["ad_intercept"] + inputs["ad_shift"]) - inputs["ad_slope"] * prices
    as1 = (inputs["as_intercept"] + inputs["as_shift"]) + inputs["as_slope"] * prices

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ad0, y=prices, mode="lines", name="AD (baseline)",
                              line=dict(color="#2563eb", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=as0, y=prices, mode="lines", name="AS (baseline)",
                              line=dict(color="#dc2626", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=ad1, y=prices, mode="lines", name="AD (after shock)",
                              line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=as1, y=prices, mode="lines", name="AS (after shock)",
                              line=dict(color="#dc2626", width=3)))
    fig.add_trace(go.Scatter(x=[results["y0"]], y=[results["p0"]], mode="markers",
                              marker=dict(size=10, color="gray"), name="Baseline equilibrium"))
    fig.add_trace(go.Scatter(x=[results["y1"]], y=[results["p1"]], mode="markers",
                              marker=dict(size=12, color="#111827"), name="New equilibrium"))
    fig.update_layout(xaxis_title="Output (Y)", yaxis_title="Price level (P)",
                       template="plotly_white", height=460, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    m1, m2 = st.columns(2)
    m1.metric("ΔOutput", f"{results['delta_y']:+.2f}")
    m2.metric("ΔPrice level", f"{results['delta_p']:+.2f}")


MODULE = register_module(
    EconModule(
        key="macro_ad_as",
        domain="Macroeconomics",
        title="Aggregate Demand & Aggregate Supply",
        concept=(
            "Aggregate demand (total desired spending) slopes down in the price "
            "level; aggregate supply (total desired output) slopes up. Their "
            "intersection pins down the economy-wide price level and output. A "
            "demand shock shifts AD; a supply shock shifts AS -- and the same "
            "linear-intersection algebra as the single-market model applies."
        ),
        equation=r"Y=A_d-b_dP \qquad Y=A_s+b_sP \qquad P^*=\dfrac{A_d-A_s}{b_d+b_s}, \quad Y^*=A_d-b_dP^*",
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Apply a positive demand shock alone (ad_shift > 0, as_shift = 0) and "
            "note that both output and the price level rise. Then instead apply a "
            "negative supply shock alone (as_shift < 0) and note output falls while "
            "the price level rises -- the classic 'stagflationary' signature that "
            "distinguishes a supply shock from a demand shock on this diagram."
        ),
        explanation=(
            "This is the same two-line intersection as the microeconomic "
            "supply-and-demand model, relabeled: price level replaces price, and "
            "aggregate output replaces quantity. A rightward AD shift (ad_shift>0) "
            "raises both P and Y. A leftward AS shift (as_shift<0) raises P but lowers "
            "Y -- demand and supply shocks move price and output in different "
            "relative directions, which is the key diagnostic lesson of the diagram."
        ),
        limitations=(
            "This is a static, single-period, two-linear-curve sketch of AD/AS -- it "
            "has no explicit money market, no expectations, no multi-period dynamics, "
            "and is deliberately much simpler than a full macro model. For a richer "
            "treatment with a fiscal multiplier, monetary transmission, a Phillips "
            "curve, and debt dynamics, see the `india-economic-policy-simulator` "
            "sibling project. The intercepts and slopes here are illustrative, "
            "user-chosen numbers, not calibrated to any real economy."
        ),
    )
)
