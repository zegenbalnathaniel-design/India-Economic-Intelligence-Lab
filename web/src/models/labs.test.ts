/**
 * Parity with the Python analysis modules. Every expected number below is a
 * `reference` value written into the lab bundles by
 * web/scripts/export_lab_data.py from the Python code itself.
 */
import { describe, expect, it } from 'vitest';
import housingData from '../data/labs/housing.json';
import ineq from '../data/labs/inequality.json';
import rel from '../data/labs/relationships.json';
import states from '../data/labs/states.json';
import tx from '../data/labs/transmission.json';
import { beta, dispersion, sigma, speedOfConvergence, type Row } from './convergence/engine';
import { cityAffordability, emi, rpipi, stressIndex, type HousingData } from './housing/engine';
import { giniLowerBound, lorenzPoints, redistribute, type Shares } from './inequality/engine';
import { spearman } from './stats/regression';
import { run, tradeBalanceChange, type Link } from './transmission/engine';

const rows = states.spliced as unknown as Row[];

/** Relative agreement: the bundles store references to 10 significant digits. */
const near = (a: number, b: number, digits = 8) => expect(a / b).toBeCloseTo(1, digits);

describe('convergence engine matches analysis/convergence.py', () => {
  const ref = states.reference;
  it('σ on the full balanced panel', () => {
    const r = sigma(rows, ref.sigma.start, ref.sigma.end, 'sd_log');
    expect(r.included.length).toBe(ref.sigma.n);
    near(r.first, ref.sigma.first);
    near(r.last, ref.sigma.last);
    near(r.slope, ref.sigma.slope);
    expect(r.slopeP).toBeCloseTo(ref.sigma.p, 8);
    expect(r.verdict).toBe(ref.sigma.verdict);
  });
  it('β with classical and HC1 errors, speed and half-life', () => {
    const b = beta(rows, ref.sigma.start, ref.sigma.end);
    expect(b.fit!.n).toBe(ref.beta.n);
    near(b.fit!.slope, ref.beta.slope);
    near(b.fit!.se, ref.beta.se);
    expect(b.fit!.p).toBeCloseTo(ref.beta.p, 8);
    near(b.fit!.r2, ref.beta.r2);
    if (ref.beta.speed === null) expect(b.speed).toBeNaN();
    else near(b.speed, ref.beta.speed);
    const h = beta(rows, ref.sigma.start, ref.sigma.end, 'HC1');
    near(h.fit!.se, ref.beta.seHC1);
    expect(h.fit!.p).toBeCloseTo(ref.beta.pHC1, 8);
  });
  it('dispersion measures', () => {
    expect(dispersion([1, 2, 3, 4], 'gini')).toBeCloseTo(0.25, 12);
    expect(dispersion([2, 8], 'max_min')).toBe(4);
    expect(dispersion([1, -1], 'cv')).toBeNaN();
  });
  it('speed of convergence formula', () => {
    const s = speedOfConvergence(-2, 10);
    expect(s.speed).toBeCloseTo(-Math.log(0.8) / 10, 12);
    expect(s.halfLife).toBeCloseTo(Math.log(2) / s.speed, 12);
    expect(speedOfConvergence(1, 10).speed).toBeNaN();
  });
});

describe('housing engine matches analysis/housing.py', () => {
  const d = housingData as unknown as HousingData;
  const ref = housingData.reference;
  const base = { unitSqm: 70, downPayment: 0.2, rate: 0.085, tenure: 20, incomeSource: 'nsdp' as const };
  it('EMI formula', () => {
    expect(emi(1_000_000, 0, 10)).toBeCloseTo(1_000_000 / 120, 8);
    expect(emi(1_000_000, 0.12, 1)).toBeCloseTo(88848.79, 1);
  });
  it('Mumbai affordability at the latest quarter', () => {
    const a = cityAffordability(d, 'Mumbai', base)!;
    expect(a.quarter).toBe(ref.mumbai.quarter);
    near(a.unitPrice, ref.mumbai.unitPrice);
    near(a.income, ref.mumbai.income);
    near(a.pti, ref.mumbai.pti);
    near(a.emiMonthly, ref.mumbai.emi);
    near(a.emiPct, ref.mumbai.emiPct);
  });
  it('RPIPI for Mumbai', () => {
    const r = rpipi(d, 'Mumbai')!;
    expect(r.base).toBe(ref.rpipiMumbai.base);
    expect(r.latest.fy).toBe(ref.rpipiMumbai.latest);
    near(r.latest.rpipi, ref.rpipiMumbai.value);
  });
  it('ICHASI stress scores', () => {
    const s = stressIndex(d, base)!;
    ref.stressTop.forEach((t, i) => {
      expect(s.scores[i].city).toBe(t.city);
      near(s.scores[i].pti, t.price_to_income as number);
      expect(s.scores[i].score).toBeCloseTo(t.stress_score_0_100 as number, 6);
    });
  });
});

describe('inequality engine matches analysis/inequality.py', () => {
  const income = ineq.incomeShares as unknown as Shares[];
  it('lower-bound Gini series', () => {
    for (const r of ineq.reference.giniIncome) {
      const s = income.find((x) => x.year === r.year)!;
      expect(giniLowerBound(s)).toBeCloseTo(r.gini_lower_bound as number, 12);
    }
  });
  it('Lorenz points and redistribution keep the partition', () => {
    const s = income[income.length - 1];
    expect(lorenzPoints(s)[5]).toEqual([1, 1]);
    const r = redistribute(s, 2);
    expect(r.bottom_50 + r.middle_40 + r.top_10).toBeCloseTo(s.bottom_50 + s.middle_40 + s.top_10, 10);
    expect(giniLowerBound(r)).toBeLessThan(giniLowerBound(s));
  });
});

describe('relationships: Spearman ρ matches the Python overview table', () => {
  type H = { id: string; key: string; xData: [unknown, number | null][]; yData: [unknown, number | null][]; exclude: Record<string, string> };
  const hyps = rel.hypotheses as unknown as H[];
  const overview = rel.overview as unknown as { id: string; n: number; 'Spearman ρ': number; 'p-value': number }[];
  for (const id of ['inc_mpce', 'inc_unemp', 'wil_bottom50_vs_top10_income', 'mpce_vs_unemployment', 'city_price_vs_state_mpce']) {
    it(id, () => {
      const h = hyps.find((x) => x.id === id)!;
      const y = new Map(h.yData.map(([k, v]) => [String(k), v]));
      const pairs = h.xData
        .filter(([k, v]) => v !== null && y.get(String(k)) != null && !(String(k) in h.exclude))
        .map(([k, v]) => [v as number, y.get(String(k)) as number]);
      const o = overview.find((r) => r.id === id)!;
      const s = spearman(pairs.map((p) => p[0]), pairs.map((p) => p[1]));
      expect(pairs.length).toBe(o.n);
      expect(s.r).toBeCloseTo(o['Spearman ρ'], 10);
      expect(s.p / o['p-value']).toBeCloseTo(1, 6);
    });
  }
});

describe('transmission engine matches analysis/transmission.py', () => {
  const links = tx.links as unknown as Record<string, Link[]>;
  const scenarios = tx.scenarios as unknown as Record<string, { slider: number[] }>;
  for (const [key, expected] of Object.entries(tx.reference as Record<string, { id: string; value: number | null; status: string }[]>)) {
    it(key, () => {
      const [scn, regime] = key.split('|');
      const res = run(links[scn], scenarios[scn].slider[2], tx.defaultsA as Record<string, number | null>, regime);
      res.forEach((r, i) => {
        expect(r.link.id).toBe(expected[i].id);
        expect(r.status).toBe(expected[i].status);
        if (expected[i].value === null) expect(r.value).toBeNull();
        else expect(r.value!).toBeCloseTo(expected[i].value!, 12);
      });
    });
  }
  it('trade balance arithmetic', () => {
    expect(tradeBalanceChange(10, 20, 25, 0.5, 0.3)).toBeCloseTo(0.1 * (10 - 17.5), 12);
  });
});
