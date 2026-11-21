import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { RETRIEVAL_NOTE } from '../data/sources';
import { Notice } from '../components/ui';
import { EASE_OUT } from '../lib/motion';
import { PageHeader } from './PageHeader';

const CHAIN = ['Research', 'Data', 'Model', 'Experiment', 'Insight'];

const PRINCIPLES = [
  {
    n: '01',
    title: 'Every number carries its paperwork',
    body: 'A value without a source, a reporting period and a status is not evidence. Every figure on this site travels inside a record that carries all three, and the provenance panel attached to it is not decorative — it is where the number is actually justified.',
  },
  {
    n: '02',
    title: 'Absence is shown as absence',
    body: 'Missing data is never replaced with a zero, a sample mean, the previous period’s value or an interpolation. Where a figure could not be obtained, the lab says so and names what is missing. Sixteen of the forty-two cells in the BFPI panel are empty, and they are visibly empty.',
  },
  {
    n: '03',
    title: 'Observations and assumptions are never mixed',
    body: 'The household allocation in Figure 2 is a measurement. The thirty-year returns applied to it are not. Conflating them would make an arithmetic exercise look like a forecast, so every variable is classified and the classification is on the page next to the control that changes it.',
  },
  {
    n: '04',
    title: 'Disagreement is surfaced, not resolved',
    body: 'Where authoritative sources conflict — as they do on state GSDP levels, by roughly a factor of two — the lab shows both and explains what it could not establish. Quietly picking one would be the easier product and the worse research.',
  },
  {
    n: '05',
    title: 'The working is always available',
    body: 'Every model output can be expanded into the calculation that produced it, copied as text, and exported as data. Nothing is precomputed: if the working and the answer could ever disagree, the answer is not worth much.',
  },
  {
    n: '06',
    title: 'Motion carries meaning',
    body: 'A curve morphs because an assumption changed; a pillar falls because an input moved through it. Animation here is a way of showing causality, which is why it reduces to instant state changes when the reader prefers reduced motion rather than simply running faster.',
  },
];

export function About() {
  return (
    <>
      <PageHeader
        label="About"
        title="Why IEIL?"
        lede="Economics is often presented as something to read rather than something to interrogate. A paper states a result; a reader accepts or doubts it; nothing in between is available. IEIL exists to put something in between."
      />

      <div className="mx-auto max-w-[1400px] px-5 py-14 md:px-10 md:py-20">
        <section className="mx-auto max-w-reading">
          <p className="prose-research text-pretty">
            The conventional research artefact is a PDF. It is an excellent format for stating a conclusion and a
            poor one for interrogating it. A figure in a PDF is a picture of a calculation that happened
            somewhere else, under assumptions described in prose, which the reader cannot vary. The reader’s only
            options are to trust the author or to rebuild the model themselves.
          </p>
          <p className="prose-research mt-5 text-pretty">
            Everything on this site is built on the premise that the second option should be one gesture rather
            than an afternoon. Figure 2 is not an image of a wealth curve — it is the model, running in the
            browser, with its assumptions exposed as controls. Change the property return and the paper’s central
            claim weakens in front of you. Set every return equal and it disappears entirely, as it should. That
            is not a weakness of the argument; it is what it means for an argument to be testable.
          </p>
          <p className="prose-research mt-5 text-pretty">
            The same discipline applies to the data. An economics site that presents a plausible-looking number
            without a traceable source is doing something worse than being wrong — it is being unfalsifiable.
            Where this build could not verify a figure, it says so; where sources conflict, it shows the conflict;
            where a value does not exist, it shows nothing rather than something convenient.
          </p>
        </section>

        <section className="mt-16">
          <p className="label mb-5">The chain</p>
          <div className="flex flex-wrap items-center gap-3">
            {CHAIN.map((step, i) => (
              <motion.div
                key={step}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.5, ease: EASE_OUT }}
                className="flex items-center gap-3"
              >
                <span className="border border-white/[0.12] px-4 py-2.5 font-mono text-2xs uppercase tracking-[0.16em] text-ink-200">
                  {step}
                </span>
                {i < CHAIN.length - 1 && <span className="text-ink-700">→</span>}
              </motion.div>
            ))}
          </div>
          <p className="mt-5 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-400">
            A reader should be able to move along this chain in either direction. From a claim in the paper to
            the figure that supports it, to the model behind the figure, to the assumptions behind the model, to
            the source behind the assumptions — and back.
          </p>
        </section>

        <section className="mt-20">
          <p className="label mb-6">Principles</p>
          <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] md:grid-cols-2 lg:grid-cols-3">
            {PRINCIPLES.map((p, i) => (
              <motion.div
                key={p.n}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: Math.min(i * 0.05, 0.3), duration: 0.5, ease: EASE_OUT }}
                className="bg-ink-950 p-5 md:p-6"
              >
                <span className="metric text-2xl text-[#e8933a] opacity-40">{p.n}</span>
                <h3 className="display mt-3 text-[1.1875rem] leading-snug">{p.title}</h3>
                <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-400 text-pretty">{p.body}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <section className="mt-20 grid gap-8 lg:grid-cols-2">
          <div>
            <p className="label mb-4">How it is built</p>
            <dl className="space-y-px border border-white/[0.09] bg-white/[0.09]">
              {[
                ['Frontend', 'React 19, TypeScript, Vite'],
                ['Styling', 'Tailwind CSS with a fixed token set'],
                ['Motion', 'Framer Motion, spring physics throughout'],
                ['Scrolling', 'Lenis, disabled under reduced motion'],
                ['Visualisation', 'D3 scales and shapes over hand-built SVG'],
                ['WebGL', 'Three.js via React Three Fiber, lazy-loaded'],
                ['Model engines', 'Pure TypeScript, no UI dependency'],
                ['Tests', '85 unit tests over the two model engines'],
              ].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-4 bg-ink-950 px-4 py-2.5">
                  <dt className="label">{k}</dt>
                  <dd className="font-mono text-2xs text-ink-300">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="space-y-4">
            <p className="label mb-4">Standing disclosures</p>
            <Notice tone="caution" title="BFPI">
              BFPI is an original composite index constructed for analytical purposes. It is not an official RBI
              measure or banking-sector rating. Results depend on the selected sample, period, variables,
              standardisation method and weighting methodology. It does not establish that any bank is best,
              safest or strongest.
            </Notice>
            <Notice tone="caution" title="Figure 2">
              Every result is conditional on the assumptions entered. Historical returns do not guarantee future
              performance. No allocation shown is a recommendation, and nothing on this site is financial advice.
            </Notice>
            <Notice title="Data retrieval">{RETRIEVAL_NOTE}</Notice>
          </div>
        </section>

        <section className="mt-20 border-t border-white/[0.07] pt-10">
          <h2 className="display max-w-[20ch] text-balance text-[1.75rem] leading-tight md:text-[2.5rem]">
            What if an economics research paper were an interactive laboratory instead of a PDF?
          </h2>
          <div className="mt-7 flex flex-wrap gap-2">
            <Link to="/research/the-great-indian-promise" className="btn btn-primary">
              Read the research <ArrowRight size={13} />
            </Link>
            <Link to="/models" className="btn">
              Explore the lab <ArrowRight size={13} />
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
