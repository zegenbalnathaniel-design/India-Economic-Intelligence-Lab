// "Branches" on the State Economic Divergence Lab: a commit graph, main
// line plus a feature branch that forks and merges back. Used here with
// REAL labels -- the 8 main-line commits are the 8 states with the
// highest latest per-capita NSDP (the "main" growth path), and the 3
// feature-branch commits are the 3 states with the highest average
// annual growth rate in the same real RBI Handbook series (states
// catching up fastest) -- both lists computed server-side from real data
// and passed in as query params, never hardcoded or invented here.
// Hairline's own commit heights/physics stay generic, same as Terrain's
// pillars: only the LABELS are real, the animation is a metaphor for
// "states don't all follow one path."
import { branches } from "@lucasmarkes/hairline";

function params() {
  const raw = typeof window.__hairlineParams === "string" ? window.__hairlineParams : window.location.search.replace(/^\?/, "");
  const p = new URLSearchParams(raw);
  const parseList = (key, fallback) => {
    try {
      const v = JSON.parse(p.get(key) || "null");
      return Array.isArray(v) && v.length ? v : fallback;
    } catch {
      return fallback;
    }
  };
  return {
    main: parseList("main", ["State 1", "State 2", "State 3", "State 4", "State 5", "State 6", "State 7", "State 8"]),
    feature: parseList("feature", ["State A", "State B", "State C"]),
  };
}

function init() {
  const root = document.getElementById("figure-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const { main, feature } = params();

  const wrap = document.createElement("div");
  wrap.className = "hf-wrap";
  root.appendChild(wrap);
  const caption = document.createElement("div");
  caption.className = "hf-caption";
  caption.textContent = "Hover the graph — the branch is real states, ranked by real data.";
  root.appendChild(caption);

  branches(wrap, {
    intensity: reduceMotion ? 0.15 : 0.55,
    theme: "dark",
    label: "A commit graph: the main line is the highest-income states, the branch is the fastest-growing states.",
    onRead: (text) => {
      if (!text || text === "rest") {
        caption.textContent = "Main line: highest per-capita NSDP. Branch: fastest-growing states.";
        return;
      }
      const m = /^(main|feature) · (\d+)$/.exec(text);
      if (!m) { caption.textContent = text; return; }
      const list = m[1] === "main" ? main : feature;
      const name = list[Number(m[2]) - 1];
      caption.textContent = name
        ? `${name} — ${m[1] === "main" ? "among the highest per-capita NSDP" : "among the fastest-growing"}`
        : text;
    },
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
