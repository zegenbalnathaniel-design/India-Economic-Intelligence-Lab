import { AnimatePresence, motion } from 'framer-motion';
import { CornerDownLeft, Search } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { KIND_LABEL, buildRegistry, scoreCommand, type Command } from './registry';

const KIND_COLOUR: Record<string, string> = {
  action: '#e8933a',
  indicator: '#4fae86',
  bank: '#5b9bd5',
  term: '#8b7fd4',
  research: '#e8933a',
  state: '#4aa5a8',
  page: '#818e96',
  event: '#c9a227',
};

/**
 * The dialog holds the query and the highlighted index. It is mounted only
 * while the palette is open, so closing it discards that state rather than
 * requiring an effect to reset it.
 */
function PaletteDialog({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const registry = useMemo(() => buildRegistry(), []);

  const results = useMemo(() => {
    const scored = registry
      .map((c) => ({ c, s: scoreCommand(c, query) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s || a.c.title.localeCompare(b.c.title));
    return scored.slice(0, 40).map((r) => r.c);
  }, [registry, query]);

  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  const run = (c: Command | undefined) => {
    if (!c) return;
    onClose();
    navigate(c.to);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => Math.min(results.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      run(results[active]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-[90] flex items-start justify-center px-4 pt-[12vh]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.16 }}
    >
      <div className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm" onClick={onClose} aria-hidden />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={{ opacity: 0, y: -12, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.99 }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
            className="relative w-full max-w-2xl border border-white/[0.12] bg-ink-900/95 shadow-2xl shadow-black/60"
          >
            <div className="flex items-center gap-3 border-b border-white/[0.09] px-4">
              <Search size={15} className="shrink-0 text-ink-500" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onKeyDown}
                placeholder="Search indicators, banks, research, terms — or type > for commands"
                className="w-full bg-transparent py-3.5 font-mono text-sm text-ink-50 outline-none placeholder:text-ink-600"
                aria-controls="cmd-results"
                aria-activedescendant={results[active] ? `cmd-${results[active].id}` : undefined}
              />
              <kbd className="hidden shrink-0 border border-white/[0.12] px-1.5 py-0.5 font-mono text-[10px] text-ink-500 sm:block">
                ESC
              </kbd>
            </div>

            <div
              ref={listRef}
              id="cmd-results"
              role="listbox"
              className="max-h-[52vh] overflow-y-auto overscroll-contain py-1"
            >
              {results.length === 0 ? (
                <p className="px-4 py-8 text-center text-sm text-ink-500">
                  Nothing in the lab matches “{query}”.
                </p>
              ) : (
                results.map((c, i) => (
                  <button
                    key={c.id}
                    id={`cmd-${c.id}`}
                    data-index={i}
                    role="option"
                    aria-selected={i === active}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => run(c)}
                    className={cn(
                      'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors',
                      i === active ? 'bg-white/[0.055]' : 'hover:bg-white/[0.03]',
                    )}
                  >
                    <span
                      aria-hidden
                      className="h-1 w-1 shrink-0 rounded-full"
                      style={{ background: KIND_COLOUR[c.kind] }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-ink-100">{c.verb ?? c.title}</span>
                      {c.subtitle && (
                        <span className="block truncate text-2xs text-ink-500">{c.subtitle}</span>
                      )}
                    </span>
                    <span
                      className="shrink-0 font-mono text-[9px] uppercase tracking-[0.14em]"
                      style={{ color: KIND_COLOUR[c.kind] }}
                    >
                      {KIND_LABEL[c.kind]}
                    </span>
                    {i === active && <CornerDownLeft size={12} className="shrink-0 text-ink-500" />}
                  </button>
                ))
              )}
            </div>

            <div className="flex items-center justify-between border-t border-white/[0.09] px-4 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-600">
              <span>{results.length} result{results.length === 1 ? '' : 's'}</span>
              <span className="hidden gap-3 sm:flex">
                <span>↑↓ navigate</span>
                <span>↵ open</span>
              </span>
            </div>
      </motion.div>
    </motion.div>
  );
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  return <AnimatePresence>{open && <PaletteDialog onClose={onClose} />}</AnimatePresence>;
}
