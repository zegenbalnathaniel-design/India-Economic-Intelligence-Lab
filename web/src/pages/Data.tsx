import { ExternalLink } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AUDIT_LOG } from '../data/audit';
import { MACRO_BY_ID, MACRO_INDICATORS } from '../data/macro/indicators';
import { RETRIEVAL_NOTE, RETRIEVED_ON, SOURCES, SOURCE_TIER_LABEL, getSource } from '../data/sources';
import { STATUS_STYLE, type DataStatus } from '../data/types';
import { BankExplorer } from '../components/BankExplorer/BankExplorer';
import { Sparkline } from '../components/charts/Sparkline';
import { DataProvenance } from '../components/DataProvenance/DataProvenance';
import { IndiaMap } from '../components/IndiaMap/IndiaMap';
import { Notice, StatusBadge, Unavailable } from '../components/ui';
import { cn, indicatorValue, longDate, number } from '../lib/format';
import { PageHeader } from './PageHeader';

type Tab = 'macro' | 'banking' | 'states';

export function Data() {
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>('macro');
  const selectedId = params.get('indicator') ?? MACRO_INDICATORS[0].id;
  const selected = MACRO_BY_ID[selectedId] ?? MACRO_INDICATORS[0];

  const statusCounts = useMemo(() => {
    const m = new Map<DataStatus, number>();
    for (const d of MACRO_INDICATORS) m.set(d.status, (m.get(d.status) ?? 0) + 1);
    return m;
  }, []);

  return (
    <>
      <PageHeader
        label="India Data Explorer"
        title="Every number, with its paperwork"
        lede={
          <>
            An indicator without a source, a period and a status is not evidence. This explorer carries all three
            on every value, preserves reporting periods exactly as the publisher writes them, and shows gaps as
            gaps.
          </>
        }
      />

      <div className="mx-auto max-w-[1400px] px-5 py-10 md:px-10 md:py-14">
        <div className="flex flex-wrap gap-1.5">
          {(
            [
              ['macro', 'Macro'],
              ['banking', 'Banking'],
              ['states', 'States'],
            ] as [Tab, string][]
          ).map(([t, label]) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              aria-pressed={tab === t}
              className={cn(
                'border px-3 py-1.5 font-mono text-2xs uppercase tracking-[0.14em] transition-colors',
                tab === t
                  ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                  : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'macro' && (
          <div className="mt-7 grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[300px_minmax(0,1fr)]">
            <nav className="bg-ink-900/60 p-1" aria-label="Indicators">
              {MACRO_INDICATORS.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setParams({ indicator: d.id })}
                  aria-current={d.id === selected.id}
                  className={cn(
                    'flex w-full items-center justify-between gap-2 border-l-2 px-3 py-2.5 text-left transition-colors',
                    d.id === selected.id
                      ? 'border-[#e8933a] bg-white/[0.04]'
                      : 'border-transparent hover:bg-white/[0.02]',
                  )}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[0.8125rem] text-ink-200">{d.indicator}</span>
                    <span className="block font-mono text-2xs text-ink-600">{d.period.label}</span>
                  </span>
                  <span className="metric shrink-0 text-xs text-ink-400" data-numeric>
                    {indicatorValue(d.value, d.decimals)}
                  </span>
                </button>
              ))}
            </nav>

            <div className="bg-ink-950 p-5 md:p-7">
              <div className="flex flex-wrap items-center gap-3">
                <span className="label">{getSource(selected.sourceId).name}</span>
                <StatusBadge status={selected.status} />
              </div>
              <h2 className="display mt-3 text-[1.75rem] md:text-[2.25rem]">{selected.indicator}</h2>

              <div className="mt-5 flex flex-wrap items-end gap-x-8 gap-y-4">
                {selected.value === null ? (
                  <Unavailable reason={selected.note} />
                ) : (
                  <span className="flex items-baseline gap-2">
                    <span className="metric text-[3rem] leading-none">
                      {indicatorValue(selected.value, selected.decimals)}
                    </span>
                    <span className="font-mono text-sm text-ink-500">{selected.unit}</span>
                  </span>
                )}
                <div>
                  <p className="label">Reporting period</p>
                  <p className="mt-1 font-mono text-sm text-ink-200">{selected.period.label}</p>
                </div>
                <div>
                  <p className="label">Published</p>
                  <p className="mt-1 font-mono text-sm text-ink-200">{longDate(selected.publicationDate)}</p>
                </div>
              </div>

              {selected.series && selected.series.length > 1 && (
                <div className="mt-7 border border-white/[0.07] bg-ink-900/40 p-4">
                  <p className="label mb-3">Historical series — gaps are shown as gaps</p>
                  <Sparkline series={selected.series} height={140} showAxis />
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                    {selected.series.map((s) => (
                      <span key={s.periodLabel} className="font-mono text-2xs text-ink-600">
                        {s.periodLabel}{' '}
                        <span className={s.value === null ? 'text-ink-700' : 'text-ink-300'}>
                          {s.value === null ? 'n/a' : number(s.value, 2)}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selected.analysis && (
                <div className="mt-7">
                  <p className="label mb-2">Reading</p>
                  <p className="max-w-reading text-[0.9375rem] leading-relaxed text-ink-200 text-pretty">
                    {selected.analysis}
                  </p>
                </div>
              )}

              <div className="mt-7">
                <DataProvenance point={selected} defaultOpen />
              </div>
            </div>
          </div>
        )}

        {tab === 'banking' && (
          <div className="mt-7">
            <BankExplorer />
          </div>
        )}

        {tab === 'states' && (
          <div className="mt-7">
            <IndiaMap />
          </div>
        )}

        {/* --------------------------- Provenance --------------------------- */}
        <section id="provenance" className="mt-20 scroll-mt-24">
          <span className="label-accent">Provenance</span>
          <h2 className="display mt-2 text-[1.75rem] md:text-[2.25rem]">Source registry and audit log</h2>

          <div className="mt-6">
            <Notice title="How data got here">{RETRIEVAL_NOTE}</Notice>
          </div>

          <div className="mt-8 grid gap-px border border-white/[0.09] bg-white/[0.09] sm:grid-cols-2 lg:grid-cols-3">
            {Object.values(STATUS_STYLE).map((s, i) => {
              const key = Object.keys(STATUS_STYLE)[i] as DataStatus;
              return (
                <div key={s.label} className="bg-ink-950 p-4">
                  <div className="flex items-baseline justify-between gap-2">
                    <StatusBadge status={key} />
                    <span className="metric text-sm text-ink-500" data-numeric>
                      {statusCounts.get(key) ?? 0}
                    </span>
                  </div>
                  <p className="mt-2.5 text-2xs leading-relaxed text-ink-400">{s.description}</p>
                </div>
              );
            })}
          </div>

          <h3 className="label mt-12 mb-3">Sources</h3>
          <div className="overflow-x-auto border border-white/[0.09]">
            <table className="w-full min-w-[620px] border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.09] bg-ink-900/60">
                  {['Source', 'Full name', 'Tier', ''].map((h) => (
                    <th key={h} className="label px-4 py-2.5 font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.values(SOURCES).map((s) => (
                  <tr key={s.id} className="border-b border-white/[0.04] last:border-0">
                    <td className="px-4 py-2.5 font-mono text-2xs uppercase tracking-[0.12em] text-ink-100">
                      {s.name}
                    </td>
                    <td className="px-4 py-2.5 text-[0.8125rem] text-ink-300">{s.fullName}</td>
                    <td className="px-4 py-2.5 font-mono text-2xs text-ink-500">{SOURCE_TIER_LABEL[s.tier]}</td>
                    <td className="px-4 py-2.5 text-right">
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex items-center gap-1 font-mono text-2xs text-ink-500 hover:text-[#e8933a]"
                      >
                        Open <ExternalLink size={10} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="label mt-12 mb-3">Data audit log</h3>
          <div className="overflow-x-auto border border-white/[0.09]">
            <table className="w-full min-w-[900px] border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.09] bg-ink-900/60">
                  {['Dataset', 'Version', 'Retrieved', 'Transformation', 'Validation', 'Status'].map((h) => (
                    <th key={h} className="label px-4 py-2.5 font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {AUDIT_LOG.map((a) => (
                  <tr key={a.dataset} className="border-b border-white/[0.04] last:border-0 align-top">
                    <td className="px-4 py-3 text-[0.8125rem] text-ink-100">
                      {a.dataset}
                      {a.notes && <p className="mt-1 text-2xs leading-snug text-ink-600">{a.notes}</p>}
                    </td>
                    <td className="px-4 py-3 font-mono text-2xs text-ink-400">{a.version}</td>
                    <td className="px-4 py-3 font-mono text-2xs text-ink-400">{longDate(a.retrieved)}</td>
                    <td className="max-w-[260px] px-4 py-3 text-2xs leading-relaxed text-ink-400">
                      {a.transformation}
                    </td>
                    <td className="max-w-[280px] px-4 py-3 text-2xs leading-relaxed text-ink-400">{a.validation}</td>
                    <td className="px-4 py-3">
                      {a.status === 'mixed' ? (
                        <span className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-400">Mixed</span>
                      ) : (
                        <StatusBadge status={a.status} size="xs" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 font-mono text-2xs text-ink-700">
            All datasets retrieved {longDate(RETRIEVED_ON)}.
          </p>
        </section>
      </div>
    </>
  );
}
