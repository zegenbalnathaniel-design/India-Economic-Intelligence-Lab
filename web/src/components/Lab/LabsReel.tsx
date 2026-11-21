import { motion, useScroll, useSpring, useTransform } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { LABS } from '../../labs/registry';
import { useReducedMotionPref } from '../../lib/motion';

/**
 * The seven labs as a scroll-driven reel: the section pins while vertical
 * scroll slides the cards sideways. Falls back to a plain grid under
 * reduced motion and on narrow screens, where pinning fights the thumb.
 */
export function LabsReel() {
  const reduced = useReducedMotionPref();
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1024);
  useEffect(() => {
    const on = () => setWide(window.innerWidth >= 1024);
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);

  const outer = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const [travel, setTravel] = useState(0);
  useEffect(() => {
    const measure = () => {
      if (track.current) setTravel(Math.max(0, track.current.scrollWidth - window.innerWidth + 80));
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [wide]);

  const { scrollYProgress } = useScroll({ target: outer, offset: ['start start', 'end end'] });
  const smooth = useSpring(scrollYProgress, { stiffness: 90, damping: 24, mass: 0.5 });
  const x = useTransform(smooth, [0, 1], [0, -travel]);
  const bar = useTransform(smooth, [0, 1], ['0%', '100%']);

  const cards = LABS.map((l, i) => (
    <Link
      key={l.slug}
      to={`/labs/${l.slug}`}
      className="group relative flex h-full w-full shrink-0 flex-col overflow-hidden border border-white/[0.09] bg-ink-950/90 p-7 transition-colors duration-300 hover:bg-ink-900 lg:w-[420px]"
    >
      <span aria-hidden className="absolute inset-x-0 top-0 h-[2px]" style={{ background: l.accent }} />
      <span aria-hidden className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full opacity-40 blur-3xl transition-opacity duration-500 group-hover:opacity-80" style={{ background: l.accent }} />
      <div className="relative flex items-baseline justify-between">
        <span className="font-mono text-[3rem] font-light leading-none" style={{ color: l.accent }}>
          {String(i + 1).padStart(2, '0')}
        </span>
        <span className="label">{l.group}</span>
      </div>
      <h3 className="display relative mt-8 text-[1.85rem] leading-tight">{l.title}</h3>
      <p className="relative mt-3 font-display text-[1.1rem] italic leading-snug text-ink-100">{l.question}</p>
      <p className="relative mt-4 flex-1 text-[13px] leading-relaxed text-ink-400">{l.blurb}</p>
      <span className="relative mt-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em]" style={{ color: l.accent }}>
        Enter <ArrowUpRight size={13} className="transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </span>
    </Link>
  ));

  if (reduced || !wide) {
    return <div className="mx-auto grid max-w-[1400px] gap-4 px-5 md:grid-cols-2 md:px-10">{cards}</div>;
  }

  return (
    <div ref={outer} style={{ height: `calc(100vh + ${travel}px)` }} className="relative">
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <motion.div ref={track} style={{ x }} className="flex h-[min(560px,70vh)] gap-5 pl-10 pr-10 will-change-transform">
          {cards}
          <Link to="/labs" className="flex w-[300px] shrink-0 flex-col items-center justify-center border border-dashed border-white/[0.14] text-center transition-colors hover:border-[var(--accent)]">
            <span className="display text-[1.6rem]">All seven labs</span>
            <span className="label mt-3 inline-flex items-center gap-2">
              Open the index <ArrowUpRight size={12} />
            </span>
          </Link>
        </motion.div>
        <div className="mx-10 mt-8 h-px bg-white/[0.08]">
          <motion.div className="spectrum-bar h-px" style={{ width: bar }} />
        </div>
      </div>
    </div>
  );
}
