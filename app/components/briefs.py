"""Research briefs: a self-contained HTML document for one investigation.

Contains the question, motivation, data sources (evidence-ledger records),
method, charts, results tables, findings (facts / statistics /
interpretation / hypotheses kept separate), limitations, further
questions, the settings used and the time it was generated — so a reader
can check and reproduce it. Charts load plotly.js from its CDN when the
file is opened.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go

from data_sources import registry

_CSS = """
body{font-family:Inter,Helvetica Neue,Arial,sans-serif;background:#11131A;color:#F5F0E6;max-width:960px;margin:40px auto;padding:0 20px;line-height:1.55}
h1{font-size:30px;margin-bottom:4px} h2{font-size:20px;margin-top:32px;border-bottom:1px solid #2A2E3C;padding-bottom:4px}
.kicker{color:#24A6A1;letter-spacing:.12em;font-size:12px;text-transform:uppercase}
.muted{color:#8B8D99;font-size:13px} table{border-collapse:collapse;font-size:13px;margin:8px 0}
td,th{border:1px solid #2A2E3C;padding:4px 8px;text-align:left} th{background:#181B26}
.box{border-left:3px solid #F3C542;background:#181B26;padding:10px 14px;margin:10px 0}
a{color:#3155D9}
"""


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>" if items else "<p class='muted'>None.</p>"


def _source(dataset_id: str) -> str:
    try:
        d = registry.get(dataset_id)
    except KeyError:
        return f"<li>{html.escape(dataset_id)} (not in the evidence ledger)</li>"
    link = f" — <a href='{html.escape(d.url)}'>{html.escape(d.url)}</a>" if d.url.startswith("http") else ""
    return (f"<li><b>{html.escape(d.name)}</b> ({html.escape(d.status)}). {html.escape(d.publisher)}{link}. "
            f"Period: {html.escape(d.period)}. Units: {html.escape(d.units)}. "
            f"Limitations: {html.escape(d.limitations)}</li>")


def brief_html(inv, figures: list[go.Figure], max_rows: int = 40) -> str:
    """Standalone HTML research brief for an `analysis.research_library.Investigation`."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    charts = "".join(
        f.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False, config={"displaylogo": False})
        for i, f in enumerate(figures))
    tables = ""
    for name, df in inv.tables.items():
        shown = df.head(max_rows)
        note = f"<p class='muted'>First {max_rows} of {len(df)} rows — full data in the CSV download.</p>" if len(df) > max_rows else ""
        tables += f"<h3>{html.escape(name)}</h3>" + shown.to_html(index=False, float_format=lambda v: f"{v:,.3f}",
                                                                  border=0, na_rep="—") + note
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(inv.title)} — research brief</title>
<style>{_CSS}</style></head><body>
<div class="kicker">India Economic Intelligence Lab · Research brief</div>
<h1>{html.escape(inv.title)}</h1>
<p class="muted">Generated {generated} from the data files listed below. Every number is computed from those files; nothing is estimated or filled in.</p>
<h2>1. Research question</h2><p>{html.escape(inv.question)}</p>
<h2>2. Economic motivation</h2><p>{html.escape(inv.motivation)}</p>
<h2>3. Data sources</h2><ul>{''.join(_source(i) for i in inv.data)}</ul>
<h2>4. Methodology</h2><p>{html.escape(inv.method)}</p>
<h2>5. Results</h2>{charts}{tables}
<div class="box"><b>Observed facts</b>{_list(inv.facts)}<b>Statistical results</b>{_list(inv.statistics)}</div>
<h2>6. Interpretation</h2>{_list(inv.interpretation)}
<p class="muted">Descriptive and correlational only — no causal claim is made.</p>
<h2>7. Limitations</h2>{_list(inv.limitations)}
<h2>8. Further research questions</h2>{_list(inv.further_questions)}
<h3>Hypotheses requiring further testing</h3>{_list(inv.hypotheses)}
<h2>Reproducibility</h2><pre>{html.escape(json.dumps(inv.settings, indent=2, default=str))}</pre>
<p class="muted">Investigation id: {html.escape(inv.id)} · code: analysis/research_library.py</p>
</body></html>"""


def tables_csv(inv) -> bytes:
    """All result tables in one CSV, each block labelled with its table name."""
    parts = []
    for name, df in inv.tables.items():
        parts.append(f"# table: {name}\n" + df.to_csv(index=False))
    return ("\n".join(parts)).encode("utf-8")
