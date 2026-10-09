// "Lockers" on the Housing Intelligence Lab: a bank of twelve lockers; the
// one under the pointer opens. Each locker is one of the twelve RESIDEX
// cities with the highest price-to-income ratio, computed server-side by
// analysis/housing.py and passed in as the `cities` param (one caption
// per locker) -- never written here. Without the param the lockers show
// no city or number.
import { lockers } from "@lucasmarkes/hairline";

const IDLE = "Hover a locker to open one city.";

function cities() {
  const raw = typeof window.__hairlineParams === "string" ? window.__hairlineParams : window.location.search.replace(/^\?/, "");
  try {
    const v = JSON.parse(new URLSearchParams(raw).get("cities") || "null");
    return Array.isArray(v) ? v.map(String) : [];
  } catch {
    return [];
  }
}

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const CITIES = cities();

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = IDLE;
  root.appendChild(caption);

  lockers(wrap, {
    intensity: reduceMotion ? 0.15 : 0.6,
    theme: "dark",
    label: "A bank of twelve lockers, one per city with the highest price-to-income ratio.",
    onRead: (text) => {
      const m = /(\d+)/.exec(text || "");
      if (!m || text === "rest") {
        caption.textContent = IDLE;
        return;
      }
      caption.textContent = CITIES[parseInt(m[1], 10) - 1] || "No city for this locker.";
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
