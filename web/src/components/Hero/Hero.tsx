import { AnimatePresence, motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { EASE_OUT, useReducedMotionPref } from '../../lib/motion';

const SYSTEMS = ['GDP', 'MONETARY', 'HOUSEHOLDS', 'BANKING', 'RESEARCH'] as const;
const DOTS = (name: string) => '.'.repeat(Math.max(2, 18 - name.length));

/**
 * The boot sequence. It is brief by design — five lines, about a second and
 * a half — and it is skipped entirely under reduced motion or on a repeat
 * visit within the session, because a loading ritual that cannot be
 * dismissed stops being elegant the second time you see it.
 */
function BootSequence({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (step > SYSTEMS.length + 1) {
      onDone();
      return;
    }
    const delay = step === 0 ? 260 : step <= SYSTEMS.length ? 150 : 420;
    const t = setTimeout(() => setStep((s) => s + 1), delay);
    return () => clearTimeout(t);
  }, [step, onDone]);

  return (
    <motion.div
      className="absolute inset-0 z-20 flex items-center justify-center bg-ink-950 px-5"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: EASE_OUT }}
    >
      <div className="w-full max-w-md font-mono text-2xs leading-[1.9] sm:text-xs">
        <p className="text-ink-500">
          <span className="text-[#e8933a]">IEIL</span> // INDIA ECONOMICS INTELLIGENCE LAB
        </p>
        <p className="mt-3 text-ink-600">INITIALISING ECONOMIC SYSTEM...</p>
        <div className="mt-3 space-y-0.5">
          {SYSTEMS.map((s, i) => (
            <motion.p
              key={s}
              initial={{ opacity: 0 }}
              animate={{ opacity: step > i ? 1 : 0 }}
              transition={{ duration: 0.12 }}
              className="flex justify-between text-ink-400"
            >
              <span>
                {s} <span className="text-ink-700">{DOTS(s)}</span>
              </span>
              <span className="text-[#4fae86]">ONLINE</span>
            </motion.p>
          ))}
        </div>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: step > SYSTEMS.length ? 1 : 0 }}
          transition={{ duration: 0.2 }}
          className="mt-3 tracking-[0.2em] text-ink-100"
        >
          SYSTEM READY
        </motion.p>
      </div>
    </motion.div>
  );
}

export function Hero() {
  const reduced = useReducedMotionPref();
  const alreadyBooted = typeof sessionStorage !== 'undefined' && sessionStorage.getItem('ieil-booted') === '1';
  const [booting, setBooting] = useState(!reduced && !alreadyBooted);
  const ref = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '22%']);
  const opacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);

  const finish = () => {
    try {
      sessionStorage.setItem('ieil-booted', '1');
    } catch {
      /* private browsing — the sequence simply replays */
    }
    setBooting(false);
  };

  return (
    <div ref={ref} className="relative min-h-[92vh] overflow-hidden">
      {/* Analytical grid, not decoration: it establishes the instrument frame. */}
      <div className="lab-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 80% at 50% 0%, rgba(232,147,58,0.07), transparent 55%), radial-gradient(90% 60% at 50% 100%, rgba(91,155,213,0.05), transparent 60%)',
        }}
        aria-hidden
      />

      <AnimatePresence>{booting && <BootSequence onDone={finish} />}</AnimatePresence>

      <motion.div
        style={reduced ? undefined : { y, opacity }}
        className="relative mx-auto flex min-h-[92vh] max-w-[1400px] flex-col justify-center px-5 pb-20 pt-32 md:px-10"
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: booting ? 0 : 1 }}
          transition={{ duration: 0.7, delay: booting ? 0 : 0.1, ease: EASE_OUT }}
        >
          <div className="flex items-center gap-3">
            <span className="h-px w-8 bg-[#e8933a]" aria-hidden />
            <span className="label-accent">India Economics Intelligence Lab</span>
          </div>

          <h1 className="display mt-8 max-w-[15ch] text-balance text-[2.75rem] leading-[1.02] sm:text-[4rem] md:text-[5.5rem] lg:text-[6.5rem]">
            Understanding India through data, research and experimentation.
          </h1>

          <p className="mt-8 max-w-[58ch] text-[1.0625rem] leading-relaxed text-ink-400 text-pretty">
            An independent economics research laboratory exploring growth, inequality, wealth, banking,
            policy and India’s changing economic structure.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-3">
            <Link to="/models" className="btn btn-primary">
              Explore the Lab <ArrowRight size={13} />
            </Link>
            <Link to="/research/the-great-indian-promise" className="btn">
              Read the Research <ArrowRight size={13} />
            </Link>
          </div>

          <p className="mt-12 max-w-[50ch] border-l border-white/[0.09] pl-4 font-mono text-2xs leading-relaxed text-ink-600">
            Don’t just read economics. Experiment with it.
            <br />
            Every number on this site carries its source, its reporting period and its status.
          </p>
        </motion.div>
      </motion.div>

      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: booting ? 0 : 1 }}
        transition={{ delay: 1, duration: 0.6 }}
        style={reduced ? undefined : { opacity }}
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-ink-700">Scroll</span>
      </motion.div>
    </div>
  );
}
