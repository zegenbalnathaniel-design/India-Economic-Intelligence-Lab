import { describe, expect, it } from 'vitest';
import rel from '../../data/labs/relationships.json';
import { chi2Sf, fSf, tPpf, tSf } from './dist';
import { percentile, rankAverage } from './describe';
import { breuschPagan, fitOLS, jarqueBera, pearson, spearman, spearmanExactP } from './regression';

// Expected values: scipy.stats / statsmodels 0.14 (see web/scripts/export_lab_data.py for the regression).
describe('distributions match scipy', () => {
  it('t survival and quantiles', () => {
    expect(tSf(2.1, 7)).toBeCloseTo(0.036935598106461326, 10);
    expect(tSf(-0.4, 25)).toBeCloseTo(0.6537230773308277, 10);
    expect(2 * tSf(3.3, 40)).toBeCloseTo(0.0020388122224484434, 10);
    expect(tPpf(0.975, 5)).toBeCloseTo(2.5705818356363146, 9);
    expect(tPpf(0.975, 26)).toBeCloseTo(2.0555294386428735, 9);
    expect(tPpf(0.05, 12)).toBeCloseTo(-1.7822875556493198, 9);
  });
  it('chi-square and F tails', () => {
    expect(chi2Sf(8.4707, 2)).toBeCloseTo(0.014474743150975381, 9);
    expect(chi2Sf(0.6656, 2)).toBeCloseTo(0.7169135625308898, 9);
    expect(chi2Sf(15, 7)).toBeCloseTo(0.03599940476342876, 9);
    expect(fSf(0.5638, 2, 25)).toBeCloseTo(0.5761109444453776, 8);
    expect(fSf(4.2, 3, 30)).toBeCloseTo(0.013541284163521478, 9);
  });
});

describe('descriptives', () => {
  it('numpy linear percentile', () => {
    expect(percentile([1, 2, 3, 4, 10], 90)).toBeCloseTo(7.6, 12);
    expect(percentile([5, 1, 3], 10)).toBeCloseTo(1.4, 12);
  });
  it('average ranks for ties', () => {
    expect(rankAverage([10, 20, 20, 5])).toEqual([2, 3.5, 3.5, 1]);
  });
});

const X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
const Y = [2.1, 2.9, 4.2, 3.8, 5.5, 6.1, 5.9, 7.7, 8.4, 8.1, 9.9, 10.2, 11.8, 11.1, 13.0];

describe('correlation matches scipy', () => {
  it('pearson and spearman', () => {
    const p = pearson(X, Y);
    expect(p.r).toBeCloseTo(0.9890746161299798, 12);
    expect(p.p / 3.4027115160709878e-12).toBeCloseTo(1, 6);
    const s = spearman(X, Y);
    expect(s.r).toBeCloseTo(0.9857142857142854, 12);
    expect(s.p / 1.9290948746067857e-11).toBeCloseTo(1, 6);
  });
  it('exact permutation p for small n', () => {
    expect(spearmanExactP([3, 1, 4, 1.5, 9], [2, 7, 1, 8, 2.8])).toBeCloseTo(0.35, 12);
  });
});

describe('OLS matches statsmodels', () => {
  it('Newey–West HAC, 2 lags', () => {
    const fit = fitOLS(Y, [X], ['x'], 'HAC', 2);
    expect(fit.terms[0].coef).toBeCloseTo(1.4142857142857135, 10);
    expect(fit.terms[1].coef).toBeCloseTo(0.7457142857142859, 10);
    expect(fit.terms[0].se).toBeCloseTo(0.09173779637373328, 10);
    expect(fit.terms[1].se).toBeCloseTo(0.013673131785861761, 10);
    expect(fit.f / 2974.465435472953).toBeCloseTo(1, 8);
  });

  const ref = rel.reference.ols!;
  const cat = rel.catalogue as unknown as { id: string; defaultPeriod: string; frames: Record<string, [string, number | null][]> }[];
  const frame = (id: string, period?: string) => {
    const v = cat.find((c) => c.id === id)!;
    return new Map(v.frames[period ?? v.defaultPeriod]);
  };
  const y = frame('st_unemployment', '2023-24');
  const x1 = frame('st_mpce_urban', '2023-24');
  const x2 = frame('st_nsdp_current');
  const keys = ref.keys;
  const Yv = keys.map((k) => y.get(k) as number);
  const X1 = keys.map((k) => x1.get(k) as number);
  const X2 = keys.map((k) => x2.get(k) as number);

  it('two regressors, HC1 and classical', () => {
    const hc1 = fitOLS(Yv, [X1, X2], ['mpce', 'nsdp'], 'HC1');
    hc1.terms.forEach((t, i) => {
      expect(t.coef / ref.params[i]).toBeCloseTo(1, 8);
      expect(t.se / ref.bse[i]).toBeCloseTo(1, 8);
      expect(t.p).toBeCloseTo(ref.p[i], 8);
    });
    expect(hc1.r2).toBeCloseTo(ref.r2, 10);
    expect(hc1.adjR2).toBeCloseTo(ref.adjR2, 10);
    expect(hc1.f).toBeCloseTo(ref.f, 8);
    expect(hc1.fP).toBeCloseTo(ref.fP, 8);
    const nr = fitOLS(Yv, [X1, X2], ['mpce', 'nsdp']);
    nr.terms.forEach((t, i) => expect(t.se / ref.bseClassical[i]).toBeCloseTo(1, 8));
  });

  it('Breusch–Pagan and Jarque–Bera', () => {
    const fit = fitOLS(Yv, [X1, X2], ['mpce', 'nsdp'], 'HC1');
    const bp = breuschPagan(fit);
    expect(bp.statistic).toBeCloseTo(ref.bp[0], 8);
    expect(bp.p).toBeCloseTo(ref.bp[1], 8);
    const jb = jarqueBera(fit);
    expect(jb.statistic).toBeCloseTo(ref.jb[0], 8);
    expect(jb.p).toBeCloseTo(ref.jb[1], 8);
  });
});
