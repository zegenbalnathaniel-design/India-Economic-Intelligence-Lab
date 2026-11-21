import { AnimatePresence, motion } from 'framer-motion';
import { ArrowDownRight, ArrowRight, ArrowUpRight, X } from 'lucide-react';
import { useState } from 'react';
import { getSource } from '../../data/sources';
import { MACRO_BY_ID, PULSE_ORDER } from '../../data/macro/indicators';
import type { DataPoint } from '../../data/types';
import { cn, indicatorValue, longDate, signed } from '../../lib/format';
import { EASE_OUT, SPRING } from '../../lib/motion';
import { DataProvenance, SourceDiscrepancy } from '../DataProvenance/DataProvenance';
import { Sparkline } from '../charts/Sparkline';
import { AnimatedNumber, Notice, StatusBadge, Unavailable } from '../ui';

function ChangeChip({ change }: { change: DataPoint['change'] }) {
  if (!change) return null;
  const flat = change.value === 0;
  const up = change.value > 0;
  const good = change.better === 'neutral' ? null : up === (change.better === 'up');
  const colour = flat ? '#818e96' : good === null ? '#818e96' : good ? '#4fae86' : '#d3675d';
  const Icon = flat ? ArrowRight : up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className="flex items-center gap-1.5 font-mono text-2xs" style={{ color: colour }}>
      <Icon size={11} />
      {flat ? 'unchanged' : signed(change.value, Math.abs(change.value) < 1 ? 1 : 1, ' pp')}
      <span className="text-ink-600">{change.label}</span>
    </span>
  );
}

function PulseTile({ point, onOpen, index }: { point: DataPoint; onOpen: () => void; index: number }) {
  const source = getSource(point.sourceId);
  const missing = point.value === null;

  return (
    <motion.button
      type="button"
      onClick={onOpen}
      layoutId={`pulse-${point.id}`}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.5, delay: Math.min(index * 0.035, 0.3), ease: EASE_OUT }}
      className="group relative flex min-h-[188px] flex-col justify-between border border-white/[0.07] bg-ink-900/40 p-5 text-left transition-colors hover:border-white/[0.16] hover:bg-ink-900/70"
      aria-label={`${point.indicator}. Open detail.`}
    >
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-[#e8933a] transition-transform duration-300 group-hover:scale-x-100"
      />

      <div className="flex items-start justify-between gap-3">
        <span className="label max-w-[70%] leading-snug text-ink-400">{point.indicator}</span>
        <StatusBadge status={point.status} size="xs" withLabel={false} />
      </div>

      <div className="mt-4">
        {missing ? (
          <Unavailable reason={point.note} />
        ) : (
          <div className="flex items-baseline gap-1.5">
            <AnimatedNumber
              value={point.value}
              format={(n) => indicatorValue(n, point.decimals)}
              className="metric text-[2.125rem] leading-none"
            />
            <span className="font-mono text-xs text-ink-500">{point.unitShort ?? point.unit}</span>
          </div>
        )}
        <div className="mt-2 h-8">
          {point.series && point.series.length > 1 && (
            <Sparkline series={point.series} colour={missing ? '#5d6a72' : '#e8933a'} />
          )}
        </div>
      </div>

      <div className="mt-3 space-y-1.5">
        <ChangeChip change={point.change} />
        <div className="flex items-center justify-between gap-2 border-t border-white/[0.05] pt-2">
          <span className="font-mono text-2xs text-ink-600">{point.period.label}</span>
          <span className="font-mono text-2xs uppercase tracking-[0.1em] text-ink-600">{source.name}</span>
        </div>
      </div>
    </motion.button>
  );
}

function DetailPanel({ point, onClose }: { point: DataPoint; onClose: () => void }) {
  const source = getSource(point.sourceId);
  return (
    <motion.div
      className="fixed inset-0 z-[80] flex items-end justify-center sm:items-center sm:p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-ink-950/85 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <motion.div
        layoutId={`pulse-${point.id}`}
        transition={SPRING.surface}
        role="dialog"
        aria-modal="true"
        aria-label={point.indicator}
        className="relative max-h-[88vh] w-full max-w-3xl overflow-y-auto border border-white/[0.12] bg-ink-900 p-6 sm:p-8"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-ink-500 transition-colors hover:text-ink-100"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        <div className="flex flex-wrap items-center gap-3">
          <span className="label">{source.name}</span>
          <StatusBadge status={point.status} />
        </div>

        <h3 className="display mt-3 text-3xl">{point.indicator}</h3>

        <div className="mt-5 flex flex-wrap items-end gap-x-6 gap-y-3">
          {point.value === null ? (
            <Unavailable reason={point.note} />
          ) : (
            <div className="flex items-baseline gap-2">
              <span className="metric text-5xl leading-none">{indicatorValue(point.value, point.decimals)}</span>
              <span className="font-mono text-sm text-ink-500">{point.unit}</span>
            </div>
          )}
          <div className="font-mono text-2xs text-ink-500">
            <p className="uppercase tracking-[0.14em] text-ink-600">Reporting period</p>
            <p className="mt-0.5 text-ink-200">{point.period.label}</p>
          </div>
          {point.publicationDate && (
            <div className="font-mono text-2xs text-ink-500">
              <p className="uppercase tracking-[0.14em] text-ink-600">Published</p>
              <p className="mt-0.5 text-ink-200">{longDate(point.publicationDate)}</p>
            </div>
          )}
        </div>

        {point.change && (
          <div className="mt-4">
            <ChangeChip change={point.change} />
          </div>
        )}

        {point.series && point.series.length > 1 && (
          <div className="mt-6 border border-white/[0.07] bg-ink-950/50 p-4">
            <p className="label mb-3">Historical series</p>
            <Sparkline series={point.series} colour="#e8933a" height={96} showAxis />
          </div>
        )}

        {point.analysis && (
          <div className="mt-6">
            <p className="label mb-2">Reading</p>
            <p className="text-[0.9375rem] leading-relaxed text-ink-200 text-pretty">{point.analysis}</p>
          </div>
        )}

        {point.vintages && point.vintages.length > 1 && (
          <div className="mt-6">
            <p className="label mb-2">Official vintages</p>
            <div className="border border-white/[0.07]">
              {point.vintages.map((v, i) => (
                <div
                  key={v.label}
                  className={cn(
                    'flex flex-wrap items-baseline justify-between gap-2 px-3 py-2',
                    i > 0 && 'border-t border-white/[0.05]',
                    i === point.vintages!.length - 1 && 'bg-[#e8933a]/[0.05]',
                  )}
                >
                  <span className="text-[0.8125rem] text-ink-200">{v.label}</span>
                  <span className="flex items-baseline gap-3">
                    <span className="font-mono text-2xs text-ink-600">{longDate(v.releasedOn)}</span>
                    <span className="metric text-sm">{v.value}</span>
                  </span>
                  {v.note && <p className="w-full text-2xs text-ink-500">{v.note}</p>}
                </div>
              ))}
            </div>
            <p className="mt-2 text-2xs text-ink-600">
              The latest vintage is used throughout the lab unless a paper explicitly requires an earlier one.
            </p>
          </div>
        )}

        {point.discrepancy && (
          <div className="mt-6">
            <SourceDiscrepancy d={point.discrepancy} />
          </div>
        )}

        {point.note && !point.discrepancy && (
          <div className="mt-6">
            <Notice title="Note">{point.note}</Notice>
          </div>
        )}

        <div className="mt-6">
          <DataProvenance point={point} defaultOpen />
        </div>
      </motion.div>
    </motion.div>
  );
}

export function EconomicPulse({ ids = PULSE_ORDER }: { ids?: string[] }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const points = ids.map((id) => MACRO_BY_ID[id]).filter(Boolean);
  const open = openId ? MACRO_BY_ID[openId] : null;

  return (
    <>
      <div className="grid grid-cols-1 gap-px border border-white/[0.07] bg-white/[0.07] sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {points.map((p, i) => (
          <PulseTile key={p.id} point={p} index={i} onOpen={() => setOpenId(p.id)} />
        ))}
      </div>
      <AnimatePresence>{open && <DetailPanel point={open} onClose={() => setOpenId(null)} />}</AnimatePresence>
    </>
  );
}
