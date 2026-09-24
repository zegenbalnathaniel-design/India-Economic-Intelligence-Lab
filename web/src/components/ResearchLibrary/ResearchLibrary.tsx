import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { LIBRARY, RESEARCH_CATEGORIES, type LibraryEntry } from '../../data/research/library';
import { cn, longDate } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';

const STATUS_LABEL: Record<LibraryEntry['status'], string> = {
  published: 'Paper',
  methodology: 'Methodology note',
  'in-preparation': 'In preparation',
};

const STATUS_TONE: Record<LibraryEntry['status'], string> = {
  published: '#e8933a',
  methodology: '#5b9bd5',
  'in-preparation': '#5d6a72',
};

export function ResearchLibrary({ limit }: { limit?: number }) {
  const [category, setCategory] = useState<string | null>(null);

  const entries = useMemo(() => {
    const filtered = category ? LIBRARY.filter((e) => e.category === category) : LIBRARY;
    return limit ? filtered.slice(0, limit) : filtered;
  }, [category, limit]);

  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of LIBRARY) m.set(e.category, (m.get(e.category) ?? 0) + 1);
    return m;
  }, []);

  return (
    <div>
      {!limit && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setCategory(null)}
            aria-pressed={category === null}
            className={cn(
              'border px-2.5 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
              category === null
                ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
            )}
          >
            All <span className="ml-1 text-ink-600">{LIBRARY.length}</span>
          </button>
          {RESEARCH_CATEGORIES.map((c) => {
            const n = counts.get(c) ?? 0;
            return (
              <button
                key={c}
                type="button"
                disabled={n === 0}
                onClick={() => setCategory(category === c ? null : c)}
                aria-pressed={category === c}
                className={cn(
                  'border px-2.5 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
                  n === 0 && 'cursor-not-allowed border-white/[0.05] text-ink-700',
                  n > 0 && category === c && 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]',
                  n > 0 && category !== c && 'border-white/[0.09] text-ink-500 hover:text-ink-200',
                )}
              >
                {c} <span className="ml-1 text-ink-600">{n}</span>
              </button>
            );
          })}
        </div>
      )}

      <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] md:grid-cols-2 xl:grid-cols-3">
        {entries.map((e, i) => {
          const body = (
            <>
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className="font-mono text-2xs uppercase tracking-[0.14em]"
                    style={{ color: STATUS_TONE[e.status] }}
                  >
                    {STATUS_LABEL[e.status]}
                  </span>
                  <span className="label">{e.category}</span>
                </div>

                <h3 className="display mt-3.5 text-[1.375rem] leading-tight">{e.title}</h3>
                <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-400 text-pretty">{e.summary}</p>
                {e.note && (
                  <p className="mt-3 border-l border-white/[0.09] pl-3 text-2xs leading-relaxed text-ink-600">
                    {e.note}
                  </p>
                )}
              </div>

              <div className="mt-6 flex items-end justify-between gap-3 border-t border-white/[0.07] pt-3.5">
                <span className="font-mono text-2xs text-ink-600">
                  {e.date ? longDate(e.date) : 'Not started'}
                  {e.readingMinutes ? ` · ${e.readingMinutes} min` : ''}
                </span>
                {e.to && (
                  <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-[0.14em] text-ink-400 transition-colors group-hover:text-[#e8933a]">
                    Read <ArrowRight size={12} />
                  </span>
                )}
              </div>
            </>
          );
          return (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.45, delay: Math.min(i * 0.04, 0.24), ease: EASE_OUT }}
              className="bg-ink-950"
            >
              {e.to ? (
                <Link to={e.to} className="group flex h-full flex-col justify-between p-5 transition-colors hover:bg-ink-900/70 md:p-6">
                  {body}
                </Link>
              ) : (
                <div className="group flex h-full flex-col justify-between p-5 opacity-70 md:p-6">{body}</div>
              )}
            </motion.div>
          );
        })}
      </div>

      {!limit && (
        <p className="mt-4 max-w-3xl text-2xs leading-relaxed text-ink-600">
          Entries marked “In preparation” are not written. They are listed because a research programme stated
          honestly is more useful than a catalogue padded with placeholders — each one names the data it needs
          and does not have.
        </p>
      )}
    </div>
  );
}
