// "Elevator" on the Methodology page: the pointer's height picks a floor,
// the car travels there. Hairline's own floors are generic ("ground",
// "floor 1"..."floor 3"); translated here to this site's own methodology
// steps (Question -> Data -> Model & Simulation -> Interpretation -- the
// same flow already stated in prose on the homepage and this page, not a
// new claim).
import { elevator } from "@lucasmarkes/hairline";

const STEP_NAMES = {
  ground: "01 · QUESTION",
  "floor 1": "02 · DATA",
  "floor 2": "03 · MODEL & SIMULATION",
  "floor 3": "04 · INTERPRETATION",
};

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = "Move the pointer up and down the shaft to step through the process.";
  root.appendChild(caption);

  elevator(wrap, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "dark",
    label: "An elevator against four floors, each a step in this site's research process.",
    onRead: (text) => {
      caption.textContent = STEP_NAMES[text] || "Move the pointer up and down the shaft to step through the process.";
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
