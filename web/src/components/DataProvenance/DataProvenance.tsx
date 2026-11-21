import { ExternalLink } from 'lucide-react';
import { getSource, RETRIEVAL_NOTE } from '../../data/sources';
import { STATUS_STYLE, type DataPoint, type Discrepancy } from '../../data/types';
import { longDate, number } from '../../lib/format';
import { Disclosure, StatusBadge } from '../ui';

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[112px_1fr] gap-3 border-b border-white/[0.05] py-2 last:border-0 sm:grid-cols-[140px_1fr]">
      <dt className="label pt-[3px] text-ink-600">{k}</dt>
      <dd className="text-[0.8125rem] leading-relaxed text-ink-200">{v}</dd>
    </div>
  );
}

export function SourceDiscrepancy({ d }: { d: Discrepancy }) {
  return (
    <div className="border border-[#e8933a]/30 bg-[#e8933a]/[0.05] p-4">
      <p className="font-mono text-2xs uppercase tracking-[0.14em] text-[#e8933a]">
        ⚠ Source discrepancy detected
      </p>
      <p className="mt-2 text-[0.8125rem] leading-relaxed text-ink-200">{d.summary}</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/[0.09]">
              <th className="label py-1.5 pr-3 font-normal">Source</th>
              <th className="label py-1.5 pr-3 text-right font-normal">Value</th>
              <th className="label py-1.5 font-normal">Period</th>
            </tr>
          </thead>
          <tbody>
            {d.entries.map((e) => (
              <tr key={e.label} className="border-b border-white/[0.05] last:border-0">
                <td className="py-2 pr-3 text-[0.8125rem] text-ink-200">
                  <a
                    href={e.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1.5 hover:text-[#e8933a]"
                  >
                    {e.label}
                    <ExternalLink size={11} className="opacity-50" />
                  </a>
                </td>
                <td className="metric py-2 pr-3 text-right text-sm">
                  {Number.isFinite(e.value) ? number(e.value, 2) : 'not read'}
                </td>
                <td className="py-2 font-mono text-2xs text-ink-400">{e.period}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink-400">{d.explanation}</p>
    </div>
  );
}

/**
 * The provenance panel attached to every chart and metric (spec §53).
 * Collapsed by default so it does not compete with the number, but always
 * present — a figure without a traceable source is not a finding.
 */
export function DataProvenance({ point, defaultOpen = false }: { point: DataPoint; defaultOpen?: boolean }) {
  const source = getSource(point.sourceId);
  const style = STATUS_STYLE[point.status];

  return (
    <Disclosure defaultOpen={defaultOpen} summary={<span>Data provenance</span>}>
      <dl className="mt-1">
        <Row k="Indicator" v={point.indicator} />
        <Row
          k="Value"
          v={
            point.value === null ? (
              <span className="text-ink-500">Not available for this period</span>
            ) : (
              <span className="metric">
                {point.value}
                <span className="ml-1.5 text-ink-500">{point.unit}</span>
              </span>
            )
          }
        />
        <Row k="Period" v={<span className="font-mono text-xs">{point.period.label}</span>} />
        <Row
          k="Source"
          v={
            <a
              href={point.sourceUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 hover:text-[#e8933a]"
            >
              {source.fullName}
              <ExternalLink size={11} className="opacity-50" />
            </a>
          }
        />
        {point.dataset && <Row k="Dataset" v={point.dataset} />}
        <Row k="Published" v={longDate(point.publicationDate)} />
        <Row k="Retrieved" v={longDate(point.accessedDate)} />
        <Row k="Processing" v={point.processing ?? 'None. Carried at the unit and period of the source release.'} />
        <Row
          k="Status"
          v={
            <span className="flex flex-wrap items-center gap-2">
              <StatusBadge status={point.status} />
              <span className="text-ink-400">{style.description}</span>
            </span>
          }
        />
        {point.methodology && <Row k="Methodology" v={point.methodology} />}
        {point.note && <Row k="Note" v={point.note} />}
        {point.vintages && point.vintages.length > 0 && (
          <Row
            k="Vintages"
            v={
              <ul className="space-y-1">
                {point.vintages.map((v) => (
                  <li key={v.label} className="flex flex-wrap items-baseline gap-2">
                    <span className="metric text-sm">{v.value}</span>
                    <span className="text-ink-300">{v.label}</span>
                    <span className="font-mono text-2xs text-ink-600">{longDate(v.releasedOn)}</span>
                    {v.note && <span className="text-ink-500">— {v.note}</span>}
                  </li>
                ))}
              </ul>
            }
          />
        )}
      </dl>

      {point.discrepancy && (
        <div className="mt-4">
          <SourceDiscrepancy d={point.discrepancy} />
        </div>
      )}

      <p className="mt-4 border-t border-white/[0.05] pt-3 text-2xs leading-relaxed text-ink-600">
        {RETRIEVAL_NOTE}
      </p>

      <a
        href={point.sourceUrl}
        target="_blank"
        rel="noreferrer noopener"
        className="btn mt-4 inline-flex"
      >
        Open source <ExternalLink size={12} />
      </a>
    </Disclosure>
  );
}
