import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TIMELINE } from '../../data/timeline/events';
import { cn } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { StatusBadge } from '../ui';

export function EconomicTimeline({ initialId }: { initialId?: string }) {
  const [openId, setOpenId] = useState<string | null>(initialId ?? TIMELINE[TIMELINE.length - 1].id);

  return (
    <div>
      {/* Rail */}
      <div className="relative">
        <div className="absolute inset-x-0 top-[13px] h-px bg-white/[0.09]" aria-hidden />
        <ol className="relative flex snap-x snap-mandatory gap-2 overflow-x-auto pb-4 no-scrollbar">
          {TIMELINE.map((e) => {
            const active = e.id === openId;
            return (
              <li key={e.id} className="min-w-[128px] flex-1 snap-start">
                <button
                  type="button"
                  onClick={() => setOpenId(active ? null : e.id)}
                  aria-expanded={active}
                  className="group block w-full text-left"
                >
                  <span className="relative block h-[27px]">
                    <motion.span
                      className={cn(
                        'absolute left-0 top-[8px] block h-2.5 w-2.5 rounded-full border transition-colors',
                        active
                          ? 'border-[#e8933a] bg-[#e8933a]'
                          : 'border-ink-600 bg-ink-950 group-hover:border-ink-400',
                      )}
                      layout
                    />
                  </span>
                  <span
                    className={cn(
                      'mt-1 block font-mono text-xs transition-colors',
                      active ? 'text-[#e8933a]' : 'text-ink-500 group-hover:text-ink-300',
                    )}
                  >
                    {e.year}
                  </span>
                  <span
                    className={cn(
                      'mt-0.5 block text-[0.8125rem] leading-snug transition-colors',
                      active ? 'text-ink-100' : 'text-ink-400 group-hover:text-ink-200',
                    )}
                  >
                    {e.title}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      <AnimatePresence mode="wait">
        {openId && (
          <motion.article
            key={openId}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: EASE_OUT }}
            className="mt-2 border border-white/[0.09] bg-ink-900/40 p-5 md:p-7"
          >
            {(() => {
              const e = TIMELINE.find((x) => x.id === openId)!;
              return (
                <>
                  <div className="flex flex-wrap items-baseline gap-4">
                    <span className="metric text-3xl text-[#e8933a]">{e.year}</span>
                    <h3 className="display text-2xl">{e.title}</h3>
                  </div>
                  <p className="mt-1.5 font-mono text-2xs uppercase tracking-[0.14em] text-ink-500">{e.kicker}</p>

                  <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
                    <div className="space-y-4">
                      <div>
                        <p className="label mb-1.5">Context</p>
                        <p className="text-[0.9375rem] leading-relaxed text-ink-200 text-pretty">{e.context}</p>
                      </div>
                      <div>
                        <p className="label mb-1.5">What the data supports</p>
                        <p className="text-[0.9375rem] leading-relaxed text-ink-300 text-pretty">{e.consequence}</p>
                      </div>
                    </div>

                    <div className="space-y-px border border-white/[0.07] bg-white/[0.07]">
                      {e.indicators.map((ind) => (
                        <div key={ind.label} className="bg-ink-900 p-3">
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="label">{ind.label}</span>
                            <StatusBadge status={ind.status} size="xs" withLabel={false} />
                          </div>
                          <p
                            className={cn(
                              'metric mt-1.5 text-base',
                              ind.status === 'unavailable' && 'text-ink-600',
                            )}
                            data-numeric
                          >
                            {ind.value}
                          </p>
                          {ind.note && <p className="mt-1 text-2xs leading-snug text-ink-600">{ind.note}</p>}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/[0.07] pt-4">
                    {e.relatedResearch && (
                      <Link to={e.relatedResearch.to} className="btn">
                        {e.relatedResearch.label} <ArrowRight size={12} />
                      </Link>
                    )}
                    {e.relatedIndicator && (
                      <Link to={`/data?indicator=${e.relatedIndicator}`} className="btn">
                        Related indicator <ArrowRight size={12} />
                      </Link>
                    )}
                    <a href={e.sourceUrl} target="_blank" rel="noreferrer noopener" className="btn">
                      {e.sourceLabel} <ExternalLink size={12} />
                    </a>
                  </div>
                </>
              );
            })()}
          </motion.article>
        )}
      </AnimatePresence>
    </div>
  );
}
