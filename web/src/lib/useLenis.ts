import { useEffect } from 'react';
import Lenis from 'lenis';
import { useReducedMotionPref } from './motion';

/**
 * Smooth scrolling, mounted once at the app root. Disabled entirely when the
 * reader prefers reduced motion — smoothing scroll is exactly the kind of
 * momentum that setting exists to remove.
 */
export function useLenis(): void {
  const reduced = useReducedMotionPref();

  useEffect(() => {
    if (reduced) return;
    const lenis = new Lenis({
      duration: 1.05,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.6,
    });

    let frame = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      frame = requestAnimationFrame(raf);
    };
    frame = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(frame);
      lenis.destroy();
    };
  }, [reduced]);
}
