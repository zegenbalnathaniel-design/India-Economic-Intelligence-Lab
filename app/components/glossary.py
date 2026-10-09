"""A reusable "what does this mean" indicator-glossary component.

Every Lab page in this project shows numbers that are real (or transparent
calculations over real numbers — see DATA_REGISTRY.md for the VERIFIED /
PARTIAL / ESTIMATED / DERIVED / SPLICED status of each underlying series).
That does not make the numbers self-explanatory. A reader who has never
seen a robust z-score, a beta-convergence regression or an EMI formula
needs a plain-language bridge between "here is a chart" and "here is what
the chart is telling you, and where it can mislead you."

`indicator_note()` renders that bridge as a simple, labelled
`st.expander` — no new CSS, no new widget, nothing that competes visually
with the charts themselves. Each call is meant to explain exactly one
concept: what it measures, how to read a high value against a low one,
what moves it in practice, and one honest caveat about where the
indicator stops being informative. The caveats are written the way a
careful economist would write them for a general reader — precise about
what *is* established (robust statistics, convergence theory, loan
amortisation mechanics, the r > g accounting identity) and explicit about
uncertainty where none of the data resolves it (causality, forecasting,
welfare comparisons, anything that depends on an assumption the page
states rather than measures).

Nothing in this module computes, fetches or caches data. It only renders
text that was already decided elsewhere (the calling page), so it is safe
to call as many times per page as there are charts, stat cards or derived
metrics that need a plain-language explanation nearby.
"""
from __future__ import annotations

import streamlit as st

# The three framings a note can take. Each produces a different, honest
# expander label for the same underlying content -- a concept note answers
# "what is this", a method note answers "how is this calculated", and a
# caveat note answers "where does this stop being reliable". Defaulting to
# "concept" keeps the common case (`indicator_note("X", "...")`) matching
# the literal "What is X?" phrasing used throughout this project's pages.
_LABEL_TEMPLATES = {
    "concept": "What is {title}?",
    "method": "How is {title} calculated?",
    "caveat": "What are the limits of {title}?",
}


def indicator_note(title: str, body_markdown: str, *, kind: str = "concept") -> None:
    """Render an expandable "What is {title}?" explainer.

    Parameters
    ----------
    title : str
        The concept, index or chart being explained (e.g. "r − g",
        "robust z-score", "sigma convergence"). Used only to build the
        expander's label -- it is not re-stated inside `body_markdown`
        unless the caller wants it to be.
    body_markdown : str
        Plain-language explanation, rendered as markdown. By convention
        on this project's pages, a good note covers: what the indicator
        measures, how to read a high value versus a low one, what moves
        it in practice, and one honest caveat about its limits (e.g.
        "this is a descriptive statistic, not evidence of causation").
    kind : str, optional
        Changes only the expander's label template, not its content or
        appearance -- "concept" (default) asks "What is {title}?",
        "method" asks "How is {title} calculated?", and "caveat" asks
        "What are the limits of {title}?". Any other value falls back to
        the "concept" phrasing.
    """
    label = _LABEL_TEMPLATES.get(kind, _LABEL_TEMPLATES["concept"]).format(title=title)
    with st.expander(label):
        st.markdown(body_markdown)
