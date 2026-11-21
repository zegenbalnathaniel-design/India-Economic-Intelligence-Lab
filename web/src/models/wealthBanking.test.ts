/** Parity with analysis/wealth.py and analysis/banking.py (reference values exported by the Python). */
import { describe, expect, it } from 'vitest';
import B from '../data/labs/banking.json';
import W from '../data/labs/wealth.json';
import {
  aggregate,
  computeIbfpi,
  directionFlips,
  fixedEffects,
  leaveOneOut,
  mergeRepo,
  regimes,
  rho,
  robustZ,
  weightSensitivity,
  type Row,
} from './banking/engine';
import { allocationRanking, cholesky, compositionEffect, equityMix, impliedExcessGrowth, monteCarlo, singleAsset } from './wealth/engine';

const near = (a: number, b: number, digits = 8) => expect(a / b).toBeCloseTo(1, digits);

describe('wealth engine matches analysis/wealth.py', () => {
  const keys = W.assetKeys;
  const ref = W.reference;
  it('composition effect, with and without rebalancing', () => {
    const c = compositionEffect(100000, 30, W.defaultAllocation, W.defaultReturns, keys, 0.05);
    near(c.nominal[29], ref.composition.final);
    near(c.real[29], ref.composition.real);
    near(c.r, ref.composition.r);
    near(c.rReal, ref.composition.rReal);
    const n = compositionEffect(100000, 30, W.defaultAllocation, W.defaultReturns, keys, 0.05, false);
    near(n.nominal[29], ref.composition.noRebalFinal);
  });
  it('single asset, ranking and excess growth', () => {
    const s = singleAsset(100000, 30, 0.12, 0.05);
    near(s.finalNominal, ref.single.final_nominal);
    near(s.finalReal, ref.single.final_real);
    const R = W.paperR as Record<string, number>;
    const rank = allocationRanking(
      {
        'All listed equity': R['Listed equity'],
        '75% equity / 25% household mix': equityMix(0.75, R['Listed equity'], R['Typical household portfolio']),
        'Typical household portfolio': R['Typical household portfolio'],
      },
      100000,
      30,
      0.065,
    );
    rank.forEach((r, i) => {
      expect(r.allocation).toBe(ref.ranking[i].allocation);
      near(r.finalNominal, ref.ranking[i].final_nominal as number);
      near(r.multiple, ref.ranking[i].multiple_of_last as number);
    });
    near(impliedExcessGrowth(3.83, 5.75, 27), ref.excess);
  });
  it('Paper A Figure 2 endpoints (₹ crore, as printed)', () => {
    const R = W.paperR as Record<string, number>;
    const eq = allocationRanking({ e: R['Listed equity'] }, 100000, 30, 0)[0].finalNominal / 1e7;
    expect(eq).toBeCloseTo(3.24, 1);
  });
  it('Monte Carlo collapses to the deterministic path when volatility is zero', () => {
    const zero = Object.fromEntries(keys.map((k) => [k, 0]));
    const mc = monteCarlo({ contribution: 100000, years: 20, alloc: W.defaultAllocation, rets: W.defaultReturns, vols: zero, keys, inflation: 0.05, paths: 50, seed: 3 });
    const det = compositionEffect(100000, 20, W.defaultAllocation, W.defaultReturns, keys, 0.05);
    near(mc.bands[19].p05, det.nominal[19], 10);
    near(mc.bands[19].p95, det.nominal[19], 10);
  });
  it('Monte Carlo median sits near the deterministic path and bands are ordered', () => {
    const mc = monteCarlo({ contribution: 100000, years: 30, alloc: W.defaultAllocation, rets: W.defaultReturns, vols: W.defaultVolatility, keys, inflation: 0.05, paths: 4000, seed: 7 });
    const det = compositionEffect(100000, 30, W.defaultAllocation, W.defaultReturns, keys, 0.05);
    const b = mc.bands[29];
    expect(b.p05).toBeLessThan(b.p25);
    expect(b.p25).toBeLessThan(b.p50);
    expect(b.p75).toBeLessThan(b.p95);
    expect(Math.abs(b.p50 / det.nominal[29] - 1)).toBeLessThan(0.05);
  });
  it('rejects impossible correlation matrices', () => {
    expect(() => cholesky([[1, 0.9, -0.9], [0.9, 1, 0.9], [-0.9, 0.9, 1]])).toThrow(/impossible/);
    expect(cholesky([[1, 0.5], [0.5, 1]])[1][1]).toBeCloseTo(Math.sqrt(0.75), 10);
  });
});

describe('banking engine matches analysis/banking.py', () => {
  const ind = B.indicators;
  const rows: Row[] = (B.panel as (string | number)[][]).map((r) => ({
    bank: r[0] as string,
    period: r[1] as string,
    values: Object.fromEntries(ind.map((c, i) => [c, r[2 + i] as number])),
  }));
  const repo = B.repo as [string, number][];
  const ref = B.reference;
  const scored = computeIbfpi(rows, ind, B.directions);
  const sys = aggregate(scored);

  it('robust z-score', () => {
    const z = robustZ([1, 2, 3, 4, 100]);
    expect(z[2]).toBe(0);
    expect(z[3]).toBeCloseTo(1 / 1.4826, 12);
    expect(robustZ([5, 5, 5])).toEqual([0, 0, 0]);
  });
  it('system iBFPI series', () => {
    ref.system.forEach((r, i) => {
      expect(sys[i].period).toBe(r.period);
      expect(sys[i].ibfpi).toBeCloseTo(r.ibfpi_system as number, 8);
    });
  });
  it('repo correlation and regime split', () => {
    const m = mergeRepo(sys, repo);
    const c = rho(m.map((r) => r.repo), m.map((r) => r.ibfpi));
    expect(c.rho).toBeCloseTo(ref.rho[0], 9);
    near(c.p, ref.rho[1], 6);
    expect(c.n).toBe(ref.rho[2]);
    const g = regimes(m);
    expect(g.labelled.map((r) => r.regime)).toEqual(ref.regimeLabels);
    for (const k of ['rising', 'falling', 'stable'] as const) {
      expect(g[k].rho).toBeCloseTo(ref.regimes[k][0], 9);
      expect(g[k].n).toBe(ref.regimes[k][2]);
      near(g[k].p, ref.regimes[k][1], 6);
    }
  });
  it('fixed effects: conventional, clustered and Newey–West', () => {
    fixedEffects(scored, repo).forEach((r, i) => {
      near(r.slope, ref.fe[i].slope);
      near(r.se, ref.fe[i].se);
      near(r.p, ref.fe[i].p, 6);
      expect(r.n).toBe(ref.fe[i].n);
    });
  });
  it('leave-one-out and direction flips', () => {
    leaveOneOut(rows, repo, ind, B.directions, B.labels).forEach((r, i) => {
      expect(r.variant).toBe(ref.loo[i].variant);
      expect(r.rho).toBeCloseTo(ref.loo[i].rho as number, 9);
    });
    directionFlips(rows, repo, ind, B.directions, B.labels).forEach((r, i) => {
      expect(r.rho).toBeCloseTo(ref.flips[i].rho as number, 9);
    });
  });
  it('random-weight sensitivity lands in the Python range', () => {
    const s = weightSensitivity(rows, repo, ind, B.directions, 300).map((d) => d.rho);
    const neg = s.filter((v) => v < 0).length / s.length;
    expect(Math.abs(neg - ref.sensitivity.shareNegative)).toBeLessThan(0.1);
    expect(Math.min(...s)).toBeGreaterThan(ref.sensitivity.min - 0.15);
    expect(Math.max(...s)).toBeLessThan(ref.sensitivity.max + 0.15);
  });
});
