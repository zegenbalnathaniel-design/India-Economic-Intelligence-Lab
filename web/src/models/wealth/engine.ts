/**
 * Wealth accumulation, ported from analysis/wealth.py: the composition-effect
 * simulator, single-asset projections, a seeded Monte Carlo with optional
 * correlation and fat tails, r − g, and the Paper A Figure 2 annuity paths.
 */
import { percentile } from '../stats/describe';

export type Alloc = Record<string, number>;

export function normalise(alloc: Alloc, keys: readonly string[]): Alloc {
  const total = keys.reduce((s, k) => s + (alloc[k] ?? 0), 0);
  if (total <= 0) throw new Error('Allocation weights must sum to a positive value.');
  return Object.fromEntries(keys.map((k) => [k, (alloc[k] ?? 0) / total]));
}

export const portfolioReturn = (alloc: Alloc, rets: Alloc, keys: readonly string[]) => {
  const a = normalise(alloc, keys);
  return keys.reduce((s, k) => s + a[k] * (rets[k] ?? 0), 0);
};

/** Fisher: (1 + r) / (1 + π) − 1. */
export const realReturn = (nominal: number, inflation: number) => (1 + nominal) / (1 + inflation) - 1;

export interface Composition {
  years: number[];
  nominal: number[];
  real: number[];
  contributions: number[];
  gains: number[];
  byAsset: Alloc[];
  r: number;
  rReal: number;
}

/** Contribute at the start of each year, compound, optionally rebalance to target. */
export function compositionEffect(
  contribution: number,
  years: number,
  alloc: Alloc,
  rets: Alloc,
  keys: readonly string[],
  inflation = 0.05,
  rebalance = true,
): Composition {
  const a = normalise(alloc, keys);
  const bal: Alloc = Object.fromEntries(keys.map((k) => [k, 0]));
  const out: Composition = { years: [], nominal: [], real: [], contributions: [], gains: [], byAsset: [], r: 0, rReal: 0 };
  for (let y = 1; y <= years; y++) {
    for (const k of keys) bal[k] += contribution * a[k];
    for (const k of keys) bal[k] *= 1 + (rets[k] ?? 0);
    if (rebalance) {
      const tot = keys.reduce((s, k) => s + bal[k], 0);
      for (const k of keys) bal[k] = tot * a[k];
    }
    const nom = keys.reduce((s, k) => s + bal[k], 0);
    out.years.push(y);
    out.nominal.push(nom);
    out.real.push(nom / (1 + inflation) ** y);
    out.contributions.push(contribution * y);
    out.gains.push(nom - contribution * y);
    out.byAsset.push({ ...bal });
  }
  out.r = portfolioReturn(alloc, rets, keys);
  out.rReal = realReturn(out.r, inflation);
  return out;
}

export function singleAsset(contribution: number, years: number, r: number, inflation: number) {
  let b = 0;
  for (let i = 0; i < years; i++) b = (b + contribution) * (1 + r);
  return { finalNominal: b, finalReal: b / (1 + inflation) ** years, contribution: contribution * years, gain: b - contribution * years };
}

/** Value at the end of each year 0..n when `c` is saved at the END of each year (Figure 2 convention). */
export function annuityPath(c: number, rate: number, years: number): number[] {
  return Array.from({ length: years + 1 }, (_, t) => (rate === 0 ? c * t : (c * ((1 + rate) ** t - 1)) / rate));
}

export const equityMix = (share: number, equity: number, rest: number) => share * equity + (1 - share) * rest;

export function allocationRanking(options: Record<string, number>, c: number, years: number, inflation: number) {
  const rows = Object.entries(options)
    .map(([allocation, r]) => {
      const fin = annuityPath(c, r, years)[years];
      return { allocation, r, finalNominal: fin, finalReal: fin / (1 + inflation) ** years };
    })
    .sort((a, b) => b.finalNominal - a.finalNominal);
  const last = rows[rows.length - 1].finalNominal;
  return rows.map((r) => ({ ...r, multiple: r.finalNominal / last }));
}

export const impliedExcessGrowth = (start: number, end: number, years: number) => (end / start) ** (1 / years) - 1;

// ---------------------------------------------------------------------------
// Monte Carlo
// ---------------------------------------------------------------------------

/** Mulberry32: small, fast, seedable. */
export function rng(seed: number) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  let spare: number | null = null;
  const normal = () => {
    if (spare !== null) {
      const s = spare;
      spare = null;
      return s;
    }
    let u = 0;
    while (u === 0) u = next();
    const v = next();
    const r = Math.sqrt(-2 * Math.log(u));
    spare = r * Math.sin(2 * Math.PI * v);
    return r * Math.cos(2 * Math.PI * v);
  };
  return { next, normal };
}

/** Cholesky factor of a symmetric PSD matrix (with a tiny ridge), or an error naming the problem. */
export function cholesky(m: number[][]): number[][] {
  const n = m.length;
  for (let i = 0; i < n; i++) {
    if (Math.abs(m[i][i] - 1) > 1e-9) throw new Error('correlation matrix must have 1s on the diagonal.');
    for (let j = 0; j < n; j++) {
      if (Math.abs(m[i][j] - m[j][i]) > 1e-9) throw new Error('correlation matrix must be symmetric.');
      if (Math.abs(m[i][j]) > 1 + 1e-12) throw new Error('correlations must lie between -1 and 1.');
    }
  }
  const L = Array.from({ length: n }, () => new Array<number>(n).fill(0));
  for (let i = 0; i < n; i++)
    for (let j = 0; j <= i; j++) {
      let s = m[i][j] + (i === j ? 1e-12 : 0);
      for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k];
      if (i === j) {
        if (s < -1e-8)
          throw new Error('these correlations are mutually impossible (not positive semi-definite): e.g. A and B, and B and C, strongly positive while A and C are strongly negative.');
        L[i][j] = Math.sqrt(Math.max(s, 0));
      } else L[i][j] = L[j][j] > 0 ? s / L[j][j] : 0;
    }
  return L;
}

export interface MonteCarlo {
  years: number[];
  bands: { year: number; p05: number; p25: number; p50: number; p75: number; p95: number }[];
  finalNominal: number[];
  finalReal: number[];
}

export function monteCarlo(opts: {
  contribution: number;
  years: number;
  alloc: Alloc;
  rets: Alloc;
  vols: Alloc;
  keys: readonly string[];
  inflation: number;
  paths: number;
  seed: number;
  correlation?: number[][] | null;
  tDf?: number | null;
}): MonteCarlo {
  const { keys, years, paths } = opts;
  const n = keys.length;
  const w = keys.map((k) => normalise(opts.alloc, keys)[k]);
  const mu = keys.map((k) => opts.rets[k] ?? 0);
  const sig = keys.map((k) => opts.vols[k] ?? 0);
  const L = opts.correlation ? cholesky(opts.correlation) : null;
  if (opts.tDf != null && !(opts.tDf > 2)) throw new Error('t degrees of freedom must be greater than 2.');
  const r = rng(opts.seed);
  const bal = Array.from({ length: paths }, () => new Array<number>(n).fill(0));
  const nominal = Array.from({ length: years }, () => new Array<number>(paths).fill(0));
  const z = new Array<number>(n);
  for (let t = 0; t < years; t++) {
    for (let p = 0; p < paths; p++) {
      const b = bal[p];
      for (let i = 0; i < n; i++) z[i] = r.normal();
      let shock = z;
      if (L) shock = L.map((row) => row.reduce((s, v, j) => s + v * z[j], 0));
      let scale = 1;
      if (opts.tDf) {
        let chi = 0;
        for (let k = 0; k < Math.round(opts.tDf); k++) chi += r.normal() ** 2;
        scale = Math.sqrt((opts.tDf - 2) / opts.tDf) / Math.sqrt(chi / opts.tDf);
      }
      let tot = 0;
      for (let i = 0; i < n; i++) {
        b[i] = (b[i] + opts.contribution * w[i]) * (1 + mu[i] + sig[i] * shock[i] * scale);
        tot += b[i];
      }
      for (let i = 0; i < n; i++) b[i] = tot * w[i];
      nominal[t][p] = tot;
    }
  }
  const bands = nominal.map((col, t) => ({
    year: t + 1,
    p05: percentile(col, 5),
    p25: percentile(col, 25),
    p50: percentile(col, 50),
    p75: percentile(col, 75),
    p95: percentile(col, 95),
  }));
  const finalNominal = nominal[years - 1];
  return { years: bands.map((b) => b.year), bands, finalNominal, finalReal: finalNominal.map((v) => v / (1 + opts.inflation) ** years) };
}
