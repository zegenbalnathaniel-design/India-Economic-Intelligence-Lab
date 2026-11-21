import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { EASE_OUT } from '../lib/motion';

export function PageHeader({
  label,
  title,
  lede,
  actions,
}: {
  label: string;
  title: string;
  lede?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="border-b border-white/[0.07] pt-28 md:pt-36">
      <div className="mx-auto max-w-[1400px] px-5 pb-12 md:px-10 md:pb-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <div className="flex items-center gap-3">
            <span className="h-px w-8 bg-[#e8933a]" aria-hidden />
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
      </div>
    </header>
  );
}
