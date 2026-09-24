import { Link } from 'react-router-dom';
import { RETRIEVED_ON, SOURCES } from '../../data/sources';
import { longDate } from '../../lib/format';

const COLUMNS = [
  {
    title: 'Research',
    links: [
      { label: 'The Great Indian Promise', to: '/research/the-great-indian-promise' },
      { label: 'Research library', to: '/research' },
      { label: 'BFPI methodology', to: '/models/bfpi/methodology' },
    ],
  },
  {
    title: 'Models',
    links: [
      { label: 'Figure 2 — Wealth', to: '/models/figure-2' },
      { label: 'BFPI — Banking', to: '/models/bfpi' },
      { label: 'Experiments', to: '/experiments' },
    ],
  },
  {
    title: 'Data',
    links: [
      { label: 'Macro indicators', to: '/data' },
      { label: 'Source registry', to: '/data#provenance' },
      { label: 'Glossary', to: '/glossary' },
    ],
  },
  {
    title: 'India',
    links: [
      { label: 'Economic map', to: '/india' },
      { label: 'Timeline', to: '/india#timeline' },
      { label: 'About IEIL', to: '/about' },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-white/[0.09] bg-ink-950">
      <div className="mx-auto max-w-[1400px] px-5 py-14 md:px-10 md:py-20">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_2fr]">
          <div>
            <p className="font-mono text-sm tracking-[0.18em] text-ink-50">IEIL</p>
            <p className="mt-2 font-mono text-2xs uppercase tracking-[0.18em] text-ink-500">
              India Economics Intelligence Lab
            </p>
            <p className="mt-5 max-w-sm font-display text-lg leading-snug text-ink-300">
              Don’t just read economics. Experiment with it.
            </p>
            <p className="mt-5 max-w-md text-[0.8125rem] leading-relaxed text-ink-500">
              An independent research laboratory. Every number carries its source, its reporting period and its
              status; every model shows its working; every assumption can be overwritten by the reader.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {COLUMNS.map((c) => (
              <div key={c.title}>
                <p className="label">{c.title}</p>
                <ul className="mt-3.5 space-y-2">
                  {c.links.map((l) => (
                    <li key={l.to + l.label}>
                      <Link
                        to={l.to}
                        className="text-[0.8125rem] text-ink-400 transition-colors hover:text-[#e8933a]"
                      >
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 border-t border-white/[0.07] pt-6">
          <p className="label mb-3">Primary sources</p>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {Object.values(SOURCES)
              .filter((s) => s.tier !== 'issuer')
              .map((s) => (
                <a
                  key={s.id}
                  href={s.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="font-mono text-2xs text-ink-600 transition-colors hover:text-ink-300"
                  title={s.fullName}
                >
                  {s.name}
                </a>
              ))}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-baseline justify-between gap-4 border-t border-white/[0.07] pt-6">
          <p className="max-w-2xl text-2xs leading-relaxed text-ink-600">
            BFPI is an original composite index constructed for analytical purposes. It is not an official RBI
            measure or banking-sector rating. Nothing on this site is financial advice, and no model output is a
            forecast.
          </p>
          <p className="font-mono text-2xs text-ink-700">Data retrieved {longDate(RETRIEVED_ON)}</p>
        </div>
      </div>
    </footer>
  );
}
