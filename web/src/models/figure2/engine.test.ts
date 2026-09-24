import { describe, expect, it } from 'vitest';
import {
  ALLOCATION_TOLERANCE,
  calculateFutureValue,
  calculatePortfolioReturn,
  calculateScenario,
  compareScenarios,
  periodicRate,
  reallocate,
  validateAllocation,
} from './engine';
import { ASSET_KEYS, type Allocation, type Figure2Inputs, type Returns } from './types';

const alloc = (property: number, gold: number, financial: number, other: number): Allocation => ({
  property,
  gold,
  financial,
  other,
});

const rets: Returns = { property: 0.06, gold: 0.1, financial: 0.11, other: 0.02 };

const base = (over: Partial<Figure2Inputs> = {}): Figure2Inputs => ({
  annualSaving: 100_000,
  startingCapital: 0,
  years: 30,
  frequency: 'annual',
  timing: 'end',
  allocation: alloc(0.77, 0.11, 0.05, 0.07),
  returns: rets,
  ...over,
});

describe('calculatePortfolioReturn', () => {
  it('computes the weighted sum R_p = Σ wᵢRᵢ', () => {
    // 0.77·0.06 + 0.11·0.10 + 0.05·0.11 + 0.07·0.02
    //   = 0.0462 + 0.0110 + 0.0055 + 0.0014 = 0.0641
    expect(calculatePortfolioReturn(alloc(0.77, 0.11, 0.05, 0.07), rets)).toBeCloseTo(0.0641, 12);
  });

  it('returns the single asset return when fully concentrated', () => {
    expect(calculatePortfolioReturn(alloc(0, 0, 1, 0), rets)).toBeCloseTo(0.11, 12);
  });

  it('is linear in the weights', () => {
    const a = calculatePortfolioReturn(alloc(1, 0, 0, 0), rets);
    const b = calculatePortfolioReturn(alloc(0, 1, 0, 0), rets);
    const mix = calculatePortfolioReturn(alloc(0.5, 0.5, 0, 0), rets);
    expect(mix).toBeCloseTo(0.5 * a + 0.5 * b, 12);
  });

  it('treats a missing return as zero rather than NaN', () => {
    const partial = { property: 0.06 } as unknown as Returns;
    expect(calculatePortfolioReturn(alloc(0.5, 0.5, 0, 0), partial)).toBeCloseTo(0.03, 12);
  });
});

describe('validateAllocation', () => {
  it('accepts weights summing to exactly 100%', () => {
    const v = validateAllocation(alloc(0.77, 0.11, 0.05, 0.07));
    expect(v.valid).toBe(true);
    expect(v.message).toBeNull();
    expect(v.offBy).toBeCloseTo(0, 10);
  });

  it('rejects an under-allocated portfolio and reports the shortfall', () => {
    const v = validateAllocation(alloc(0.5, 0.1, 0.05, 0.05));
    expect(v.valid).toBe(false);
    expect(v.total).toBeCloseTo(0.7, 10);
    expect(v.offBy).toBeCloseTo(-30, 8);
    expect(v.message).toContain('Allocation must equal 100%');
  });

  it('rejects an over-allocated portfolio', () => {
    const v = validateAllocation(alloc(0.8, 0.2, 0.1, 0.05));
    expect(v.valid).toBe(false);
    expect(v.offBy).toBeCloseTo(15, 8);
  });

  it('tolerates floating-point dust but not a real 0.5 pp gap', () => {
    expect(validateAllocation(alloc(1 / 3, 1 / 3, 1 / 3, 0)).valid).toBe(true);
    expect(validateAllocation(alloc(0.77, 0.11, 0.05, 0.065)).valid).toBe(false);
  });

  it('never mutates or renormalises the weights it was given', () => {
    const a = alloc(0.5, 0.1, 0.05, 0.05);
    const snapshot = { ...a };
    validateAllocation(a);
    expect(a).toEqual(snapshot);
  });

  it('exposes a tolerance tighter than one hundredth of a percentage point', () => {
    expect(ALLOCATION_TOLERANCE).toBeLessThanOrEqual(1e-4);
  });
});

describe('calculateFutureValue', () => {
  it('matches the closed form FV = C·[(1+r)ⁿ−1]/r', () => {
    const c = 100_000;
    const r = 0.0857;
    const n = 30;
    const expected = c * ((Math.pow(1 + r, n) - 1) / r);
    expect(calculateFutureValue(c, r, n)).toBeCloseTo(expected, 6);
  });

  it('degenerates to C·n at a zero rate', () => {
    expect(calculateFutureValue(100_000, 0, 30)).toBe(3_000_000);
  });

  it('is continuous as the rate approaches zero', () => {
    // The limit of C·[(1+r)ⁿ−1]/r as r→0 is C·n. A naive Math.pow loses
    // ~8 significant figures here; log1p/expm1 keeps it to the cent.
    expect(calculateFutureValue(100_000, 1e-9, 30)).toBeCloseTo(3_000_000.0435, 2);
  });

  it('returns zero for a non-positive horizon', () => {
    expect(calculateFutureValue(100_000, 0.08, 0)).toBe(0);
    expect(calculateFutureValue(100_000, 0.08, -5)).toBe(0);
  });

  it('handles a negative rate without breaking', () => {
    const v = calculateFutureValue(100_000, -0.02, 10);
    expect(v).toBeGreaterThan(0);
    expect(v).toBeLessThan(1_000_000);
  });
});

describe('periodicRate', () => {
  it('is the identity for annual compounding', () => {
    expect(periodicRate(0.0857, 1)).toBe(0.0857);
  });

  it('compounds back to the annual rate', () => {
    const m = 12;
    const r = periodicRate(0.0857, m);
    expect(Math.pow(1 + r, m) - 1).toBeCloseTo(0.0857, 12);
  });
});

describe('calculateScenario', () => {
  it('reproduces the closed-form annuity for end-of-year annual contributions', () => {
    const result = calculateScenario(base());
    const expected = calculateFutureValue(100_000, result.portfolioReturn, 30);
    expect(result.finalValue).toBeCloseTo(expected, 4);
  });

  it('reports total contributions as C·n and the paper default of ₹30,00,000', () => {
    const result = calculateScenario(base());
    expect(result.totalContributed).toBe(3_000_000);
    expect(result.investmentGain).toBeCloseTo(result.finalValue - 3_000_000, 6);
  });

  it('derives the wealth multiple from final value over contributions', () => {
    const r = calculateScenario(base());
    expect(r.wealthMultiple).toBeCloseTo(r.finalValue / r.totalContributed, 12);
  });

  it('produces one row per year with monotonically rising contributions', () => {
    const r = calculateScenario(base({ years: 12 }));
    expect(r.rows).toHaveLength(12);
    expect(r.rows[0].year).toBe(1);
    for (let i = 1; i < r.rows.length; i += 1) {
      expect(r.rows[i].contributed).toBeGreaterThan(r.rows[i - 1].contributed);
    }
    expect(r.rows[11].contributed).toBe(1_200_000);
  });

  it('keeps per-asset balances at target weights after the annual rebalance', () => {
    const r = calculateScenario(base({ years: 5 }));
    const last = r.rows[4];
    expect(last.byAsset.property / last.value).toBeCloseTo(0.77, 10);
    expect(last.byAsset.financial / last.value).toBeCloseTo(0.05, 10);
    const sum = Object.values(last.byAsset).reduce((a, b) => a + b, 0);
    expect(sum).toBeCloseTo(last.value, 4);
  });

  it('start-of-period contributions beat end-of-period by exactly one period of growth', () => {
    const end = calculateScenario(base({ timing: 'end' }));
    const start = calculateScenario(base({ timing: 'start' }));
    expect(start.finalValue).toBeCloseTo(end.finalValue * (1 + end.portfolioReturn), 4);
  });

  it('compounds a starting balance over the full horizon', () => {
    const r = calculateScenario(base({ startingCapital: 500_000, annualSaving: 0 }));
    expect(r.finalValue).toBeCloseTo(500_000 * Math.pow(1 + r.portfolioReturn, 30), 4);
    expect(r.totalContributed).toBe(500_000);
  });

  it('adds the starting balance into total contributions, not into gains', () => {
    const r = calculateScenario(base({ startingCapital: 200_000 }));
    expect(r.totalContributed).toBe(3_200_000);
  });

  it('gives a higher outcome at a finer contribution frequency, holding the annual amount fixed', () => {
    const annual = calculateScenario(base({ frequency: 'annual' }));
    const monthly = calculateScenario(base({ frequency: 'monthly' }));
    expect(monthly.finalValue).toBeGreaterThan(annual.finalValue);
    expect(monthly.totalContributed).toBeCloseTo(annual.totalContributed, 6);
  });

  it('returns the starting capital untouched over a zero-year horizon', () => {
    const r = calculateScenario(base({ years: 0, startingCapital: 250_000 }));
    expect(r.rows).toHaveLength(0);
    expect(r.finalValue).toBe(250_000);
  });

  it('still computes when the allocation is invalid, and says so', () => {
    const r = calculateScenario(base({ allocation: alloc(0.5, 0.1, 0.05, 0.05) }));
    expect(r.validation.valid).toBe(false);
    expect(r.validation.message).toContain('100%');
    // The reader's numbers are not silently rescaled.
    expect(r.inputs.allocation.property).toBe(0.5);
  });

  it('never fabricates growth at a zero return', () => {
    const r = calculateScenario(
      base({ returns: { property: 0, gold: 0, financial: 0, other: 0 } }),
    );
    expect(r.finalValue).toBeCloseTo(3_000_000, 6);
    expect(r.investmentGain).toBeCloseTo(0, 6);
    expect(r.wealthMultiple).toBeCloseTo(1, 10);
  });
});

describe('invalid allocations', () => {
  it('holds the unallocated share as non-earning residual rather than losing it', () => {
    // Weights sum to 93%: 7% of every contribution is not allocated anywhere.
    const r = calculateScenario(base({ allocation: alloc(0.7, 0.11, 0.05, 0.07) }));
    expect(r.validation.valid).toBe(false);
    expect(r.residualWeight).toBeCloseTo(0.07, 12);
    expect(r.residualValue).toBeCloseTo(0.07 * 100_000 * 30, 6);
  });

  it('never loses a rupee: final value is at least the amount actually contributed', () => {
    const r = calculateScenario(base({ allocation: alloc(0.7, 0.11, 0.05, 0.07) }));
    expect(r.finalValue).toBeGreaterThan(r.totalContributed);
    // Assets plus residual reconcile to the reported value.
    const last = r.rows[r.rows.length - 1];
    const assets = ASSET_KEYS.reduce((s, k) => s + last.byAsset[k], 0);
    expect(assets + last.residual).toBeCloseTo(last.value, 4);
  });

  it('reports a negative residual for an over-allocated portfolio', () => {
    const r = calculateScenario(base({ allocation: alloc(0.8, 0.2, 0.1, 0.07) }));
    expect(r.validation.valid).toBe(false);
    expect(r.residualWeight).toBeCloseTo(-0.17, 12);
    expect(r.residualValue).toBeLessThan(0);
  });

  it('preserves the relative asset mix the reader specified', () => {
    const r = calculateScenario(base({ allocation: alloc(0.7, 0.11, 0.05, 0.07), years: 5 }));
    const last = r.rows[4];
    const invested = ASSET_KEYS.reduce((s, k) => s + last.byAsset[k], 0);
    // Property is 0.70 of a 0.93 total, so 75.3% of the invested portion.
    expect(last.byAsset.property / invested).toBeCloseTo(0.7 / 0.93, 10);
  });

  it('separates the literal Σ wᵢRᵢ from the return on the invested portion', () => {
    const r = calculateScenario(base({ allocation: alloc(0.7, 0.11, 0.05, 0.07) }));
    expect(r.portfolioReturn).toBeCloseTo(0.7 * 0.06 + 0.11 * 0.1 + 0.05 * 0.11 + 0.07 * 0.02, 12);
    expect(r.assetReturn).toBeCloseTo(r.portfolioReturn / 0.93, 12);
    expect(r.assetReturn).toBeGreaterThan(r.portfolioReturn);
  });

  it('leaves residual at zero and the two returns equal when the allocation is valid', () => {
    const r = calculateScenario(base());
    expect(r.residualWeight).toBeCloseTo(0, 12);
    expect(r.residualValue).toBeCloseTo(0, 6);
    expect(r.assetReturn).toBeCloseTo(r.portfolioReturn, 12);
  });

  it('puts everything into the residual when no weight is allocated at all', () => {
    const r = calculateScenario(base({ allocation: alloc(0, 0, 0, 0) }));
    expect(r.finalValue).toBeCloseTo(3_000_000, 6);
    expect(r.investmentGain).toBeCloseTo(0, 6);
    expect(r.assetReturn).toBe(0);
  });
});

describe('compareScenarios', () => {
  it('isolates the effect of shifting 15 pp from property into financial assets', () => {
    const baseline = base();
    const scenario = base({ allocation: alloc(0.62, 0.11, 0.2, 0.07) });
    const c = compareScenarios(baseline, scenario);

    expect(c.returnDifference).toBeCloseTo(0.15 * (0.11 - 0.06), 12);
    expect(c.scenario.finalValue).toBeGreaterThan(c.baseline.finalValue);
    expect(c.difference).toBeCloseTo(c.scenario.finalValue - c.baseline.finalValue, 6);
    expect(c.percentDifference).toBeCloseTo((c.difference / c.baseline.finalValue) * 100, 10);
  });

  it('reports a zero difference when the scenario equals the baseline', () => {
    const c = compareScenarios(base(), base());
    expect(c.difference).toBeCloseTo(0, 8);
    expect(c.percentDifference).toBeCloseTo(0, 8);
  });

  it('reports a negative difference when the reader lowers the return', () => {
    const c = compareScenarios(base(), base({ allocation: alloc(0.92, 0.03, 0.02, 0.03) }));
    expect(c.difference).toBeLessThan(0);
  });
});

describe('reallocate', () => {
  it('moves weight between two assets and keeps the total at 100%', () => {
    const next = reallocate(alloc(0.77, 0.11, 0.05, 0.07), 'property', 'financial', 0.2);
    expect(next.financial).toBeCloseTo(0.2, 12);
    expect(next.property).toBeCloseTo(0.62, 12);
    expect(validateAllocation(next).valid).toBe(true);
  });

  it('can move weight back the other way', () => {
    const next = reallocate(alloc(0.62, 0.11, 0.2, 0.07), 'property', 'financial', 0.05);
    expect(next.property).toBeCloseTo(0.77, 12);
    expect(validateAllocation(next).valid).toBe(true);
  });
});
