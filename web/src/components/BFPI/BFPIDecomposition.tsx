import { motion } from 'framer-motion';
import { INDICATORS, PILLARS, bandFor } from '../../models/bfpi/engine';
import type { BFPIResult, PillarScore } from '../../models/bfpi/types';
import { number } from '../../lib/format';
import { useReducedMotionPref } from '../../lib/motion';
import { AnimatedNumber } from '../ui';

const PILLAR_COLOUR: Record<string, string> = {
  profitability: '#e8933a',
  capital: '#5b9bd5',
  assetQuality: '#4fae86',
  liquidity: '#4aa5a8',
};

/**
 * Radial decomposition. The ring is the composite; the four arcs are the
 * pillars, each drawn at its own 0–100 position. Hovering an arc reveals
 * the standardisation that produced it.
 */
export function BFPIDecomposition({
  result,
  previousBfpi,
  onHoverPillar,
}: {
  result: BFPIResult;
  previousBfpi?: number | null;
  onHoverPillar?: (key: string | null) => void;
}) {
  const reduced = useReducedMotionPref();
  const band = bandFor(result.bfpi);
  const R = 104;
  const STROKE = 13;
  const GAP = 5; // degrees between arcs
  const arcSpan = 360 / 4 - GAP;

  const polar = (cx: number, cy: number, r: number, deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const arcPath = (startDeg: number, sweepDeg: number, r: number) => {
    const a = polar(140, 140, r, startDeg);
    const b = polar(140, 140, r, startDeg + sweepDeg);
    return `M${a.x.toFixed(2)},${a.y.toFixed(2)} A${r},${r} 0 ${sweepDeg > 180 ? 1 : 0} 1 ${b.x.toFixed(2)},${b.y.toFixed(2)}`;
  };

  const delta =
    previousBfpi !== undefined && previousBfpi !== null && result.bfpi !== null
      ? result.bfpi - previousBfpi
      : null;

  return (
    <div className="grid items-center gap-6 md:grid-cols-[280px_minmax(0,1fr)]">
      <div className="relative mx-auto" style={{ width: 280, height: 280 }}>
        <svg viewBox="0 0 280 280" className="h-full w-full" role="img" aria-label={`BFPI ${result.bfpi === null ? 'unavailable' : result.bfpi.toFixed(1)}`}>
          {/* Reference ring at 50 — the sample centre. */}
          <circle cx={140} cy={140} r={R} fill="none" stroke="rgba(255,255,255,0.055)" strokeWidth={STROKE} />

          {result.pillars.map((p, i) => {
            const start = i * (360 / 4) + GAP / 2;
            const colour = PILLAR_COLOUR[p.key];
            const frac = p.scaled === null ? 0 : p.scaled / 100;
            return (
              <g
                key={p.key}
                onMouseEnter={() => onHoverPillar?.(p.key)}
                onMouseLeave={() => onHoverPillar?.(null)}
                style={{ cursor: 'pointer' }}
              >
                <path
                  d={arcPath(start, arcSpan, R)}
                  fill="none"
                  stroke={p.available ? 'rgba(255,255,255,0.07)' : 'rgba(129,142,150,0.12)'}
                  strokeWidth={STROKE}
                  strokeLinecap="butt"
                  strokeDasharray={p.available ? undefined : '3 4'}
                />
                {p.available && (
                  <motion.path
                    d={arcPath(start, Math.max(0.6, arcSpan * frac), R)}
                    fill="none"
                    stroke={colour}
                    strokeWidth={STROKE}
                    strokeLinecap="butt"
                    initial={false}
                    animate={{ d: arcPath(start, Math.max(0.6, arcSpan * frac), R) }}
                    transition={reduced ? { duration: 0 } : { type: 'spring', stiffness: 130, damping: 22 }}
                    opacity={p.partial ? 0.6 : 1}
                  />
                )}
              </g>
            );
          })}

          {/* Tick at the 50 mark on each arc, so "above average" is visible. */}
          {result.pillars.map((_, i) => {
            const mid = i * (360 / 4) + GAP / 2 + arcSpan / 2;
            const inner = polar(140, 140, R - STROKE / 2, mid);
            const outer = polar(140, 140, R + STROKE / 2, mid);
            return (
              <line
                key={i}
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="rgba(8,9,10,0.5)"
                strokeWidth={1}
              />
            );
          })}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="label">BFPI</span>
          {result.bfpi === null ? (
            <>
              <span className="metric mt-1 text-2xl text-ink-600">—</span>
              <span className="mt-1 max-w-[9rem] font-mono text-[9px] uppercase leading-snug tracking-[0.12em] text-ink-600">
                Withheld
              </span>
            </>
          ) : (
            <>
              <AnimatedNumber
                value={result.bfpi}
                format={(n) => number(n, 1)}
                className="metric mt-1 text-[3rem] leading-none"
              />
              {delta !== null && Math.abs(delta) > 0.05 && (
                <span
                  className="mt-1 font-mono text-2xs"
                  style={{ color: delta > 0 ? '#4fae86' : '#d3675d' }}
                  data-numeric
                >
                  {delta > 0 ? '+' : '−'}
                  {Math.abs(delta).toFixed(1)} vs baseline
                </span>
              )}
              {band && (
                <span
                  className="mt-2 max-w-[10rem] font-mono text-[9px] uppercase leading-snug tracking-[0.12em]"
                  style={{ color: band.tone }}
                >
                  {band.label}
                </span>
              )}
            </>
          )}
        </div>
      </div>

      <div className="space-y-px border border-white/[0.07] bg-white/[0.07]">
        {result.pillars.map((p) => (
          <PillarRow key={p.key} pillar={p} onHover={onHoverPillar} />
        ))}
      </div>
    </div>
  );
}

function PillarRow({ pillar, onHover }: { pillar: PillarScore; onHover?: (k: string | null) => void }) {
  const colour = PILLAR_COLOUR[pillar.key];
  return (
    <div
      className="group bg-ink-900 p-3.5"
      onMouseEnter={() => onHover?.(pillar.key)}
      onMouseLeave={() => onHover?.(null)}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2" style={{ background: colour }} aria-hidden />
          <span className="text-[0.8125rem] text-ink-100">{pillar.label}</span>
          <span className="font-mono text-2xs text-ink-600">{(pillar.weight * 100).toFixed(0)}%</span>
        </span>
        {pillar.scaled === null ? (
          <span className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-600">Unavailable</span>
        ) : (
          <AnimatedNumber
            value={pillar.scaled}
            format={(n) => number(n, 1)}
            className="metric text-sm"
          />
        )}
      </div>

      <div className="relative mt-2 h-[3px] bg-ink-800">
        <span className="absolute left-1/2 top-[-2px] h-[7px] w-px bg-ink-600" aria-hidden title="Sample centre = 50" />
        {pillar.scaled !== null && (
          <motion.span
            className="absolute inset-y-0 left-0"
            style={{ background: colour }}
            initial={false}
            animate={{ width: `${pillar.scaled}%` }}
            transition={{ type: 'spring', stiffness: 130, damping: 22 }}
          />
        )}
      </div>

      <div className="mt-2 space-y-0.5">
        {pillar.indicators.map((ind) => (
          <div key={ind.key} className="flex items-baseline justify-between gap-3 font-mono text-2xs">
            <span className="text-ink-500">{INDICATORS[ind.key].short}</span>
            {ind.available && ind.z !== null ? (
              <span className="flex items-baseline gap-3">
                <span className="text-ink-400" data-numeric>
                  {number(ind.raw, 2)}
                  {INDICATORS[ind.key].unit === '%' ? '%' : ''}
                </span>
                <span
                  className="w-14 text-right"
                  style={{ color: ind.z >= 0 ? '#4fae86' : '#d3675d' }}
                  data-numeric
                >
                  z {ind.z >= 0 ? '+' : ''}
                  {ind.z.toFixed(2)}
                </span>
              </span>
            ) : (
              <span className="text-ink-700" title={ind.note}>
                data unavailable
              </span>
            )}
          </div>
        ))}
      </div>

      {pillar.note && <p className="mt-2 text-2xs leading-snug text-ink-600">{pillar.note}</p>}
      <p className="mt-1.5 hidden text-2xs leading-snug text-ink-600 group-hover:block">
        {PILLARS[pillar.key].rationale}
      </p>
    </div>
  );
}
