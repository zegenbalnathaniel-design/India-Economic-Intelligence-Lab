import { AnimatePresence, motion, useInView, useSpring } from 'framer-motion';
import { type ReactNode, useEffect, useRef, useState } from 'react';
import { STATUS_STYLE, type DataStatus } from '../../data/types';
import { cn } from '../../lib/format';
import { EASE_OUT, SPRING, useReducedMotionPref } from '../../lib/motion';

/* ------------------------------------------------------------------ *
 * Status badge — the visual grammar of data reliability (spec §46).
 * ------------------------------------------------------------------ */

export function StatusBadge({
  status,
  size = 'sm',
  withLabel = true,
  title,
}: {
  status: DataStatus;
  size?: 'xs' | 'sm';
  withLabel?: boolean;
  title?: string;
}) {
  const s = STATUS_STYLE[status];
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 border font-mono uppercase tracking-[0.14em]',
        size === 'xs' ? 'px-1.5 py-[1px] text-[9px]' : 'px-2 py-0.5 text-2xs',
      )}
      style={{ color: s.fg, background: s.bg, borderColor: s.border }}
      title={title ?? s.description}
    >
      <span aria-hidden className="inline-block h-1 w-1 rounded-full" style={{ background: s.fg }} />
      {withLabel && s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Animated numerals — numbers move so the reader can see causality.
 * ------------------------------------------------------------------ */

export function AnimatedNumber({
  value,
  format,
  className,
  ariaLabel,
}: {
  value: number | null;
  format: (n: number | null) => string;
  className?: string;
  ariaLabel?: string;
}) {
  const reduced = useReducedMotionPref();
  const ref = useRef<HTMLSpanElement>(null);
  const spring = useSpring(value ?? 0, SPRING.readout);

  // The spring is an external system, so an effect is the right place to
  // synchronise with it — but the frames are written straight to the DOM
  // node rather than through state, so an animating number does not
  // re-render the panel around it sixty times a second.
  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (value === null || !Number.isFinite(value)) {
      spring.jump(0);
      node.textContent = format(null);
      return;
    }
    if (reduced) {
      spring.jump(value);
      node.textContent = format(value);
      return;
    }
    spring.set(value);
    return spring.on('change', (v) => {
      node.textContent = format(v);
    });
  }, [value, reduced, spring, format]);

  return (
    <span ref={ref} className={className} data-numeric aria-label={ariaLabel}>
      {format(value)}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Structure
 * ------------------------------------------------------------------ */

export function Panel({
  children,
  className,
  as: As = 'div',
}: {
  children: ReactNode;
  className?: string;
  as?: 'div' | 'section' | 'article' | 'aside';
}) {
  return <As className={cn('lab-panel', className)}>{children}</As>;
}

export function SectionShell({
  id,
  index,
  label,
  title,
  lede,
  children,
  className,
  actions,
}: {
  id?: string;
  index?: string;
  label: string;
  title: ReactNode;
  lede?: ReactNode;
  children?: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id={id} ref={ref} className={cn('relative border-t border-white/[0.07] py-20 md:py-28', className)}>
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <motion.header
          initial={{ opacity: 0, y: 18 }}
          animate={inView ? { opacity: 1, y: 0 } : undefined}
          transition={{ duration: 0.7, ease: EASE_OUT }}
          className="mb-10 md:mb-14"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <div className="flex items-baseline gap-4">
              {index && <span className="label-accent">{index}</span>}
              <span className="label">{label}</span>
            </div>
            {actions}
          </div>
          <h2 className="display mt-5 max-w-4xl text-balance text-[2rem] leading-[1.08] md:text-[3.25rem]">
            {title}
          </h2>
          {lede && (
            <div className="mt-5 max-w-3xl text-[0.95rem] leading-relaxed text-ink-400 text-pretty">{lede}</div>
          )}
        </motion.header>
        {children}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ *
 * Controls
 * ------------------------------------------------------------------ */

export function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format,
  unit,
  hint,
  accent = '#e8933a',
  disabled,
  baselineValue,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (n: number) => void;
  format?: (n: number) => string;
  unit?: string;
  hint?: string;
  accent?: string;
  disabled?: boolean;
  /** Renders a tick at the research baseline so drift from it is visible. */
  baselineValue?: number;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  const basePct =
    baselineValue !== undefined ? ((baselineValue - min) / (max - min)) * 100 : null;
  const id = `sl-${label.replace(/\W+/g, '-').toLowerCase()}`;

  return (
    <div className={cn('group', disabled && 'opacity-40')}>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="label text-ink-400">
          {label}
        </label>
        <span className="metric text-sm" style={{ color: accent }}>
          {format ? format(value) : value}
          {unit && <span className="ml-1 text-ink-500">{unit}</span>}
        </span>
      </div>

      <div className="relative mt-2.5">
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 bg-ink-700" />
        <div
          className="pointer-events-none absolute left-0 top-1/2 h-[2px] -translate-y-1/2 transition-[width] duration-100"
          style={{ width: `${pct}%`, background: accent }}
        />
        {basePct !== null && (
          <span
            className="pointer-events-none absolute top-1/2 h-3 w-px -translate-y-1/2 bg-ink-500"
            style={{ left: `${basePct}%` }}
            title={`Research baseline: ${format ? format(baselineValue!) : baselineValue}`}
          />
        )}
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative z-10 w-full"
          aria-valuetext={format ? format(value) : String(value)}
        />
      </div>
      {hint && <p className="mt-1.5 text-2xs leading-snug text-ink-500">{hint}</p>}
    </div>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  prefix,
  suffix,
  hint,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  step?: number;
  prefix?: string;
  suffix?: string;
  hint?: string;
}) {
  const id = `nf-${label.replace(/\W+/g, '-').toLowerCase()}`;
  return (
    <div>
      <label htmlFor={id} className="label text-ink-400">
        {label}
      </label>
      <div className="mt-1.5 flex items-center gap-0">
        {prefix && (
          <span className="border border-r-0 border-white/[0.09] bg-ink-900 px-2 py-1.5 font-mono text-sm text-ink-500">
            {prefix}
          </span>
        )}
        <input
          id={id}
          type="number"
          className="numfield"
          value={Number.isFinite(value) ? value : ''}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        {suffix && (
          <span className="border border-l-0 border-white/[0.09] bg-ink-900 px-2 py-1.5 font-mono text-sm text-ink-500">
            {suffix}
          </span>
        )}
      </div>
      {hint && <p className="mt-1.5 text-2xs leading-snug text-ink-500">{hint}</p>}
    </div>
  );
}

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label?: string;
  options: { value: T; label: string; title?: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      {label && <span className="label text-ink-400">{label}</span>}
      <div className={cn('flex border border-white/[0.09]', label && 'mt-1.5')} role="group">
        {options.map((o) => {
          const active = o.value === value;
          return (
            <button
              key={o.value}
              type="button"
              title={o.title}
              onClick={() => onChange(o.value)}
              aria-pressed={active}
              className={cn(
                'relative flex-1 px-3 py-1.5 font-mono text-2xs uppercase tracking-[0.14em] transition-colors',
                active ? 'text-ink-950' : 'text-ink-400 hover:text-ink-100',
              )}
            >
              {active && (
                <motion.span
                  layoutId={`seg-${label ?? options.map((x) => x.value).join()}`}
                  className="absolute inset-0 bg-[#e8933a]"
                  transition={SPRING.control}
                />
              )}
              <span className="relative">{o.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Disclosure
 * ------------------------------------------------------------------ */

export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  tone = 'default',
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  tone?: 'default' | 'accent';
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-white/[0.07]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={cn(
          'flex w-full items-center justify-between gap-4 py-3 text-left font-mono text-2xs uppercase tracking-[0.14em] transition-colors',
          tone === 'accent' ? 'text-[#e8933a] hover:text-[#f0a45a]' : 'text-ink-400 hover:text-ink-100',
        )}
      >
        {summary}
        <span aria-hidden className="text-ink-500">
          {open ? '−' : '+'}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: EASE_OUT }}
            className="overflow-hidden"
          >
            <div className="pb-5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Messaging
 * ------------------------------------------------------------------ */

export function Notice({
  tone = 'note',
  title,
  children,
}: {
  tone?: 'note' | 'caution' | 'missing';
  title?: string;
  children: ReactNode;
}) {
  const colour =
    tone === 'caution' ? '#e8933a' : tone === 'missing' ? '#818e96' : '#5b9bd5';
  return (
    <div
      className="border-l-2 bg-ink-900/50 px-4 py-3"
      style={{ borderColor: colour }}
      role={tone === 'caution' ? 'alert' : undefined}
    >
      {title && (
        <p className="font-mono text-2xs uppercase tracking-[0.14em]" style={{ color: colour }}>
          {title}
        </p>
      )}
      <div className={cn('text-[0.8125rem] leading-relaxed text-ink-300', title && 'mt-1.5')}>{children}</div>
    </div>
  );
}

/** Rendered wherever a value genuinely does not exist (spec §52). */
export function Unavailable({ reason }: { reason?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="metric text-ink-600">—</span>
      <span className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-600" title={reason}>
        Data unavailable
      </span>
    </span>
  );
}

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1800);
        } catch {
          setDone(false);
        }
      }}
    >
      {done ? 'Copied' : label}
    </button>
  );
}

export function DownloadButton({
  filename,
  content,
  mime = 'text/csv;charset=utf-8',
  label,
}: {
  filename: string;
  content: () => string;
  mime?: string;
  label: string;
}) {
  return (
    <button
      type="button"
      className="btn"
      onClick={() => {
        const blob = new Blob([content()], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }}
    >
      {label}
    </button>
  );
}
