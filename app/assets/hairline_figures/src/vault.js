// "Vault" on the Limitations page: a dial that, turned to the combination,
// draws its bolts back. Used as an evocative opener for that page, not as
// a literal mapping of dial positions to limitation categories (Hairline's
// vault has one open/closed state, not six) -- the six real categories
// (Data, Measurement, Causality, Assumptions, External Validity, Time)
// are written out as real page content below the figure, same as the
// terrain hero is navigation chrome rather than a data visualisation.
import { vault } from "@lucasmarkes/hairline";

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = "Turn the dial.";
  root.appendChild(caption);

  vault(wrap, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "dark",
    label: "A vault door with a combination dial; turning it to the combination opens the bolts.",
    onRead: (text) => {
      if (!text || text === "rest") {
        caption.textContent = "Turn the dial.";
      } else if (text.includes("open")) {
        caption.textContent = "A model is not reality. It is a way of asking questions about reality.";
      } else {
        caption.textContent = "Keep turning…";
      }
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
