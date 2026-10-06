"""Builds the self-contained Three.js scene for the 3D asset-correlation
network view. Node positions come from `portfolio_lab.network3d`'s
classical-MDS layout (a real dimensionality-reduction technique, not an
arbitrary decorative placement); this module only handles rendering.
"""
from __future__ import annotations

import json

import pandas as pd

EXCHANGE_COLORS = {
    "NASDAQ": "#4f8ef7", "NYSE": "#4f8ef7",
    "NSE": "#f7a24f", "BSE": "#f7c34f",
    "LSE": "#7fd37f", "JPX": "#e86fd3",
    "SSE": "#f75f5f", "HKEX": "#5fd7d7",
}


def build_network_html(
    nodes: pd.DataFrame,  # columns: ticker, x, y, z, weight, exchange
    edges: pd.DataFrame,  # columns: source, target, correlation
    height_px: int = 560,
) -> str:
    scale = 60.0
    node_payload = [
        {
            "ticker": row.ticker,
            "x": float(row.x) * scale,
            "y": float(row.y) * scale,
            "z": float(row.z) * scale,
            "size": 2.0 + 14.0 * float(row.weight),
            "color": EXCHANGE_COLORS.get(row.exchange, "#aaaaaa"),
        }
        for row in nodes.itertuples()
    ]
    index = {row.ticker: i for i, row in enumerate(nodes.itertuples())}
    edge_payload = [
        {
            "a": index[row.source], "b": index[row.target],
            "corr": float(row.correlation),
        }
        for row in edges.itertuples() if row.source in index and row.target in index
    ]

    data_json = json.dumps({"nodes": node_payload, "edges": edge_payload})

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body {{ margin:0; padding:0; overflow:hidden; background:#0b0f1a; }}
  #label {{
    position:absolute; top:8px; left:12px; color:#cbd5e1; font-family:monospace;
    font-size:12px; pointer-events:none;
  }}
</style>
</head>
<body>
<div id="label">drag to rotate · scroll to zoom</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/128/three.min.js"></script>
<script>
const DATA = {data_json};

const width = window.innerWidth, height = {height_px};
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0f1a);

const camera = new THREE.PerspectiveCamera(55, width/height, 0.1, 5000);
camera.position.set(0, 0, 260);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(width, height);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const point = new THREE.PointLight(0xffffff, 1.1);
point.position.set(150, 200, 250);
scene.add(point);

const group = new THREE.Group();
scene.add(group);

function makeLabelSprite(text) {{
  const canvas = document.createElement('canvas');
  canvas.width = 128; canvas.height = 48;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(0,0,0,0)';
  ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.font = '20px monospace';
  ctx.fillStyle = '#e2e8f0';
  ctx.textAlign = 'center';
  ctx.fillText(text, canvas.width/2, canvas.height/2 + 7);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({{ map: tex, depthWrite: false }});
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(28, 10, 1);
  return sprite;
}}

const nodeMeshes = [];
DATA.nodes.forEach(n => {{
  const geo = new THREE.SphereGeometry(n.size, 24, 24);
  const mat = new THREE.MeshStandardMaterial({{ color: n.color, roughness: 0.4, metalness: 0.15 }});
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(n.x, n.y, n.z);
  group.add(mesh);
  nodeMeshes.push(mesh);

  const label = makeLabelSprite(n.ticker);
  label.position.set(n.x, n.y + n.size + 8, n.z);
  group.add(label);
}});

DATA.edges.forEach(e => {{
  const a = DATA.nodes[e.a], b = DATA.nodes[e.b];
  const positive = e.corr >= 0;
  const color = positive ? 0x4ade80 : 0xf87171;
  const opacity = Math.min(1, Math.abs(e.corr));
  const points = [new THREE.Vector3(a.x, a.y, a.z), new THREE.Vector3(b.x, b.y, b.z)];
  const geo = new THREE.BufferGeometry().setFromPoints(points);
  const mat = new THREE.LineBasicMaterial({{ color, transparent: true, opacity: 0.25 + 0.6 * opacity }});
  group.add(new THREE.Line(geo, mat));
}});

// Manual drag-to-rotate (no external OrbitControls dependency needed).
let isDragging = false, prevX = 0, prevY = 0;
renderer.domElement.addEventListener('pointerdown', e => {{ isDragging = true; prevX = e.clientX; prevY = e.clientY; }});
window.addEventListener('pointerup', () => {{ isDragging = false; }});
window.addEventListener('pointermove', e => {{
  if (!isDragging) return;
  const dx = e.clientX - prevX, dy = e.clientY - prevY;
  group.rotation.y += dx * 0.005;
  group.rotation.x += dy * 0.005;
  prevX = e.clientX; prevY = e.clientY;
}});
renderer.domElement.addEventListener('wheel', e => {{
  camera.position.z = Math.max(80, Math.min(600, camera.position.z + e.deltaY * 0.1));
}});

let autoRotate = true;
renderer.domElement.addEventListener('pointerdown', () => {{ autoRotate = false; }});

function animate() {{
  requestAnimationFrame(animate);
  if (autoRotate) group.rotation.y += 0.0025;
  renderer.render(scene, camera);
}}
animate();
</script>
</body>
</html>
"""
