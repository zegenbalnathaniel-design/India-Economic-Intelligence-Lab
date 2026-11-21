import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { HairlineFigure, type HairlineName } from '../components/Lab/HairlineFigure';
import { EASE_OUT } from '../lib/motion';

export function PageHeader({
  label,
  title,
  lede,
  actions,
  figure,
}: {
  label: string;
  title: string;
  lede?: ReactNode;
  actions?: ReactNode;
  figure?: { name: HairlineName; label: string; idle: string; caption?: (read: string) => string | null; accent?: string };
}) {
  return (
    <header className="border-b border-white/[0.07] pt-28 md:pt-36">
      <div className={`mx-auto grid max-w-[1400px] items-center gap-10 px-5 pb-12 md:px-10 md:pb-16 ${figure ? 'lg:grid-cols-[1.2fr_0.8fr]' : ''}`}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <div className="flex items-center gap-3">
            <span className="h-px w-8" style={{ background: "var(--accent)" }} aria-hidden />
            <span className="label-accent">{label}</span>
          </div>
          <h1 className="display mt-6 max-w-[20ch] text-balance text-[2.25rem] leading-[1.05] md:text-[3.75rem]">
            {title}
          </h1>
          {lede && (
            <div className="mt-6 max-w-[64ch] text-[1rem] leading-relaxed text-ink-400 text-pretty">{lede}</div>
          )}
          {actions && <div className="mt-8 flex flex-wrap gap-3">{actions}</div>}
        </motion.div>
        {figure && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, ease: EASE_OUT, delay: 0.1 }}
            className="ticked border border-white/[0.08] bg-ink-900/70 p-5"
          >
            <HairlineFigure maxWidth={420} {...figure} />
          </motion.div>
        )}
      </div>
    </header>
  );
}
