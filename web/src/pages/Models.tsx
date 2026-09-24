import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EASE_OUT } from '../lib/motion';
import { PageHeader } from './PageHeader';

const MODELS = [
  {
    n: '01',
    title: 'Household Wealth Accumulation',
    subtitle: 'Figure 2',
    to: '/models/figure-2',
    question: 'What happens when ₹1 lakh is saved every year for thirty years?',
    description:
      'A deterministic accumulation model over the household portfolio the RBI’s Household Finance Committee measured. Allocation is observed; returns are assumptions, each anchored below its historical range and each editable. The model shows its full working and exports its series.',
    inputs: ['Annual saving', 'Horizon', 'Starting capital', 'Frequency', 'Four portfolio weights', 'Four assumed returns'],
    outputs: ['Portfolio return Σ wᵢRᵢ', 'Terminal wealth', 'Investment gain', 'Wealth multiple'],
    tone: '#e8933a',
  },
  {
    n: '02',
    title: 'Bank Financial Performance Index',
    subtitle: 'BFPI',
    to: '/models/bfpi',
    question: 'How does a bank sit within its peer group across four dimensions at once?',
    description:
      'An original composite index over profitability, capital, asset quality and liquidity, built by standardising six indicators within a selected sample and averaging them into four equally-weighted pillars. Relative by construction: change the sample and every score moves.',
    inputs: ['NIM', 'ROE', 'CET1', 'NPL ratio', 'Credit-loss provisions', 'LCR'],
    outputs: ['Six z-scores', 'Four pillar scores', 'Composite on a 0–100 scale', 'Full derivation'],
    tone: '#5b9bd5',
  },
];

export function Models() {
  return (
    <>
      <PageHeader
        label="The IEIL Model Lab"
        title="Two instruments, both fully open"
        lede="Neither model hides its arithmetic. Every output on this site is computed in the browser from inputs you can see and change, and every one of them exports the working that produced it."
      />

      <div className="mx-auto max-w-[1400px] px-5 py-16 md:px-10 md:py-24">
        <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-2">
          {MODELS.map((m, i) => (
            <motion.div
              key={m.n}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.08, ease: EASE_OUT }}
              className="group relative flex flex-col bg-ink-950 p-6 md:p-9"
            >
              <span
                aria-hidden
                className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 transition-transform duration-500 group-hover:scale-x-100"
                style={{ background: m.tone }}
              />

              <div className="flex items-baseline justify-between gap-4">
                <span className="metric text-[3.5rem] leading-none" style={{ color: m.tone, opacity: 0.35 }}>
                  {m.n}
                </span>
                <span className="label">{m.subtitle}</span>
              </div>

              <h2 className="display mt-6 text-[1.75rem] leading-tight md:text-[2.25rem]">{m.title}</h2>
              <p className="mt-4 font-display text-[1.0625rem] leading-snug text-ink-300">{m.question}</p>
              <p className="mt-5 text-[0.875rem] leading-relaxed text-ink-400 text-pretty">{m.description}</p>

              <dl className="mt-7 grid gap-5 sm:grid-cols-2">
                <div>
                  <dt className="label mb-2">Inputs you control</dt>
                  <dd>
                    <ul className="space-y-1">
                      {m.inputs.map((x) => (
                        <li key={x} className="font-mono text-2xs text-ink-400">
                          {x}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
                <div>
                  <dt className="label mb-2">What it computes</dt>
                  <dd>
                    <ul className="space-y-1">
                      {m.outputs.map((x) => (
                        <li key={x} className="font-mono text-2xs text-ink-400">
                          {x}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
              </dl>

              <div className="mt-auto pt-8">
                <Link to={m.to} className="btn btn-primary">
                  Open the model <ArrowRight size={13} />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>

        <p className="mx-auto mt-10 max-w-3xl text-center text-2xs leading-relaxed text-ink-600">
          Both engines are pure functions with no UI dependency, covered by 85 unit tests asserting the
          mathematics — closed-form agreement, directionality, equal weighting, the 0–100 transformation, missing
          values and edge cases. Mathematical correctness is not a matter of opinion.
        </p>
      </div>
    </>
  );
}
