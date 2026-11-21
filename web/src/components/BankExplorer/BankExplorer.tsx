import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import { useMemo, useState } from 'react';
import { BANKS, BANK_BY_ID, FY2025_PANEL, rowFor, toObservation } from '../../data/banking/panel';
import { INDICATORS, calculateSample } from '../../models/bfpi/engine';
import { INDICATOR_KEYS, PILLAR_KEYS, type IndicatorKey, type PillarKey } from '../../models/bfpi/types';
import { cn, number } from '../../lib/format';
import { MIN_PILLARS } from '../../models/bfpi/policy';
import { Notice, StatusBadge } from '../ui';

const PILLAR_LABEL: Record<PillarKey, string> = {
  profitability: 'Profitability',
  capital: 'Capital',
  assetQuality: 'Asset Quality',
  liquidity: 'Liquidity',
};

type View = 'raw' | 'z' | 'pillars';

/**
 * The bank explorer is deliberately not a leaderboard. Banks are listed in a
 * fixed order — public sector then private, alphabetical within each — and
 * never sorted by score, because sorting by a composite invites exactly the
 * "best bank" reading the index cannot support.
 */
export function BankExplorer() {
  const [selected, setSelected] = useState<string[]>(BANKS.map((b) => b.id));
  const [indicators, setIndicators] = useState<IndicatorKey[]>([...INDICATOR_KEYS]);
  const [view, setView] = useState<View>('raw');

  const sample = useMemo(
    () => FY2025_PANEL.filter((r) => selected.includes(r.bankId)).map(toObservation),
    [selected],
  );

  const { stats, results } = useMemo(
    () => calculateSample(sample, { minPillars: MIN_PILLARS }),
    [sample],
  );

  const ordered = useMemo(() => {
    const ids = new Set(selected);
    return BANKS.filter((b) => ids.has(b.id));
  }, [selected]);

  const toggleBank = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const toggleIndicator = (k: IndicatorKey) =>
    setIndicators((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));

  return (
    <div className="border border-white/[0.09]">
      {/* Controls */}
      <div className="grid gap-px bg-white/[0.07] md:grid-cols-3">
        <div className="bg-ink-900 p-4">
          <p className="label mb-3">Banks in the sample</p>
          <div className="flex flex-wrap gap-1.5">
            {BANKS.map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => toggleBank(b.id)}
                aria-pressed={selected.includes(b.id)}
                className={cn(
                  'border px-2 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
                  selected.includes(b.id)
                    ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                    : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
                )}
              >
                {b.shortName}
              </button>
            ))}
          </div>
          <p className="mt-2.5 text-2xs leading-snug text-ink-600">
            Every score is relative to whichever banks are selected. Remove one and the rest move.
          </p>
        </div>

        <div className="bg-ink-900 p-4">
          <p className="label mb-3">Variables</p>
          <div className="flex flex-wrap gap-1.5">
            {INDICATOR_KEYS.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => toggleIndicator(k)}
                aria-pressed={indicators.includes(k)}
                className={cn(
                  'border px-2 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
                  indicators.includes(k)
                    ? 'border-white/25 bg-white/[0.06] text-ink-100'
                    : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
                )}
                title={INDICATORS[k].rationale}
              >
                {INDICATORS[k].short}
              </button>
            ))}
          </div>
          <p className="mt-2.5 text-2xs leading-snug text-ink-600">
            Hiding a variable changes what the table shows, not what the index computed — the composite always
            uses every available indicator.
          </p>
        </div>

        <div className="bg-ink-900 p-4">
          <p className="label mb-3">View</p>
          <div className="flex gap-1.5">
            {(
              [
                ['raw', 'Raw values'],
                ['z', 'z-scores'],
                ['pillars', 'Pillars'],
              ] as [View, string][]
            ).map(([v, label]) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                aria-pressed={view === v}
                className={cn(
                  'border px-2 py-1 font-mono text-2xs uppercase tracking-[0.12em] transition-colors',
                  view === v
                    ? 'border-[#e8933a]/50 bg-[#e8933a]/10 text-[#e8933a]'
                    : 'border-white/[0.09] text-ink-500 hover:text-ink-200',
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="mt-2.5 text-2xs leading-snug text-ink-600">
            Period: FY2025 (year ended 31 March 2025) for every bank shown.
          </p>
        </div>
      </div>

      {selected.length === 0 ? (
        <div className="p-8">
          <Notice tone="missing" title="No banks selected">
            BFPI is a relative index; with an empty sample there is nothing to be relative to.
          </Notice>
        </div>
      ) : (
        <div className="overflow-x-auto border-t border-white/[0.07]">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b border-white/[0.09] bg-ink-900/50">
                <th className="label sticky left-0 z-10 bg-ink-900 px-4 py-3 font-normal">Bank</th>
                {view === 'pillars'
                  ? PILLAR_KEYS.map((p) => (
                      <th key={p} className="label px-3 py-3 text-right font-normal">
                        {PILLAR_LABEL[p]}
                      </th>
                    ))
                  : indicators.map((k) => (
                      <th key={k} className="label px-3 py-3 text-right font-normal" title={INDICATORS[k].label}>
                        {INDICATORS[k].short}
                        <span className="ml-1 text-ink-700">{INDICATORS[k].direction > 0 ? '↑' : '↓'}</span>
                      </th>
                    ))}
                <th className="label px-4 py-3 text-right font-normal">BFPI</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((bank, i) => {
                const res = results.find((r) => r.bankId === bank.id);
                const row = rowFor(bank.id)!;
                return (
                  <motion.tr
                    key={bank.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="border-b border-white/[0.04] transition-colors hover:bg-white/[0.02]"
                  >
                    <th scope="row" className="sticky left-0 z-10 bg-ink-950 px-4 py-3 text-left font-normal">
                      <span className="block text-[0.8125rem] text-ink-100">{bank.shortName}</span>
                      <span className="block font-mono text-2xs text-ink-600">
                        {bank.ownership === 'public' ? 'Public sector' : 'Private sector'}
                      </span>
                    </th>

                    {view === 'pillars'
                      ? PILLAR_KEYS.map((pk) => {
                          const p = res?.pillars.find((x) => x.key === pk);
                          return (
                            <td key={pk} className="px-3 py-3 text-right">
                              {p?.scaled == null ? (
                                <span className="font-mono text-2xs text-ink-700">—</span>
                              ) : (
                                <span className="metric text-sm" data-numeric>
                                  {p.scaled.toFixed(1)}
                                  {p.partial && <span className="ml-1 text-2xs text-ink-600">*</span>}
                                </span>
                              )}
                            </td>
                          );
                        })
                      : indicators.map((k) => {
                          const field = row.fields[k];
                          const score = res?.pillars.flatMap((p) => p.indicators).find((s) => s.key === k);
                          return (
                            <td key={k} className="px-3 py-3 text-right">
                              {field.value === null ? (
                                <span
                                  className="font-mono text-2xs text-ink-700"
                                  title={field.note}
                                >
                                  unavailable
                                </span>
                              ) : view === 'raw' ? (
                                <span className="metric text-sm" data-numeric title={field.basis}>
                                  {number(field.value, 2)}
                                </span>
                              ) : (
                                <span
                                  className="metric text-sm"
                                  data-numeric
                                  style={{ color: (score?.z ?? 0) >= 0 ? '#4fae86' : '#d3675d' }}
                                >
                                  {score?.z == null ? '—' : `${score.z >= 0 ? '+' : ''}${score.z.toFixed(2)}`}
                                </span>
                              )}
                            </td>
                          );
                        })}

                    <td className="px-4 py-3 text-right">
                      {res?.bfpi == null ? (
                        <span className="font-mono text-2xs uppercase tracking-[0.12em] text-ink-600" title={res?.treatment ?? undefined}>
                          withheld
                        </span>
                      ) : (
                        <span className="metric text-base text-[#e8933a]" data-numeric>
                          {res.bfpi.toFixed(1)}
                          {res.partial && <span className="ml-1 text-2xs text-ink-600">*</span>}
                        </span>
                      )}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Sample statistics — the reference every z-score is measured against. */}
      <div className="border-t border-white/[0.07] bg-ink-900/40 px-4 py-4">
        <p className="label mb-2.5">Sample statistics — the reference for every z-score above</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3 lg:grid-cols-6">
          {INDICATOR_KEYS.map((k) => {
            const s = stats[k];
            return (
              <div key={k} className="font-mono text-2xs">
                <span className="text-ink-500">{INDICATORS[k].short}</span>
                {s ? (
                  <span className="ml-2 text-ink-300" data-numeric>
                    μ {s.mean.toFixed(2)} · σ {s.sd.toFixed(2)} · n {s.n}
                  </span>
                ) : (
                  <span className="ml-2 text-ink-700">no observations</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] px-4 py-3">
        <p className="max-w-3xl text-2xs leading-relaxed text-ink-600">
          <span className="text-ink-500">* </span>
          computed from fewer than all of the pillar’s indicators. Banks are listed in a fixed order, never
          ranked: BFPI describes position within this sample and period and does not establish that any bank is
          best, safest or strongest. Two banks are withheld entirely for insufficient coverage.
        </p>
        <div className="flex items-center gap-2">
          <StatusBadge status="reported" size="xs" />
          <a
            href={BANK_BY_ID[ordered[0]?.id ?? 'sbi']?.disclosureUrl ?? '#'}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1.5 font-mono text-2xs text-ink-500 hover:text-[#e8933a]"
          >
            Issuer disclosures <ExternalLink size={10} />
          </a>
        </div>
      </div>
    </div>
  );
}
