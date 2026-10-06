"""Methodology & Sources — the full source table, validation rules, and
this environment's actual live-fetch probe result."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from data_observatory import loaders  # noqa: E402

st.set_page_config(page_title="Methodology & Sources — India Economic Data Observatory", page_icon="📊", layout="wide")
st.title("Methodology & Sources")

st.markdown(
    """
### Network probe result (this specific environment)

I tested a plain, unauthenticated `requests.get()` against the World Bank's
open REST API (`api.worldbank.org`) — the most tractable real target of the
four official sources this project targets — before writing any loader
code, not after. **The result in this specific sandboxed runtime: the
request failed at the outbound network proxy** (`ProxyError` /
`403 Forbidden` from the environment's own egress proxy, before reaching
World Bank at all). RBI's DBIE portal and MoSPI's site were not separately
retested since they sit behind the same proxy.

This means that, **as deployed in this exact environment**, every
indicator below runs its synthetic fallback path on every load — not
because the architecture doesn't try, but because this sandbox's network
policy blocks the outbound call before it leaves the container. **Outside
this sandbox, with ordinary internet access, every indicator whose row
below has a World Bank URL will fetch live, real data on each load** —
nothing about the pipeline is faked to always prefer synthetic; try it
yourself with `allow_live=True` on a normal machine and compare the
`status` field you get back.

See `docs/DATA_SOURCES.md` for the full source table in plain Markdown and
the exact error text the probe returned.
"""
)

st.divider()
st.subheader("Source table")

rows = []
for key, spec in loaders.INDICATORS.items():
    rows.append(
        {
            "indicator": spec.name,
            "category": spec.category,
            "provider": spec.provider,
            "source": spec.source_name,
            "url": spec.url,
            "unit": spec.unit,
            "frequency": spec.frequency,
            "has_plain_rest_api": "yes (World Bank)" if spec.wb_code else "no — probe only",
            "limitations": spec.limitations,
        }
    )
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Validation rules applied to every series")
st.markdown(
    """
1. **Sorted, monotonically increasing dates** — any out-of-order input is re-sorted.
2. **No duplicate periods** — if a period appears twice (e.g. a revised release superseding
   an earlier figure), the later value wins and the duplicate is logged.
3. **No impossible values** — each indicator has a documented domain (e.g. unemployment rate
   must be 0–100%); a value outside it is treated as missing, never silently kept.
4. **Explicit missing-data flagging** — any gap (from a domain violation or a genuine missing
   period) is forward-filled from the prior observation, and every forward-filled point is
   marked `True` in an `imputed` column. Nothing is imputed silently.
"""
)

st.subheader("Caching")
st.markdown(
    """
Every loaded series is cached to a CSV file under `data/cache/`, keyed by indicator, date
range, and live-vs-synthetic status, so a synthetic result is never served back as if it
were live or vice versa. See `src/data_observatory/cache.py` for the full rationale (on-disk
over in-memory, specifically because it needs to survive Streamlit's rerun-per-interaction
model and stay human-inspectable).
"""
)
