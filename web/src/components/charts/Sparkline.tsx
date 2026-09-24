import { useMemo } from 'react';
import type { SeriesPoint } from '../../data/types';

/**
 * A minimal series plot. Gaps in the data are rendered as gaps — the path
 * breaks where a value is null rather than bridging it, because bridging
 * would draw a line through data that does not exist.
 */
export function Sparkline({
  series,
  colour = '#e8933a',
  height = 32,
  showAxis = false,
}: {
  series: SeriesPoint[];
  colour?: string;
  height?: number;
  showAxis?: boolean;
}) {
  const W = 300;
  const H = height;
  const pad = showAxis ? 14 : 3;

  const { segments, points, min, max, zeroY } = useMemo(() => {
    const values = series.map((s) => s.value).filter((v): v is number => v !== null && Number.isFinite(v));
    if (values.length === 0) return { segments: [], points: [], min: 0, max: 0, zeroY: null as number | null };

    const lo = Math.min(...values, 0);
    const hi = Math.max(...values);
    const range = hi - lo || 1;
    const x = (i: number) => pad + (i / Math.max(1, series.length - 1)) * (W - pad * 2);
    const y = (v: number) => H - pad - ((v - lo) / range) * (H - pad * 2);

    const segs: string[] = [];
    const pts: { x: number; y: number; s: SeriesPoint }[] = [];
    let current: string[] = [];
    series.forEach((s, i) => {
      if (s.value === null || !Number.isFinite(s.value)) {
        if (current.length > 1) segs.push(current.join(' '));
        current = [];
        return;
      }
      const px = x(i);
      const py = y(s.value);
      current.push(`${current.length === 0 ? 'M' : 'L'}${px.toFixed(2)},${py.toFixed(2)}`);
      pts.push({ x: px, y: py, s });
    });
    if (current.length > 1) segs.push(current.join(' '));

    return { segments: segs, points: pts, min: lo, max: hi, zeroY: lo < 0 ? y(0) : null };
  }, [series, H, pad]);

  if (points.length === 0) {
    return (
      <div className="flex h-full items-center font-mono text-2xs text-ink-700">No series available</div>
    );
  }

  const last = points[points.length - 1];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="h-full w-full overflow-visible"
      role="img"
      aria-label={`Series from ${series[0].periodLabel} to ${series[series.length - 1].periodLabel}. Range ${min.toFixed(1)} to ${max.toFixed(1)}.`}
    >
      {zeroY !== null && (
        <line x1={0} x2={W} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.12)" strokeWidth={1} strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />
      )}
      {segments.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke={colour}
          strokeWidth={1.4}
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          opacity={0.85}
        />
      ))}
      {/* Points that exist are marked; absent periods leave visible gaps. */}
      {series.map((s, i) => {
        if (s.value !== null && Number.isFinite(s.value)) return null;
        const px = pad + (i / Math.max(1, series.length - 1)) * (W - pad * 2);
        return (
          <line
            key={`gap-${i}`}
            x1={px}
            x2={px}
            y1={pad}
            y2={H - pad}
            stroke="rgba(129,142,150,0.3)"
            strokeWidth={1}
            strokeDasharray="1 3"
            vectorEffect="non-scaling-stroke"
          />
        );
      })}
      <circle cx={last.x} cy={last.y} r={2.2} fill={colour} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
