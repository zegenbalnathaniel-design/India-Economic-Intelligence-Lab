// Turntable, homepage: "Four ways of looking at this site." Drag the
// platter; Hairline's own quarter-turn detents settle it onto one of four
// faces, each mapped to a real section of this app (never a fabricated
// destination). A real Streamlit custom-component return value (not a
// direct iframe navigation, which this sandbox's own earlier testing
// showed the browser silently refuses) sends the chosen page back to
// Python on click, same protocol as the terrain hero.
import { turntable } from "@lucasmarkes/hairline";

function sendToStreamlit(type, extra) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...extra }, "*");
}
const setComponentReady = () => sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
const setFrameHeight = (height) => sendToStreamlit("streamlit:setFrameHeight", { height });
const setComponentValue = (value) => sendToStreamlit("streamlit:setComponentValue", { value, dataType: "json" });

const FACES = [
  { name: "MARKETS", desc: "Interest rates, bank performance, the iBFPI", href: "Banking_Monetary_Policy_Lab", az: [315, 360, 0, 45] },
  { name: "PEOPLE", desc: "Income, ownership, wealth accumulation", href: "Wealth_Inequality_Lab", az: [45, 135] },
  { name: "INSTITUTIONS", desc: "States, convergence, regional divergence", href: "State_Economic_Divergence_Lab", az: [135, 225] },
  { name: "DATA", desc: "Every source, every assumption, in one place", href: "Data", az: [225, 315] },
];

function faceForAz(az) {
  const a = ((az % 360) + 360) % 360;
  for (const f of FACES) {
    const [a0, a1, a2, a3] = f.az;
    if (a3 !== undefined) {
      if (a >= a0 && a < a1) return f;
      if (a >= a2 && a < a3) return f;
    } else if (a >= a0 && a < a1) {
      return f;
    }
  }
  return FACES[0];
}

function init() {
  const root = document.getElementById("turntable-root");
  if (!root) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const wrap = document.createElement("div");
  wrap.className = "tt-wrap";
  const stage = document.createElement("div");
  stage.className = "tt-stage";
  wrap.appendChild(stage);
  const caption = document.createElement("div");
  caption.className = "tt-caption";
  caption.textContent = "Drag to turn — four ways into this site.";
  wrap.appendChild(caption);
  const faceLabel = document.createElement("div");
  faceLabel.className = "tt-face-label";
  wrap.appendChild(faceLabel);
  const goBtn = document.createElement("button");
  goBtn.className = "tt-go";
  goBtn.type = "button";
  root.appendChild(wrap);
  wrap.appendChild(goBtn);

  let current = FACES[0];
  const render = (face) => {
    current = face;
    faceLabel.textContent = face.name;
    caption.textContent = face.desc;
    goBtn.textContent = `Open ${face.name} →`;
  };
  render(FACES[0]);

  turntable(stage, {
    intensity: reduceMotion ? 0.2 : 0.55,
    theme: "dark",
    label: "A turntable with four faces: Markets, People, Institutions and Data, each a way into this site.",
    onRead: (text) => {
      const m = /az (\d+)°/.exec(text || "");
      if (!m) return;
      render(faceForAz(Number(m[1])));
    },
  });

  goBtn.addEventListener("click", () => setComponentValue(current.href));

  setComponentReady();
  setFrameHeight(root.getBoundingClientRect().height || 420);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
