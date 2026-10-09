"""Sources panel: the evidence-ledger records behind a page or section.

`sources_panel("wil_india", "paper_a")` renders one expander listing, for
each dataset: publisher, link, status, period, units, coverage, when it was
published and added to the project, how it was transformed, how missing
values are treated, and its known limitations. Records live in
data_sources/registry.py; the full ledger is on the Data page.
"""
from __future__ import annotations

import html

import streamlit as st

from data_sources import registry


def _link(url: str) -> str:
    if not url:
        return "no stable public URL"
    if url.startswith("http"):
        return f"<a href='{html.escape(url)}' target='_blank' rel='noopener'>{html.escape(url[:80])}{'…' if len(url) > 80 else ''}</a>"
    return f"<code>{html.escape(url)}</code>"


def _card(d: registry.Dataset) -> str:
    rows = [
        ("Publisher", html.escape(d.publisher)),
        ("Source", _link(d.url)),
        ("Status", f"<b>{html.escape(d.status)}</b>"),
        ("Period", html.escape(d.period)),
        ("Units", html.escape(d.units)),
        ("Coverage", f"{html.escape(d.coverage)} · {html.escape(d.frequency)}"),
        ("Published / added", " · ".join(x for x in (html.escape(d.publication),
                                                      f"added to this project {d.added}" if d.added else "fetched live")
                                         if x)),
        ("Transformations", html.escape(d.transformations)),
        ("Missing values", html.escape(d.missing)),
        ("Limitations", html.escape(d.limitations)),
    ]
    if d.files:
        rows.append(("Files", "<br>".join(f"<code>{html.escape(f)}</code>" for f in d.files)))
    body = "".join(f"<tr><td style='color:#8B8D99;padding:3px 12px 3px 0;vertical-align:top;white-space:nowrap'>{k}</td>"
                   f"<td style='padding:3px 0'>{v}</td></tr>" for k, v in rows if v)
    return (f"<div style='margin:6px 0 14px'><div style='font-weight:700;margin-bottom:4px'>{html.escape(d.name)}</div>"
            f"<table style='font-size:13.5px;border-collapse:collapse'>{body}</table></div>")


def sources_panel(*dataset_ids: str, title: str = "Sources & methodology for this page") -> None:
    """Expander with the ledger records for `dataset_ids`; unknown ids are
    reported, not silently skipped."""
    with st.expander(title):
        unknown = []
        for i in dataset_ids:
            try:
                st.markdown(_card(registry.get(i)), unsafe_allow_html=True)
            except KeyError:
                unknown.append(i)
        if unknown:
            st.warning(f"Not in the evidence ledger: {', '.join(unknown)}")
        st.caption("Full ledger, validation checks and downloads: Data page.")
