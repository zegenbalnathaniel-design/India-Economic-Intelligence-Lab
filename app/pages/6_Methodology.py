"""Methodology page — transparent write-up of every calculation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reload data_sources/ and analysis/ if a redeploy changed them (Streamlit
# only watches app/); must run before those packages are imported below.
from app.components.freshness import reload_stale_modules  # noqa: E402

reload_stale_modules()

import streamlit as st

from app.components.theme import setup, kicker, callout, footnote
from app.components import hairline_display


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

fig_col, text_col = st.columns([2, 3])
with fig_col:
    hairline_display.render("elevator")
with text_col:
    st.markdown(
        "**From question to model, one floor at a time.** Move the pointer "
        "up and down the shaft: every number on this site passes through "
        "the same four stops — a real question, real data, a stated model "
        "or simulation, and an interpretation that names its own limits. "
        "No chart on this site skips a floor."
    )

st.markdown("---")


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
    "The Wealth Lab computes a Gini for every year of the World Inequality "
    "Lab series from five published group shares (Bottom 50%, Middle 40%, "
    "Top 10%, Top 1%, Top 0.1%). The Lorenz curve through those points is "
    "joined with straight lines and the Gini is 1 − 2 × the area under it "
    "(trapezoidal rule). Because everyone inside a group is treated as "
    "equal, this is a **lower bound** on the true Gini. A redistribution "
    "scenario moves share from the Top 1% to the Bottom 50% and recomputes "
    "it. A household-level Gini needs AIDIS / NSS microdata."
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


# ---- Robustness of the iBFPI association
st.header("Robustness of the iBFPI–repo association")
st.markdown(
    "- **Weight sensitivity.** 300 random indicator weightings drawn uniformly from the simplex "
    "(Dirichlet(1,…,1)); ρ is recomputed for each and the distribution is shown.\n"
    "- **Leave-one-out.** Each indicator dropped in turn, the rest equal-weighted.\n"
    "- **Direction flips.** Each direction coefficient `D_k` reversed in turn.\n"
    "- **Panel regression.** iBFPI on the repo rate with bank fixed effects (within-bank OLS); "
    "standard errors conventional, clustered by bank (CR1; unreliable with five banks and labelled "
    "so), and, for the system series, Newey–West with lag `⌊4(n/100)^{2/9}⌋`. No macro controls — "
    "quarterly GDP and CPI are not in the project."
)


# ---- Convergence
st.header("Interstate convergence")
st.markdown(
    "**σ-convergence** is the coefficient of variation (population standard deviation ÷ mean, %) of "
    "real per-capita NSDP across states in each year. Coverage changes over time, so the headline "
    "uses a **balanced panel** — only the states observed in every year — and fits an OLS trend on "
    "year. The all-states series is shown alongside and labelled as not like-for-like.\n\n"
    "**β-convergence** regresses each state's average annual growth over the whole window on its "
    "log initial income (one observation per state); a significantly negative slope means poorer "
    "states grew faster. Both are descriptive: they say nothing about why."
)


# ---- Data validation and evidence ledger
st.header("Evidence ledger and data validation")
st.markdown(
    "Every dataset has a record (`data_sources/registry.py`) with its publisher, link, status, "
    "period, units, coverage, publication and download dates, transformations, missing-value "
    "treatment and limitations. A test fails if any CSV in `data/` is not registered.\n\n"
    "Each file is checked for duplicate rows and keys, missing cells (counted, never filled), "
    "malformed period labels, names with stray spaces or inconsistent spellings, impossible values "
    "(shares above 100, negative prices or levels) and suspicious period-on-period jumps "
    "(|robust z| > 8 within one state or city). Findings are reported on the Data page; nothing is "
    "removed or corrected automatically."
)


# ---- Reproducibility
st.header("Exports and reproducibility")
st.markdown(
    "Every chart's camera button saves a PNG at three times screen resolution, with the chart title "
    "and a *Source:* line. Indian financial-year labels (e.g. `2012-13`) are plotted as ordered "
    "categories, never parsed as dates. The Research Library computes each investigation from the "
    "files listed in its sources and downloads it as an HTML brief (question, motivation, sources, "
    "method, results, interpretation, limitations, further questions, settings and a UTC timestamp), "
    "with the result tables as CSV and the settings as JSON."
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
    "| Weight sensitivity, leave-one-out, fixed-effects regression | New here | Number of draws (fixed at 300) |\n"
    "| Group shares, Gini lower bound | **World Inequality Lab** shares; Gini new here | Redistribution scenario |\n"
    "| Convergence (σ balanced panel, β) | New here | None |\n"
    "| Research Library investigations | New here | Inflation and g (composition effect) |\n"
    "| Illustrative bank panel | New here (synthetic) | Replace CSV to reproduce with real data |"
)

footnote(
    "The distinction between what already exists in the written papers "
    "and what is added by this computational supplement is deliberate. "
    "This site does not claim novelty for the papers; it claims utility "
    "as an interactive extension."
)
