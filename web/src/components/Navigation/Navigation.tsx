import { AnimatePresence, motion, useMotionValueEvent, useScroll } from 'framer-motion';
import { Menu, Search, X } from 'lucide-react';
import { useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../lib/format';
import { EASE_OUT, SPRING } from '../../lib/motion';
import { NAV_ITEMS } from './items';

export function Navigation({ onOpenPalette }: { onOpenPalette: () => void }) {
  const { scrollY } = useScroll();
  const [compact, setCompact] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useMotionValueEvent(scrollY, 'change', (v) => setCompact(v > 40));

  return (
    <>
      <motion.header
        className="fixed inset-x-0 top-0 z-50"
        initial={false}
        animate={{
          backgroundColor: compact ? 'rgba(8,9,10,0.82)' : 'rgba(8,9,10,0)',
          borderBottomColor: compact ? 'rgba(255,255,255,0.09)' : 'rgba(255,255,255,0)',
        }}
        transition={{ duration: 0.3, ease: EASE_OUT }}
        style={{ backdropFilter: compact ? 'blur(14px) saturate(140%)' : 'none', borderBottomWidth: 1 }}
      >
        <nav
          aria-label="Primary"
          className={cn(
            'mx-auto flex max-w-[1400px] items-center justify-between px-5 transition-[height] duration-300 md:px-10',
            compact ? 'h-[52px]' : 'h-[68px]',
          )}
        >
          <Link to="/" className="group flex items-baseline gap-2.5" aria-label="IEIL — home">
            <span className="font-mono text-sm font-medium tracking-[0.18em] text-ink-50">IEIL</span>
            <AnimatePresence initial={false}>
              {!compact && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.25, ease: EASE_OUT }}
                  className="hidden overflow-hidden whitespace-nowrap font-mono text-2xs uppercase tracking-[0.18em] text-ink-500 lg:inline"
                >
                  India Economics Intelligence Lab
                </motion.span>
              )}
            </AnimatePresence>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'relative px-3 py-1.5 font-mono text-2xs uppercase tracking-[0.16em] transition-colors',
                    isActive || location.pathname.startsWith(item.to)
                      ? 'text-ink-50'
                      : 'text-ink-400 hover:text-ink-100',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {(isActive || location.pathname.startsWith(item.to)) && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-x-2 -bottom-px h-px bg-[#e8933a]"
                        transition={SPRING.control}
                      />
                    )}
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}

            <button
              type="button"
              onClick={onOpenPalette}
              className="ml-3 flex items-center gap-2 border border-white/[0.12] px-2.5 py-1.5 font-mono text-2xs text-ink-400 transition-colors hover:border-[#e8933a]/50 hover:text-ink-100"
              aria-label="Open command palette"
            >
              <Search size={12} />
              <span className="tracking-[0.1em]">⌘K</span>
            </button>
          </div>

          <button
            type="button"
            className="flex items-center gap-2 text-ink-300 md:hidden"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </nav>
      </motion.header>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-ink-950/96 pt-[68px] backdrop-blur-xl md:hidden"
          >
            <div className="flex flex-col px-5 py-6">
              {NAV_ITEMS.map((item, i) => (
                <motion.div
                  key={item.to}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.04 * i, ease: EASE_OUT }}
                >
                  <Link
                    to={item.to}
                    onClick={() => setMobileOpen(false)}
                    className="block border-b border-white/[0.07] py-4 font-display text-2xl text-ink-100"
                  >
                    {item.label}
                  </Link>
                </motion.div>
              ))}
              <button
                type="button"
                onClick={() => {
                  setMobileOpen(false);
                  onOpenPalette();
                }}
                className="btn mt-6 justify-center"
              >
                <Search size={12} /> Search the lab
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
