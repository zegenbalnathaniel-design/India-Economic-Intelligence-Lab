import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, RotateCcw } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ASSETS,
  BASELINE_INPUTS,
  DEFAULT_ALLOCATION,
  DEFAULT_RETURNS,
  FIGURE2_CAVEAT,
  FIGURE2_CLASSIFICATION,
} from '../../data/wealth/assumptions';
import { compareScenarios, reallocate } from '../../models/figure2/engine';
import {
  ASSET_KEYS,
  type AssetKey,
  type ContributionFrequency,
  type ContributionTiming,
  type Figure2Inputs,
} from '../../models/figure2/types';
import { cn, fractionAsPercent, rupees, rupeesCompact } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { CalculationViewer } from '../CalculationViewer/CalculationViewer';
import {
  AnimatedNumber,
  Disclosure,
  NumberField,
  Notice,
  SegmentedControl,
  Slider,
  StatusBadge,
} from '../ui';
import { WealthChart } from './WealthChart';

const CLASS_TONE: Record<string, string> = {
  OBSERVED: '#4fae86',
  DERIVED: '#4aa5a8',
  ASSUMPTION: '#e8933a',
  SCENARIO: '#8b7fd4',
};

function Readout({
  label,
  value,
  format,
  tone,
  sub,
}: {
  label: string;
  value: number | null;
  format: (n: number | null) => string;
  tone?: string;
  sub?: string;
}) {
  return (
    <div className="bg-ink-900 p-4">
      <p className="label">{label}</p>
      <AnimatedNumber
        value={value}
        format={format}
        className="metric mt-2 block text-[1.25rem] leading-none sm:text-[1.5rem]"
      />
      {sub && <p className="mt-1.5 font-mono text-2xs text-ink-600">{sub}</p>}
      {tone && <span className="mt-2 block h-px w-8" style={{ background: tone }} aria-hidden />}
    </div>
  );
}

export function Figure2Lab({ compact = false }: { compact?: boolean }) {
  const [inputs, setInputs] = useState<Figure2Inputs>(() => ({
    ...BASELINE_INPUTS,
    allocation: { ...DEFAULT_ALLOCATION },
    returns: { ...DEFAULT_RETURNS },
  }));
  const [showCalc, setShowCalc] = useState(false);

  const set = useCallback(<K extends keyof Figure2Inputs>(key: K, value: Figure2Inputs[K]) => {
    setInputs((s) => ({ ...s, [key]: value }));
  }, []);

  const setWeight = useCallback((k: AssetKey, v: number) => {
    setInputs((s) => ({ ...s, allocation: { ...s.allocation, [k]: v / 100 } }));
  }, []);

  const setReturn = useCallback((k: AssetKey, v: number) => {
    setInputs((s) => ({ ...s, returns: { ...s.returns, [k]: v / 100 } }));
  }, []);

  const comparison = useMemo(() => compareScenarios(BASELINE_INPUTS, inputs), [inputs]);
  const result = comparison.scenario;
  const baseline = comparison.baseline;

  const diverged = useMemo(
    () =>
      JSON.stringify(inputs) !== JSON.stringify(BASELINE_INPUTS),
    [inputs],
  );

  const reset = () =>
    setInputs({ ...BASELINE_INPUTS, allocation: { ...DEFAULT_ALLOCATION }, returns: { ...DEFAULT_RETURNS } });

  const valid = result.validation.valid;

  return (
    <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[minmax(0,1fr)_340px]">
      {/* ------------------------------ CHART ------------------------------ */}
      <div className="order-2 bg-ink-950 p-5 md:p-7 lg:order-1">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <span className="label-accent">Figure 02</span>
            <h3 className="display mt-2 text-2xl md:text-3xl">Household Wealth Accumulation</h3>
          </div>
          {diverged && (
            <button type="button" onClick={reset} className="btn">
              <RotateCcw size={12} /> Reset to research defaults
            </button>
          )}
        </div>

        <p className="mt-3 max-w-2xl font-display text-[1.0625rem] leading-relaxed text-ink-300">
          What happens when {rupees(inputs.annualSaving)} is saved every year for {inputs.years} years?
        </p>

        <AnimatePresence>
          {!valid && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-4">
                <Notice tone="caution" title="Allocation error">
                  {result.validation.message} Your weights have been left exactly as you entered them — the model
                  does not rescale them for you. The curve is still computed so you can see what the allocation
                  implies, but it does not describe a real portfolio.{' '}
                  {result.residualWeight > 0 ? (
                    <>
                      The {fractionAsPercent(result.residualWeight, 1)} you have not allocated is carried as
                      cash earning nothing — {rupees(result.residualValue)} by year {inputs.years} — so no
                      contribution is lost from the total.
                    </>
                  ) : (
                    <>
                      You have allocated {fractionAsPercent(-result.residualWeight, 1)} more than you contribute,
                      which the model carries as a negative balance of {rupees(result.residualValue)}: a
                      borrowing position rather than a portfolio.
                    </>
                  )}
                </Notice>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-5">
          <WealthChart
            scenario={result}
            baseline={baseline}
            showBaseline={diverged}
            aspect={compact ? 'compact' : 'wide'}
          />
        </div>

        <dl
          className={cn(
            'mt-6 grid grid-cols-2 gap-px border border-white/[0.07] bg-white/[0.07]',
            !compact && 'lg:grid-cols-4',
          )}
        >
          <Readout
            label="Total contributed"
            value={result.totalContributed}
            format={(n) => rupees(n)}
            sub={`${rupees(inputs.annualSaving)} × ${inputs.years} years`}
            tone="#5d6a72"
          />
          <Readout
            label="Final value"
            value={result.finalValue}
            format={(n) => rupees(n)}
            sub={
              valid
                ? `at ${fractionAsPercent(result.portfolioReturn, 2)} p.a.`
                : `invested portion at ${fractionAsPercent(result.assetReturn, 2)} p.a.`
            }
            tone="#e8933a"
          />
          <Readout
            label="Investment gain"
            value={result.investmentGain}
            format={(n) => rupees(n)}
            sub="final value − contributed"
            tone="#4fae86"
          />
          <Readout
            label="Wealth multiple"
            value={result.wealthMultiple}
            format={(n) => (n === null ? '—' : `${n.toFixed(2)}×`)}
            sub="per rupee contributed"
            tone="#5b9bd5"
          />
        </dl>

        {/* --------------------- BASELINE COMPARISON --------------------- */}
        <AnimatePresence>
          {diverged && !valid && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: EASE_OUT }}
              className="mt-px border border-white/[0.07] bg-ink-900 p-4"
            >
              <p className="label">Comparison withheld</p>
              <p className="mt-2 max-w-2xl text-[0.8125rem] leading-relaxed text-ink-400">
                A scenario whose weights do not sum to 100% is not comparable with the research baseline on
                equal terms: part of the contribution is not invested, so the weighted return Σ wᵢRᵢ no longer
                describes how the balance actually grows. Bring the allocation back to 100% and the comparison
                returns.
              </p>
            </motion.div>
          )}
          {diverged && valid && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: EASE_OUT }}
              className="mt-px grid grid-cols-1 gap-px border border-white/[0.07] bg-white/[0.07] sm:grid-cols-3"
            >
              <div className="bg-ink-900 p-4">
                <p className="label">Baseline</p>
                <p className="metric mt-2 text-lg text-[#5b9bd5]">{rupees(baseline.finalValue)}</p>
                <p className="mt-1 font-mono text-2xs text-ink-600">
                  observed portfolio · {fractionAsPercent(baseline.portfolioReturn, 2)} p.a.
                </p>
              </div>
              <div className="bg-ink-900 p-4">
                <p className="label">Your scenario</p>
                <p className="metric mt-2 text-lg text-[#e8933a]">{rupees(result.finalValue)}</p>
                <p className="mt-1 font-mono text-2xs text-ink-600">
                  {fractionAsPercent(result.portfolioReturn, 2)} p.a.
                </p>
              </div>
              <div className="bg-ink-900 p-4">
                <p className="label">Difference</p>
                <p
                  className="metric mt-2 text-lg"
                  style={{ color: comparison.difference >= 0 ? '#4fae86' : '#d3675d' }}
                >
                  {comparison.difference >= 0 ? '+' : '−'}
                  {rupees(Math.abs(comparison.difference))}
                </p>
                <p className="mt-1 font-mono text-2xs text-ink-600">
                  {comparison.percentDifference >= 0 ? '+' : ''}
                  {comparison.percentDifference.toFixed(1)}% · return{' '}
                  {comparison.returnDifference >= 0 ? '+' : ''}
                  {(comparison.returnDifference * 10000).toFixed(0)} bps
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <button type="button" className="btn" onClick={() => setShowCalc((s) => !s)} aria-expanded={showCalc}>
            {showCalc ? 'Hide calculation' : 'Show calculation'}
          </button>
          {!compact && (
            <Link to="/research/the-great-indian-promise#methodology" className="btn">
              Read the methodology <ArrowRight size={12} />
            </Link>
          )}
          {compact && (
            <Link to="/models/figure-2" className="btn btn-primary">
              Open the full model <ArrowRight size={12} />
            </Link>
          )}
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
              <div className="pt-5">
                <CalculationViewer result={result} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <p className="mt-5 border-t border-white/[0.07] pt-4 text-2xs leading-relaxed text-ink-600">
          {FIGURE2_CAVEAT}
        </p>
      </div>

      {/* ----------------------------- CONTROLS ---------------------------- */}
      <aside className="order-1 space-y-6 bg-ink-900/70 p-5 md:p-6 lg:order-2 lg:max-h-[calc(100vh-var(--lab-nav-h))] lg:overflow-y-auto">
        <section>
          <h4 className="label-accent">Saving</h4>
          <div className="mt-4 space-y-4">
            <Slider
              label="Annual contribution"
              value={inputs.annualSaving}
              min={0}
              max={1_000_000}
              step={10_000}
              baselineValue={BASELINE_INPUTS.annualSaving}
              onChange={(v) => set('annualSaving', v)}
              format={(v) => rupeesCompact(v)}
            />
            <Slider
              label="Horizon"
              value={inputs.years}
              min={1}
              max={50}
              step={1}
              baselineValue={BASELINE_INPUTS.years}
              onChange={(v) => set('years', v)}
              format={(v) => `${v} yr`}
            />
            <NumberField
              label="Starting capital"
              value={inputs.startingCapital}
              min={0}
              step={50_000}
              prefix="₹"
              onChange={(v) => set('startingCapital', Math.max(0, v))}
            />
            <SegmentedControl<ContributionFrequency>
              label="Frequency"
              value={inputs.frequency}
              onChange={(v) => set('frequency', v)}
              options={[
                { value: 'annual', label: 'Annual' },
                { value: 'quarterly', label: 'Quarterly' },
                { value: 'monthly', label: 'Monthly' },
              ]}
            />
            <SegmentedControl<ContributionTiming>
              label="Timing"
              value={inputs.timing}
              onChange={(v) => set('timing', v)}
              options={[
                { value: 'end', label: 'End of period', title: 'The paper’s convention.' },
                { value: 'start', label: 'Start of period', title: 'Each contribution earns one more period of growth.' },
              ]}
            />
          </div>
        </section>

        <section className="border-t border-white/[0.07] pt-5">
          <div className="flex items-baseline justify-between">
            <h4 className="label-accent">Portfolio</h4>
            <span
              className="metric text-xs"
              style={{ color: valid ? '#4fae86' : '#d3675d' }}
              data-numeric
            >
              {(result.validation.total * 100).toFixed(1)}%
            </span>
          </div>
          <div className="mt-4 space-y-4">
            {ASSET_KEYS.map((k) => (
              <Slider
                key={k}
                label={ASSETS[k].label}
                value={Math.round((inputs.allocation[k] ?? 0) * 1000) / 10}
                min={0}
                max={100}
                step={0.5}
                accent={ASSETS[k].colour}
                baselineValue={(DEFAULT_ALLOCATION[k] ?? 0) * 100}
                onChange={(v) => setWeight(k, v)}
                format={(v) => `${v.toFixed(1)}%`}
              />
            ))}
          </div>
          {!valid && (
            <p className="mt-3 font-mono text-2xs leading-relaxed text-[#d3675d]">
              Allocation must equal 100%.
            </p>
          )}
        </section>

        <section className="border-t border-white/[0.07] pt-5">
          <h4 className="label-accent">Assumed returns</h4>
          <p className="mt-2 text-2xs leading-relaxed text-ink-500">
            These are assumptions, not observations. Each default is set at or below its historical anchor.
          </p>
          <div className="mt-4 space-y-4">
            {ASSET_KEYS.map((k) => (
              <Slider
                key={k}
                label={`${ASSETS[k].label} return`}
                value={Math.round((inputs.returns[k] ?? 0) * 10000) / 100}
                min={-5}
                max={20}
                step={0.1}
                accent={ASSETS[k].colour}
                baselineValue={(DEFAULT_RETURNS[k] ?? 0) * 100}
                onChange={(v) => setReturn(k, v)}
                format={(v) => `${v.toFixed(1)}%`}
              />
            ))}
          </div>
        </section>

        <div className="border-t border-white/[0.07]">
          <Disclosure summary={<span>Variable classification</span>}>
            <ul className="space-y-3">
              {FIGURE2_CLASSIFICATION.map((c) => (
                <li key={c.variable} className="border-b border-white/[0.04] pb-3 last:border-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-[0.8125rem] text-ink-200">{c.variable}</span>
                    <span className="metric text-xs">{c.value}</span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <span
                      className="border px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-[0.14em]"
                      style={{
                        color: CLASS_TONE[c.classification],
                        borderColor: `${CLASS_TONE[c.classification]}55`,
                      }}
                    >
                      {c.classification}
                    </span>
                    <StatusBadge status={c.status} size="xs" />
                  </div>
                  <p className="mt-1.5 text-2xs leading-relaxed text-ink-500">{c.basis}</p>
                  {c.sourceUrl && (
                    <a
                      href={c.sourceUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-1 inline-block font-mono text-2xs text-ink-500 underline decoration-ink-700 underline-offset-2 hover:text-[#e8933a]"
                    >
                      {c.source}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </Disclosure>
        </div>
      </aside>
    </div>
  );
}

/**
 * The single-slider experiment (spec §22): one control, one causal chain,
 * baseline and scenario side by side. Deliberately narrower than the full
 * lab — it asks one question rather than offering every control.
 */
export function WealthExperiment() {
  const [financial, setFinancial] = useState(DEFAULT_ALLOCATION.financial * 100);

  const scenarioInputs = useMemo<Figure2Inputs>(
    () => ({
      ...BASELINE_INPUTS,
      allocation: reallocate(DEFAULT_ALLOCATION, 'property', 'financial', financial / 100),
      returns: { ...DEFAULT_RETURNS },
    }),
    [financial],
  );

  const comparison = useMemo(
    () => compareScenarios(BASELINE_INPUTS, scenarioInputs),
    [scenarioInputs],
  );
  const alloc = scenarioInputs.allocation;
  const moved = Math.abs(financial - DEFAULT_ALLOCATION.financial * 100) > 0.05;

  return (
    <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="bg-ink-900/70 p-5 md:p-6">
        <span className="label-accent">Experiment 01</span>
        <h3 className="display mt-2 text-2xl">Run an economic experiment</h3>
        <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-300">
          What happens if financial assets increase from 5% to 20%?
        </p>

        <div className="mt-6">
          <Slider
            label="Financial assets"
            value={financial}
            min={0}
            max={60}
            step={0.5}
            accent={ASSETS.financial.colour}
            baselineValue={DEFAULT_ALLOCATION.financial * 100}
            onChange={setFinancial}
            format={(v) => `${v.toFixed(1)}%`}
            hint="The offsetting change comes out of property, so the allocation stays at exactly 100%."
          />
        </div>

        <dl className="mt-5 space-y-1.5 border-t border-white/[0.07] pt-4">
          {ASSET_KEYS.map((k) => (
            <div key={k} className="flex items-center justify-between gap-3">
              <dt className="flex items-center gap-2 font-mono text-2xs text-ink-400">
                <span className="h-2 w-2" style={{ background: ASSETS[k].colour }} aria-hidden />
                {ASSETS[k].label}
              </dt>
              <dd className="metric text-xs" data-numeric>
                {fractionAsPercent(alloc[k] ?? 0, 1)}
              </dd>
            </div>
          ))}
        </dl>

        {alloc.property < 0 && (
          <p className="mt-4 font-mono text-2xs leading-relaxed text-[#d3675d]">
            Property has gone negative. The slider has taken more out of property than exists there — a
            borrowing position rather than a portfolio. The arithmetic still runs; it just no longer describes a
            household.
          </p>
        )}
      </div>

      <div className="bg-ink-950 p-5 md:p-7">
        {/* Causal chain — the point of the animation is that it shows propagation. */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 font-mono text-2xs uppercase tracking-[0.14em]">
          <span className={cn('transition-colors', moved ? 'text-[#5b9bd5]' : 'text-ink-600')}>
            Financial share {moved ? (financial > DEFAULT_ALLOCATION.financial * 100 ? '↑' : '↓') : '—'}
          </span>
          <span className="text-ink-700">→</span>
          <span className={cn('transition-colors', moved ? 'text-[#5b9bd5]' : 'text-ink-600')}>
            Portfolio return {fractionAsPercent(comparison.scenario.portfolioReturn, 2)}
          </span>
          <span className="text-ink-700">→</span>
          <span className={cn('transition-colors', moved ? 'text-[#e8933a]' : 'text-ink-600')}>
            Final wealth
          </span>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-px border border-white/[0.07] bg-white/[0.07] sm:grid-cols-3">
          <div className="bg-ink-900 p-4">
            <p className="label">Baseline</p>
            <p className="metric mt-2 text-xl text-[#5b9bd5]" data-numeric>
              {rupees(comparison.baseline.finalValue)}
            </p>
            <p className="mt-1 font-mono text-2xs text-ink-600">observed 5% financial</p>
          </div>
          <div className="bg-ink-900 p-4">
            <p className="label">Your scenario</p>
            <AnimatedNumber
              value={comparison.scenario.finalValue}
              format={(n) => rupees(n)}
              className="metric mt-2 block text-xl text-[#e8933a]"
            />
            <p className="mt-1 font-mono text-2xs text-ink-600">{financial.toFixed(1)}% financial</p>
          </div>
          <div className="bg-ink-900 p-4">
            <p className="label">Difference</p>
            <AnimatedNumber
              value={comparison.difference}
              format={(n) => (n === null ? '—' : `${n >= 0 ? '+' : '−'}${rupees(Math.abs(n))}`)}
              className="metric mt-2 block text-xl"
            />
            <p className="mt-1 font-mono text-2xs text-ink-600">
              {comparison.percentDifference >= 0 ? '+' : ''}
              {comparison.percentDifference.toFixed(1)}% on identical contributions
            </p>
          </div>
        </div>

        <div className="mt-5">
          <WealthChart
            scenario={comparison.scenario}
            baseline={comparison.baseline}
            showBaseline={moved}
            aspect="compact"
          />
        </div>

        <p className="mt-4 border-t border-white/[0.07] pt-4 text-2xs leading-relaxed text-ink-600">
          {FIGURE2_CAVEAT}
        </p>
      </div>
    </div>
  );
}
