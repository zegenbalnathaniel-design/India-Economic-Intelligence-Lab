import { animate, useAnimationFrame, useMotionValue } from 'framer-motion';
import { scaleLinear } from 'd3-scale';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Figure2Result } from '../../models/figure2/types';
import { rupees, rupeesAxis } from '../../lib/format';
import { useReducedMotionPref } from '../../lib/motion';

interface Props {
  scenario: Figure2Result;
  baseline: Figure2Result;
  /** Hide the baseline when the reader has not diverged from it. */
  showBaseline: boolean;
  /** Plot aspect. The SVG scales to its container width at this ratio, so
   *  the chart never letterboxes inside a fixed pixel height. */
  aspect?: 'wide' | 'compact';
}

const M = { top: 20, right: 18, bottom: 34, left: 62 };

/**
 * Samples per curve. Every curve is resampled onto this fixed grid before
 * it is drawn, which is what makes morphing possible: two scenarios with
 * different horizons still produce point arrays of identical length, so the
 * chart can interpolate between them rather than snapping.
 */
const N = 160;

/** Screen-space y values for one curve, sampled across the year axis. */
type Curve = Float64Array;

interface Frame {
  xs: Curve;
  scenario: Curve;
  baseline: Curve;
  contributed: Curve;
  /** Terminal marker position. */
  markerX: number;
  markerY: number;
}

const cloneFrame = (f: Frame): Frame => ({
  xs: Float64Array.from(f.xs),
  scenario: Float64Array.from(f.scenario),
  baseline: Float64Array.from(f.baseline),
  contributed: Float64Array.from(f.contributed),
  markerX: f.markerX,
  markerY: f.markerY,
});

const blend = (a: Curve, b: Curve, k: number, out: Curve): Curve => {
  for (let i = 0; i < out.length; i += 1) out[i] = a[i] + (b[i] - a[i]) * k;
  return out;
};

/** Value of a result's series at a continuous year, linearly interpolated. */
function valueAt(
  rows: { value: number; contributed: number }[],
  startingCapital: number,
  year: number,
  key: 'value' | 'contributed',
) {
  if (year <= 0 || rows.length === 0) return startingCapital;
  const whole = Math.floor(year);
  if (whole >= rows.length) return rows[rows.length - 1][key];
  // Year 0 is the opening balance; year n is the end of row n − 1.
  const prev = whole === 0 ? startingCapital : rows[whole - 1][key];
  const next = rows[whole][key];
  return prev + (next - prev) * (year - whole);
}

function buildPath(xs: Curve, ys: Curve): string {
  let d = '';
  for (let i = 0; i < xs.length; i += 1) {
    d += `${i === 0 ? 'M' : 'L'}${xs[i].toFixed(2)},${ys[i].toFixed(2)}`;
  }
  return d;
}

function buildArea(xs: Curve, hi: Curve, lo: Curve): string {
  let d = '';
  for (let i = 0; i < xs.length; i += 1) d += `${i === 0 ? 'M' : 'L'}${xs[i].toFixed(2)},${hi[i].toFixed(2)}`;
  for (let i = xs.length - 1; i >= 0; i -= 1) d += `L${xs[i].toFixed(2)},${lo[i].toFixed(2)}`;
  return `${d}Z`;
}

export function WealthChart({ scenario, baseline, showBaseline, aspect = 'wide' }: Props) {
  const reduced = useReducedMotionPref();
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverYear, setHoverYear] = useState<number | null>(null);

  // Chosen so the plot reads at roughly 2.3:1 wide and 2.6:1 compact.
  const W = aspect === 'wide' ? 960 : 780;
  const H = aspect === 'wide' ? 420 : 300;
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const { x, y, ticksY, ticksX, maxValue, target } = useMemo(() => {
    const years = Math.max(scenario.inputs.years, 1);
    const top = Math.max(
      scenario.finalValue,
      showBaseline ? baseline.finalValue : 0,
      scenario.totalContributed,
      1,
    );
    const xs = scaleLinear().domain([0, years]).range([0, iw]);
    const ys = scaleLinear().domain([0, top * 1.06]).range([ih, 0]).nice();

    const gx = new Float64Array(N + 1);
    const gScenario = new Float64Array(N + 1);
    const gBaseline = new Float64Array(N + 1);
    const gContrib = new Float64Array(N + 1);

    for (let i = 0; i <= N; i += 1) {
      const yr = (i / N) * years;
      gx[i] = xs(yr);
      gScenario[i] = ys(valueAt(scenario.rows, scenario.inputs.startingCapital, yr, 'value'));
      gContrib[i] = ys(valueAt(scenario.rows, scenario.inputs.startingCapital, yr, 'contributed'));
      // The baseline is drawn on the scenario's own horizon so both curves
      // share an x-grid; beyond its end it holds its terminal value.
      const byr = Math.min(yr, baseline.inputs.years);
      gBaseline[i] = ys(valueAt(baseline.rows, baseline.inputs.startingCapital, byr, 'value'));
    }

    return {
      x: xs,
      y: ys,
      ticksY: ys.ticks(5),
      ticksX: xs.ticks(Math.min(8, years)).filter((t) => Number.isInteger(t) && t > 0),
      maxValue: top,
      target: {
        xs: gx,
        scenario: gScenario,
        baseline: gBaseline,
        contributed: gContrib,
        markerX: xs(years),
        markerY: ys(scenario.finalValue),
      } satisfies Frame,
    };
  }, [scenario, baseline, showBaseline, iw, ih]);

  /* --------------------------------------------------------------- *
   * Morphing. Framer Motion cannot interpolate an SVG `d` string, so
   * the curves are interpolated as point arrays and written straight to
   * the path nodes each frame — which also means an animating chart
   * never re-renders the panel around it.
   * --------------------------------------------------------------- */
  const scenarioRef = useRef<SVGPathElement>(null);
  const baselineRef = useRef<SVGPathElement>(null);
  const contribRef = useRef<SVGPathElement>(null);
  const areaRef = useRef<SVGPathElement>(null);
  const markerRef = useRef<SVGCircleElement>(null);

  const progress = useMotionValue(1);
  // Three buffers rather than two: `from` must not alias `shown`, or each
  // frame would blend the previous frame's output into itself and the
  // spring would degrade into exponential smoothing.
  // Mutable scratch buffers for the animation. They are seeded on first use
  // — which always happens in an effect or an animation frame, never during
  // render — and reused thereafter so a morphing chart allocates nothing.
  const framesRef = useRef<{ from: Frame; shown: Frame } | null>(null);
  const settledRef = useRef(false);
  const ensureFrames = (seed: Frame) => {
    if (framesRef.current === null) {
      framesRef.current = { from: cloneFrame(seed), shown: cloneFrame(seed) };
    }
    return framesRef.current;
  };

  useEffect(() => {
    const { from, shown } = ensureFrames(target);
    settledRef.current = false;

    if (reduced) {
      from.xs.set(target.xs);
      from.scenario.set(target.scenario);
      from.baseline.set(target.baseline);
      from.contributed.set(target.contributed);
      from.markerX = target.markerX;
      from.markerY = target.markerY;
      progress.set(1);
      return;
    }

    from.xs.set(shown.xs);
    from.scenario.set(shown.scenario);
    from.baseline.set(shown.baseline);
    from.contributed.set(shown.contributed);
    from.markerX = shown.markerX;
    from.markerY = shown.markerY;
    progress.set(0);

    const controls = animate(progress, 1, { type: 'spring', stiffness: 130, damping: 24, mass: 1 });
    return () => controls.stop();
  }, [target, reduced, progress]);

  useAnimationFrame(() => {
    const k = progress.get();
    if (settledRef.current && k >= 1) return;

    const { from, shown } = ensureFrames(target);

    blend(from.xs, target.xs, k, shown.xs);
    blend(from.scenario, target.scenario, k, shown.scenario);
    blend(from.contributed, target.contributed, k, shown.contributed);
    if (showBaseline) blend(from.baseline, target.baseline, k, shown.baseline);
    shown.markerX = from.markerX + (target.markerX - from.markerX) * k;
    shown.markerY = from.markerY + (target.markerY - from.markerY) * k;

    scenarioRef.current?.setAttribute('d', buildPath(shown.xs, shown.scenario));
    contribRef.current?.setAttribute('d', buildPath(shown.xs, shown.contributed));
    areaRef.current?.setAttribute('d', buildArea(shown.xs, shown.scenario, shown.contributed));
    if (showBaseline) baselineRef.current?.setAttribute('d', buildPath(shown.xs, shown.baseline));
    markerRef.current?.setAttribute('cx', String(shown.markerX));
    markerRef.current?.setAttribute('cy', String(shown.markerY));

    if (k >= 1) settledRef.current = true;
  });

  const hovered = hoverYear !== null ? scenario.rows.find((r) => r.year === hoverYear) : undefined;
  const hoveredBaseline = hoverYear !== null ? baseline.rows.find((r) => r.year === hoverYear) : undefined;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W - M.left;
    const yr = Math.round(x.invert(Math.max(0, Math.min(iw, px))));
    setHoverYear(yr >= 1 && yr <= scenario.inputs.years ? yr : null);
  };

  return (
    <div className="relative w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        onMouseMove={onMove}
        onMouseLeave={() => setHoverYear(null)}
        role="img"
        aria-label={`Portfolio value over ${scenario.inputs.years} years. Your scenario ends at ${rupees(scenario.finalValue)} against ${rupees(scenario.totalContributed)} contributed.${showBaseline ? ` The research baseline ends at ${rupees(baseline.finalValue)}.` : ''}`}
      >
        <defs>
          <linearGradient id="gain-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e8933a" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#e8933a" stopOpacity="0.015" />
          </linearGradient>
        </defs>

        <g transform={`translate(${M.left},${M.top})`}>
          {ticksY.map((t) => (
            <g key={t} transform={`translate(0,${y(t)})`}>
              <line x1={0} x2={iw} stroke="rgba(255,255,255,0.05)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
              <text x={-10} dy="0.32em" textAnchor="end" className="fill-ink-600 font-mono" fontSize={10}>
                {rupeesAxis(t)}
              </text>
            </g>
          ))}

          {ticksX.map((t) => (
            <g key={t} transform={`translate(${x(t)},0)`}>
              <line y1={0} y2={ih} stroke="rgba(255,255,255,0.03)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
              <text y={ih + 18} textAnchor="middle" className="fill-ink-600 font-mono" fontSize={10}>
                {t}
              </text>
            </g>
          ))}

          {/* Investment gain: the wedge between what was put in and what it became. */}
          <path ref={areaRef} d={buildArea(target.xs, target.scenario, target.contributed)} fill="url(#gain-fill)" />

          {/* Total contributed — the no-return counterfactual. */}
          <path
            ref={contribRef}
            d={buildPath(target.xs, target.contributed)}
            fill="none"
            stroke="#5d6a72"
            strokeWidth={1.25}
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
          />

          <path
            ref={baselineRef}
            d={buildPath(target.xs, target.baseline)}
            fill="none"
            stroke="#5b9bd5"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            vectorEffect="non-scaling-stroke"
            opacity={showBaseline ? 0.85 : 0}
          />

          <path
            ref={scenarioRef}
            d={buildPath(target.xs, target.scenario)}
            fill="none"
            stroke="#e8933a"
            strokeWidth={2.25}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {hovered && (
            <g>
              <line
                x1={x(hovered.year)}
                x2={x(hovered.year)}
                y1={0}
                y2={ih}
                stroke="rgba(232,147,58,0.4)"
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
              <circle cx={x(hovered.year)} cy={y(hovered.value)} r={3.5} fill="#e8933a" />
              <circle cx={x(hovered.year)} cy={y(hovered.contributed)} r={2.5} fill="#5d6a72" />
              {showBaseline && hoveredBaseline && (
                <circle cx={x(hoveredBaseline.year)} cy={y(hoveredBaseline.value)} r={2.5} fill="#5b9bd5" />
              )}
            </g>
          )}

          <circle ref={markerRef} cx={target.markerX} cy={target.markerY} r={4} fill="#e8933a" />
        </g>
      </svg>

      {hovered && (
        <div
          className="pointer-events-none absolute top-3 z-10 border border-white/[0.12] bg-ink-950/95 px-3 py-2 backdrop-blur"
          style={{
            left: `${((M.left + x(hovered.year)) / W) * 100}%`,
            transform: `translateX(${x(hovered.year) > iw * 0.6 ? '-105%' : '12px'})`,
          }}
        >
          <p className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-500">Year {hovered.year}</p>
          <dl className="mt-1.5 space-y-0.5">
            <div className="flex items-baseline gap-3">
              <dt className="w-24 font-mono text-2xs text-[#e8933a]">Your scenario</dt>
              <dd className="metric text-xs">{rupees(hovered.value)}</dd>
            </div>
            {showBaseline && hoveredBaseline && (
              <div className="flex items-baseline gap-3">
                <dt className="w-24 font-mono text-2xs text-[#5b9bd5]">Baseline</dt>
                <dd className="metric text-xs">{rupees(hoveredBaseline.value)}</dd>
              </div>
            )}
            <div className="flex items-baseline gap-3">
              <dt className="w-24 font-mono text-2xs text-ink-500">Contributed</dt>
              <dd className="metric text-xs text-ink-300">{rupees(hovered.contributed)}</dd>
            </div>
            <div className="flex items-baseline gap-3 border-t border-white/[0.07] pt-0.5">
              <dt className="w-24 font-mono text-2xs text-ink-500">Gain</dt>
              <dd className="metric text-xs text-ink-300">{rupees(hovered.gain)}</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[0.07] pt-3">
        <Legend colour="#e8933a" label="Your scenario" />
        {showBaseline && <Legend colour="#5b9bd5" label="Research baseline" dashed />}
        <Legend colour="#5d6a72" label="Total contributed" dashed />
        <span className="flex items-center gap-2 font-mono text-2xs text-ink-500">
          <span className="h-2.5 w-4" style={{ background: 'rgba(232,147,58,0.2)' }} aria-hidden />
          Investment gain
        </span>
        <span className="ml-auto flex gap-4 font-mono text-2xs text-ink-700">
          <span>X: years</span>
          <span>Peak {rupeesAxis(maxValue)}</span>
        </span>
      </div>
    </div>
  );
}

function Legend({ colour, label, dashed }: { colour: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-2 font-mono text-2xs text-ink-500">
      <svg width="16" height="2" aria-hidden>
        <line
          x1="0"
          y1="1"
          x2="16"
          y2="1"
          stroke={colour}
          strokeWidth="2"
          strokeDasharray={dashed ? '4 3' : undefined}
        />
      </svg>
      {label}
    </span>
  );
}
