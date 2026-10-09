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

# Figure (max 330px wide at 5:4 -> 264px tall) + the boxed caption (up to
# three lines at 15px) must fit inside the iframe, or the caption is clipped.
FRAME_HEIGHT = 400


@lru_cache(maxsize=8)
def _bundle(name: str) -> tuple[str, str] | None:
    js_path = _DIST_DIR / name / "bundle.js"
    css_path = _DIST_DIR / name / "style.css"
    if not js_path.exists() or not css_path.exists():
        return None
    return css_path.read_text(encoding="utf-8"), js_path.read_text(encoding="utf-8")


# The lab-page hero: a larger figure with heavier strokes, lit in the lab's
# accent colour. Figure up to 520px wide at 5:4 (416px) + a caption of up to
# three 17px lines must fit, so the frame is taller than FRAME_HEIGHT.
HERO_HEIGHT = 580


def _hero_css(accent: str) -> str:
    return f"""
.hf-wrap {{ max-width: 520px;
  --hairline-stroke: 1.7;
  --hairline-hi: {accent};
  --hairline-edge: #F5F0E6;
  --hairline-mid: #8B8D99;
  --hairline-lo: #3A3F52; }}
.hf-caption {{ max-width: 560px; font-size: 17px; font-weight: 700; padding: 12px 16px;
  white-space: pre-line; border-left: 4px solid {accent}; }}
"""


def render(name: str, height: int | None = None, *, hero: bool = False,
           accent: str = "#F3C542", **params: str) -> None:
    """Render a built Hairline figure (e.g. "slow", "riffle", "lockers").

    `hero=True` is the large, bold variant used at the top of each Lab page,
    lit in `accent`. Extra keyword args become URL query params the figure's
    own JS reads (e.g. render("slow", repoRate="6.50")) -- silently does
    nothing if the bundle hasn't been built, keeping pages usable without
    the Node toolchain.
    """
    bundle = _bundle(name)
    if bundle is None:
        return
    css, js = bundle
    if hero:
        css += _hero_css(accent)
    if height is None:
        height = HERO_HEIGHT if hero else FRAME_HEIGHT
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
