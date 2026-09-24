import { Suspense, lazy } from 'react';
import { WealthExperiment } from '../components/Figure2Lab/Figure2Lab';
import { Notice } from '../components/ui';
import { PageHeader } from './PageHeader';

const BFPILab = lazy(() => import('../components/BFPI/BFPILab').then((m) => ({ default: m.BFPILab })));

export function Experiments() {
  return (
    <>
      <PageHeader
        label="Experiments"
        title="Change one thing. Watch what follows."
        lede="An experiment isolates a single variable so the causal chain is visible rather than asserted. Everything below is conditional on the inputs you enter: a hypothetical, never a forecast, and never advice."
      />

      <div className="mx-auto max-w-[1400px] space-y-20 px-5 py-12 md:px-10 md:py-16">
        <section id="wealth" className="scroll-mt-24">
          <div className="flex flex-wrap items-baseline gap-4">
            <span className="label-accent">Wealth</span>
            <span className="label">Figure 2 · household portfolio</span>
          </div>
          <h2 className="display mt-3 text-[1.75rem] md:text-[2.25rem]">
            What if financial assets rose from 5% to 20%?
          </h2>
          <p className="mt-4 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-400">
            One slider, one offsetting change, everything else held fixed. The chain runs: financial share →
            weighted portfolio return → terminal wealth. Contributions never change, so anything that separates
            the two curves is composition alone.
          </p>
          <div className="mt-7">
            <WealthExperiment />
          </div>
        </section>

        <section id="banking" className="scroll-mt-24">
          <div className="flex flex-wrap items-baseline gap-4">
            <span className="label-accent">Banking</span>
            <span className="label">BFPI · stress test</span>
          </div>
          <h2 className="display mt-3 text-[1.75rem] md:text-[2.25rem]">Stress the bank</h2>
          <p className="mt-4 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-400">
            Raise the NPL ratio and watch it travel: NPL ↑ → Asset Quality ↓ → BFPI ↓. Because BFPI is relative,
            editing a bank also moves the sample it is measured against, and the panel recomputes both. Try NIM,
            capital, provisions and LCR too — each one enters exactly one pillar, so the propagation is legible.
          </p>
          <div className="mt-7">
            <Suspense
              fallback={
                <div className="flex min-h-[560px] items-center justify-center border border-white/[0.09] bg-ink-900/30">
                  <span className="label animate-pulse">Loading the BFPI lab…</span>
                </div>
              }
            >
              <BFPILab initialBank="sbi" />
            </Suspense>
          </div>
        </section>

        <section id="economics" className="scroll-mt-24">
          <div className="flex flex-wrap items-baseline gap-4">
            <span className="label-accent">Economics</span>
            <span className="label">In preparation</span>
          </div>
          <h2 className="display mt-3 text-[1.75rem] md:text-[2.25rem]">What is not here yet</h2>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <Notice tone="missing" title="Monetary transmission">
              An experiment moving the repo rate through deposit and lending rates to bank margins would be the
              natural third instrument. It needs the RBI weighted-average deposit and lending-rate series, which
              this build could not obtain. Building it on assumed pass-through coefficients would be a
              simulation of a belief rather than an experiment on evidence, so it is not here.
            </Notice>
            <Notice tone="missing" title="Distributional wealth">
              The composition effect in Figure 2 describes a representative household. Running it across the
              wealth distribution — where composition varies sharply and the effect almost certainly widens
              inequality — needs AIDIS unit-level microdata rather than published averages.
            </Notice>
          </div>
        </section>
      </div>
    </>
  );
}
