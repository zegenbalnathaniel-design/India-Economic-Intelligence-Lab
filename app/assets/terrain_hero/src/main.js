// Economic Terrain hero — adapts Hairline's `terrain` figure (81 isometric
// pillars that rise around the pointer) into a labelled map of this site's
// actual labs. The pillar physics/pointer-response are Hairline's own,
// unmodified; what's added here is a transparent hotspot overlay: four
// regions, each mapped to a real page in this app (never a fabricated
// destination), with a hover label/descriptor and click-to-navigate.
//
// Regions deliberately use this app's ACTUAL four labs, not a generic list —
// adapting the pattern to what exists here rather than inventing links to
// pages this project doesn't have.
//
// This is a bidirectional Streamlit custom component (declare_component),
// not a plain components.v1.html() iframe: that sandbox blocks a frame from
// navigating the top-level window directly (confirmed while building this —
// `window.top.location = ...` is silently refused), which is also just the
// correct contract for a component. A click sends the chosen page back to
// Python over Streamlit's own postMessage protocol, and Python decides what
// to do with it (st.switch_page) — the frontend never drives navigation
// itself. The protocol below is hand-rolled (three message types) rather
// than pulling in the full streamlit-component-lib/React package, which
// this static, non-React component doesn't need.
import { terrain } from "@lucasmarkes/hairline";

function sendToStreamlit(type, extra) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...extra }, "*");
}
const setComponentReady = () => sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
const setFrameHeight = (height) => sendToStreamlit("streamlit:setFrameHeight", { height });
const setComponentValue = (value) => sendToStreamlit("streamlit:setComponentValue", { value, dataType: "json" });

// Positions are fractions (0..1, 0..1) of .th-figure -- which is sized to
// exactly match the terrain SVG's 400x320 viewBox (see style.css), so these
// line up with the drawn pillar field regardless of how wide the hero is.
// The field's own bounding box (measured from the rendered SVG, at rest)
// is roughly x:[0.13,0.87] y:[0.36,0.84] of the viewBox; the four spots
// below sit in that field's four quadrants, each over real pillars.
const REGIONS = [
  {
    key: "wealth",
    name: "WEALTH & INEQUALITY",
    descriptor: "Composition effect, asset allocation, r − g",
    href: "Wealth_Inequality_Lab",
    x: 0.33, y: 0.71,
  },
  {
    key: "banking",
    name: "BANKING & MONETARY POLICY",
    descriptor: "iBFPI vs. the RBI repo rate, by regime",
    href: "Banking_Monetary_Policy_Lab",
    x: 0.67, y: 0.49,
  },
  {
    key: "regional",
    name: "REGIONAL DEVELOPMENT",
    descriptor: "Are states converging or diverging?",
    href: "State_Economic_Divergence_Lab",
    x: 0.67, y: 0.71,
  },
  {
    key: "housing",
    name: "HOUSING",
    descriptor: "Real city prices vs. a state-income proxy",
    href: "Housing_Intelligence_Lab",
    x: 0.33, y: 0.49,
  },
];

function mountTerrainHero(root) {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "th-wrap";
  // th-figure matches the terrain figure's own 5:4 viewBox ratio and is
  // centered by th-wrap's flexbox -- the hotspot overlay lives inside it
  // (not th-wrap) so percentages land on the figure, however wide th-wrap is.
  const figureBox = document.createElement("div");
  figureBox.className = "th-figure";
  wrap.appendChild(figureBox);
  const stage = document.createElement("div");
  stage.className = "th-stage";
  figureBox.appendChild(stage);
  const overlay = document.createElement("div");
  overlay.className = "th-overlay";
  figureBox.appendChild(overlay);
  const caption = document.createElement("div");
  caption.className = "th-caption";
  caption.textContent = "Hover the terrain — each rise is part of the Lab.";
  wrap.appendChild(caption);
  root.appendChild(wrap);

  const figure = terrain(stage, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "auto",
    label: "An isometric field representing this site's four Labs; hover to find each one.",
  });

  REGIONS.forEach((region) => {
    const hot = document.createElement("div");
    hot.className = "th-hot";
    hot.style.left = `${region.x * 100}%`;
    hot.style.top = `${region.y * 100}%`;
    hot.setAttribute("role", "link");
    hot.setAttribute("tabindex", "0");
    hot.setAttribute("aria-label", `${region.name} — ${region.descriptor}`);

    const label = document.createElement("div");
    label.className = "th-label";
    label.innerHTML = `<span class="th-label-name">${region.name}</span><span class="th-label-desc">${region.descriptor}</span>`;
    hot.appendChild(label);

    const activate = () => setComponentValue(region.href);
    hot.addEventListener("click", activate);
    hot.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activate(); }
    });
    hot.addEventListener("mouseenter", () => { caption.textContent = `${region.name} — ${region.descriptor}`; });
    hot.addEventListener("mouseleave", () => { caption.textContent = "Hover the terrain — each rise is part of the Lab."; });
    overlay.appendChild(hot);
  });

  return figure;
}

function init() {
  const root = document.getElementById("terrain-hero-root");
  if (!root) return;
  mountTerrainHero(root);
  setComponentReady();
  // Fixed height: the hero's own aspect-ratio (set in CSS) determines its
  // visual size; Streamlit just needs the iframe tall enough to show it.
  setFrameHeight(root.getBoundingClientRect().height || 420);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
