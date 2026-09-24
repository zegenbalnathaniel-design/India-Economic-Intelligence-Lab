import { AnimatePresence, motion } from 'framer-motion';
import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { GLOSSARY, GLOSSARY_CATEGORIES, type GlossaryTerm } from '../../data/glossary/terms';
import { cn } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';

export function Glossary({ initialTerm }: { initialTerm?: string }) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(initialTerm ?? null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return GLOSSARY.filter((t) => {
      if (category && t.category !== category) return false;
      if (!q) return true;
      return [t.term, t.abbreviation ?? '', t.short, t.full, t.category].join(' ').toLowerCase().includes(q);
    });
  }, [query, category]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-[240px] flex-1 items-center gap-2.5 border border-white/[0.09] bg-ink-950 px-3">
          <Search size={14} className="text-ink-600" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the glossary"
            aria-label="Search the glossary"
            className="w-full bg-transparent py-2.5 font-mono text-sm text-ink-100 outline-none placeholder:text-ink-600"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setCategory(null)}
            aria-pressed={category === null}
            className={cn(
              'border px-2 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
              category === null
                ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
            )}
          >
            All
          </button>
          {GLOSSARY_CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(category === c ? null : c)}
              aria-pressed={category === c}
              className={cn(
                'border px-2 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
                category === c
                  ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                  : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
              )}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 border border-white/[0.09]">
        {results.length === 0 ? (
          <p className="p-8 text-center text-sm text-ink-500">No term matches “{query}”.</p>
        ) : (
          results.map((t) => <TermRow key={t.id} term={t} open={openId === t.id} onToggle={() => setOpenId(openId === t.id ? null : t.id)} />)
        )}
      </div>
    </div>
  );
}

function TermRow({ term, open, onToggle }: { term: GlossaryTerm; open: boolean; onToggle: () => void }) {
  return (
    <div className="border-b border-white/[0.05] last:border-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-start justify-between gap-4 px-4 py-3.5 text-left transition-colors hover:bg-white/[0.02]"
      >
        <span className="min-w-0">
          <span className="flex flex-wrap items-baseline gap-2.5">
            <span className="text-[0.9375rem] text-ink-100">{term.term}</span>
            {term.abbreviation && (
              <span className="font-mono text-2xs uppercase tracking-[0.14em] text-[#e8933a]">
                {term.abbreviation}
              </span>
            )}
            <span className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-600">{term.category}</span>
          </span>
          {!open && <span className="mt-1 block text-[0.8125rem] leading-snug text-ink-500">{term.short}</span>}
        </span>
        <span aria-hidden className="shrink-0 pt-1 text-ink-600">
          {open ? '−' : '+'}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.26, ease: EASE_OUT }}
            className="overflow-hidden"
          >
            <div className="space-y-3 px-4 pb-5">
              <p className="max-w-reading text-[0.9375rem] leading-relaxed text-ink-200 text-pretty">{term.full}</p>

              {term.formula && (
                <pre className="overflow-x-auto border border-white/[0.07] bg-ink-950 px-3 py-2.5 font-mono text-xs text-ink-200">
                  {term.formula.ascii}
                </pre>
              )}

              {term.caution && (
                <p className="border-l-2 border-[#e8933a] pl-3 text-[0.8125rem] leading-relaxed text-ink-400">
                  <span className="font-mono text-2xs uppercase tracking-[0.14em] text-[#e8933a]">Caution · </span>
                  {term.caution}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-2 pt-1">
                {term.sourceUrl && term.sourceUrl.startsWith('/') && (
                  <Link to={term.sourceUrl} className="btn">
                    {term.sourceLabel}
                  </Link>
                )}
                {term.related?.map((r) => {
                  const rel = GLOSSARY.find((t) => t.id === r);
                  if (!rel) return null;
                  return (
                    <span key={r} className="font-mono text-2xs text-ink-600">
                      see also <span className="text-ink-400">{rel.term}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
