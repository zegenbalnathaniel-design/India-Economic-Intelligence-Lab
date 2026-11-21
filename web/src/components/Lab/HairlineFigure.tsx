import {
  Branches,
  Cabinet,
  Dish,
  Elevator,
  Exploded,
  Lockers,
  Plot,
  Riffle,
  Slow,
  Terrain,
  Turntable,
  Vault,
} from '@lucasmarkes/hairline/react';
import { useState, type CSSProperties } from 'react';
import { cn } from '../../lib/format';
import { useReducedMotionPref } from '../../lib/motion';

const FIGURES = { Branches, Cabinet, Dish, Elevator, Exploded, Lockers, Plot, Riffle, Slow, Terrain, Turntable, Vault };
export type HairlineName = keyof typeof FIGURES;

/**
 * One @lucasmarkes/hairline figure, lit in `accent`, with a boxed caption
 * underneath. The figures answer the pointer; with `play` they also walk
 * through their answer on their own until the pointer arrives (they rest
 * under prefers-reduced-motion).
 *
 * `caption` maps the figure's own read-out (e.g. "3", "main · 2", "az 90°")
 * onto this lab's real labels; return null to show `idle`. As in the
 * Streamlit version, only labels are real — the animation is a metaphor.
 */
export function HairlineFigure({
  name,
  accent = 'var(--accent)',
  label,
  idle,
  caption,
  play = true,
  intensity = 0.6,
  plate = '#11131a',
  className,
  maxWidth = 520,
}: {
  name: HairlineName;
  accent?: string;
  label: string;
  idle: string;
  caption?: (read: string) => string | null;
  play?: boolean;
  intensity?: number;
  plate?: string;
  className?: string;
  maxWidth?: number;
}) {
  const reduced = useReducedMotionPref();
  const [text, setText] = useState(idle);
  const Figure = FIGURES[name];
  const style = {
    '--hairline-hi': accent,
    '--hairline-plate': plate,
    '--hairline-edge': '#f5f0e6',
    '--hairline-mid': '#8b8d99',
    '--hairline-lo': '#3a3f52',
    '--hairline-stroke': 1.5,
  } as CSSProperties;

  return (
    <figure className={cn('mx-auto w-full', className)} style={{ maxWidth, ...style }}>
      <Figure
        className="w-full"
        style={{ aspectRatio: '5 / 4' }}
        theme="dark"
        play={play && !reduced}
        intensity={reduced ? 0.15 : intensity}
        label={label}
        onRead={(read) => setText((caption?.(read) ?? null) || idle)}
      />
      <figcaption
        aria-live="polite"
        className="mt-3 min-h-[3.4em] whitespace-pre-line border border-l-2 px-4 py-2.5 font-mono text-[11.5px] leading-relaxed text-ink-100"
        style={{ borderColor: 'var(--hairline)', borderLeftColor: accent, background: 'rgba(24,27,38,0.7)' }}
      >
        {text}
      </figcaption>
    </figure>
  );
}
