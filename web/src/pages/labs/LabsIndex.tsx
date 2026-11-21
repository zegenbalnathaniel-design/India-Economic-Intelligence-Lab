import { motion } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { HairlineFigure } from '../../components/Lab/HairlineFigure';
import { LABS } from '../../labs/registry';
import { EASE_OUT } from '../../lib/motion';

const FACES = [
  { name: 'MARKETS', desc: 'Repo rate, oil, the rupee and capex — the transmission simulator', to: '/labs/transmission' },
  { name: 'PEOPLE', desc: 'Income, wealth and who holds them — inequality & financialisation', to: '/labs/inequality' },
  { name: 'INSTITUTIONS', desc: 'States, convergence and regional divergence', to: '/labs/states' },
  { name: 'DATA', desc: 'Every relationship tested, every regression diagnosed', to: '/labs/relationships' },
];

function faceForAz(az: number) {
  const a = ((az % 360) + 360) % 360;
  if (a >= 315 || a < 45) return FACES[0];
  if (a < 135) return FACES[1];
  if (a < 225) return FACES[2];
  return FACES[3];
}

export function LabsIndex() {
  const [face, setFace] = useState(FACES[0]);
  const navigate = useNavigate();

  return (
    <>
      <header className="relative overflow-hidden border-b border-white/[0.07] pt-28 md:pt-36">
        <div aria-hidden className="pointer-events-none absolute inset-0 lab-grid opacity-70" style={{ maskImage: 'radial-gradient(60% 70% at 70% 40%, black, transparent)' }} />
        <div className="relative mx-auto grid max-w-[1400px] items-center gap-12 px-5 pb-16 md:px-10 md:pb-24 lg:grid-cols-[1.05fr_0.95fr]">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE_OUT }}>
            <div className="flex items-center gap-3">
              <span className="spectrum-bar h-px w-12" aria-hidden />
              <span className="label-accent">The research labs</span>
            </div>
            <h1 className="display mt-6 max-w-[14ch] text-balance text-[2.8rem] leading-[1.02] md:text-[4.6rem]">
              Ten labs. <span className="spectrum-text">One economy</span>, taken apart.
            </h1>
            <p className="mt-6 max-w-[58ch] text-[1rem] leading-relaxed text-ink-300">
              Each lab asks one question of real Indian data — RBI, MoSPI, NHB, the World Inequality Lab, the World Bank — and
              shows the working. The arithmetic runs in your browser and is tested against the lab’s original Python.
            </p>
            <div className="mt-8 flex flex-wrap gap-2">
              {LABS.map((l) => (
                <Link key={l.slug} to={`/labs/${l.slug}`} className="chip" style={{ borderColor: `${l.accent}66`, color: l.accent }}>
                  {l.short}
                </Link>
              ))}
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, ease: EASE_OUT, delay: 0.1 }}
            className="ticked border border-white/[0.08] bg-ink-900/70 p-5 md:p-8"
          >
            <HairlineFigure
              name="Turntable"
              accent="#f3c542"
              label="A turntable with four faces: Markets, People, Institutions and Data, each a way into the labs."
              idle="Drag to turn — four ways into the labs."
              caption={(read) => {
                const m = /az (\d+)°/.exec(read);
                if (!m) return null;
                const f = faceForAz(Number(m[1]));
                if (f !== face) setTimeout(() => setFace(f), 0);
                return `${f.name}\n${f.desc}`;
              }}
            />
            <button type="button" className="btn btn-primary mt-4 w-full justify-center" onClick={() => navigate(face.to)}>
              Open {face.name.toLowerCase()} <ArrowUpRight size={13} />
            </button>
          </motion.div>
        </div>
      </header>

      <div className="mx-auto max-w-[1400px] px-5 py-16 md:px-10 md:py-24">
        <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] md:grid-cols-2 xl:grid-cols-3">
          {LABS.map((l, i) => (
            <motion.div
              key={l.slug}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.7, delay: (i % 3) * 0.08, ease: EASE_OUT }}
            >
              <Link to={`/labs/${l.slug}`} className="group relative flex h-full flex-col bg-ink-950 p-6 transition-colors duration-300 hover:bg-ink-900 md:p-8">
                <span aria-hidden className="absolute inset-x-0 top-0 h-[2px] origin-left scale-x-0 transition-transform duration-500 group-hover:scale-x-100" style={{ background: l.accent }} />
                <span aria-hidden className="pointer-events-none absolute right-0 top-0 h-40 w-40 opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100" style={{ background: `radial-gradient(circle, ${l.accent}33, transparent 70%)` }} />
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-[2.2rem] font-light leading-none" style={{ color: l.accent }}>
                    {l.n}
                  </span>
                  <span className="label">{l.group}</span>
                </div>
                <h2 className="display mt-6 text-[1.7rem] leading-tight">{l.title}</h2>
                <p className="mt-3 font-display text-[1.05rem] italic leading-snug text-ink-100">{l.question}</p>
                <p className="mt-4 flex-1 text-[13px] leading-relaxed text-ink-400">{l.blurb}</p>
                <span className="mt-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em]" style={{ color: l.accent }}>
                  Enter the lab <ArrowUpRight size={13} className="transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                </span>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </>
  );
}

export default LabsIndex;
