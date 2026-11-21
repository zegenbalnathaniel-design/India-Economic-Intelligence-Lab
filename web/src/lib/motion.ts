import { useEffect, useState } from 'react';

/**
 * Reads prefers-reduced-motion and keeps it live. Components use this to
 * shorten or remove JS-driven animation — CSS transitions are handled by the
 * media query in index.css. Motion in this lab carries meaning (a curve
 * morphing shows a causal chain), so under reduced motion the end state is
 * shown immediately rather than the interaction being removed.
 */
export function useReducedMotionPref(): boolean {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  return reduced;
}

/** Spring presets. Physical rather than timed, so interruptions look right. */
export const SPRING = {
  /** Numbers settling into place. */
  readout: { type: 'spring', stiffness: 170, damping: 26, mass: 0.9 } as const,
  /** Panels and layout. */
  surface: { type: 'spring', stiffness: 220, damping: 32, mass: 1 } as const,
  /** Small controls and hovers. */
  control: { type: 'spring', stiffness: 420, damping: 34, mass: 0.6 } as const,
  /** Chart geometry. */
  curve: { type: 'spring', stiffness: 120, damping: 24, mass: 1 } as const,
};

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;

/** Staggered reveal used by every section that lists items. */
export const stagger = (delay = 0.04) => ({
  hidden: {},
  show: { transition: { staggerChildren: delay } },
});

export const riseIn = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE_OUT } },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.5, ease: EASE_OUT } },
};
