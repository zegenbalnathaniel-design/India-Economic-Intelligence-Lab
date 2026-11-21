import { ASSETS } from '../../data/wealth/assumptions';
import { ASSET_KEYS, type Figure2Result } from '../../models/figure2/types';
import { calculateFutureValue } from '../../models/figure2/engine';
import { buildCalculationText, buildCsv, buildScenarioJson } from './build';
import { fractionAsPercent, rupees } from '../../lib/format';
import { CopyButton, DownloadButton } from '../ui';

function Step({ n, label, children }: { n: string; label: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-white/[0.07] py-4 first:border-t-0 first:pt-0">
      <div className="flex items-baseline gap-3">
        <span className="label-accent">{n}</span>
        <span className="label text-ink-400">{label}</span>
      </div>
      <div className="mt-2.5">{children}</div>
    </div>
  );
}

export function CalculationViewer({ result }: { result: Figure2Result }) {
  const r = result;
  const closedForm = calculateFutureValue(
    r.inputs.annualSaving / r.periodsPerYear,
    r.periodicRate,
    r.inputs.years * r.periodsPerYear,
  );

  return (
    <div className="border border-white/[0.09] bg-ink-950/60 p-5 md:p-6">
      <Step n="01" label="Portfolio weights and returns">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[440px] border-collapse text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.09]">
                <th className="label py-1.5 pr-3 font-normal">Asset</th>
                <th className="label py-1.5 pr-3 text-right font-normal">Weight wᵢ</th>
                <th className="label py-1.5 pr-3 text-right font-normal">Return Rᵢ</th>
                <th className="label py-1.5 text-right font-normal">wᵢ × Rᵢ</th>
              </tr>
            </thead>
            <tbody>
              {ASSET_KEYS.map((k) => {
                const w = r.inputs.allocation[k] ?? 0;
                const ret = r.inputs.returns[k] ?? 0;
                return (
                  <tr key={k} className="border-b border-white/[0.04]">
                    <td className="py-1.5 pr-3">
                      <span className="inline-flex items-center gap-2 text-ink-200">
                        <span className="h-2 w-2" style={{ background: ASSETS[k].colour }} aria-hidden />
                        {ASSETS[k].label}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-right text-ink-200" data-numeric>{fractionAsPercent(w, 1)}</td>
                    <td className="py-1.5 pr-3 text-right text-ink-200" data-numeric>{fractionAsPercent(ret, 2)}</td>
                    <td className="py-1.5 text-right text-ink-100" data-numeric>{fractionAsPercent(w * ret, 4)}</td>
                  </tr>
                );
              })}
              <tr className="border-t border-white/[0.12]">
                <td className="py-2 pr-3 text-ink-400">Total</td>
                <td className="py-2 pr-3 text-right text-ink-200" data-numeric>
                  {fractionAsPercent(ASSET_KEYS.reduce((s, k) => s + (r.inputs.allocation[k] ?? 0), 0), 1)}
                </td>
                <td className="py-2 pr-3" />
                <td className="py-2 text-right text-[#e8933a]" data-numeric>
                  {fractionAsPercent(r.portfolioReturn, 4)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Step>

      <Step n="02" label="Weighted portfolio return">
        <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-ink-300">
{`R_p = Σ wᵢ Rᵢ
    = ${ASSET_KEYS.map((k) => `${(r.inputs.allocation[k] ?? 0).toFixed(2)} × ${((r.inputs.returns[k] ?? 0) * 100).toFixed(2)}%`).join('\n    + ')}
    = `}<span className="text-[#e8933a]">{fractionAsPercent(r.portfolioReturn, 4)}</span>
        </pre>
      </Step>

      {r.periodsPerYear > 1 && (
        <Step n="02b" label="Per-period rate">
          <pre className="overflow-x-auto font-mono text-xs leading-relaxed text-ink-300">
{`r = (1 + R_p)^(1/${r.periodsPerYear}) − 1 = ${fractionAsPercent(r.periodicRate, 6)}`}
          </pre>
          <p className="mt-2 text-2xs leading-relaxed text-ink-500">
            The equivalent compounded rate is used rather than R_p ÷ {r.periodsPerYear}, so that changing the
            contribution frequency shows the effect of timing alone and not of a different annual return.
          </p>
        </Step>
      )}

      <Step n="03" label="Future value">
        <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-ink-300">
{`FV = C × [ (1 + r)ⁿ − 1 ] / r

   C = ${rupees(r.inputs.annualSaving / r.periodsPerYear)}   (per contribution)
   r = ${r.periodicRate.toFixed(6)}
   n = ${r.inputs.years * r.periodsPerYear}

FV = ${rupees(r.inputs.annualSaving / r.periodsPerYear)} × [ (1 + ${r.periodicRate.toFixed(6)})^${r.inputs.years * r.periodsPerYear} − 1 ] / ${r.periodicRate.toFixed(6)}
   = `}<span className="text-[#e8933a]">{rupees(closedForm)}</span>
        </pre>
        {r.inputs.startingCapital > 0 && (
          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-300">
{`plus starting capital compounded:
   ${rupees(r.inputs.startingCapital)} × (1 + ${r.portfolioReturn.toFixed(6)})^${r.inputs.years} = ${rupees(r.inputs.startingCapital * Math.pow(1 + r.portfolioReturn, r.inputs.years))}`}
          </pre>
        )}
        {r.inputs.timing === 'start' && (
          <p className="mt-2 text-2xs leading-relaxed text-ink-500">
            Contributions are made at the start of each period, so each earns one additional period of growth:
            the closed form above is multiplied by (1 + r).
          </p>
        )}
      </Step>

      <Step n="04" label="Result">
        <dl className="grid grid-cols-2 gap-px border border-white/[0.07] bg-white/[0.07] sm:grid-cols-4">
          {[
            ['Total contributed', rupees(r.totalContributed)],
            ['Final value', rupees(r.finalValue)],
            ['Investment gain', rupees(r.investmentGain)],
            ['Wealth multiple', `${r.wealthMultiple.toFixed(2)}×`],
          ].map(([k, v]) => (
            <div key={k} className="bg-ink-900 p-3">
              <dt className="label">{k}</dt>
              <dd className="metric mt-1.5 text-sm" data-numeric>
                {v}
              </dd>
            </div>
          ))}
        </dl>
      </Step>

      <div className="mt-5 flex flex-wrap gap-2 border-t border-white/[0.07] pt-5">
        <CopyButton text={buildCalculationText(r)} label="Copy calculation" />
        <DownloadButton filename="ieil-figure2-series.csv" content={() => buildCsv(r)} label="Download CSV" />
        <DownloadButton
          filename="ieil-figure2-scenario.json"
          mime="application/json"
          content={() => buildScenarioJson(r)}
          label="Download scenario"
        />
      </div>
    </div>
  );
}
