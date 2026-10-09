// "Riffle" on the Wealth Inequality Lab: a tray of eight cards, the one
// under the pointer stands up. Each card is one population group (bottom
// card = Bottom 10%, top card = Top 0.1%) and its caption is built
// server-side by analysis/inequality.py from the World Inequality Lab
// files in data/raw/wil/ -- passed in as the `bands` param, never written
// here. Without the param the cards fall back to their percentile names
// only, with no numbers. Arrow keys walk the cards (Hairline's own a11y).
import { riffle } from "@lucasmarkes/hairline";

const FALLBACK = [
  "P0–P10 · Bottom 10%", "P10–P50 · Lower middle", "P0–P50 · Bottom 50%",
  "P50–P90 · Middle 40%", "P90–P99 · Upper middle", "P90–P100 · Top 10%",
  "P99–P100 · Top 1%", "P99.9–P100 · Top 0.1%",
];
const IDLE = "Hover a card, or tab in and use the arrow keys.";

function bands() {
  const raw = typeof window.__hairlineParams === "string" ? window.__hairlineParams : window.location.search.replace(/^\?/, "");
  try {
    const v = JSON.parse(new URLSearchParams(raw).get("bands") || "null");
    return Array.isArray(v) && v.length === 8 ? v.map(String) : FALLBACK;
  } catch {
    return FALLBACK;
  }
}

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const BANDS = bands();

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = IDLE;
  root.appendChild(caption);

  riffle(wrap, {
    intensity: reduceMotion ? 0.15 : 0.6,
    theme: "dark",
    label: "A tray of eight cards, one per population group, from the bottom 10% to the top 0.1%, each with its share of India's income and wealth.",
    onRead: (text) => {
      if (!text || text === "rest") {
        caption.textContent = IDLE;
        return;
      }
      const band = BANDS[parseInt(text, 10) - 1];
      caption.textContent = band || text;
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
