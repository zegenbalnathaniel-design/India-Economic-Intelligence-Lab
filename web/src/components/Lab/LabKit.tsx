/**
 * The lab page kit: shell (accent + scroll progress), hero with a Hairline
 * figure, lettered sections whose hairline rule draws itself in on scroll,
 * controls, stat tiles, callouts, chart frames and tables.
 */
import { motion, useScroll, useSpring, useTransform } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import { useRef, type CSSProperties, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { LabMeta } from '../../labs/registry';
import { cn } from '../../lib/format';
import { EASE_OUT, useReducedMotionPref } from '../../lib/motion';
import { HairlineFigure, type HairlineName } from './HairlineFigure';

// ---------------------------------------------------------------------------
// Chart theme (recharts)
// ---------------------------------------------------------------------------

export const SERIES = ['#4d6ff0', '#f04a32', '#f3c542', '#6fae4f', '#24a6a1', '#f5f0e6', '#5fd0c9', '#f0663f'];

export const axis = {
  stroke: 'rgba(245,240,230,0.18)',
  tick: { fill: '#8b8d99', fontSize: 11, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
  tickLine: false,
} as const;

export const grid = { stroke: 'rgba(245,240,230,0.06)', strokeDasharray: '2 4' } as const;

export const tooltip = {
  contentStyle: {
    background: 'rgba(17,19,26,0.96)',
    border: '1px solid rgba(245,240,230,0.16)',
    borderRadius: 0,
    fontFamily: '"JetBrains Mono", ui-monospace, monospace',
    fontSize: 11.5,
    color: '#e6e0d3',
    boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
  },
  labelStyle: { color: '#f5f0e6', marginBottom: 4 },
  itemStyle: { padding: 0 },
  cursor: { stroke: 'rgba(245,240,230,0.25)', strokeWidth: 1 },
} as const;

export const legend = {
  wrapperStyle: { fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontSize: 11, color: '#b6af9e', paddingTop: 8 },
  iconType: 'plainline' as const,
};

// ---------------------------------------------------------------------------
// Shell, progress, hero
// ---------------------------------------------------------------------------

function ScrollProgress({ accent }: { accent: string }) {
  const { scrollYProgress } = useScroll();
  const x = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.4 });
  return (
    <motion.div
      aria-hidden
      className="fixed inset-x-0 top-0 z-[60] h-[2px] origin-left"
      style={{ scaleX: x, background: `linear-gradient(90deg, ${accent}, ${accent}88)` }}
    />
  );
}

export function LabShell({ lab, children }: { lab: LabMeta; children: ReactNode }) {
  return (
    <div style={{ '--accent': lab.accent } as CSSProperties} className="relative">
      <ScrollProgress accent={lab.accent} />
      {children}
    </div>
  );
}

export function LabHero({
  lab,
  lede,
  stats,
  figure,
}: {
  lab: LabMeta;
  lede: ReactNode;
  stats?: { label: string; value: ReactNode; sub?: ReactNode }[];
  figure: { name: HairlineName; label: string; idle: string; caption?: (read: string) => string | null };
}) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotionPref();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const yFig = useTransform(scrollYProgress, [0, 1], [0, reduced ? 0 : 90]);
  const yText = useTransform(scrollYProgress, [0, 1], [0, reduced ? 0 : -40]);
  const fade = useTransform(scrollYProgress, [0, 0.85], [1, reduced ? 1 : 0.15]);

  return (
    <header ref={ref} className="relative overflow-hidden border-b border-white/[0.07] pt-24 md:pt-32">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 lab-grid opacity-60"
        style={{ maskImage: 'radial-gradient(70% 70% at 70% 40%, black, transparent)' }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-40 -top-40 h-[620px] w-[620px] rounded-full blur-3xl"
        style={{ background: `radial-gradient(circle, ${lab.accent}22, transparent 65%)` }}
      />
      <div className="relative mx-auto grid max-w-[1400px] items-center gap-12 px-5 pb-16 md:px-10 md:pb-24 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div style={{ y: yText, opacity: fade }}>
          <Link to="/labs" className="label inline-flex items-center gap-2 transition-colors hover:text-ink-100">
            <ArrowLeft size={12} /> All labs
          </Link>
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE_OUT }}
            className="mt-8"
          >
            <div className="flex items-center gap-3">
              <motion.span
                aria-hidden
                className="h-px w-10"
                style={{ background: lab.accent }}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.9, ease: EASE_OUT, delay: 0.15 }}
              />
              <span className="label-accent">
                Lab {lab.n} · {lab.group}
              </span>
            </div>
            <h1 className="display mt-6 max-w-[16ch] text-balance text-[2.6rem] leading-[1.02] md:text-[4.4rem]">{lab.title}</h1>
            <p className="mt-6 max-w-[34ch] font-display text-[1.35rem] italic leading-snug text-ink-100 md:text-[1.6rem]">
              {lab.question}
            </p>
            <div className="mt-6 max-w-[60ch] text-[0.98rem] leading-relaxed text-ink-300 text-pretty">{lede}</div>
          </motion.div>
          {stats && (
            <motion.dl
              initial="hidden"
              animate="show"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.35 } } }}
              className="mt-10 grid grid-cols-2 gap-px border border-white/[0.09] bg-white/[0.09] sm:grid-cols-3"
            >
              {stats.map((s) => (
                <motion.div
                  key={s.label}
                  variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } } }}
                  className="bg-ink-950/90 px-4 py-4"
                >
                  <dt className="label">{s.label}</dt>
                  <dd className="metric mt-2 text-[1.35rem]" style={{ color: lab.accent }}>
                    {s.value}
                  </dd>
                  {s.sub && <dd className="mt-1 text-[11.5px] leading-snug text-ink-500">{s.sub}</dd>}
                </motion.div>
              ))}
            </motion.dl>
          )}
        </motion.div>
        <motion.div
          style={{ y: yFig }}
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: EASE_OUT, delay: 0.1 }}
          className="ticked border border-white/[0.08] bg-ink-900/70 p-5 backdrop-blur-sm md:p-8"
        >
          <HairlineFigure accent={lab.accent} {...figure} />
        </motion.div>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

export function LabSection({
  id,
  index,
  title,
  lede,
  children,
  className,
}: {
  id?: string;
  index: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={cn('relative py-16 md:py-24', className)}>
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <motion.div
          aria-hidden
          className="rule-draw mb-10"
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 1.2, ease: EASE_OUT }}
        />
        <motion.header
          initial={{ opacity: 0, y: 22 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.75, ease: EASE_OUT }}
          className="mb-10 grid gap-6 md:grid-cols-[120px_1fr]"
        >
          <div className="font-mono text-[2.6rem] font-light leading-none md:text-[3.4rem]" style={{ color: 'var(--accent)' }}>
            {index}
          </div>
          <div>
            <h2 className="display max-w-4xl text-balance text-[1.9rem] leading-[1.08] md:text-[2.75rem]">{title}</h2>
            {lede && <div className="mt-4 max-w-3xl text-[0.95rem] leading-relaxed text-ink-300 text-pretty">{lede}</div>}
          </div>
        </motion.header>
        <Reveal>{children}</Reveal>
      </div>
    </section>
  );
}

export function Reveal({ children, className, delay = 0.05 }: { children: ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.8, ease: EASE_OUT, delay }}
    >
      {children}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Building blocks
// ---------------------------------------------------------------------------

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: string }) {
  return (
    <div className="border border-white/[0.09] bg-ink-900/60 px-4 py-4">
      <div className="label">{label}</div>
      <div className="metric mt-2 text-[1.4rem] leading-none" style={{ color: tone ?? 'var(--accent)' }}>
        {value}
      </div>
      {sub && <div className="mt-2 text-[11.5px] leading-snug text-ink-500">{sub}</div>}
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{children}</div>;
}

export function Callout({ tone = 'note', title, children }: { tone?: 'note' | 'warn' | 'accent'; title?: string; children: ReactNode }) {
  const c = tone === 'warn' ? '#f04a32' : tone === 'accent' ? 'var(--accent)' : '#8b8d99';
  return (
    <div className="border border-l-2 border-white/[0.08] bg-ink-900/60 px-4 py-3 text-[13.5px] leading-relaxed text-ink-200" style={{ borderLeftColor: c }}>
      {title && <div className="label mb-1.5" style={{ color: c }}>{title}</div>}
      {children}
    </div>
  );
}

export function SourceLine({ children }: { children: ReactNode }) {
  return <p className="mt-3 font-mono text-[10.5px] leading-relaxed tracking-wide text-ink-500">Source · {children}</p>;
}

export function ChartFrame({
  title,
  subtitle,
  source,
  children,
  height = 340,
  actions,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  source?: ReactNode;
  children: ReactNode;
  height?: number;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <figure className={cn('ticked border border-white/[0.08] bg-ink-900/50 p-4 md:p-6', className)}>
      <figcaption className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[15px] font-medium text-ink-50">{title}</div>
          {subtitle && <div className="mt-1 text-[12.5px] text-ink-400">{subtitle}</div>}
        </div>
        {actions}
      </figcaption>
      <div style={{ height }}>{children}</div>
      {source && <SourceLine>{source}</SourceLine>}
    </figure>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-2 block">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-[11px] text-ink-500">{hint}</span>}
    </label>
  );
}

export function Select<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: readonly (T | { value: T; label: string })[];
}) {
  return (
    <select className="select" value={value} onChange={(e) => onChange(e.target.value as T)}>
      {options.map((o) => {
        const v = typeof o === 'string' ? o : o.value;
        const l = typeof o === 'string' ? o : o.label;
        return (
          <option key={v} value={v}>
            {l}
          </option>
        );
      })}
    </select>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: readonly (T | { value: T; label: string })[];
}) {
  return (
    <div className="inline-flex flex-wrap gap-1.5" role="group">
      {options.map((o) => {
        const v = typeof o === 'string' ? o : o.value;
        const l = typeof o === 'string' ? o : o.label;
        return (
          <button key={v} type="button" className="chip" aria-pressed={v === value} onClick={() => onChange(v)}>
            {l}
          </button>
        );
      })}
    </div>
  );
}

export function Range({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  format = (v: number) => String(v),
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <label className="block">
      <span className="mb-2 flex items-baseline justify-between gap-3">
        <span className="label">{label}</span>
        <span className="metric text-[13px]" style={{ color: 'var(--accent)' }}>
          {format(value)}
        </span>
      </span>
      <input
        type="range"
        className="w-full"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ background: `linear-gradient(90deg, var(--accent) ${pct}%, transparent ${pct}%) center / 100% 2px no-repeat` }}
      />
    </label>
  );
}

export function ChipMulti({
  values,
  onChange,
  options,
  max,
  colour,
}: {
  values: string[];
  onChange: (v: string[]) => void;
  options: readonly string[];
  max?: number;
  colour?: (v: string) => string | undefined;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => {
        const on = values.includes(o);
        const c = on ? colour?.(o) : undefined;
        return (
          <button
            key={o}
            type="button"
            className="chip"
            aria-pressed={on}
            style={c ? { background: c, borderColor: c } : undefined}
            onClick={() => {
              if (on) onChange(values.filter((v) => v !== o));
              else if (!max || values.length < max) onChange([...values, o]);
            }}
          >
            {o}
          </button>
        );
      })}
    </div>
  );
}

export function Controls({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('grid gap-5 border border-white/[0.08] bg-ink-900/50 p-4 md:grid-cols-3 md:p-5', className)}>{children}</div>
  );
}

export function DataTable({
  columns,
  rows,
  maxHeight = 380,
}: {
  columns: { key: string; label: string; align?: 'left' | 'right'; format?: (v: unknown, row: Record<string, unknown>) => ReactNode }[];
  rows: Record<string, unknown>[];
  maxHeight?: number;
}) {
  return (
    <div className="overflow-auto border border-white/[0.08]" style={{ maxHeight }} data-lenis-prevent>
      <table className="w-full border-collapse text-[12.5px]">
        <thead className="sticky top-0 z-10 bg-ink-900">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={cn('border-b border-white/[0.1] px-3 py-2.5 font-mono text-[10.5px] font-normal uppercase tracking-[0.12em] text-ink-400', c.align === 'right' ? 'text-right' : 'text-left')}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-white/[0.05] transition-colors hover:bg-white/[0.03]">
              {columns.map((c) => (
                <td key={c.key} className={cn('px-3 py-2 text-ink-200', c.align === 'right' && 'text-right font-mono tabular-nums')}>
                  {c.format ? c.format(r[c.key], r) : (r[c.key] as ReactNode) ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone: Record<string, string> = {
    VERIFIED: '#6fae4f',
    PARTIAL: '#f3c542',
    SPLICED: '#4d6ff0',
    DERIVED: '#24a6a1',
    ILLUSTRATIVE: '#f0663f',
    ESTIMATED: '#f0663f',
    CITED: '#6fae4f',
    'DATA REQUIRED': '#f04a32',
    'USER-SET': '#5fd0c9',
  };
  const c = tone[status] ?? '#8b8d99';
  return (
    <span className="inline-flex items-center gap-1.5 border px-1.5 py-[1px] font-mono text-[9.5px] uppercase tracking-[0.14em]" style={{ color: c, borderColor: `${c}66`, background: `${c}14` }}>
      <span className="h-1 w-1 rounded-full" style={{ background: c }} />
      {status}
    </span>
  );
}

export const fmt = {
  n: (v: number | null | undefined, d = 2) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d })),
  pct: (v: number | null | undefined, d = 1) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : `${v.toFixed(d)}%`),
  pp: (v: number | null | undefined, d = 2) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(d)} pp`),
  inr: (v: number | null | undefined) => {
    if (v === null || v === undefined || !Number.isFinite(v)) return '—';
    if (Math.abs(v) >= 1e7) return `₹${(v / 1e7).toFixed(2)} cr`;
    if (Math.abs(v) >= 1e5) return `₹${(v / 1e5).toFixed(2)} lakh`;
    return `₹${Math.round(v).toLocaleString('en-IN')}`;
  },
  inrFull: (v: number | null | undefined) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : `₹${Math.round(v).toLocaleString('en-IN')}`),
  p: (p: number) => (!Number.isFinite(p) ? 'p n/a' : p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`),
};
