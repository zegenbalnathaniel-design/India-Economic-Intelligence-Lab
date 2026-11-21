import { motion, useScroll, useSpring } from 'framer-motion';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { Block, Citation, Paper, Section } from '../../data/research/types';
import { cn, longDate } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { Figure2Lab } from '../Figure2Lab/Figure2Lab';

/* ---------------------------------------------------------------- *
 * Inline citations: [12] renders as a link into the reference list.
 * ---------------------------------------------------------------- */

function renderInline(text: string, citations: Citation[], onCite: (n: number) => void): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /\[(\d+)\]|<em>(.*?)<\/em>/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[1]) {
      const n = Number(m[1]);
      const cite = citations.find((c) => c.n === n);
      parts.push(
        <button
          key={`c-${key++}`}
          type="button"
          onClick={() => onCite(n)}
          title={cite ? `${cite.publisher} (${cite.year})` : undefined}
          className="mx-[1px] align-super font-mono text-[0.65em] text-[#e8933a] transition-colors hover:text-[#f0a45a]"
        >
          [{n}]
        </button>,
      );
    } else if (m[2]) {
      parts.push(
        <em key={`e-${key++}`} className="italic text-ink-100">
          {m[2]}
        </em>,
      );
    }
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function BlockView({
  block,
  citations,
  onCite,
}: {
  block: Block;
  citations: Citation[];
  onCite: (n: number) => void;
}) {
  switch (block.kind) {
    case 'lead':
      return (
        <p className="font-display text-[1.25rem] leading-[1.6] text-ink-100 text-pretty first-letter:float-left first-letter:mr-2 first-letter:mt-1 first-letter:font-display first-letter:text-[3.25rem] first-letter:leading-[0.82] first-letter:text-[#e8933a]">
          {renderInline(block.text, citations, onCite)}
        </p>
      );
    case 'p':
      return <p className="prose-research text-pretty">{renderInline(block.text, citations, onCite)}</p>;
    case 'h3':
      return <h3 className="display mt-10 text-[1.375rem] leading-snug">{block.text}</h3>;
    case 'list':
      return (
        <ul className="my-2 space-y-3">
          {block.items.map((it, i) => (
            <li key={i} className="flex gap-3">
              <span aria-hidden className="mt-[0.7em] h-px w-3 shrink-0 bg-[#e8933a]" />
              <span className="font-display text-[1rem] leading-[1.7] text-ink-300 text-pretty">
                {renderInline(it, citations, onCite)}
              </span>
            </li>
          ))}
        </ul>
      );
    case 'equation':
      return (
        <figure className="my-6 border-y border-white/[0.09] py-5 text-center">
          <p className="metric text-lg text-ink-50">{block.ascii}</p>
          {block.caption && (
            <figcaption className="mx-auto mt-3 max-w-lg text-2xs leading-relaxed text-ink-500">
              {block.caption}
            </figcaption>
          )}
        </figure>
      );
    case 'callout':
      return (
        <aside
          className="my-6 border-l-2 bg-ink-900/40 px-5 py-4"
          style={{ borderColor: block.tone === 'caution' ? '#e8933a' : '#5b9bd5' }}
        >
          <p
            className="font-mono text-2xs uppercase tracking-[0.14em]"
            style={{ color: block.tone === 'caution' ? '#e8933a' : '#5b9bd5' }}
          >
            {block.title}
          </p>
          <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-200 text-pretty">
            {renderInline(block.text, citations, onCite)}
          </p>
        </aside>
      );
    case 'quote':
      return (
        <blockquote className="my-6 border-l-2 border-[#e8933a] pl-5">
          <p className="font-display text-[1.375rem] leading-[1.45] text-ink-50 text-pretty">{block.text}</p>
          {block.attribution && (
            <cite className="mt-2 block font-mono text-2xs not-italic text-ink-500">{block.attribution}</cite>
          )}
        </blockquote>
      );
    case 'table':
      return (
        <figure className="my-6">
          <div className="overflow-x-auto border border-white/[0.09]">
            <table className="w-full min-w-[520px] border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.09] bg-ink-900/60">
                  {block.head.map((h) => (
                    <th key={h} className="label px-3 py-2.5 font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {block.rows.map((r, i) => (
                  <tr key={i} className="border-b border-white/[0.04] last:border-0">
                    {r.map((c, j) => (
                      <td
                        key={j}
                        className={cn(
                          'px-3 py-2 text-[0.8125rem]',
                          j === 1 ? 'metric text-ink-100' : 'text-ink-300',
                          j === 2 && 'font-mono text-2xs uppercase tracking-[0.1em]',
                        )}
                        style={
                          j === 2
                            ? {
                                color:
                                  c === 'OBSERVED'
                                    ? '#4fae86'
                                    : c === 'DERIVED'
                                      ? '#4aa5a8'
                                      : c === 'ASSUMPTION'
                                        ? '#e8933a'
                                        : undefined,
                              }
                            : undefined
                        }
                      >
                        {j === 3 ? renderInline(c, citations, onCite) : c}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {block.caption && (
            <figcaption className="mt-2.5 text-2xs leading-relaxed text-ink-500">{block.caption}</figcaption>
          )}
        </figure>
      );
    case 'link':
      return (
        <Link to={block.to} className="my-5 block border border-white/[0.09] p-4 transition-colors hover:border-[#e8933a]/40 hover:bg-ink-900/50">
          <span className="flex items-center gap-2 font-mono text-2xs uppercase tracking-[0.14em] text-[#e8933a]">
            {block.label}
          </span>
          {block.sublabel && <span className="mt-1.5 block text-[0.8125rem] text-ink-400">{block.sublabel}</span>}
        </Link>
      );
    case 'figure':
      return null; // handled by SectionView, which breaks out of the reading column
    default:
      return null;
  }
}

function SectionView({
  section,
  citations,
  onCite,
}: {
  section: Section;
  citations: Citation[];
  onCite: (n: number) => void;
}) {
  return (
    <section id={section.id} className="scroll-mt-24 border-t border-white/[0.07] py-12 first:border-0 md:py-16">
      <div className="mx-auto max-w-reading px-5 md:px-0">
        <h2 className="display text-[1.75rem] leading-tight md:text-[2.25rem]">{section.title}</h2>
      </div>

      <div className="mt-7 space-y-5">
        {section.blocks.map((b, i) => {
          if (b.kind === 'figure') {
            return (
              <figure key={i} className="my-10 w-full">
                <div className="mx-auto max-w-[1400px] px-5 md:px-10">
                  <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
                    <span className="label-accent">{b.title} — interactive</span>
                    <Link
                      to="/models/figure-2"
                      className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-400 transition-colors hover:text-[#e8933a]"
                    >
                      Open in the Model Lab →
                    </Link>
                  </div>
                  <Figure2Lab compact />
                  <figcaption className="mx-auto mt-3 max-w-3xl text-2xs leading-relaxed text-ink-500">
                    {b.caption}
                  </figcaption>
                </div>
              </figure>
            );
          }
          return (
            <div key={i} className="mx-auto max-w-reading px-5 md:px-0">
              <BlockView block={b} citations={citations} onCite={onCite} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function ResearchReader({ paper }: { paper: Paper }) {
  const [activeId, setActiveId] = useState(paper.sections[0].id);
  const [highlightCite, setHighlightCite] = useState<number | null>(null);
  const refsRef = useRef<HTMLElement>(null);
  const articleRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({ target: articleRef, offset: ['start start', 'end end'] });
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 28, mass: 0.4 });

  const navItems = useMemo(
    () => [...paper.sections.map((s) => ({ id: s.id, label: s.navLabel })), { id: 'references', label: 'References' }],
    [paper],
  );

  useEffect(() => {
    const ids = navItems.map((n) => n.id);
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { rootMargin: '-96px 0px -60% 0px', threshold: 0 },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [navItems]);

  const goToCitation = (n: number) => {
    setHighlightCite(n);
    document.getElementById(`ref-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => setHighlightCite(null), 2400);
  };

  return (
    <div>
      <motion.div
        className="fixed inset-x-0 top-0 z-[60] h-px origin-left bg-[#e8933a]"
        style={{ scaleX: progress }}
        aria-hidden
      />

      {/* -------------------------- Masthead -------------------------- */}
      <header className="border-b border-white/[0.07] pt-28 md:pt-36">
        <div className="mx-auto max-w-[1400px] px-5 pb-14 md:px-10">
          <div className="flex flex-wrap items-center gap-3">
            <span className="label-accent">Research</span>
            <span className="label">{paper.category}</span>
            <span className="label">{paper.readingMinutes} min read</span>
          </div>

          <h1 className="display mt-7 max-w-[18ch] text-balance text-[2.5rem] leading-[1.03] md:text-[4.5rem]">
            {paper.title}
          </h1>
          <p className="mt-6 max-w-[62ch] font-display text-[1.25rem] leading-snug text-ink-300 text-pretty">
            {paper.subtitle}
          </p>

          <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 border-t border-white/[0.07] pt-5">
            <div>
              <p className="label">Author</p>
              <p className="mt-1 text-[0.8125rem] text-ink-200">{paper.author}</p>
            </div>
            <div>
              <p className="label">Affiliation</p>
              <p className="mt-1 text-[0.8125rem] text-ink-200">{paper.affiliation}</p>
            </div>
            <div>
              <p className="label">Published</p>
              <p className="mt-1 text-[0.8125rem] text-ink-200">{longDate(paper.date)}</p>
            </div>
            <div className="ml-auto flex items-end gap-2">
              <Link to="/models/figure-2" className="btn btn-primary">
                Explore Figure 2 <ArrowRight size={12} />
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1400px] px-0 md:px-10">
        <div className="grid gap-10 lg:grid-cols-[210px_minmax(0,1fr)]">
          {/* ------------------------ Navigator ------------------------ */}
          <aside className="hidden lg:block">
            <nav aria-label="Article contents" className="sticky top-24 py-14">
              <p className="label mb-4">Article</p>
              <ul className="space-y-0.5 border-l border-white/[0.09]">
                {navItems.map((n) => {
                  const active = n.id === activeId;
                  return (
                    <li key={n.id} className="relative">
                      {active && (
                        <motion.span
                          layoutId="reader-marker"
                          className="absolute -left-px top-0 h-full w-px bg-[#e8933a]"
                        />
                      )}
                      <a
                        href={`#${n.id}`}
                        onClick={(e) => {
                          e.preventDefault();
                          document.getElementById(n.id)?.scrollIntoView({ behavior: 'smooth' });
                        }}
                        className={cn(
                          'block py-1.5 pl-3 text-[0.8125rem] transition-colors',
                          active ? 'text-ink-50' : 'text-ink-500 hover:text-ink-200',
                        )}
                      >
                        {n.label}
                      </a>
                    </li>
                  );
                })}
              </ul>

              <div className="mt-6 border-t border-white/[0.07] pt-4">
                <Link
                  to="/models/figure-2"
                  className="block font-mono text-2xs uppercase leading-relaxed tracking-[0.14em] text-ink-400 transition-colors hover:text-[#e8933a]"
                >
                  Figure 2 model →
                </Link>
                <Link
                  to="/models/bfpi/methodology"
                  className="mt-2 block font-mono text-2xs uppercase leading-relaxed tracking-[0.14em] text-ink-400 transition-colors hover:text-[#e8933a]"
                >
                  BFPI methodology →
                </Link>
              </div>
            </nav>
          </aside>

          {/* ------------------------- Article ------------------------- */}
          <div ref={articleRef}>
            {/* Abstract & question */}
            <section className="py-12 md:py-16">
              <div className="mx-auto max-w-reading px-5 md:px-0">
                <p className="label mb-3">Abstract</p>
                <p className="font-display text-[1.0625rem] leading-[1.75] text-ink-200 text-pretty">
                  {paper.abstract}
                </p>

                <div className="mt-8 border-l-2 border-[#e8933a] pl-5">
                  <p className="label mb-2">Research question</p>
                  <p className="font-display text-[1.125rem] leading-snug text-ink-100 text-pretty">
                    {paper.question}
                  </p>
                </div>
              </div>
            </section>

            {paper.sections.map((s) => (
              <SectionView key={s.id} section={s} citations={paper.citations} onCite={goToCitation} />
            ))}

            {/* ------------------------ References ------------------------ */}
            <section id="references" ref={refsRef} className="scroll-mt-24 border-t border-white/[0.07] py-12 md:py-16">
              <div className="mx-auto max-w-reading px-5 md:px-0">
                <h2 className="display text-[1.75rem] leading-tight md:text-[2.25rem]">References</h2>
                <ol className="mt-7 space-y-4">
                  {paper.citations.map((c) => (
                    <li
                      key={c.n}
                      id={`ref-${c.n}`}
                      className={cn(
                        'scroll-mt-32 border-l-2 pl-4 transition-colors duration-500',
                        highlightCite === c.n ? 'border-[#e8933a] bg-[#e8933a]/[0.06]' : 'border-white/[0.09]',
                      )}
                    >
                      <div className="flex gap-3">
                        <span className="font-mono text-2xs text-[#e8933a]">[{c.n}]</span>
                        <div>
                          <p className="text-[0.875rem] leading-relaxed text-ink-200">{c.text}</p>
                          <p className="mt-1.5 flex flex-wrap items-center gap-2 font-mono text-2xs text-ink-500">
                            <span>{c.publisher}</span>
                            <span className="text-ink-700">·</span>
                            <span>{c.year}</span>
                            <a
                              href={c.url}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="inline-flex items-center gap-1 text-ink-400 transition-colors hover:text-[#e8933a]"
                            >
                              Open source <ExternalLink size={10} />
                            </a>
                          </p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>

                <div className="mt-10 flex flex-wrap gap-2 border-t border-white/[0.07] pt-6">
                  <Link to="/models/figure-2" className="btn btn-primary">
                    Explore this figure interactively <ArrowRight size={12} />
                  </Link>
                  <Link to="/research" className="btn">
                    Research library <ArrowRight size={12} />
                  </Link>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

export { EASE_OUT };
