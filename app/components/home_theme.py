"""Homepage-only visual system: vibrant editorial identity for the Home
page hero, numbers strip, research index and process diagram.

Deliberately separate from app/components/theme.py, which stays in force
on every Lab/Research/Methodology/etc. page. Scope, per the brief this
was built from: redesign the HOME PAGE's visual identity; do not touch
the Labs' existing dark/gold theme, routes, data or methodology.

The base stays the site's existing near-black (already functionally
"Deep Ink") and parchment text -- this module only adds the vibrant
accent system and large-type hero/index layout on top of it, rather
than re-deriving a whole second base palette.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from app.components.theme import (
    INK, WARM_WHITE, COBALT, VERMILLION, GOLD, LEAF, TURQUOISE, LAB_ACCENTS, ESPRESSO, RULE,
)

# Per-lab colour direction (2-3 colours each, all from theme.py's fixed
# 7-colour set -- single source of truth, shared with the Lab pages'
# own per-page accent so a Lab's colour on the homepage matches the
# colour it opens into).
LAB_COLORS = {
    "wealth": {"primary": LAB_ACCENTS["wealth"], "secondary": GOLD},
    "banking": {"primary": LAB_ACCENTS["banking"], "secondary": TURQUOISE},
    "regional": {"primary": LAB_ACCENTS["regional"], "secondary": VERMILLION},
    "housing": {"primary": LAB_ACCENTS["housing"], "secondary": COBALT},
}


def inject_home_css() -> None:
    st.markdown(
        f"""
        <style>
        .ieil-micro {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
            color: #8C8779; display: flex; gap: 1.5rem; flex-wrap: wrap;
            margin-bottom: .6rem;
        }}
        .ieil-hero-title {{
            font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-weight: 800; letter-spacing: -0.02em; line-height: 0.95;
            font-size: clamp(3.2rem, 9vw, 7.2rem); color: #F5F0E6;
            margin: 0;
        }}
        .ieil-hero-title .accent {{ color: {VERMILLION}; }}
        .ieil-hero-sub {{
            max-width: 560px; font-size: 1.05rem; color: #B6AF9E; line-height: 1.5;
            margin-top: .6rem;
        }}
        .ieil-numbers {{
            display: flex; flex-wrap: wrap; gap: 3rem; margin: 1rem 0 .5rem;
        }}
        .ieil-number .n {{
            font-weight: 800; font-size: clamp(2.6rem, 6vw, 4.2rem); line-height: 1;
            letter-spacing: -0.02em;
        }}
        .ieil-number .l {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
            color: #8C8779; margin-top: .35rem;
        }}
        .ieil-index-num {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 13px; color: #8C8779;
        }}
        .ieil-index-headline {{
            font-weight: 800; font-size: 1.5rem;
            letter-spacing: -0.01em; line-height: 1.08; margin: .4rem 0 0;
        }}
        .ieil-index-meta {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
            color: #8C8779; margin-top: .4rem;
        }}
        .ieil-index-desc {{ color: #B6AF9E; font-size: .9rem; margin-top: .4rem; line-height: 1.4; }}

        /* Research Index as a draggable carousel, not a stacked list: the
           cards scroll/snap horizontally (trackpad, touch-swipe, or a
           click-drag via the JS below), rather than sitting fixed in a
           vertical stack. Targets the stMain/stHorizontalBlock Streamlit
           renders for a horizontal st.container(key=...). */
        div[class*="st-key-research_carousel"] {{
            overflow-x: auto !important; flex-wrap: nowrap !important;
            scroll-snap-type: x proximity; cursor: grab; padding-bottom: .6rem;
            scrollbar-width: thin;
        }}
        div[class*="st-key-research_carousel"]:active {{ cursor: grabbing; }}
        div[class*="st-key-research_carousel"] [data-testid="stLayoutWrapper"] {{
            scroll-snap-align: start; flex: 0 0 auto; min-width: 300px; max-width: 320px;
        }}
        div[class*="st-key-research_carousel"] [data-testid="stVerticalBlock"] {{
            background: {ESPRESSO}; border-radius: 6px; height: 100%;
        }}
        .ieil-flow {{ display: flex; align-items: center; gap: .9rem; flex-wrap: wrap; margin: 1rem 0; }}
        .ieil-flow-step {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
            padding: .55rem 1rem; border: 1px solid #3A3026; border-radius: 2px;
            color: #F5F0E6;
        }}
        .ieil-flow-arrow {{ color: #8C8779; font-size: 16px; }}
        .ieil-secondary-links {{
            display: flex; flex-wrap: wrap; gap: 1.4rem; margin-top: .4rem;
        }}

        /* Scroll-triggered reveal: sections start faded/offset and ease in
           once scrolled into view (see scroll_reveal_script() -- a real
           IntersectionObserver, not a CSS-only fake). Respects
           prefers-reduced-motion by skipping the offset/transition. */
        [class*="st-key-reveal_"] {{
            opacity: 0; transform: translateY(18px);
            transition: opacity 700ms cubic-bezier(.2,.7,.3,1), transform 700ms cubic-bezier(.2,.7,.3,1);
        }}
        [class*="st-key-reveal_"].ieil-visible {{ opacity: 1; transform: none; }}
        @media (prefers-reduced-motion: reduce) {{
            [class*="st-key-reveal_"] {{ opacity: 1; transform: none; transition: none; }}
        }}

        /* Scroll-drawn line chart: the path's own length becomes its dash
           array/offset (set inline per-path, since length is data-
           dependent), then eased to 0 on reveal -- same "line draws
           itself" idea as the ScrollGraph reference, built from this
           site's real sigma-convergence series, not a placeholder curve. */
        .ieil-graph-path {{ transition: stroke-dashoffset 1600ms cubic-bezier(.2,.7,.3,1); }}
        @media (prefers-reduced-motion: reduce) {{
            .ieil-graph-path {{ transition: none !important; stroke-dashoffset: 0 !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_micro(items: list[str]) -> None:
    html = '<div class="ieil-micro">' + "".join(f"<span>{i}</span>" for i in items) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def hero_title(lines: list[tuple[str, bool]]) -> None:
    """lines: list of (text, is_accent) rendered one per line."""
    inner = "".join(
        f'<div class="{"accent" if accent else ""}">{text}</div>' for text, accent in lines
    )
    st.markdown(f'<div class="ieil-hero-title">{inner}</div>', unsafe_allow_html=True)


def number_stat(value: str, label: str, color: str) -> None:
    st.markdown(
        f'<div class="ieil-number"><div class="n" style="color:{color}">{value}</div>'
        f'<div class="l">{label}</div></div>',
        unsafe_allow_html=True,
    )


def index_card(num: str, headline: str, meta: str, desc: str, color: str) -> None:
    """One Research Index card -- a carousel item (see inject_home_css's
    `research_carousel` CSS), not a static stacked row."""
    st.markdown(
        f"""
        <div class="ieil-index-num">{num}</div>
        <div class="ieil-index-headline" style="color:{color}">{headline}</div>
        <div class="ieil-index-meta">{meta}</div>
        <div class="ieil-index-desc">{desc}</div>
        """,
        unsafe_allow_html=True,
    )


def carousel_drag_script(key: str) -> None:
    """Wires real click-and-drag-to-scroll onto a `st.container(key=key,
    horizontal=True)` carousel (CSS alone gives scroll-snap + touch/trackpad
    swipe, but not mouse click-drag on desktop).

    st.markdown() inserts HTML via innerHTML, so a <script> tag there is
    inert (the browser doesn't execute scripts added that way) -- that's
    why this goes through components.v1.html() instead: its iframe loads
    an actual srcdoc document, where <script> runs normally, same as the
    terrain hero. allow-same-origin (present on that iframe's sandbox, as
    confirmed while building the terrain hero) lets it reach
    window.parent.document to wire the *parent* page's carousel element,
    since the carousel itself lives in the main app, not in this iframe.
    """
    html = f"""
<!doctype html><html><body><script>
(function() {{
  try {{
    var doc = window.parent.document;
    var sel = 'div[class*="st-key-{key}"]';
    var tries = 0;
    var iv = setInterval(function() {{
      var el = doc.querySelector(sel);
      tries++;
      if (el && !el.dataset.dragWired) {{
        el.dataset.dragWired = "1";
        var isDown = false, startX = 0, startScroll = 0;
        el.addEventListener('pointerdown', function(e) {{
          isDown = true; startX = e.pageX; startScroll = el.scrollLeft;
          el.setPointerCapture(e.pointerId);
        }});
        el.addEventListener('pointermove', function(e) {{
          if (!isDown) return;
          el.scrollLeft = startScroll - (e.pageX - startX);
        }});
        var stop = function() {{ isDown = false; }};
        el.addEventListener('pointerup', stop);
        el.addEventListener('pointercancel', stop);
      }}
      if (tries > 20 || (el && el.dataset.dragWired)) clearInterval(iv);
    }}, 150);
  }} catch (e) {{ /* cross-origin or missing element: no-op */ }}
}})();
</script></body></html>
"""
    components.html(html, height=0)


def scroll_reveal_script() -> None:
    """Real IntersectionObserver-driven reveal for every `st.container(key=
    "reveal_...")` section on the page, plus the stroke-draw-in for
    `.ieil-graph-path` elements (see sigma_convergence_svg()). Same
    cross-iframe technique as carousel_drag_script() -- a components.html()
    srcdoc document, which executes scripts normally, reaching into
    window.parent.document via allow-same-origin to observe the *actual*
    page elements (they don't live in this iframe)."""
    html = """
<!doctype html><html><body><script>
(function() {
  try {
    var doc = window.parent.document;
    var wired = false;
    var iv = setInterval(function() {
      var targets = doc.querySelectorAll('[class*="st-key-reveal_"]:not([data-reveal-wired])');
      var paths = doc.querySelectorAll('.ieil-graph-path:not([data-reveal-wired])');
      if (!targets.length && !paths.length) { if (wired) clearInterval(iv); return; }
      wired = true;
      var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(e) {
          if (e.isIntersecting) {
            e.target.classList.add('ieil-visible');
            if (e.target.classList.contains('ieil-graph-path')) {
              e.target.style.strokeDashoffset = '0';
            }
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      targets.forEach(function(t) { t.dataset.revealWired = '1'; io.observe(t); });
      paths.forEach(function(p) {
        p.dataset.revealWired = '1';
        var len = p.getTotalLength ? p.getTotalLength() : 400;
        p.style.strokeDasharray = len;
        p.style.strokeDashoffset = len;
        io.observe(p);
      });
    }, 200);
    setTimeout(function() { clearInterval(iv); }, 6000);
  } catch (e) { /* cross-origin or missing elements: no-op */ }
})();
</script></body></html>
"""
    components.html(html, height=0)


def sigma_convergence_svg(by_year, color: str) -> str:
    """A hand-built inline SVG line (not Plotly) for the real sigma-
    convergence CV-by-year series, so its path can be animated with a
    scroll-triggered stroke draw-in (.ieil-graph-path, see
    scroll_reveal_script()) -- the "line draws itself" idea from the
    ScrollGraph reference, built from this site's own real data, not a
    placeholder curve. `by_year` is the real DataFrame from
    analysis.regional.sigma_convergence(...).by_year (columns: year, cv_pct)."""
    years = list(by_year["financial_year"])
    values = list(by_year["cv_pct"])
    w, h, pad = 640, 160, 10
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = pad + (w - 2 * pad) * (i / max(1, n - 1))
        y = h - pad - (h - 2 * pad) * ((v - lo) / span)
        pts.append((x, y))
    path_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" />' for x, y in pts[-1:])
    first_year, last_year = years[0], years[-1]
    return f"""
<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;" role="img"
     aria-label="Cross-state coefficient of variation of per-capita NSDP, {first_year} to {last_year}, real RBI Handbook data.">
  <path class="ieil-graph-path" d="{path_d}" fill="none" stroke="{color}" stroke-width="2.5"
        stroke-linecap="round" stroke-linejoin="round" />
  {dots}
</svg>
"""


def flow(steps: list[str]) -> None:
    parts = []
    for i, s in enumerate(steps):
        if i:
            parts.append('<span class="ieil-flow-arrow">→</span>')
        parts.append(f'<span class="ieil-flow-step">{s}</span>')
    st.markdown(f'<div class="ieil-flow">{"".join(parts)}</div>', unsafe_allow_html=True)
