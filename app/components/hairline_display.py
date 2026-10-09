"""Embeds the small, display-only Hairline figures (see
app/assets/hairline_figures/) used as conceptual, decorative aids inside
existing pages -- Slow on the Banking Lab, Elevator on Methodology, Vault
on Limitations. Unlike the terrain hero, these don't navigate anywhere and
don't need a bidirectional component: components.v1.html() is enough.

Bundles are built offline with esbuild (see
app/assets/hairline_figures/build.mjs) because Streamlit Cloud runs
Python only -- this module just reads the already-built files.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import streamlit.components.v1 as components

_DIST_DIR = Path(__file__).resolve().parents[1] / "assets" / "hairline_figures" / "dist"


@lru_cache(maxsize=8)
def _bundle(name: str) -> tuple[str, str] | None:
    js_path = _DIST_DIR / name / "bundle.js"
    css_path = _DIST_DIR / name / "style.css"
    if not js_path.exists() or not css_path.exists():
        return None
    return css_path.read_text(encoding="utf-8"), js_path.read_text(encoding="utf-8")


def render(name: str, height: int = 360, **params: str) -> None:
    """Render a built Hairline figure (name = "slow" | "elevator" | "vault").

    Extra keyword args become URL query params the figure's own JS reads
    (e.g. render("slow", repoRate="6.50")) -- silently does nothing if the
    bundle hasn't been built, keeping pages usable without the Node toolchain.
    """
    bundle = _bundle(name)
    if bundle is None:
        return
    css, js = bundle
    query = f"?{urlencode(params)}" if params else ""
    html = f"""
<!doctype html>
<html>
<head><meta charset="utf-8" /><style>{css}</style></head>
<body style="margin:0;">
  <div id="figure-root"></div>
  <script>
    // The bundle reads window.location.search for params (see slow.js);
    // a components.html() iframe's URL is about:srcdoc, so params are
    // passed as a hash instead and the bundle checks both.
    window.__hairlineParams = "{query.lstrip('?')}";
  </script>
  <script>{js}</script>
</body>
</html>
"""
    components.html(html, height=height, scrolling=False)
