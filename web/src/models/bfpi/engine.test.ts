import { describe, expect, it } from 'vitest';
import {
  BFPI_BANDS,
  INDICATORS,
  PILLARS,
  bandFor,
  calculateAssetQuality,
  calculateBFPI,
  calculateCapital,
  calculateLiquidity,
  calculateProfitability,
  calculateSample,
  calculateZScore,
  computeSampleStats,
  mean,
  standardDeviation,
  transformTo100Scale,
  validateObservations,
} from './engine';
import { INDICATOR_KEYS, PILLAR_KEYS, type BankObservation, type Observations } from './types';

const obs = (v: Partial<Observations>): Observations => ({
  nim: null,
  roe: null,
  capital: null,
  npl: null,
  provisions: null,
  lcr: null,
  ...v,
});

/** A small symmetric sample with known moments, so z-scores are checkable by hand. */
const sample: BankObservation[] = [
  { bankId: 'a', periodLabel: 'FY2025', values: obs({ nim: 3, roe: 10, capital: 12, npl: 2, provisions: 1, lcr: 120 }) },
  { bankId: 'b', periodLabel: 'FY2025', values: obs({ nim: 4, roe: 14, capital: 14, npl: 3, provisions: 2, lcr: 130 }) },
  { bankId: 'c', periodLabel: 'FY2025', values: obs({ nim: 5, roe: 18, capital: 16, npl: 4, provisions: 3, lcr: 140 }) },
];

describe('descriptive statistics', () => {
  it('computes the arithmetic mean', () => {
    expect(mean([3, 4, 5])).toBe(4);
  });

  it('computes the population standard deviation', () => {
    // σ² = ((3−4)² + (4−4)² + (5−4)²)/3 = 2/3
    expect(standardDeviation([3, 4, 5])).toBeCloseTo(Math.sqrt(2 / 3), 12);
  });

  it('returns zero dispersion for a constant series', () => {
    expect(standardDeviation([7, 7, 7])).toBe(0);
  });

  it('returns NaN for an empty series rather than a fabricated zero', () => {
    expect(Number.isNaN(mean([]))).toBe(true);
    expect(Number.isNaN(standardDeviation([]))).toBe(true);
  });
});

describe('calculateZScore', () => {
  it('applies zᵢ = dᵢ(Xᵢ − μᵢ)/σᵢ for a higher-is-better variable', () => {
    expect(calculateZScore(6, 4, 2, 1)).toBe(1);
    expect(calculateZScore(2, 4, 2, 1)).toBe(-1);
  });

  it('reverses the sign for a lower-is-better variable', () => {
    // A bank with NPL above the sample mean must score below average.
    expect(calculateZScore(6, 4, 2, -1)).toBe(-1);
    expect(calculateZScore(2, 4, 2, -1)).toBe(1);
  });

  it('gives zero at the sample mean, whatever the direction', () => {
    expect(calculateZScore(4, 4, 2, 1)).toBe(0);
    expect(calculateZScore(4, 4, 2, -1)).toBe(-0);
  });

  it('returns zero rather than infinity when the sample has no variation', () => {
    expect(calculateZScore(5, 5, 0, 1)).toBe(0);
  });

  it('propagates NaN instead of inventing a score', () => {
    expect(Number.isNaN(calculateZScore(NaN, 4, 2, 1))).toBe(true);
    expect(Number.isNaN(calculateZScore(5, NaN, 2, 1))).toBe(true);
  });
});

describe('direction coefficients', () => {
  it('marks NIM, ROE, capital and LCR as higher-is-better', () => {
    for (const k of ['nim', 'roe', 'capital', 'lcr'] as const) {
      expect(INDICATORS[k].direction).toBe(1);
    }
  });

  it('marks NPL and credit-loss provisions as lower-is-better', () => {
    expect(INDICATORS.npl.direction).toBe(-1);
    expect(INDICATORS.provisions.direction).toBe(-1);
  });

  it('a bank with the worst asset quality scores lowest on that pillar', () => {
    const stats = computeSampleStats(sample);
    const best = calculateAssetQuality(sample[0].values, stats);
    const worst = calculateAssetQuality(sample[2].values, stats);
    expect(best.z).toBeGreaterThan(0);
    expect(worst.z).toBeLessThan(0);
    expect(best.z as number).toBeGreaterThan(worst.z as number);
  });
});

describe('computeSampleStats', () => {
  it('computes μ and σ per indicator over the banks that reported it', () => {
    const stats = computeSampleStats(sample);
    expect(stats.nim?.mean).toBe(4);
    expect(stats.nim?.n).toBe(3);
    expect(stats.roe?.mean).toBe(14);
    expect(stats.lcr?.mean).toBe(130);
  });

  it('ignores banks with no value instead of counting them as zero', () => {
    const withGap = [...sample, { bankId: 'd', periodLabel: 'FY2025', values: obs({ nim: null }) }];
    const stats = computeSampleStats(withGap);
    expect(stats.nim?.n).toBe(3);
    expect(stats.nim?.mean).toBe(4);
  });

  it('omits an indicator no bank reported', () => {
    const stats = computeSampleStats([
      { bankId: 'x', periodLabel: 'FY2025', values: obs({ nim: 3 }) },
    ]);
    expect(stats.provisions).toBeUndefined();
  });
});

describe('pillar construction', () => {
  it('averages NIM and ROE into profitability: P = (z_NIM + z_ROE)/2', () => {
    const stats = computeSampleStats(sample);
    const p = calculateProfitability(sample[2].values, stats);
    const zn = calculateZScore(5, stats.nim!.mean, stats.nim!.sd, 1);
    const zr = calculateZScore(18, stats.roe!.mean, stats.roe!.sd, 1);
    expect(p.z).toBeCloseTo((zn + zr) / 2, 12);
    expect(p.partial).toBe(false);
  });

  it('uses the single capital indicator directly', () => {
    const stats = computeSampleStats(sample);
    const c = calculateCapital(sample[0].values, stats);
    expect(c.z).toBeCloseTo(calculateZScore(12, 14, stats.capital!.sd, 1), 12);
  });

  it('averages NPL and provisions into asset quality, both reversed', () => {
    const stats = computeSampleStats(sample);
    const a = calculateAssetQuality(sample[0].values, stats);
    const zn = calculateZScore(2, stats.npl!.mean, stats.npl!.sd, -1);
    const zp = calculateZScore(1, stats.provisions!.mean, stats.provisions!.sd, -1);
    expect(a.z).toBeCloseTo((zn + zp) / 2, 12);
  });

  it('uses LCR directly for liquidity', () => {
    const stats = computeSampleStats(sample);
    const l = calculateLiquidity(sample[2].values, stats);
    expect(l.z).toBeCloseTo(calculateZScore(140, 130, stats.lcr!.sd, 1), 12);
  });

  it('computes a pillar from the one indicator available and flags it partial', () => {
    const stats = computeSampleStats(sample);
    const p = calculateProfitability(obs({ nim: 5, roe: null }), stats);
    expect(p.available).toBe(true);
    expect(p.partial).toBe(true);
    expect(p.note).toContain('1 of 2');
    expect(p.z).toBeCloseTo(calculateZScore(5, 4, stats.nim!.sd, 1), 12);
  });

  it('does not compute a pillar with no available indicator', () => {
    const stats = computeSampleStats(sample);
    const l = calculateLiquidity(obs({ lcr: null }), stats);
    expect(l.available).toBe(false);
    expect(l.z).toBeNull();
    expect(l.indicators[0].note).toContain('Nothing substituted');
  });
});

describe('equal weighting', () => {
  it('assigns 25% to each of the four pillars', () => {
    for (const k of PILLAR_KEYS) expect(PILLARS[k].weight).toBe(0.25);
  });

  it('weights sum to exactly 1', () => {
    expect(PILLAR_KEYS.reduce((s, k) => s + PILLARS[k].weight, 0)).toBe(1);
  });

  it('composite Z equals 0.25P + 0.25C + 0.25A + 0.25L', () => {
    const stats = computeSampleStats(sample);
    const r = calculateBFPI(sample[1], stats);
    const byKey = Object.fromEntries(r.pillars.map((p) => [p.key, p.z as number]));
    const expected =
      0.25 * byKey.profitability + 0.25 * byKey.capital + 0.25 * byKey.assetQuality + 0.25 * byKey.liquidity;
    expect(r.compositeZ).toBeCloseTo(expected, 12);
  });

  it('places a bank at the sample centre on exactly 50', () => {
    const stats = computeSampleStats(sample);
    // Bank b sits at the mean of every indicator in this symmetric sample.
    const r = calculateBFPI(sample[1], stats);
    expect(r.compositeZ).toBeCloseTo(0, 12);
    expect(r.bfpi).toBeCloseTo(50, 10);
  });
});

describe('transformTo100Scale', () => {
  it('maps BFPI = 50 + 10Z', () => {
    expect(transformTo100Scale(0)).toBe(50);
    expect(transformTo100Scale(1)).toBe(60);
    expect(transformTo100Scale(-1)).toBe(40);
    expect(transformTo100Scale(1.42)).toBeCloseTo(64.2, 10);
  });

  it('clamps to the presentation range at extreme z-scores', () => {
    expect(transformTo100Scale(9)).toBe(100);
    expect(transformTo100Scale(-9)).toBe(0);
  });

  it('propagates NaN rather than clamping it to a plausible score', () => {
    expect(Number.isNaN(transformTo100Scale(NaN))).toBe(true);
  });
});

describe('interpretation bands', () => {
  it('covers 0 to 100 with no gaps', () => {
    const ordered = [...BFPI_BANDS].sort((a, b) => a.min - b.min);
    expect(ordered[0].min).toBe(0);
    for (let i = 1; i < ordered.length; i += 1) expect(ordered[i].min).toBe(ordered[i - 1].max);
  });

  it('labels each band as relative performance, never as best or safest', () => {
    for (const b of BFPI_BANDS) {
      expect(b.label.toLowerCase()).toMatch(/performance/);
      expect(b.label.toLowerCase()).not.toMatch(/best|worst|safest|strongest bank|weakest bank/);
    }
  });

  it('assigns the documented band at each boundary', () => {
    expect(bandFor(80)?.label).toBe('Very strong relative performance');
    expect(bandFor(79.9)?.label).toBe('Strong relative performance');
    expect(bandFor(60)?.label).toBe('Above-average performance');
    expect(bandFor(59.9)?.label).toBe('Around-average performance');
    expect(bandFor(49.9)?.label).toBe('Below-average performance');
    expect(bandFor(19.9)?.label).toBe('Extremely weak relative performance');
    expect(bandFor(100)?.label).toBe('Very strong relative performance');
  });

  it('returns no band when BFPI is unavailable', () => {
    expect(bandFor(null)).toBeNull();
  });
});

describe('missing values', () => {
  it('renormalises the surviving pillar weights and says so', () => {
    const stats = computeSampleStats(sample);
    const r = calculateBFPI(
      { bankId: 'gap', periodLabel: 'FY2025', values: obs({ nim: 5, roe: 18, capital: 16, npl: 4, provisions: 3 }) },
      stats,
    );
    const byKey = Object.fromEntries(r.pillars.map((p) => [p.key, p.z]));
    const expected = (byKey.profitability! + byKey.capital! + byKey.assetQuality!) / 3;
    expect(r.compositeZ).toBeCloseTo(expected, 12);
    expect(r.partial).toBe(true);
    expect(r.missing).toContain('lcr');
    expect(r.treatment).toContain('Liquidity');
  });

  it('never substitutes a zero for a missing indicator', () => {
    const stats = computeSampleStats(sample);
    const withGap = calculateBFPI(
      { bankId: 'gap', periodLabel: 'FY2025', values: obs({ nim: 5, roe: 18, capital: 16, npl: 4, provisions: 3 }) },
      stats,
    );
    const zeroed = calculateBFPI(
      { bankId: 'zero', periodLabel: 'FY2025', values: obs({ nim: 5, roe: 18, capital: 16, npl: 4, provisions: 3, lcr: 0 }) },
      stats,
    );
    expect(withGap.bfpi).not.toBeCloseTo(zeroed.bfpi as number, 4);
    expect(withGap.bfpi as number).toBeGreaterThan(zeroed.bfpi as number);
  });

  it('withholds the composite when fewer pillars survive than the sample requires', () => {
    const stats = computeSampleStats(sample);
    const thin = { bankId: 'thin', periodLabel: 'FY2025', values: obs({ nim: 4 }) };
    const permissive = calculateBFPI(thin, stats);
    const strict = calculateBFPI(thin, stats, { minPillars: 3 });

    expect(permissive.bfpi).not.toBeNull();
    expect(strict.bfpi).toBeNull();
    expect(strict.treatment).toContain('withheld');
    // The pillars that could be computed are still exposed for inspection.
    expect(strict.pillars.find((p) => p.key === 'profitability')!.z).not.toBeNull();
  });

  it('still reports a composite when enough pillars survive the threshold', () => {
    const stats = computeSampleStats(sample);
    const r = calculateBFPI(
      { bankId: 'ok', periodLabel: 'FY2025', values: obs({ nim: 5, roe: 18, capital: 16, npl: 4 }) },
      stats,
      { minPillars: 3 },
    );
    expect(r.bfpi).not.toBeNull();
    expect(r.partial).toBe(true);
  });

  it('reports no BFPI at all when nothing is available', () => {
    const stats = computeSampleStats(sample);
    const r = calculateBFPI({ bankId: 'empty', periodLabel: 'FY2025', values: obs({}) }, stats);
    expect(r.bfpi).toBeNull();
    expect(r.compositeZ).toBeNull();
    expect(r.missing).toHaveLength(INDICATOR_KEYS.length);
    expect(r.treatment).toContain('not reported');
  });

  it('lists every missing indicator by key', () => {
    const stats = computeSampleStats(sample);
    const r = calculateBFPI(
      { bankId: 'p', periodLabel: 'FY2025', values: obs({ nim: 4, capital: 14, npl: 3, lcr: 130 }) },
      stats,
    );
    expect(r.missing.sort()).toEqual(['provisions', 'roe']);
  });
});

describe('edge cases', () => {
  it('scores a single-bank sample at exactly the centre of its own sample', () => {
    const solo: BankObservation[] = [
      { bankId: 'solo', periodLabel: 'FY2025', values: obs({ nim: 4, roe: 14, capital: 14, npl: 3, provisions: 2, lcr: 130 }) },
    ];
    const { results } = calculateSample(solo);
    // σ = 0 for every indicator, so every z is 0 and BFPI is 50 by construction.
    expect(results[0].bfpi).toBe(50);
  });

  it('handles a sample where every bank reports the same value', () => {
    const flat: BankObservation[] = ['a', 'b', 'c'].map((bankId) => ({
      bankId,
      periodLabel: 'FY2025',
      values: obs({ nim: 4, roe: 14, capital: 14, npl: 3, provisions: 2, lcr: 130 }),
    }));
    const { results } = calculateSample(flat);
    for (const r of results) expect(r.bfpi).toBe(50);
  });

  it('accepts negative ROE and ranks it below the sample', () => {
    const withLoss: BankObservation[] = [
      ...sample,
      { bankId: 'd', periodLabel: 'FY2025', values: obs({ nim: 2, roe: -12, capital: 9, npl: 8, provisions: 5, lcr: 105 }) },
    ];
    const { results } = calculateSample(withLoss);
    const d = results.find((r) => r.bankId === 'd')!;
    expect(d.bfpi as number).toBeLessThan(50);
  });

  it('keeps z-scores summing to zero across a complete sample', () => {
    const { results } = calculateSample(sample);
    const total = results.reduce((s, r) => s + (r.compositeZ as number), 0);
    expect(total).toBeCloseTo(0, 10);
  });

  it('is invariant to the order of banks in the sample', () => {
    const forward = calculateSample(sample).results.find((r) => r.bankId === 'a')!;
    const reversed = calculateSample([...sample].reverse()).results.find((r) => r.bankId === 'a')!;
    expect(forward.bfpi).toBeCloseTo(reversed.bfpi as number, 12);
  });

  it('shifts BFPI when the sample changes, because the index is relative', () => {
    const inSmallSample = calculateSample(sample).results.find((r) => r.bankId === 'c')!;
    const wider = calculateSample([
      ...sample,
      { bankId: 'd', periodLabel: 'FY2025', values: obs({ nim: 9, roe: 30, capital: 24, npl: 1, provisions: 0.5, lcr: 200 }) },
    ]).results.find((r) => r.bankId === 'c')!;
    expect(inSmallSample.bfpi).not.toBeCloseTo(wider.bfpi as number, 3);
  });
});

describe('stress propagation', () => {
  it('lowers asset quality and BFPI when NPL rises, holding everything else fixed', () => {
    const stats = computeSampleStats(sample);
    const beforeValues = sample[1].values;
    const before = calculateBFPI({ bankId: 'b', periodLabel: 'FY2025', values: beforeValues }, stats);
    const after = calculateBFPI(
      { bankId: 'b', periodLabel: 'FY2025', values: { ...beforeValues, npl: 6 } },
      stats,
    );
    const aqBefore = before.pillars.find((p) => p.key === 'assetQuality')!.z as number;
    const aqAfter = after.pillars.find((p) => p.key === 'assetQuality')!.z as number;
    expect(aqAfter).toBeLessThan(aqBefore);
    expect(after.bfpi as number).toBeLessThan(before.bfpi as number);
  });

  it('leaves the other three pillars untouched when only NPL moves', () => {
    const stats = computeSampleStats(sample);
    const before = calculateBFPI(sample[1], stats);
    const after = calculateBFPI(
      { bankId: 'b', periodLabel: 'FY2025', values: { ...sample[1].values, npl: 6 } },
      stats,
    );
    for (const key of ['profitability', 'capital', 'liquidity'] as const) {
      expect(after.pillars.find((p) => p.key === key)!.z).toBeCloseTo(
        before.pillars.find((p) => p.key === key)!.z as number,
        12,
      );
    }
  });

  it('raises BFPI when LCR improves', () => {
    const stats = computeSampleStats(sample);
    const before = calculateBFPI(sample[0], stats);
    const after = calculateBFPI(
      { bankId: 'a', periodLabel: 'FY2025', values: { ...sample[0].values, lcr: 180 } },
      stats,
    );
    expect(after.bfpi as number).toBeGreaterThan(before.bfpi as number);
  });
});

describe('validateObservations', () => {
  it('passes a plausible sample', () => {
    expect(validateObservations(sample)).toHaveLength(0);
  });

  it('flags a negative LCR', () => {
    const issues = validateObservations([
      { bankId: 'bad', periodLabel: 'FY2025', values: obs({ lcr: -5 }) },
    ]);
    expect(issues).toHaveLength(1);
    expect(issues[0].key).toBe('lcr');
    expect(issues[0].message).toContain('outside the plausible range');
  });

  it('flags an impossible NPL percentage', () => {
    const issues = validateObservations([
      { bankId: 'bad', periodLabel: 'FY2025', values: obs({ npl: 140 }) },
    ]);
    expect(issues[0].key).toBe('npl');
  });

  it('ignores nulls, which are legitimate gaps rather than bad data', () => {
    expect(validateObservations([{ bankId: 'gap', periodLabel: 'FY2025', values: obs({}) }])).toHaveLength(0);
  });
});
