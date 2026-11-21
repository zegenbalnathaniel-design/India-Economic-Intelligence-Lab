/**
 * Lorenz curves and the lower-bound Gini from WIL group shares, ported from
 * analysis/inequality.py and analysis/financialisation.py.
 */

export interface Shares {
  year: number;
  bottom_50: number;
  middle_40: number;
  top_10: number;
  top_1: number;
  top_0_1: number;
  tentative?: boolean | null;
}

export const LORENZ_BREAKS = [0, 0.5, 0.9, 0.99, 0.999, 1] as const;

export function lorenzPoints(s: Pick<Shares, 'bottom_50' | 'middle_40' | 'top_1' | 'top_0_1'>): [number, number][] {
  const b = s.bottom_50 / 100;
  const m = s.middle_40 / 100;
  return [
    [0, 0],
    [0.5, b],
    [0.9, b + m],
    [0.99, 1 - s.top_1 / 100],
    [0.999, 1 - s.top_0_1 / 100],
    [1, 1],
  ];
}

/** Gini of the piecewise-linear Lorenz curve: a lower bound (no within-group inequality). */
export function giniLowerBound(s: Pick<Shares, 'bottom_50' | 'middle_40' | 'top_1' | 'top_0_1'>): number {
  const p = lorenzPoints(s);
  let area = 0;
  for (let i = 1; i < p.length; i++) area += ((p[i][0] - p[i - 1][0]) * (p[i - 1][1] + p[i][1])) / 2;
  return 1 - 2 * area;
}

/** Move `pp` points from the Top 1% to the Bottom 50% (cut proportional within the Top 1%). */
export function redistribute(s: Shares, pp: number): Shares {
  const frac = s.top_1 ? pp / s.top_1 : 0;
  return {
    ...s,
    bottom_50: s.bottom_50 + pp,
    top_10: s.top_10 - pp,
    top_1: s.top_1 - pp,
    top_0_1: s.top_0_1 * (1 - frac),
  };
}

/** Align two annual series on common years in [start, end]. */
export function alignTwo(a: readonly [number, number][], b: readonly [number, number][], start: number, end: number) {
  const mb = new Map(b);
  return a
    .filter(([y, v]) => y >= start && y <= end && mb.has(y) && Number.isFinite(v) && Number.isFinite(mb.get(y)!))
    .map(([y, v]) => ({ year: y, a: v, b: mb.get(y)! }))
    .sort((p, q) => p.year - q.year);
}
