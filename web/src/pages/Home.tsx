import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Suspense, lazy } from 'react';
import { Link } from 'react-router-dom';
import { EconomicPulse } from '../components/EconomicPulse/EconomicPulse';
import { EconomicTimeline } from '../components/EconomicTimeline/EconomicTimeline';
import { Figure2Lab, WealthExperiment } from '../components/Figure2Lab/Figure2Lab';
import { Hero } from '../components/Hero/Hero';
import { IndiaMap } from '../components/IndiaMap/IndiaMap';
import { ResearchLibrary } from '../components/ResearchLibrary/ResearchLibrary';
import { SectionShell } from '../components/ui';
import { GREAT_INDIAN_PROMISE } from '../data/research/greatIndianPromise';
import { EASE_OUT } from '../lib/motion';

// WebGL and the BFPI lab are the two heaviest things on the page; neither is
// needed to read the first two screens.
const EconomicGlobe = lazy(() =>
  import('../components/EconomicGlobe/EconomicGlobe').then((m) => ({ default: m.EconomicGlobe })),
);
const BFPILab = lazy(() => import('../components/BFPI/BFPILab').then((m) => ({ default: m.BFPILab })));

function LazyFrame({ label, minHeight = 420 }: { label: string; minHeight?: number }) {
  return (
    <div
      className="flex items-center justify-center border border-white/[0.09] bg-ink-900/30"
      style={{ minHeight }}
    >
      <span className="label animate-pulse">Loading {label}…</span>
    </div>
  );
}

export function Home() {
  return (
    <>
      <Hero />

      <SectionShell
        id="pulse"
        index="01"
        label="Economic Pulse"
        title="Where the Indian economy stands"
        lede={
          <>
            Twelve indicators, each carrying its source, its reporting period and its status. Reporting periods
            are preserved exactly as the publisher labels them — FY2025-26 is never flattened into 2026. Click
            any tile for the vintages, the methodology and the provenance.
          </>
        }
      >
        <EconomicPulse />
      </SectionShell>

      <SectionShell
        id="global"
        index="02"
        label="India in the global economy"
        title="A goods deficit financed by services and remittances"
        lede={
          <>
            The external account in one quarter: US$86.1 bn of merchandise trade deficit, offset to within half a
            percent of GDP by services exports and money sent home. Drag to rotate; hover a flow for its source.
          </>
        }
      >
        <Suspense fallback={<LazyFrame label="the globe" minHeight={520} />}>
          <EconomicGlobe />
        </Suspense>
      </SectionShell>

      {/* ---------------------- Featured research ---------------------- */}
      <section id="featured" className="relative border-t border-white/[0.07] py-20 md:py-32">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background: 'radial-gradient(70% 50% at 20% 30%, rgba(232,147,58,0.06), transparent 65%)',
          }}
          aria-hidden
        />
        <div className="relative mx-auto max-w-[1400px] px-5 md:px-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.7, ease: EASE_OUT }}
          >
            <div className="flex items-baseline gap-4">
              <span className="label-accent">03</span>
              <span className="label">Featured research</span>
            </div>

            <h2 className="display mt-6 max-w-[14ch] text-balance text-[2.75rem] leading-[1.03] md:text-[5rem]">
              {GREAT_INDIAN_PROMISE.title}
            </h2>

            <p className="mt-7 max-w-[54ch] font-display text-[1.25rem] leading-snug text-ink-300 text-pretty">
              {GREAT_INDIAN_PROMISE.subtitle}
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <Link to={`/research/${GREAT_INDIAN_PROMISE.slug}`} className="btn btn-primary">
                Read the Research <ArrowRight size={13} />
              </Link>
              <Link to="/models/figure-2" className="btn">
                Explore Figure 2 <ArrowRight size={13} />
              </Link>
            </div>

            <div className="mt-12 grid gap-px border border-white/[0.09] bg-white/[0.09] sm:grid-cols-3">
              {[
                ['77%', 'of the average household portfolio is real estate', 'RBI Household Finance Committee, 2017'],
                ['5%', 'is held in financial assets', 'The same source. The paper is about this number.'],
                ['+28%', 'terminal wealth from shifting 15 pp into financial assets', 'Under the stated assumptions, over 30 years'],
              ].map(([stat, label, sub]) => (
                <div key={stat} className="bg-ink-950 p-5 md:p-6">
                  <p className="metric text-[2.5rem] leading-none text-[#e8933a]">{stat}</p>
                  <p className="mt-3 text-[0.875rem] leading-snug text-ink-200">{label}</p>
                  <p className="mt-2 font-mono text-2xs leading-snug text-ink-600">{sub}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      <SectionShell
        id="figure-2"
        index="04"
        label="Model 01 · Figure 2 Lab"
        title="Household Wealth Accumulation"
        lede={
          <>
            What happens when ₹1 lakh is saved every year for thirty years? The answer depends entirely on where
            the money goes. Move any control and the curve, the numbers and the working all recompute together.
          </>
        }
        actions={
          <Link to="/models/figure-2" className="btn">
            Open the full model <ArrowRight size={12} />
          </Link>
        }
      >
        <Figure2Lab compact />
      </SectionShell>

      <SectionShell
        id="bfpi"
        index="05"
        label="Model 02 · BFPI Lab"
        title="Bank Financial Performance Index"
        lede={
          <>
            A composite framework for evaluating bank performance across profitability, capital strength, asset
            quality and liquidity. An original analytical construction — not an RBI measure, not a rating, and
            not a prediction. Move an input and watch it propagate through its pillar into the composite.
          </>
        }
        actions={
          <Link to="/models/bfpi" className="btn">
            Open the full model <ArrowRight size={12} />
          </Link>
        }
      >
        <Suspense fallback={<LazyFrame label="the BFPI lab" minHeight={560} />}>
          <BFPILab />
        </Suspense>
      </SectionShell>

      <SectionShell
        id="experiments"
        index="06"
        label="Economic experiments"
        title="Change one thing. Watch what follows."
        lede={
          <>
            An experiment isolates a single variable so the causal chain is visible. Everything a slider produces
            is a hypothetical conditional on the inputs entered — never a forecast, never advice.
          </>
        }
        actions={
          <Link to="/experiments" className="btn">
            All experiments <ArrowRight size={12} />
          </Link>
        }
      >
        <WealthExperiment />
      </SectionShell>

      <SectionShell
        id="states"
        index="07"
        label="India Data Explorer"
        title="One country, several economies"
        lede={
          <>
            Per-capita income across eight major states differs by a factor of 3.6. Where a figure could not be
            obtained, or where sources conflict, the map says so rather than filling the gap.
          </>
        }
        actions={
          <Link to="/india" className="btn">
            Open the explorer <ArrowRight size={12} />
          </Link>
        }
      >
        <IndiaMap />
      </SectionShell>

      <SectionShell
        id="library"
        index="08"
        label="Research library"
        title="What the lab has published, and what it is working on"
        lede="Entries marked “In preparation” are not written — they name the data they need and do not have."
        actions={
          <Link to="/research" className="btn">
            Full library <ArrowRight size={12} />
          </Link>
        }
      >
        <ResearchLibrary limit={3} />
      </SectionShell>

      <SectionShell
        id="timeline"
        index="09"
        label="Economic timeline"
        title="Thirty-five years, six discontinuities"
        lede="Each entry separates what happened from what the data can support. Where credible estimates disagree — as they do on demonetisation — no number is reported."
      >
        <EconomicTimeline />
      </SectionShell>
    </>
  );
}
