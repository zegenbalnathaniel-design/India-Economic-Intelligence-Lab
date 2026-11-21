/**
 * iBFPI — the India Bank Financial Performance Index — ported from
 * analysis/banking.py: per-bank robust z-scores, the composite, cross-bank
 * aggregation, the repo-rate correlation, the rate-regime split and the
 * robustness checks (weights, leave-one-out, direction flips, fixed effects).
 */
import { tPValue, tPpf, normCdf } from '../stats/dist';
import { mean } from '../stats/describe';
import { neweyWestLags, spearman } from '../stats/regression';
import { rng } from '../wealth/engine';

export const MAD_SCALE = 1.4826;

export interface Row {
  bank: string;
  period: string;
  values: Record<string, number>;
}

const median = (x: readonly number[]) => {
  const s = [...x].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

/** Z* = D · (X − median) / (1.4826 · MAD); zeros when MAD is zero. */
export function robustZ(x: readonly number[], direction = 1): number[] {
  const m = median(x);
  const mad = median(x.map((v) => Math.abs(v - m)));
  if (mad === 0) return x.map(() => 0);
  return x.map((v) => (direction * (v - m)) / (MAD_SCALE * mad));
}

export interface Scored extends Row {
  z: Record<string, number>;
  ibfpi: number;
}

export function computeIbfpi(
  rows: readonly Row[],
  indicators: readonly string[],
  directions: Record<string, number>,
  weights?: Record<string, number> | null,
): Scored[] {
  const out: Scored[] = rows.map((r) => ({ ...r, z: {}, ibfpi: 0 }));
  const banks = [...new Set(rows.map((r) => r.bank))];
  for (const b of banks) {
    const idx = out.map((r, i) => (r.bank === b ? i : -1)).filter((i) => i >= 0);
    for (const c of indicators) {
      const z = robustZ(idx.map((i) => out[i].values[c]), directions[c]);
      idx.forEach((i, k) => (out[i].z[c] = z[k]));
    }
  }
  let w: Record<string, number> | null = null;
  if (weights) {
    const tot = indicators.reduce((s, c) => s + (weights[c] ?? 0), 0);
    if (tot <= 0) throw new Error('indicator weights must sum to a positive value.');
    w = Object.fromEntries(indicators.map((c) => [c, (weights[c] ?? 0) / tot]));
  }
  for (const r of out) r.ibfpi = w ? indicators.reduce((s, c) => s + r.z[c] * w![c], 0) : mean(indicators.map((c) => r.z[c]));
  return out;
}

/** Equal (or bank-weighted) mean of iBFPI per period, sorted by period. */
export function aggregate(scored: readonly Scored[], bankWeights?: Record<string, number> | null) {
  const periods = [...new Set(scored.map((r) => r.period))].sort();
  let w: Record<string, number> | null = null;
  if (bankWeights) {
    const tot = Object.values(bankWeights).reduce((a, b) => a + b, 0);
    w = Object.fromEntries(Object.entries(bankWeights).map(([k, v]) => [k, v / tot]));
  }
  return periods.map((p) => {
    const rs = scored.filter((r) => r.period === p);
    return { period: p, ibfpi: w ? rs.reduce((s, r) => s + r.ibfpi * (w![r.bank] ?? 0), 0) : mean(rs.map((r) => r.ibfpi)) };
  });
}

/** Spearman as banking.spearman: scipy's t-approximation p-value at every n. */
export function rho(x: readonly number[], y: readonly number[]) {
  if (x.length < 3) return { rho: NaN, p: NaN, n: x.length };
  const s = spearman(x, y, false);
  return { rho: s.r, p: s.p, n: x.length };
}

export function mergeRepo(series: readonly { period: string; ibfpi: number }[], repo: readonly [string, number][]) {
  const m = new Map(repo);
  return series.filter((s) => m.has(s.period)).map((s) => ({ ...s, repo: m.get(s.period)! }));
}

export type Regime = 'rising' | 'falling' | 'stable';

/** Three-quarter rolling change in the repo rate: > +25bp rising, < −25bp falling. */
export function regimes(merged: readonly { period: string; ibfpi: number; repo: number }[]) {
  const d = [...merged].sort((a, b) => a.period.localeCompare(b.period));
  const diff = d.map((r, i) => (i === 0 ? NaN : r.repo - d[i - 1].repo));
  const labelled = d.map((r, i) => {
    const win = diff.slice(Math.max(0, i - 2), i + 1).filter((v) => Number.isFinite(v));
    const delta = win.length ? win.reduce((a, b) => a + b, 0) : NaN;
    const regime: Regime = !Number.isFinite(delta) ? 'stable' : delta > 0.25 ? 'rising' : delta < -0.25 ? 'falling' : 'stable';
    return { ...r, delta, regime };
  });
  const corr = (g: Regime) => {
    const s = labelled.filter((r) => r.regime === g);
    return rho(s.map((r) => r.repo), s.map((r) => r.ibfpi));
  };
  return { labelled, rising: corr('rising'), falling: corr('falling'), stable: corr('stable') };
}

export function systemRho(
  rows: readonly Row[],
  repo: readonly [string, number][],
  indicators: readonly string[],
  directions: Record<string, number>,
  weights?: Record<string, number> | null,
) {
  const m = mergeRepo(aggregate(computeIbfpi(rows, indicators, directions, weights)), repo);
  return rho(m.map((r) => r.repo), m.map((r) => r.ibfpi));
}

export function leaveOneOut(rows: readonly Row[], repo: readonly [string, number][], indicators: readonly string[], directions: Record<string, number>, labels: Record<string, string>) {
  return [
    { variant: 'All five (baseline)', ...systemRho(rows, repo, indicators, directions) },
    ...indicators.map((c) => ({ variant: `Without ${labels[c]}`, ...systemRho(rows, repo, indicators.filter((k) => k !== c), directions) })),
  ];
}

export function directionFlips(rows: readonly Row[], repo: readonly [string, number][], indicators: readonly string[], directions: Record<string, number>, labels: Record<string, string>) {
  return indicators.map((c) => {
    const d = directions[c];
    const fmt = (v: number) => (v > 0 ? '+1' : '-1');
    return { variant: `Flip ${labels[c]} (${fmt(d)} → ${fmt(-d)})`, ...systemRho(rows, repo, indicators, { ...directions, [c]: -d }) };
  });
}

/** ρ under random indicator weights drawn uniformly from the simplex (Dirichlet(1,…,1)). */
export function weightSensitivity(rows: readonly Row[], repo: readonly [string, number][], indicators: readonly string[], directions: Record<string, number>, draws = 300, seed = 11) {
  const scored = computeIbfpi(rows, indicators, directions);
  const periods = [...new Set(scored.map((r) => r.period))].sort();
  const rm = new Map(repo);
  const P = periods.filter((p) => rm.has(p));
  const Z = P.map((p) => {
    const rs = scored.filter((r) => r.period === p);
    return indicators.map((c) => mean(rs.map((r) => r.z[c])));
  });
  const R = rng(seed);
  const out: { weights: number[]; rho: number }[] = [];
  for (let d = 0; d < draws; d++) {
    const e = indicators.map(() => -Math.log(1 - R.next()));
    const tot = e.reduce((a, b) => a + b, 0);
    const w = e.map((v) => v / tot);
    const y = Z.map((row) => row.reduce((s, v, i) => s + v * w[i], 0));
    out.push({ weights: w, rho: rho(P.map((p) => rm.get(p)!), y).rho });
  }
  return out;
}

export interface FEResult {
  label: string;
  slope: number;
  se: number;
  p: number;
  ciLow: number;
  ciHigh: number;
  n: number;
  seType: string;
}

function result(label: string, slope: number, se: number, dof: number | null, n: number, seType: string): FEResult {
  const t = slope / se;
  const p = dof === null ? 2 * (1 - normCdf(Math.abs(t))) : tPValue(t, dof);
  const crit = dof === null ? 1.959963984540054 : tPpf(0.975, dof);
  return { label, slope, se, p, ciLow: slope - crit * se, ciHigh: slope + crit * se, n, seType };
}

/** Within-bank OLS (conventional and bank-clustered SEs) and the system series with Newey–West HAC. */
export function fixedEffects(scored: readonly Scored[], repo: readonly [string, number][]): FEResult[] {
  const rm = new Map(repo);
  const d = scored.filter((r) => rm.has(r.period)).map((r) => ({ bank: r.bank, y: r.ibfpi, x: rm.get(r.period)! }));
  const n = d.length;
  const banks = [...new Set(d.map((r) => r.bank))];
  const my = new Map(banks.map((b) => [b, mean(d.filter((r) => r.bank === b).map((r) => r.y))]));
  const mx = new Map(banks.map((b) => [b, mean(d.filter((r) => r.bank === b).map((r) => r.x))]));
  const y = d.map((r) => r.y - my.get(r.bank)!);
  const x = d.map((r) => r.x - mx.get(r.bank)!);
  const sxx = x.reduce((s, v) => s + v * v, 0);
  const beta = x.reduce((s, v, i) => s + v * y[i], 0) / sxx;
  const e = y.map((v, i) => v - beta * x[i]);
  const dof = n - banks.length - 1;
  const seConv = Math.sqrt(e.reduce((s, v) => s + v * v, 0) / dof / sxx);
  const out = [result('Bank fixed effects', beta, seConv, dof, n, 'conventional')];
  if (banks.length >= 2) {
    let meat = 0;
    for (const b of banks) {
      let sg = 0;
      d.forEach((r, i) => r.bank === b && (sg += x[i] * e[i]));
      meat += sg * sg;
    }
    const G = banks.length;
    const corr = (G / (G - 1)) * ((n - 1) / (n - 1 - G));
    out.push(result('Bank fixed effects, clustered by bank', beta, Math.sqrt((corr * meat) / sxx ** 2), G - 1, n, `clustered, ${G} banks — too few clusters to rely on`));
  }
  const sys = mergeRepo(aggregate(scored), repo);
  const T = sys.length;
  const X = sys.map((r) => [1, r.repo]);
  const Y = sys.map((r) => r.ibfpi);
  const xm = mean(X.map((r) => r[1]));
  const ym = mean(Y);
  const sXX = X.reduce((s, r) => s + (r[1] - xm) ** 2, 0);
  const b1 = X.reduce((s, r, i) => s + (r[1] - xm) * (Y[i] - ym), 0) / sXX;
  const b0 = ym - b1 * xm;
  const u = Y.map((v, i) => v - b0 - b1 * X[i][1]);
  const xtx = [
    [T, X.reduce((s, r) => s + r[1], 0)],
    [X.reduce((s, r) => s + r[1], 0), X.reduce((s, r) => s + r[1] ** 2, 0)],
  ];
  const det = xtx[0][0] * xtx[1][1] - xtx[0][1] * xtx[1][0];
  const inv = [
    [xtx[1][1] / det, -xtx[0][1] / det],
    [-xtx[1][0] / det, xtx[0][0] / det],
  ];
  const lags = neweyWestLags(T);
  const xu = X.map((r, i) => [r[0] * u[i], r[1] * u[i]]);
  const S = [
    [0, 0],
    [0, 0],
  ];
  const addOuter = (a: number[], b: number[], w: number) => {
    for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) S[i][j] += w * a[i] * b[j];
  };
  xu.forEach((r) => addOuter(r, r, 1));
  for (let L = 1; L <= lags; L++) {
    const w = 1 - L / (lags + 1);
    for (let t = L; t < T; t++) {
      addOuter(xu[t], xu[t - L], w);
      addOuter(xu[t - L], xu[t], w);
    }
  }
  const v11 = inv[1].reduce((s, a, i) => s + a * (S[i][0] * inv[0][1] + S[i][1] * inv[1][1]), 0);
  out.push(result('System iBFPI, Newey–West', b1, Math.sqrt(v11), null, T, `HAC, ${lags} lags`));
  return out;
}
