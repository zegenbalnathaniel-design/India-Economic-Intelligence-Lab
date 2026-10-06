"""Compound interest, present value, and a simple savings annuity.

Future value of a lump sum principal P compounded at periodic rate r for
n periods:

    FV_lump = P * (1 + r)^n

Future value of an ordinary annuity (a fixed contribution C added at the
*end* of every period, each then compounding for the remaining periods):

    FV_annuity = C * [(1+r)^n - 1] / r     (r > 0)
    FV_annuity = C * n                     (r = 0, no growth to compound)

Total future value here is the sum of both: an initial lump sum plus a
stream of equal periodic contributions. Present value is the reverse
operation -- discounting a known future amount back to today:

    PV = FV / (1 + r)^n

These are the standard closed-form time-value-of-money formulas; the
principal, rate, number of periods and contribution are illustrative,
user-chosen numbers for this demo, not a real financial product's terms.
"""

from __future__ import annotations

from typing import Any, Dict, List

from econ_lab.registry import EconModule, register_module


def compute(principal: float, rate: float, periods: int, contribution: float = 0.0) -> Dict[str, Any]:
    """Compute compound future value (lump sum + annuity) and present value.

    Args:
        principal: Initial lump sum invested today. Must be >= 0.
        rate: Periodic interest rate as a decimal (e.g. 0.05 for 5%).
            Must satisfy rate > -1 (and realistically rate >= 0 for a savings
            context, but small negative "real rate" demos are allowed).
        periods: Number of compounding periods. Must be an integer >= 0.
        contribution: Additional amount contributed at the end of every
            period (an ordinary annuity). May be 0. Must be >= 0.

    Returns:
        dict with the future value of the lump sum alone (fv_lump), the
        future value of the contribution stream alone (fv_annuity), their
        sum (fv_total), the present value of that total future value
        (discounted back at the same rate -- which recovers the original
        principal + contribution stream exactly), and the year-by-year
        balance path.

    Raises:
        ValueError: for a negative principal/contribution, rate <= -1, or
            a negative number of periods.
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative.")
    if contribution < 0:
        raise ValueError("Contribution cannot be negative.")
    if rate <= -1:
        raise ValueError("Rate must be greater than -100% per period.")
    if periods < 0:
        raise ValueError("periods cannot be negative.")

    fv_lump = principal * (1.0 + rate) ** periods

    if periods == 0:
        fv_annuity = 0.0
    elif rate == 0:
        fv_annuity = contribution * periods
    else:
        fv_annuity = contribution * (((1.0 + rate) ** periods - 1.0) / rate)

    fv_total = fv_lump + fv_annuity

    balance_path: List[float] = [principal]
    balance = principal
    for _ in range(periods):
        balance = balance * (1.0 + rate) + contribution
        balance_path.append(balance)

    discount_factor = (1.0 + rate) ** periods
    present_value = fv_total / discount_factor if discount_factor != 0 else float("inf")

    return {
        "fv_lump": fv_lump,
        "fv_annuity": fv_annuity,
        "fv_total": fv_total,
        "present_value": present_value,
        "balance_path": balance_path,
    }


def render_controls() -> Dict[str, Any]:
    import streamlit as st

    col1, col2 = st.columns(2)
    with col1:
        principal = st.slider("Initial principal", 0.0, 100000.0, 10000.0, 500.0, key="ci_principal")
        rate_pct = st.slider("Periodic rate (%)", 0.0, 20.0, 7.0, 0.1, key="ci_rate")
    with col2:
        periods = st.slider("Number of periods (years)", 0, 50, 20, 1, key="ci_periods")
        contribution = st.slider("Contribution per period", 0.0, 5000.0, 1000.0, 100.0, key="ci_contribution")
    return {"principal": principal, "rate": rate_pct / 100.0, "periods": periods, "contribution": contribution}


def render_visualization(inputs: Dict[str, Any], results: Dict[str, Any]) -> None:
    import plotly.graph_objects as go
    import streamlit as st

    t = list(range(len(results["balance_path"])))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=results["balance_path"], mode="lines+markers",
                              name="Account balance", line=dict(color="#2563eb", width=3)))
    fig.update_layout(xaxis_title="Period", yaxis_title="Balance",
                       template="plotly_white", height=440)
    st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Future value (lump sum)", f"{results['fv_lump']:,.2f}")
    m2.metric("Future value (contributions)", f"{results['fv_annuity']:,.2f}")
    m3.metric("Total future value", f"{results['fv_total']:,.2f}")
    st.caption(f"Present value of that total (discounted back at the same rate): {results['present_value']:,.2f}")


MODULE = register_module(
    EconModule(
        key="finance_compound_interest",
        domain="Finance",
        title="Compound Interest & Present Value",
        concept=(
            "Money invested today grows by earning interest not just on the "
            "original principal but on previously-earned interest too. Present "
            "value runs the same formula in reverse: it answers 'what is a future "
            "sum worth today?'"
        ),
        equation=(
            r"FV_{\text{lump}} = P(1+r)^n \qquad "
            r"FV_{\text{annuity}} = C\cdot\dfrac{(1+r)^n-1}{r} \qquad "
            r"PV = \dfrac{FV}{(1+r)^n}"
        ),
        compute=compute,
        render_controls=render_controls,
        render_visualization=render_visualization,
        experiment=(
            "Set contribution to 0 and compare a 10-year horizon to a 30-year "
            "horizon at the same rate -- notice the future value doesn't just "
            "triple, it grows much faster than linearly because of compounding. "
            "Then add a modest regular contribution and see how much of the final "
            "balance comes from the contributions themselves versus the lump sum."
        ),
        explanation=(
            "The lump-sum formula P(1+r)^n is exact: each period multiplies the "
            "current balance by (1+r). The annuity formula sums a geometric series "
            "of contributions, each compounding for a different number of remaining "
            "periods; it has the closed form shown above for r != 0, and reduces to a "
            "simple C*n when r = 0 (no compounding to speak of). Discounting divides "
            "back out the same (1+r)^n factor, which is why PV here exactly recovers "
            "the account's value in today's terms."
        ),
        limitations=(
            "These are the standard closed-form time-value-of-money formulas -- "
            "always true given a constant periodic rate -- not a projection for any "
            "real account, fund, or loan. The rate, principal, contribution, and "
            "number of periods are illustrative numbers for this demo; real returns "
            "vary period to period, are not guaranteed, and this module ignores "
            "taxes, fees, and inflation. For portfolio-level risk and diversification "
            "math, see the `portfolio-optimization-lab` and `sip-monte-carlo` sibling "
            "projects."
        ),
    )
)
