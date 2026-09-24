import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
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

const toVec = (lat: number, lon: number, radius = R) => {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
};

/** A graticule sphere — the globe reads as an instrument, not a planet. */
function Graticule() {
  const geometry = useMemo(() => new THREE.SphereGeometry(R, 40, 26), []);
  return (
    <group>
      <mesh>
        <sphereGeometry args={[R * 0.995, 48, 32]} />
        <meshBasicMaterial color="#0b0d0f" />
      </mesh>
      <lineSegments>
        <wireframeGeometry args={[geometry]} />
        <lineBasicMaterial color="#2a3238" transparent opacity={0.5} />
      </lineSegments>
    </group>
  );
}

function Arc({
  flow,
  active,
  onHover,
}: {
  flow: ExternalFlow;
  active: boolean;
  onHover: (id: string | null) => void;
}) {
  const reduced = useReducedMotionPref();
  const dashRef = useRef<THREE.Mesh>(null);
  const missing = flow.value === null;

  const { curve, tube } = useMemo(() => {
    const start = toVec(INDIA_COORD.lat, INDIA_COORD.lon);
    const end = toVec(flow.lat, flow.lon);
    const mid = start.clone().add(end).multiplyScalar(0.5);
    const lift = 1 + start.distanceTo(end) * 0.28;
    mid.normalize().multiplyScalar(R * lift);
    const c = new THREE.QuadraticBezierCurve3(start, mid, end);
    return { curve: c, tube: new THREE.TubeGeometry(c, 48, missing ? 0.006 : 0.013, 6, false) };
  }, [flow.lat, flow.lon, missing]);

  const colour = missing ? '#5d6a72' : flow.direction === 'inflow' ? '#4fae86' : '#e8933a';

  useFrame(({ clock }) => {
    if (!dashRef.current || reduced) return;
    const t = (clock.elapsedTime * 0.22 + (flow.id.length % 5) * 0.2) % 1;
    const p = curve.getPoint(flow.direction === 'inflow' ? t : 1 - t);
    dashRef.current.position.copy(p);
  });

  return (
    <group
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(flow.id);
      }}
      onPointerOut={() => onHover(null)}
    >
      <mesh geometry={tube}>
        <meshBasicMaterial
          color={colour}
          transparent
          opacity={missing ? 0.22 : active ? 0.95 : 0.5}
        />
      </mesh>
      {!missing && (
        <mesh ref={dashRef}>
          <sphereGeometry args={[0.028, 8, 8]} />
          <meshBasicMaterial color={colour} transparent opacity={active ? 1 : 0.7} />
        </mesh>
      )}
      <mesh position={toVec(flow.lat, flow.lon, R * 1.005)}>
        <sphereGeometry args={[active ? 0.05 : 0.032, 10, 10]} />
        <meshBasicMaterial color={colour} transparent opacity={missing ? 0.35 : 0.9} />
      </mesh>
    </group>
  );
}

function IndiaMarker() {
  const ref = useRef<THREE.Mesh>(null);
  const reduced = useReducedMotionPref();
  useFrame(({ clock }) => {
    if (!ref.current || reduced) return;
    const s = 1 + Math.sin(clock.elapsedTime * 1.4) * 0.12;
    ref.current.scale.setScalar(s);
  });
  return (
    <group position={toVec(INDIA_COORD.lat, INDIA_COORD.lon, R * 1.01)}>
      <mesh>
        <sphereGeometry args={[0.055, 14, 14]} />
        <meshBasicMaterial color="#f4f6f6" />
      </mesh>
      <mesh ref={ref}>
        <sphereGeometry args={[0.085, 14, 14]} />
        <meshBasicMaterial color="#e8933a" transparent opacity={0.28} />
      </mesh>
    </group>
  );
}

function Scene({ onHover, hovered }: { onHover: (id: string | null) => void; hovered: string | null }) {
  const reduced = useReducedMotionPref();
  const group = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (group.current && !reduced && hovered === null) group.current.rotation.y += delta * 0.045;
  });

  return (
    // Solves x' = 0, z' > 0 for India's position vector under a rotation
    // about Y, so the country faces the camera when the scene mounts.
    <group ref={group} rotation={[0.16, 3.33, 0]}>
      <Graticule />
      <IndiaMarker />
      {EXTERNAL_FLOWS.map((f) => (
        <Arc key={f.id} flow={f} active={hovered === f.id} onHover={onHover} />
      ))}
    </group>
  );
}

export function EconomicGlobe() {
  const [hovered, setHovered] = useState<string | null>(null);
  const reduced = useReducedMotionPref();
  const flow = EXTERNAL_FLOWS.find((f) => f.id === hovered);

  return (
    <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="relative h-[400px] bg-ink-950 sm:h-[480px] lg:h-[600px]">
        <Canvas
          camera={{ position: [0, 0.5, 7.4], fov: 40 }}
          dpr={[1, 1.6]}
          gl={{ antialias: true, powerPreference: 'high-performance' }}
          frameloop={reduced ? 'demand' : 'always'}
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

        <div className="pointer-events-none absolute left-4 top-4">
          <span className="label">Current account · {EXTERNAL_SUMMARY.period}</span>
        </div>

        <div className="pointer-events-none absolute bottom-4 left-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-2xs">
          <span className="flex items-center gap-1.5 text-ink-500">
            <span className="h-1.5 w-1.5 rounded-full bg-[#4fae86]" aria-hidden /> Inflow
          </span>
          <span className="flex items-center gap-1.5 text-ink-500">
            <span className="h-1.5 w-1.5 rounded-full bg-[#e8933a]" aria-hidden /> Outflow
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
            <dd className="metric mt-1.5 text-xl text-[#e8933a]" data-numeric>
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
                      f.value === null ? '#5d6a72' : f.direction === 'inflow' ? '#4fae86' : '#e8933a',
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
          <div className="mt-3 border-l-2 border-[#e8933a] bg-ink-900/60 px-3 py-2.5">
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
