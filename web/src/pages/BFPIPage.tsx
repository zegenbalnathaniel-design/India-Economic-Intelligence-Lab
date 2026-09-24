import { ArrowRight } from 'lucide-react';
import { Suspense, lazy } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { BankExplorer } from '../components/BankExplorer/BankExplorer';
import { BANKS, PANEL_CAVEATS } from '../data/banking/panel';
import { Notice } from '../components/ui';
import { PageHeader } from './PageHeader';

// The lab carries the stress-test UI and the decomposition chart; keeping it
// in its own chunk means the methodology and explorer load without it.
const BFPILab = lazy(() => import('../components/BFPI/BFPILab').then((m) => ({ default: m.BFPILab })));

function LabFallback() {
  return (
    <div className="flex min-h-[560px] items-center justify-center border border-white/[0.09] bg-ink-900/30">
      <span className="label animate-pulse">Loading the BFPI lab…</span>
    </div>
  );
}

export function BFPIPage() {
  const [params] = useSearchParams();
  const bank = params.get('bank');
  const initialBank = bank && BANKS.some((b) => b.id === bank) ? bank : 'icicibank';

  return (
    <>
      <PageHeader
        label="Model 02 · BFPI"
        title="Bank Financial Performance Index"
        lede="A composite framework for evaluating bank performance across profitability, capital strength, asset quality and liquidity. BFPI is an original constructed analytical index — not an RBI index, not an official banking-sector rating, and not a prediction of future performance."
        actions={
          <>
            <Link to="/models/bfpi/methodology" className="btn btn-primary">
              Read the methodology <ArrowRight size={12} />
            </Link>
            <Link to="/experiments#banking" className="btn">
              Stress the bank <ArrowRight size={12} />
            </Link>
          </>
        }
      />

      <div className="mx-auto max-w-[1400px] space-y-16 px-5 py-10 md:px-10 md:py-14">
        <Suspense fallback={<LabFallback />}>
          <BFPILab initialBank={initialBank} />
        </Suspense>

        <section id="explorer" className="scroll-mt-24">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <span className="label-accent">Bank explorer</span>
              <h2 className="display mt-2 text-[1.75rem] md:text-[2.25rem]">Compare, without ranking</h2>
            </div>
          </div>
          <p className="mt-4 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-400">
            Choose which banks form the sample, which variables to display, and whether to read raw values,
            standardised scores or pillar composites. Banks are listed in a fixed order and never sorted by
            score: sorting a composite invites the "best bank" reading this index cannot support.
          </p>
          <div className="mt-7">
            <BankExplorer />
          </div>
        </section>

        <section>
          <h2 className="display text-[1.75rem]">What this sample can and cannot support</h2>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <ul className="space-y-3">
              {PANEL_CAVEATS.map((c) => (
                <li key={c} className="flex gap-3 text-[0.875rem] leading-relaxed text-ink-300">
                  <span aria-hidden className="mt-[0.6em] h-px w-3 shrink-0 bg-[#e8933a]" />
                  {c}
                </li>
              ))}
            </ul>
            <div className="space-y-4">
              <Notice tone="caution" title="Interpretation">
                BFPI describes position within the selected sample and period. Do not call a bank best, worst,
                safest, strongest or weakest on this evidence. A bank scoring 58 is not "safer" than one scoring
                48 — it sits above the sample centre on four standardised dimensions in one financial year, with
                one of those dimensions measured on an incomplete indicator set.
              </Notice>
              <Notice title="Time series">
                A multi-year panel would let the index be read through a rate cycle, which is the more
                interesting question. This build covers FY2025 only: the historical disclosures were not
                obtainable, and a series has not been constructed from partial data. It is listed in the
                research library as work in preparation.
              </Notice>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
