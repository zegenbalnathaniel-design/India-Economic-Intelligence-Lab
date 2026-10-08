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

// ---------------------------------------------------------------------
// Cell -> Lab mapping, so the terrain responds as the pointer crosses ANY
// of its 81 pillars, not just the four small labelled hotspots. Hairline's
// `terrain` reports which grid cell ("cell i·j") is under the pointer via
// `onRead`, but not that cell's screen position -- so this mirrors the
// figure's own isometric projection (camera az=45, k=0.5, S=1.58, the grid
// constants N/CELL/FOOT, and the same `fit()` centering terrain.ts does)
// to recover each cell's screen point, then matches it to the nearest of
// the four REGIONS above, which were positioned from the actual rendered
// figure (see the git history for how). Ported arithmetic, not a guess —
// see @lucasmarkes/hairline's src/figures/terrain.ts and src/core/iso.ts.
const CAM_AZ = (45 * Math.PI) / 180, CAM_K = 0.5, CAM_S = 1.58;
const CAM_ZF = Math.sqrt(1 - CAM_K * CAM_K);
const GRID_N = 9, GRID_CELL = 14, GRID_FOOT = 11, GRID_HMAX = 58, GRID_EXT = GRID_N * GRID_CELL, GRID_PAD = 5;

function projectIso(x, y, z, ox, oy) {
  const c = Math.cos(CAM_AZ), s = Math.sin(CAM_AZ);
  const X = x * c - y * s, Y = x * s + y * c;
  return [ox + CAM_S * X, oy + CAM_S * (Y * CAM_K - z * CAM_ZF)];
}

function fitCenterOffset(points, cx, cy) {
  let a = Infinity, b = -Infinity, c = Infinity, d = -Infinity;
  for (const [x, y, z] of points) {
    const [qx, qy] = projectIso(x, y, z, 0, 0);
    a = Math.min(a, qx); b = Math.max(b, qx); c = Math.min(c, qy); d = Math.max(d, qy);
  }
  return [cx - (a + b) / 2, cy - (c + d) / 2];
}

const [FIT_OX, FIT_OY] = fitCenterOffset(
  [[-6, -6, -GRID_PAD], [GRID_EXT + 6, GRID_EXT + 6, -GRID_PAD], [GRID_EXT + 6, -6, -GRID_PAD],
   [-6, GRID_EXT + 6, -GRID_PAD], [0, 0, GRID_HMAX * 0.75]],
  200, 166,
);

function cellScreenPos(i, j) {
  const x0 = i * GRID_CELL + (GRID_CELL - GRID_FOOT) / 2 + GRID_FOOT / 2;
  const y0 = j * GRID_CELL + (GRID_CELL - GRID_FOOT) / 2 + GRID_FOOT / 2;
  return projectIso(x0, y0, 0, FIT_OX, FIT_OY);
}

const REGION_SCREEN_POS = REGIONS.map((r) => [r.x * 400, r.y * 320]);

function nearestRegionIndex(sx, sy) {
  let best = 0, bestD = Infinity;
  REGION_SCREEN_POS.forEach(([rx, ry], idx) => {
    const d = (sx - rx) ** 2 + (sy - ry) ** 2;
    if (d < bestD) { bestD = d; best = idx; }
  });
  return best;
}

const CELL_RE = /^cell (\d+)·(\d+)$/;

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

  const REST_CAPTION = "Hover the terrain — each rise is part of the Lab.";
  const hotEls = [];

  const setActive = (idx) => {
    hotEls.forEach((el, i) => el.classList.toggle("is-active", i === idx));
    caption.textContent = idx === null ? REST_CAPTION : `${REGIONS[idx].name} — ${REGIONS[idx].descriptor}`;
  };

  const figure = terrain(stage, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "auto",
    label: "An isometric field representing this site's four Labs; hover to find each one.",
    // Fires on every pillar the pointer crosses, not just the four labelled
    // hotspots -- so the whole field answers, matched to the nearest Lab via
    // the projection math above. "rest" is Hairline's own idle caption.
    onRead: (text) => {
      if (text === "rest" || !text) { setActive(null); return; }
      const m = CELL_RE.exec(text);
      if (!m) return;
      const [sx, sy] = cellScreenPos(Number(m[1]), Number(m[2]));
      setActive(nearestRegionIndex(sx, sy));
    },
  });

  REGIONS.forEach((region, idx) => {
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
    hot.addEventListener("mouseenter", () => setActive(idx));
    hot.addEventListener("mouseleave", () => setActive(null));
    hot.addEventListener("focus", () => setActive(idx));
    hot.addEventListener("blur", () => setActive(null));
    overlay.appendChild(hot);
    hotEls.push(hot);
  });

  // Small decorative annotation chips -- generic economic category labels
  // (not data points, no numbers attached), echoing the brief's "technical
  // identity system" around the hero artwork. Placed in the field's margins
  // so they don't collide with the four region hotspots.
  const ANNOTATIONS = [
    { text: "CAPITAL", x: 0.06, y: 0.18 },
    { text: "GROWTH", x: 0.94, y: 0.18 },
    { text: "CREDIT", x: 0.06, y: 0.5 },
    { text: "PRODUCTIVITY", x: 0.94, y: 0.5 },
    { text: "DISTRIBUTION", x: 0.06, y: 0.84 },
    { text: "HOUSING", x: 0.94, y: 0.84 },
  ];
  ANNOTATIONS.forEach((a) => {
    const el = document.createElement("div");
    el.className = "th-annot";
    el.style.left = `${a.x * 100}%`;
    el.style.top = `${a.y * 100}%`;
    el.style.transform = `translate(${a.x > 0.5 ? "-100%" : "0"}, -50%)`;
    el.textContent = a.text;
    overlay.appendChild(el);
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
