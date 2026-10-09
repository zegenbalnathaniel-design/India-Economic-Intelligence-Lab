// "Riffle" on the Wealth Inequality Lab: a tray of eight cards, the one
// under the pointer stands up. Used here as a STRUCTURAL device naming the
// eight standard population percentile bands used in distributional
// economics (the same bracket convention the World Inequality Database and
// similar sources use) -- NOT as a chart of India-specific wealth shares,
// since no real Indian percentile-level wealth/income dataset exists in
// this project yet. No number is attached to any card; only Hairline's own
// generic "card N" animation and a real definitional label. Arrow keys
// walk the cards (Hairline's own built-in a11y for this figure).
import { riffle } from "@lucasmarkes/hairline";

// Card 1 (bottom of the tray) .. Card 8 (top), matching Hairline's own
// left-to-right "N - a" numbering (see riffle.ts's caption()).
const BANDS = [
  { range: "P0–P10", name: "Bottom 10%" },
  { range: "P10–P25", name: "Lower-middle" },
  { range: "P25–P40", name: "Lower-middle" },
  { range: "P40–P60", name: "Middle" },
  { range: "P60–P75", name: "Upper-middle" },
  { range: "P75–P90", name: "Upper-middle" },
  { range: "P90–P99", name: "Top 10%" },
  { range: "P99–P100", name: "Top 1%" },
];

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = "Hover a card, or tab in and use the arrow keys.";
  root.appendChild(caption);

  riffle(wrap, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "dark",
    label: "A tray of eight cards, one per population percentile band, from the bottom 10% to the top 1%.",
    onRead: (text) => {
      if (!text || text === "rest") {
        caption.textContent = "Hover a card, or tab in and use the arrow keys.";
        return;
      }
      const n = parseInt(text, 10);
      const band = BANDS[n - 1];
      caption.textContent = band ? `${band.range} — ${band.name}` : text;
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
