"""Methodology page — transparent write-up of every calculation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.theme import setup, kicker, callout, footnote


setup("Methodology")


with st.sidebar:
    st.markdown("## Methodology")
    st.caption("Sections")
    st.markdown(
        "- Wealth: FV, real vs nominal\n"
        "- r − g\n"
        "- Gini (used sparingly)\n"
        "- iBFPI construction\n"
        "- Spearman correlation\n"
        "- Rate-regime split\n"
        "- What is from the papers vs new here"
    )


kicker("Methodology")
st.title("Transparent methodology")
st.markdown(
    "Every number produced on this site is derived from the formulas "
    "and assumptions below. Nothing is black-box."
)


# ---- Wealth
st.header("Wealth accumulation — future value with rebalancing")
st.markdown(
    "The household contributes a constant amount `C` at the **start** of "
    "each year for `T` years, split across assets by target allocation `w`. "
    "Each asset `k` compounds at nominal return `r_k`. When rebalancing is "
    "on, holdings are reset to `w` at year-end."
)
st.latex(r"B_{k,t} = w_k \cdot \Big[ B_{k, t-1} + C \Big] \cdot (1 + r_k)")
st.latex(r"W_T^{\text{nom}} = \sum_k B_{k,T}, \qquad W_T^{\text{real}} = \frac{W_T^{\text{nom}}}{(1+\pi)^T}")
st.markdown(
    "The **weighted portfolio return** is `r_p = Σ_k w_k · r_k` and the "
    "**real weighted return** uses the Fisher approximation "
    "`(1 + r_p) / (1 + π) − 1`."
)


# ---- r - g
st.header("r − g")
st.markdown(
    "`r` and `g` must be measured on the same basis. The lab converts a "
    "nominal `r` to real using `r_real = (1+r_nom) / (1+π) − 1` and then "
    "compares to real growth `g_real`."
)
callout(
    "r > g is an **identity about capital's share**, not a mechanical claim "
    "about the distribution of wealth across individuals. Distributional "
    "outcomes depend on savings rates by wealth level, bequests, portfolio "
    "composition across the distribution, and demographic dynamics — none "
    "of which are inside this identity.",
    kind="warn",
)


# ---- Gini
st.header("Gini coefficient (used sparingly)")
st.markdown(
    "Where used, the Gini is computed from sorted individual wealth levels "
    "with the standard trapezoidal Lorenz-curve formula. The MVP does not "
    "run a distributional Gini simulation — the composition-effect module "
    "is deterministic for a single household."
)


# ---- iBFPI
st.header("iBFPI — robust composite index")
st.markdown(
    "For indicator `X_k` on bank `i` at time `t`, and direction coefficient "
    "`D_k`:"
)
st.latex(r"Z^*_{k,it} = D_k \cdot \frac{X_{k,it} - \mathrm{median}_i(X_k)}{1.4826 \cdot \mathrm{MAD}_i(X_k)}")
st.markdown(
    "The scale factor `1.4826` makes MAD consistent with the standard "
    "deviation of a normal distribution. Standardisation is done **within "
    "each bank's own history**, so a value is comparable to that bank's "
    "own baseline. The iBFPI is the equal-weight mean of the five Z*:"
)
st.latex(r"iBFPI_{it} = \frac{1}{5} \sum_k Z^*_{k,it}")
st.markdown(
    "The five indicators, direction and interpretation:\n"
    "1. **PPNR / Assets** (+) — core earnings power\n"
    "2. **CET1 Ratio** (+) — capital adequacy\n"
    "3. **Net Charge-Off Rate** (−) — realised credit losses\n"
    "4. **Liquidity Coverage Ratio** (+) — short-run liquidity\n"
    "5. **Unrealised Securities Losses / CET1** (−) — MTM stress on AFS book"
)


# ---- Spearman
st.header("Spearman rank correlation")
st.markdown(
    "Spearman ρ is a rank-based correlation that captures monotonic "
    "association without assuming linearity or normality. Used here for "
    "iBFPI × repo rate association. The p-value is the two-sided test of "
    "H0: ρ = 0. **Correlation is not causation** — an event-study or panel "
    "regression is needed for a causal claim."
)


# ---- Rate regime split
st.header("Rate-regime split")
st.markdown(
    "Rate regimes are classified from the three-quarter rolling change in "
    "the repo rate:"
)
st.latex(r"\Delta_3 r_t = \sum_{s=t-2}^{t} (r_s - r_{s-1})")
st.markdown(
    "`Δ_3 r_t > +25bp` → **rising**, `Δ_3 r_t < −25bp` → **falling**, "
    "otherwise **stable**. Correlation is then re-computed within each "
    "regime."
)


# ---- Provenance
st.markdown("---")
st.header("What is from the papers, what is new here")
st.markdown(
    "| Component | Origin | User assumption |\n"
    "| --- | --- | --- |\n"
    "| Composition-effect exhibit | **Paper A** | Contribution, horizon, weights, returns, inflation |\n"
    "| Asset-allocation comparison | New here | Same as above |\n"
    "| r − g explorer | Framing from Paper A + literature | r, π, g |\n"
    "| BFPI construction (formula) | **Paper B** | Direction coefficients (fixed) |\n"
    "| iBFPI (application to India) | New here | Bank subset, weighting |\n"
    "| Regime split | New here | Threshold (fixed at ±25bp) |\n"
    "| Illustrative bank panel | New here (synthetic) | Replace CSV to reproduce with real data |"
)

footnote(
    "The distinction between what already exists in the written papers "
    "and what is added by this computational supplement is deliberate. "
    "This site does not claim novelty for the papers; it claims utility "
    "as an interactive extension."
)
