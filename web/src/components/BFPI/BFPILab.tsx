import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, ExternalLink, RotateCcw } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BANKS,
  BANK_BY_ID,
  FY2025_PANEL,
  PANEL_CAVEATS,
  fieldsToObservations,
  rowFor,
  toObservation,
} from '../../data/banking/panel';
import { RETRIEVAL_NOTE } from '../../data/sources';
import {
  INDICATORS,
  calculateBFPI,
  calculateSample,
  computeSampleStats,
  pillarContribution,
} from '../../models/bfpi/engine';
import { MIN_PILLARS } from '../../models/bfpi/policy';
import {
  INDICATOR_KEYS,
  type BFPIResult,
  type IndicatorKey,
  type Observations,
} from '../../models/bfpi/types';
import { cn, number } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { Disclosure, Notice, Slider, StatusBadge } from '../ui';
import { BFPIDecomposition } from './BFPIDecomposition';

const REFERENCE = calculateSample(FY2025_PANEL.map(toObservation), { minPillars: MIN_PILLARS });

function buildBfpiCalculationText(r: BFPIResult, values: Observations, bankName: string): string {
  const L: string[] = [];
  L.push('BFPI — BANK FINANCIAL PERFORMANCE INDEX');
  L.push('India Economics Intelligence Lab — an original composite index.');
  L.push('Not an RBI measure, not a rating, not a prediction.');
  L.push('');
  L.push(`Bank    ${bankName}`);
  L.push(`Period  ${r.periodLabel}`);
  L.push(`Sample  ${FY2025_PANEL.length} banks, FY2025`);
  L.push('');
  L.push('STANDARDISATION   z = d · (X − μ) / σ');
  L.push('  Indicator   Raw        μ          σ        d     z');
  for (const key of INDICATOR_KEYS) {
    const spec = INDICATORS[key];
    const score = r.pillars.flatMap((p) => p.indicators).find((i) => i.key === key);
    if (!score || !score.available || score.z === null) {
      L.push(`  ${spec.short.padEnd(11)} unavailable — nothing substituted`);
      continue;
    }
    L.push(
      `  ${spec.short.padEnd(11)}${number(score.raw, 2).padStart(8)}${number(score.mean, 3).padStart(11)}${number(
        score.sd,
        3,
      ).padStart(10)}${String(score.direction).padStart(6)}${(score.z >= 0 ? '+' : '') + score.z.toFixed(3)}`,
    );
  }
  L.push('');
  L.push('PILLARS (equal weights, 25% each)');
  for (const p of r.pillars) {
    L.push(
      `  ${p.label.padEnd(16)}${p.z === null ? 'unavailable' : `z = ${(p.z >= 0 ? '+' : '') + p.z.toFixed(4)}   scaled ${p.scaled!.toFixed(1)}`}`,
    );
  }
  L.push('');
  L.push('COMPOSITE');
  if (r.compositeZ === null) {
    L.push('  BFPI withheld — see treatment note.');
  } else {
    L.push('  Z_BFPI = 0.25P + 0.25C + 0.25A + 0.25L');
    L.push(`         = ${(r.compositeZ >= 0 ? '+' : '') + r.compositeZ.toFixed(4)}`);
    L.push('  BFPI   = 50 + 10 · Z_BFPI');
    L.push(`         = 50 + 10 × ${r.compositeZ.toFixed(4)}`);
    L.push(`         = ${r.bfpi!.toFixed(2)}`);
  }
  if (r.treatment) {
    L.push('');
    L.push('TREATMENT');
    L.push(`  ${r.treatment}`);
  }
  L.push('');
  L.push('Relative to the selected sample and period. Not a judgement of any bank.');
  void values;
  return L.join('\n');
}

function buildPanelCsv(): string {
  const head = ['bank', 'period', ...INDICATOR_KEYS, 'bfpi', 'status'];
  const rows = FY2025_PANEL.map((row) => {
    const res = REFERENCE.results.find((r) => r.bankId === row.bankId);
    return [
      BANK_BY_ID[row.bankId].name,
      row.periodLabel,
      ...INDICATOR_KEYS.map((k) => (row.fields[k].value === null ? '' : row.fields[k].value)),
      res?.bfpi === null || res?.bfpi === undefined ? '' : res.bfpi.toFixed(2),
      res?.bfpi === null ? 'withheld' : 'reported',
    ].join(',');
  });
  return [head.join(','), ...rows, '', '# Empty cells are genuinely unavailable. Nothing has been imputed.'].join('\n');
}

export function BFPILab({ initialBank = 'icicibank' }: { initialBank?: string }) {
  const [bankId, setBankId] = useState(initialBank);
  const [overrides, setOverrides] = useState<Partial<Record<IndicatorKey, number>>>({});
  const [showCalc, setShowCalc] = useState(false);
  const [hoverPillar, setHoverPillar] = useState<string | null>(null);

  const row = rowFor(bankId)!;
  const bank = BANK_BY_ID[bankId];

  const baseValues = useMemo(() => fieldsToObservations(row.fields), [row]);

  const values = useMemo<Observations>(() => {
    const v = { ...baseValues };
    for (const [k, n] of Object.entries(overrides)) v[k as IndicatorKey] = n as number;
    return v;
  }, [baseValues, overrides]);

  /**
   * Sample statistics are recomputed with the reader's edited bank in the
   * sample, because BFPI is relative: changing a bank changes the sample it
   * is being compared against, and pretending otherwise would misstate it.
   */
  const stats = useMemo(() => {
    const sample = FY2025_PANEL.map((r) =>
      r.bankId === bankId
        ? { bankId: r.bankId, periodLabel: r.periodLabel, values }
        : toObservation(r),
    );
    return computeSampleStats(sample);
  }, [bankId, values]);

  const result = useMemo(
    () => calculateBFPI({ bankId, periodLabel: row.periodLabel, values }, stats, { minPillars: MIN_PILLARS }),
    [bankId, row.periodLabel, values, stats],
  );

  const baselineResult = REFERENCE.results.find((r) => r.bankId === bankId) ?? null;
  const edited = Object.keys(overrides).length > 0;

  const setOverride = useCallback((k: IndicatorKey, v: number) => {
    setOverrides((o) => ({ ...o, [k]: v }));
  }, []);

  const availableWeightSum = result.pillars.filter((p) => p.z !== null).reduce((s, p) => s + p.weight, 0);

  return (
    <div className="space-y-px border border-white/[0.09] bg-white/[0.09]">
      {/* Bank selector */}
      <div className="flex flex-wrap items-center gap-px bg-white/[0.07]">
        {BANKS.map((b) => {
          const res = REFERENCE.results.find((r) => r.bankId === b.id);
          const active = b.id === bankId;
          return (
            <button
              key={b.id}
              type="button"
              onClick={() => {
                setBankId(b.id);
                setOverrides({});
              }}
              aria-pressed={active}
              className={cn(
                'relative flex-1 whitespace-nowrap bg-ink-900 px-3 py-3 text-left transition-colors hover:bg-ink-850',
                active && 'bg-ink-850',
              )}
            >
              {active && (
                <motion.span layoutId="bfpi-bank" className="absolute inset-x-0 top-0 h-px bg-[#e8933a]" />
              )}
              <span className={cn('block font-mono text-2xs uppercase tracking-[0.14em]', active ? 'text-ink-50' : 'text-ink-400')}>
                {b.shortName}
              </span>
              <span className="mt-0.5 block metric text-xs text-ink-500" data-numeric>
                {res?.bfpi === null || res?.bfpi === undefined ? '—' : res.bfpi.toFixed(1)}
              </span>
            </button>
          );
        })}
      </div>

      <div className="grid gap-px bg-white/[0.07] lg:grid-cols-[minmax(0,1fr)_330px]">
        {/* ---------------------------- RESULT ---------------------------- */}
        <div className="bg-ink-950 p-5 md:p-7">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <span className="label-accent">{row.periodLabel} · year ended 31 March 2025</span>
              <h3 className="display mt-2 text-2xl md:text-3xl">{bank.name}</h3>
            </div>
            <div className="flex items-center gap-2">
              {edited && (
                <button type="button" className="btn" onClick={() => setOverrides({})}>
                  <RotateCcw size={12} /> Reset
                </button>
              )}
              <a href={bank.disclosureUrl} target="_blank" rel="noreferrer noopener" className="btn">
                Open source <ExternalLink size={12} />
              </a>
            </div>
          </div>

          {edited && (
            <div className="mt-4">
              <Notice title="User scenario">
                You have changed {Object.keys(overrides).length} input
                {Object.keys(overrides).length === 1 ? '' : 's'}. The scores below are hypothetical, and the
                sample statistics have been recomputed with your edited bank in the sample — because BFPI is a
                relative measure, changing one bank shifts the reference every bank is measured against.
              </Notice>
            </div>
          )}

          {result.bfpi === null && (
            <div className="mt-4">
              <Notice tone="missing" title="BFPI withheld">
                {result.treatment}
              </Notice>
            </div>
          )}

          <div className="mt-6">
            <BFPIDecomposition
              result={result}
              previousBfpi={edited ? baselineResult?.bfpi ?? null : undefined}
              onHoverPillar={setHoverPillar}
            />
          </div>

          {result.treatment && result.bfpi !== null && (
            <p className="mt-5 border-l-2 border-ink-700 pl-3 text-2xs leading-relaxed text-ink-500">
              <span className="font-mono uppercase tracking-[0.14em] text-ink-600">Treatment · </span>
              {result.treatment}
            </p>
          )}

          <div className="mt-6 flex flex-wrap gap-2">
            <button type="button" className="btn" onClick={() => setShowCalc((s) => !s)} aria-expanded={showCalc}>
              {showCalc ? 'Hide calculation' : 'Show calculation'}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => navigator.clipboard?.writeText(buildBfpiCalculationText(result, values, bank.name))}
            >
              Copy calculation
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => {
                const blob = new Blob([buildPanelCsv()], { type: 'text/csv;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'ieil-bfpi-panel-fy2025.csv';
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Download data
            </button>
            <Link to="/models/bfpi/methodology" className="btn">
              Read the methodology <ArrowRight size={12} />
            </Link>
          </div>

          <AnimatePresence>
            {showCalc && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3, ease: EASE_OUT }}
                className="overflow-hidden"
              >
                <div className="mt-5 border border-white/[0.09] bg-ink-950/60 p-5">
                  <p className="label mb-3">Transparency — every bank-year cell</p>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[720px] border-collapse text-left font-mono text-2xs">
                      <thead>
                        <tr className="border-b border-white/[0.09]">
                          {['Indicator', 'Raw', 'Mean μ', 'SD σ', 'Dir d', 'z-score', 'Pillar', 'Basis'].map((h) => (
                            <th key={h} className="label py-1.5 pr-3 font-normal">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {INDICATOR_KEYS.map((k) => {
                          const spec = INDICATORS[k];
                          const score = result.pillars.flatMap((p) => p.indicators).find((i) => i.key === k);
                          const field = row.fields[k];
                          const overridden = overrides[k] !== undefined;
                          return (
                            <tr
                              key={k}
                              className={cn(
                                'border-b border-white/[0.04]',
                                hoverPillar === spec.pillar && 'bg-white/[0.03]',
                              )}
                            >
                              <td className="py-1.5 pr-3 text-ink-200">{spec.short}</td>
                              <td className="py-1.5 pr-3" data-numeric>
                                {score?.raw === null || score?.raw === undefined ? (
                                  <span className="text-ink-700">unavailable</span>
                                ) : (
                                  <span className={overridden ? 'text-[#8b7fd4]' : 'text-ink-200'}>
                                    {number(score.raw, 2)}
                                  </span>
                                )}
                              </td>
                              <td className="py-1.5 pr-3 text-ink-400" data-numeric>{number(score?.mean ?? null, 3)}</td>
                              <td className="py-1.5 pr-3 text-ink-400" data-numeric>{number(score?.sd ?? null, 3)}</td>
                              <td className="py-1.5 pr-3 text-ink-400" data-numeric>{spec.direction > 0 ? '+1' : '−1'}</td>
                              <td
                                className="py-1.5 pr-3"
                                data-numeric
                                style={{ color: score?.z == null ? '#5d6a72' : score.z >= 0 ? '#4fae86' : '#d3675d' }}
                              >
                                {score?.z == null ? '—' : `${score.z >= 0 ? '+' : ''}${score.z.toFixed(3)}`}
                              </td>
                              <td className="py-1.5 pr-3 text-ink-500">{spec.pillar}</td>
                              <td className="py-1.5 pr-3 text-ink-600">
                                {overridden ? 'your scenario' : field.basis}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-4 space-y-2 border-t border-white/[0.07] pt-4">
                    <p className="label">Pillar contributions to BFPI</p>
                    {result.pillars.map((p) => {
                      const contrib = pillarContribution(p, availableWeightSum || 1);
                      return (
                        <div key={p.key} className="flex items-baseline justify-between gap-3 font-mono text-2xs">
                          <span className="text-ink-400">{p.label}</span>
                          <span className="text-ink-200" data-numeric>
                            {contrib === null
                              ? 'not included'
                              : `${contrib >= 0 ? '+' : ''}${contrib.toFixed(2)} points`}
                          </span>
                        </div>
                      );
                    })}
                    <div className="flex items-baseline justify-between gap-3 border-t border-white/[0.07] pt-2 font-mono text-2xs">
                      <span className="text-ink-300">50 (sample centre) + contributions</span>
                      <span className="text-[#e8933a]" data-numeric>
                        {result.bfpi === null ? 'withheld' : result.bfpi.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <pre className="mt-4 overflow-x-auto border-t border-white/[0.07] pt-4 font-mono text-2xs leading-relaxed text-ink-400">
{buildBfpiCalculationText(result, values, bank.name)}
                  </pre>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* --------------------------- STRESS PANEL --------------------------- */}
        <aside className="bg-ink-900/70 p-5 md:p-6 lg:max-h-[calc(100vh-var(--lab-nav-h))] lg:overflow-y-auto">
          <h4 className="label-accent">Stress the bank</h4>
          <p className="mt-2 text-2xs leading-relaxed text-ink-500">
            Move an input and watch it propagate through its pillar into the composite. Anything you change is a
            user scenario, not a disclosure.
          </p>

          <div className="mt-5 space-y-5">
            {INDICATOR_KEYS.map((k) => {
              const spec = INDICATORS[k];
              const field = row.fields[k];
              const current = values[k];
              const missing = field.value === null && overrides[k] === undefined;

              return (
                <div key={k}>
                  {missing ? (
                    <div className="border border-dashed border-white/[0.09] p-3">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="label text-ink-500">{spec.short}</span>
                        <StatusBadge status="unavailable" size="xs" />
                      </div>
                      <p className="mt-1.5 text-2xs leading-snug text-ink-600">{field.note}</p>
                      <button
                        type="button"
                        className="mt-2 font-mono text-2xs uppercase tracking-[0.14em] text-[#8b7fd4] hover:underline"
                        onClick={() => setOverride(k, (spec.min + spec.max) / 8)}
                      >
                        + Supply a scenario value
                      </button>
                    </div>
                  ) : (
                    <>
                      <Slider
                        label={spec.short}
                        value={current ?? 0}
                        min={spec.min}
                        max={Math.min(spec.max, k === 'lcr' ? 250 : spec.max)}
                        step={spec.step}
                        accent={overrides[k] !== undefined ? '#8b7fd4' : '#e8933a'}
                        baselineValue={field.value ?? undefined}
                        onChange={(v) => setOverride(k, v)}
                        format={(v) => `${v.toFixed(2)}`}
                        unit={spec.unit === '%' ? '%' : spec.unit}
                      />
                      <p className="mt-1 font-mono text-2xs text-ink-700">
                        {spec.direction > 0 ? 'higher is better' : 'lower is better'} · {field.basis}
                      </p>
                    </>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-6 border-t border-white/[0.07]">
            <Disclosure summary={<span>Sample caveats</span>}>
              <ul className="space-y-2">
                {PANEL_CAVEATS.map((c) => (
                  <li key={c} className="flex gap-2 text-2xs leading-relaxed text-ink-400">
                    <span className="text-ink-700">—</span>
                    {c}
                  </li>
                ))}
              </ul>
              <p className="mt-3 border-t border-white/[0.05] pt-3 text-2xs leading-relaxed text-ink-600">
                {RETRIEVAL_NOTE}
              </p>
            </Disclosure>
          </div>
        </aside>
      </div>
    </div>
  );
}

export { REFERENCE as BFPI_REFERENCE };
