import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Line, OrbitControls } from '@react-three/drei';
import { geoEquirectangular, geoPath } from 'd3-geo';
import { useInView } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { feature } from 'topojson-client';
import type { GeometryCollection, Topology } from 'topojson-specification';
import landTopo from 'world-atlas/land-110m.json';
import {
  BILATERAL_NOTE,
  EXTERNAL_FLOWS,
  EXTERNAL_SUMMARY,
  INDIA_COORD,
  type ExternalFlow,
} from '../../data/macro/external';
import { longDate, number } from '../../lib/format';
import { useReducedMotionPref } from '../../lib/motion';
import { Notice, StatusBadge } from '../ui';

const R = 2;
const GOLD = new THREE.Color('#f3c542');
const INFLOW = '#6fae4f';
const OUTFLOW = '#f0663f';
const MISSING = '#6b6f80';

const toVec = (lat: number, lon: number, radius = R) => {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
};

/** Great-circle angle (radians) between two lat/lon points. */
function angularDistance(lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * r) / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 2 * Math.asin(Math.min(1, Math.sqrt(a)));
}

/**
 * Land as a dot matrix. The Natural Earth land polygons are rasterised once
 * onto an equirectangular canvas and every point of a Fibonacci sphere is
 * kept if its pixel is land — fast, and it draws coastlines without drawing
 * a single political boundary. Dots warm towards gold with proximity to
 * India: a glow, deliberately not a border.
 */
function useLandDots(count = 16000) {
  return useMemo(() => {
    const W = 1024;
    const H = 512;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    const topo = landTopo as unknown as Topology<{ land: GeometryCollection }>;
    const land = feature(topo, topo.objects.land);
    const proj = geoEquirectangular().fitSize([W, H], { type: 'Sphere' });
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    geoPath(proj, ctx)(land);
    ctx.fill();
    const img = ctx.getImageData(0, 0, W, H).data;

    const pos: number[] = [];
    const col: number[] = [];
    const base = new THREE.Color('#7a84a6');
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const lat = (Math.asin(y) * 180) / Math.PI;
      const lon = ((((i * golden * 180) / Math.PI) % 360) + 360) % 360 - 180;
      const [px, py] = proj([lon, lat]) as [number, number];
      const ix = Math.min(W - 1, Math.max(0, Math.round(px)));
      const iy = Math.min(H - 1, Math.max(0, Math.round(py)));
      if (img[(iy * W + ix) * 4] < 128) continue;
      const v = toVec(lat, lon, R * 1.002);
      pos.push(v.x, v.y, v.z);
      const d = angularDistance(lat, lon, INDIA_COORD.lat, INDIA_COORD.lon);
      const t = Math.max(0, 1 - d / 0.32) ** 1.2;
      const c = base.clone().lerp(GOLD, t);
      col.push(c.r, c.g, c.b);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return g;
  }, [count]);
}

function Earth() {
  const dots = useLandDots();
  const ocean = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { uBase: { value: new THREE.Color('#0d1019') }, uRim: { value: new THREE.Color('#3155d9') } },
        vertexShader: `varying vec3 vN; varying vec3 vV;
          void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }`,
        fragmentShader: `uniform vec3 uBase; uniform vec3 uRim; varying vec3 vN; varying vec3 vV;
          void main(){ float f = pow(1.0 - max(dot(vN, vV), 0.0), 3.0); gl_FragColor = vec4(mix(uBase, uRim, f*0.35), 1.0); }`,
      }),
    [],
  );
  const atmosphere = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color('#3f7fe0') } },
        vertexShader: `varying vec3 vN; varying vec3 vV;
          void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }`,
        fragmentShader: `uniform vec3 uColor; varying vec3 vN; varying vec3 vV;
          void main(){ float i = pow(max(0.0, 0.66 - dot(vN, vec3(0.0, 0.0, 1.0))), 2.2); gl_FragColor = vec4(uColor, 1.0) * i * 1.25; }`,
        transparent: true,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
        depthWrite: false,
      }),
    [],
  );
  const graticule = useMemo(() => {
    const lines: THREE.Vector3[][] = [];
    for (let lat = -60; lat <= 60; lat += 30) lines.push(Array.from({ length: 121 }, (_, i) => toVec(lat, -180 + i * 3, R * 1.001)));
    for (let lon = -180; lon < 180; lon += 30) lines.push(Array.from({ length: 61 }, (_, i) => toVec(-90 + i * 3, lon, R * 1.001)));
    return lines;
  }, []);

  return (
    <group>
      <mesh material={ocean}>
        <sphereGeometry args={[R, 96, 64]} />
      </mesh>
      {graticule.map((pts, i) => (
        <Line key={i} points={pts} color="#f5f0e6" transparent opacity={0.05} lineWidth={0.6} />
      ))}
      <points geometry={dots}>
        <pointsMaterial size={0.032} vertexColors sizeAttenuation transparent opacity={0.9} depthWrite={false} />
      </points>
      <mesh material={atmosphere} scale={1.13}>
        <sphereGeometry args={[R, 64, 48]} />
      </mesh>
    </group>
  );
}

function Stars() {
  const geo = useMemo(() => {
    const p: number[] = [];
    for (let i = 0; i < 1400; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(18 + Math.random() * 18);
      p.push(v.x, v.y, v.z);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
    return g;
  }, []);
  return (
    <points geometry={geo}>
      <pointsMaterial size={0.05} color="#e6e0d3" transparent opacity={0.5} sizeAttenuation />
    </points>
  );
}

const MAX_FLOW = Math.max(...EXTERNAL_FLOWS.map((f) => f.value ?? 0));

function Arc({ flow, active, dimmed, onHover }: { flow: ExternalFlow; active: boolean; dimmed: boolean; onHover: (id: string | null) => void }) {
  const reduced = useReducedMotionPref();
  const pulses = useRef<(THREE.Mesh | null)[]>([]);
  const missing = flow.value === null;
  const colour = missing ? MISSING : flow.direction === 'inflow' ? INFLOW : OUTFLOW;

  const { curve, points, width } = useMemo(() => {
    const start = toVec(INDIA_COORD.lat, INDIA_COORD.lon);
    const end = toVec(flow.lat, flow.lon);
    const mid = start.clone().add(end).multiplyScalar(0.5);
    mid.normalize().multiplyScalar(R * (1 + start.distanceTo(end) * 0.32));
    const c = new THREE.QuadraticBezierCurve3(start, mid, end);
    return { curve: c, points: c.getPoints(64), width: missing ? 1 : 1.4 + 4.2 * ((flow.value ?? 0) / MAX_FLOW) };
  }, [flow, missing]);

  const gradient = useMemo(() => {
    const a = new THREE.Color('#f3c542');
    const b = new THREE.Color(colour);
    return points.map((_, i) => {
      const t = i / (points.length - 1);
      const c = flow.direction === 'inflow' ? b.clone().lerp(a, t) : a.clone().lerp(b, t);
      return [c.r, c.g, c.b] as [number, number, number];
    });
  }, [points, colour, flow.direction]);

  useFrame(({ clock }) => {
    if (missing || reduced) return;
    pulses.current.forEach((m, k) => {
      if (!m) return;
      const t = (clock.elapsedTime * 0.18 + k / 3 + (flow.id.length % 7) * 0.05) % 1;
      m.position.copy(curve.getPoint(flow.direction === 'inflow' ? 1 - t : t));
      const s = 0.6 + Math.sin(t * Math.PI) * 0.9;
      m.scale.setScalar(s);
    });
  });

  const opacity = missing ? 0.25 : active ? 1 : dimmed ? 0.18 : 0.75;
  return (
    <group
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(flow.id);
      }}
      onPointerOut={() => onHover(null)}
    >
      <Line points={points} vertexColors={gradient} lineWidth={active ? width + 1.5 : width} transparent opacity={opacity} dashed={missing} dashSize={0.06} gapSize={0.05} />
      {/* a fat invisible hit-path so thin arcs are easy to hover */}
      <mesh visible={false}>
        <tubeGeometry args={[curve, 32, 0.06, 6, false]} />
      </mesh>
      {!missing &&
        [0, 1, 2].map((k) => (
          <mesh key={k} ref={(m) => (pulses.current[k] = m)}>
            <sphereGeometry args={[0.024, 10, 10]} />
            <meshBasicMaterial color="#f5f0e6" transparent opacity={dimmed ? 0.2 : 0.95} />
          </mesh>
        ))}
      <EndRing lat={flow.lat} lon={flow.lon} colour={colour} active={active} />
    </group>
  );
}

function EndRing({ lat, lon, colour, active }: { lat: number; lon: number; colour: string; active: boolean }) {
  const p = toVec(lat, lon, R * 1.004);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), p.clone().normalize());
  return (
    <group position={p} quaternion={q}>
      <mesh>
        <circleGeometry args={[active ? 0.05 : 0.034, 24]} />
        <meshBasicMaterial color={colour} transparent opacity={0.95} />
      </mesh>
      <mesh>
        <ringGeometry args={[0.07, 0.085, 32]} />
        <meshBasicMaterial color={colour} transparent opacity={active ? 0.9 : 0.4} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function IndiaBeacon() {
  const rings = useRef<(THREE.Mesh | null)[]>([]);
  const reduced = useReducedMotionPref();
  const p = toVec(INDIA_COORD.lat, INDIA_COORD.lon, R * 1.006);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), p.clone().normalize());
  useFrame(({ clock }) => {
    rings.current.forEach((m, k) => {
      if (!m) return;
      const t = reduced ? 0.4 : (clock.elapsedTime * 0.45 + k / 3) % 1;
      m.scale.setScalar(0.4 + t * 2.6);
      (m.material as THREE.MeshBasicMaterial).opacity = 0.65 * (1 - t);
    });
  });
  return (
    <group position={p} quaternion={q}>
      <mesh>
        <circleGeometry args={[0.05, 24]} />
        <meshBasicMaterial color="#f5f0e6" />
      </mesh>
      {[0, 1, 2].map((k) => (
        <mesh key={k} ref={(m) => (rings.current[k] = m)}>
          <ringGeometry args={[0.07, 0.082, 48]} />
          <meshBasicMaterial color="#f3c542" transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      ))}
      <mesh position={[0, 0, 0.002]}>
        <circleGeometry args={[0.28, 48]} />
        <meshBasicMaterial color="#f3c542" transparent opacity={0.06} depthWrite={false} />
      </mesh>
    </group>
  );
}

/** Flies the camera in from far away the first time the globe mounts. */
function Intro() {
  const { camera } = useThree();
  const reduced = useReducedMotionPref();
  const t0 = useRef<number | null>(null);
  useEffect(() => {
    if (!reduced) camera.position.set(0, 2.4, 17);
  }, [camera, reduced]);
  useFrame(({ clock }) => {
    if (reduced) return;
    if (t0.current === null) t0.current = clock.elapsedTime;
    const k = Math.min(1, (clock.elapsedTime - t0.current) / 2.4);
    if (k >= 1) return;
    const e = 1 - (1 - k) ** 3;
    camera.position.lerpVectors(new THREE.Vector3(0, 2.4, 17), new THREE.Vector3(0, 0.7, 8.4), e);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

function Scene({ onHover, hovered }: { onHover: (id: string | null) => void; hovered: string | null }) {
  const reduced = useReducedMotionPref();
  const group = useRef<THREE.Group>(null);

  // Sway ±30° around India rather than spinning away from it; the clock
  // only advances while nothing is hovered, so a hovered arc holds still.
  const t = useRef(0);
  useFrame((_, delta) => {
    if (!group.current || reduced) return;
    if (hovered === null) t.current += delta;
    group.current.rotation.y = 3.33 + Math.sin(t.current * 0.16) * 0.52;
  });

  return (
    <>
      <Intro />
      <Stars />
      {/* Solves x' = 0, z' > 0 for India's position vector under a rotation
          about Y, so the country faces the camera when the scene mounts. */}
      <group ref={group} rotation={[0.16, 3.33, 0]}>
        <Earth />
        <IndiaBeacon />
        {EXTERNAL_FLOWS.map((f) => (
          <Arc key={f.id} flow={f} active={hovered === f.id} dimmed={hovered !== null && hovered !== f.id} onHover={onHover} />
        ))}
      </group>
    </>
  );
}

export function EconomicGlobe() {
  const [hovered, setHovered] = useState<string | null>(null);
  const reduced = useReducedMotionPref();
  const frame = useRef<HTMLDivElement>(null);
  // Mount and animate only once the globe is near the viewport: the fly-in
  // plays when the reader arrives, and an off-screen WebGL loop costs nothing.
  const near = useInView(frame, { margin: '200px' });
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (near) setArmed(true);
  }, [near]);
  const flow = EXTERNAL_FLOWS.find((f) => f.id === hovered);

  return (
    <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[minmax(0,1fr)_340px]">
      <div ref={frame} className="relative h-[420px] bg-[radial-gradient(ellipse_at_center,#141a2e_0%,#0c0e14_70%)] sm:h-[520px] lg:h-[640px]">
        {armed && (
        <Canvas
          camera={{ position: [0, 0.7, 8.4], fov: 38 }}
          dpr={[1, 1.6]}
          gl={{ antialias: true, powerPreference: 'high-performance' }}
          frameloop={reduced || !near ? 'demand' : 'always'}
        >
          <Scene onHover={setHovered} hovered={hovered} />
          <OrbitControls
            enablePan={false}
            enableZoom
            minDistance={4.2}
            maxDistance={11}
            rotateSpeed={0.5}
            zoomSpeed={0.6}
          />
        </Canvas>
        )}

        <div className="pointer-events-none absolute left-4 top-4">
          <span className="label">Current account · {EXTERNAL_SUMMARY.period}</span>
        </div>

        <div className="pointer-events-none absolute bottom-4 left-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-2xs">
          <span className="flex items-center gap-1.5 text-ink-500">
            <span className="h-1.5 w-1.5 rounded-full bg-[#6fae4f]" aria-hidden /> Inflow
          </span>
          <span className="flex items-center gap-1.5 text-ink-500">
            <span className="h-1.5 w-1.5 rounded-full bg-[#f0663f]" aria-hidden /> Outflow
          </span>
          <span className="flex items-center gap-1.5 text-ink-600">
            <span className="h-1.5 w-1.5 rounded-full bg-ink-500" aria-hidden /> Unavailable
          </span>
        </div>

        <div className="pointer-events-none absolute right-4 top-4 hidden font-mono text-2xs text-ink-700 sm:block">
          drag to rotate · scroll to zoom
        </div>
      </div>

      <aside className="bg-ink-900/70 p-5 md:p-6">
        <span className="label-accent">India</span>
        <h3 className="display mt-2 text-2xl">In the global economy</h3>

        <dl className="mt-5 space-y-px border border-white/[0.07] bg-white/[0.07]">
          <div className="bg-ink-900 p-3.5">
            <dt className="label">Current account balance</dt>
            <dd className="metric mt-1.5 text-xl" data-numeric>
              US${number(Math.abs(EXTERNAL_SUMMARY.currentAccountUsdBn), 1)} bn
              <span className="ml-2 text-sm text-ink-500">
                {EXTERNAL_SUMMARY.currentAccountPctGdp}% of GDP
              </span>
            </dd>
          </div>
          <div className="bg-ink-900 p-3.5">
            <dt className="label">Goods trade deficit</dt>
            <dd className="metric mt-1.5 text-xl text-[#f3c542]" data-numeric>
              US${number(Math.abs(EXTERNAL_SUMMARY.goodsDeficitUsdBn), 1)} bn
            </dd>
          </div>
        </dl>

        <div className="mt-4 space-y-px border border-white/[0.07] bg-white/[0.07]">
          {EXTERNAL_FLOWS.map((f) => (
            <button
              key={f.id}
              type="button"
              onMouseEnter={() => setHovered(f.id)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(f.id)}
              onBlur={() => setHovered(null)}
              className={`flex w-full items-baseline justify-between gap-3 bg-ink-900 px-3.5 py-2.5 text-left transition-colors ${
                hovered === f.id ? 'bg-ink-850' : 'hover:bg-ink-850'
              }`}
            >
              <span className="flex items-center gap-2">
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{
                    background:
                      f.value === null ? '#6b6f80' : f.direction === 'inflow' ? '#6fae4f' : '#f0663f',
                  }}
                  aria-hidden
                />
                <span className="text-[0.8125rem] text-ink-200">{f.label}</span>
              </span>
              {f.value === null ? (
                <span className="font-mono text-2xs uppercase tracking-[0.12em] text-ink-600">unavailable</span>
              ) : (
                <span className="metric text-sm" data-numeric>
                  {number(f.value, 1)}
                </span>
              )}
            </button>
          ))}
        </div>

        {flow && (
          <div className="mt-3 border-l-2 border-[#f3c542] bg-ink-900/60 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <StatusBadge status={flow.status} size="xs" />
            </div>
            <p className="mt-1.5 text-2xs leading-relaxed text-ink-300">{flow.note}</p>
          </div>
        )}

        <div className="mt-4">
          <Notice tone="missing" title="What this globe does not show">
            {BILATERAL_NOTE}
          </Notice>
        </div>

        <p className="mt-4 border-t border-white/[0.07] pt-3 font-mono text-2xs leading-relaxed text-ink-600">
          Source: RBI, Developments in India’s Balance of Payments, published{' '}
          {longDate(EXTERNAL_SUMMARY.publicationDate)}. Retrieved {longDate(EXTERNAL_SUMMARY.accessedDate)}.
        </p>
      </aside>
    </div>
  );
}
