"""Research page — the two underlying papers, plus an evaluation table."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app.components.theme import setup, kicker, callout, footnote


setup("Research")


with st.sidebar:
    st.markdown("## Research")
    st.caption("The two papers behind this project")
    st.markdown(
        "- Paper A · Income & wealth inequality in India\n"
        "- Paper B · Fed rates & JP Morgan (BFPI)\n"
        "- Evaluation table"
    )


kicker("Research")
st.title("The two papers behind this project")
st.markdown(
    "This site is a computational supplement to two written papers. The "
    "papers state the research questions, motivate the methodology and "
    "discuss findings; this site lets the reader interact with the models."
)


# Paper A
st.header("Paper A · Income & wealth inequality in India")
st.markdown(
    "**Research question.** How do income, ownership, asset composition "
    "and returns on capital influence wealth accumulation and economic "
    "mobility in India?\n\n"
    "**Core concepts.** Income vs wealth; the capability → employment → "
    "income → ownership → wealth chain; household asset composition; "
    "compounding; productive vs non-productive assets; r vs g; financial "
    "resilience; intergenerational mobility.\n\n"
    "**Key exhibit.** A composition-effect simulation: ₹1 lakh contributed "
    "annually for 30 years under representative household allocations, "
    "showing that outcomes diverge sharply not because of savings but "
    "because of composition."
)
st.page_link("pages/1_Wealth_Inequality_Lab.py", label="Explore Paper A interactively →")


# Paper B
st.header("Paper B · Fed rates and JP Morgan financial performance, 2018-2024")
st.markdown(
    "**Research question.** To what extent did changes in Federal Reserve "
    "interest rates influence JP Morgan's financial performance during "
    "2018-2024?\n\n"
    "**Methodology used in the paper.** A composite Bank Financial "
    "Performance Index (BFPI) constructed from five indicators (PPNR / "
    "assets, CET1 ratio, net charge-off rate, LCR, unrealised losses / "
    "CET1), each transformed into a robust z-score using historical "
    "median and MAD with a direction coefficient, then averaged with "
    "equal weights. The paper then relates BFPI to the federal funds "
    "rate using Spearman correlation and event studies around FOMC "
    "decisions.\n\n"
    "**Extension in this site.** The same construction is applied to a "
    "five-bank Indian panel (the iBFPI) and compared to the RBI repo "
    "rate. See the Banking Lab."
)
st.page_link("pages/2_Banking_Monetary_Policy_Lab.py", label="Explore Paper B / iBFPI interactively →")


# Evaluation
st.markdown("---")
st.header("Does the data support the research?")
st.markdown(
    "A conservative evaluation of the main hypotheses tested in the two "
    "papers. Verdicts are **SUPPORTS / MIXED / CONTRADICTS / INSUFFICIENT "
    "DATA**. No numeric research score is produced — the aim is to make "
    "the strength of the evidence explicit, not to compress it."
)

evaluation = pd.DataFrame([
    {
        "Claim": "Asset composition materially changes long-run wealth even at fixed savings rate",
        "Variable": "Final real wealth W(T)",
        "Measurement": "30-year FV simulation",
        "Data": "Historical long-run nominal returns; author-set allocations",
        "Method": "Deterministic future-value with annual rebalancing",
        "Result": "Different allocations produce final W(T) that differ by 3-8x under paper defaults",
        "Interpretation": "Composition effect is quantitatively large",
        "Limitations": "Historical returns ≠ future returns; no fees/taxes/transaction costs; sample of one household",
        "Verdict": "SUPPORTS",
    },
    {
        "Claim": "r > g is a mechanical driver of wealth-share divergence",
        "Variable": "r − g on a consistent real basis",
        "Measurement": "r_real − g_real",
        "Data": "User-supplied r, π, g",
        "Method": "Identity, not causal test",
        "Result": "Sign depends entirely on assumed r, π, g",
        "Interpretation": "The identity holds; distributional effect on individuals is not implied",
        "Limitations": "No behavioural or bequest channel modelled",
        "Verdict": "MIXED",
    },
    {
        "Claim": "Bank financial performance co-moves negatively with the policy rate 2018-2024",
        "Variable": "iBFPI vs repo rate",
        "Measurement": "Spearman ρ, quarterly",
        "Data": "Illustrative panel of 5 Indian banks (this build)",
        "Method": "Robust z-score composite + Spearman with regime split",
        "Result": "Negative ρ in the demo panel; regime split shows heterogeneity",
        "Interpretation": "Consistent with unrealised-loss channel; correlation only",
        "Limitations": "Illustrative data in the MVP; small n; correlation not causation; no bank-fixed-effects panel",
        "Verdict": "INSUFFICIENT DATA",
    },
    {
        "Claim": "The BFPI methodology transfers cleanly to Indian banks",
        "Variable": "iBFPI construction stability",
        "Measurement": "Direction coefficients, indicator availability",
        "Data": "Reported Basel III disclosures",
        "Method": "Direct replication",
        "Result": "Indicators are reported by all five banks; MAD > 0",
        "Interpretation": "Methodological transfer is feasible; results depend on real data replacing the demo panel",
        "Limitations": "Accounting differences between banks; possible IND-AS vs IFRS discontinuities",
        "Verdict": "MIXED",
    },
])
st.dataframe(evaluation, hide_index=True, use_container_width=True)

callout(
    "The evaluation intentionally avoids compressing evidence into a "
    "single score. A research portfolio should surface uncertainty, not "
    "hide it behind a percentage.",
    kind="note",
)

footnote(
    "The papers themselves are not reproduced verbatim on this site. "
    "This page presents the research questions, methods and evaluation in "
    "the form needed to make the interactive components legible."
)
