// "Slow" on the Banking & Monetary Policy Lab: crates on a belt, hovering
// dilates the clock. Used here purely as a metaphor for "tighter policy
// tends to slow activity" -- it does NOT display Hairline's own internal
// "rate 0.84x" readout as if it were the real RBI repo rate (that's just
// the figure's own animation-speed caption, not economic data). The real
// repo rate is passed in via a query param and shown as its own labelled
// number alongside the figure, and used only to set the figure's initial
// intensity (higher real rate -> the belt starts a little more muted).
import { slow } from "@lucasmarkes/hairline";

function params() {
  // components.html() iframes load as about:srcdoc, so a real query string
  // isn't available on window.location -- the Python wrapper sets
  // window.__hairlineParams to the encoded param string instead.
  const raw = typeof window.__hairlineParams === "string" ? window.__hairlineParams : window.location.search.replace(/^\?/, "");
  const p = new URLSearchParams(raw);
  return { repoRate: parseFloat(p.get("repoRate") || "6.5"), asOf: p.get("asOf") || "" };
}

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const { repoRate, asOf } = params();
  const idle = `RBI policy repo rate: ${repoRate.toFixed(2)}%${asOf ? " (" + asOf + ")" : ""} — hover the belt.`;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = idle;
  root.appendChild(caption);

  // Map the real repo rate (roughly 4-9% in recent RBI history) onto a
  // starting intensity -- higher rate, a touch more muted at rest. This is
  // the only place the real number touches the figure's own parameters;
  // Hairline's internal clock-rate caption is translated below, not shown.
  const baseIntensity = reduceMotion ? 0.15 : Math.max(0.3, 0.6 - (repoRate - 4) * 0.03);

  slow(wrap, {
    intensity: baseIntensity,
    theme: "dark",
    label: "A belt of crates through a gate; hovering slows it, a metaphor for policy tightening slowing activity.",
    onRead: (text) => {
      if (!text || text.startsWith("rate 1.00")) {
        caption.textContent = idle;
      } else {
        caption.textContent = "Tighter conditions, slower activity — a metaphor, not a forecast.";
      }
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
