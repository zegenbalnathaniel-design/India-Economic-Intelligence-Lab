/**
 * Figure 2 engine — household wealth accumulation.
 *
 * Pure functions, no React, no formatting. Everything the figure displays is
 * computed here from the inputs the reader supplies, so the chart, the
 * headline numbers and the "Show calculation" panel can never disagree.
 *
 *   Portfolio return    R_p = Σ wᵢ Rᵢ
 *   Annuity future value FV  = C · [ (1+r)ⁿ − 1 ] / r
 *
 * The closed form above is the identity quoted in the paper. The engine
 * accumulates period by period instead, because that generalises to a
 * starting balance, to start-of-period contributions and to contribution
 * frequencies finer than annual — and it agrees with the closed form
 * exactly in the case the closed form covers (see engine.test.ts).
 */
import {
  ASSET_KEYS,
  type Allocation,
  type AllocationValidation,
  type AssetKey,
  type ContributionFrequency,
  type Figure2Inputs,
  type Figure2Result,
  type Returns,
  type ScenarioComparison,
  type YearRow,
} from './types';

/** Weights are compared to 1 with this tolerance (0.01 pp). */
export const ALLOCATION_TOLERANCE = 1e-4;

export const PERIODS_PER_YEAR: Record<ContributionFrequency, number> = {
  annual: 1,
  quarterly: 4,
  monthly: 12,
};

/** Σ wᵢRᵢ — the weighted nominal return on the portfolio. */
export function calculatePortfolioReturn(allocation: Allocation, returns: Returns): number {
  return ASSET_KEYS.reduce((sum, k) => sum + (allocation[k] ?? 0) * (returns[k] ?? 0), 0);
}

/**
 * Allocation must equal 100%. The model never renormalises silently — an
 * invalid allocation is reported back to the reader untouched (spec §19).
 */
export function validateAllocation(allocation: Allocation): AllocationValidation {
  const total = ASSET_KEYS.reduce((sum, k) => sum + (allocation[k] ?? 0), 0);
  const offBy = (total - 1) * 100;
  const valid = Math.abs(total - 1) <= ALLOCATION_TOLERANCE;
  return {
    valid,
    total,
    offBy,
    message: valid
      ? null
      : `Allocation must equal 100%. Currently ${(total * 100).toFixed(1)}% (${
          offBy > 0 ? '+' : ''
        }${offBy.toFixed(1)} pp).`,
  };
}

/**
 * Closed-form future value of a level annuity, as printed in the paper:
 *
 *   FV = C · [ (1+r)ⁿ − 1 ] / r      (r ≠ 0)
 *   FV = C · n                       (r = 0, the limiting case)
 */
export function calculateFutureValue(contribution: number, rate: number, periods: number): number {
  if (periods <= 0) return 0;
  if (Math.abs(rate) < 1e-12) return contribution * periods;
  // log1p/expm1 rather than Math.pow: at rates near zero the naive form
  // computes (1+r)ⁿ−1 as the difference of two numbers close to 1 and
  // loses most of its significant figures.
  return contribution * (Math.expm1(periods * Math.log1p(rate)) / rate);
}

/**
 * Effective per-period rate for a given annual rate, compounded `m` times a
 * year: (1+r)^(1/m) − 1. Using the equivalent compounded rate rather than
 * r/m keeps the annual outcome identical whatever frequency the reader
 * picks, so changing frequency shows the timing effect alone.
 */
export function periodicRate(annualRate: number, periodsPerYear: number): number {
  if (periodsPerYear === 1) return annualRate;
  return Math.pow(1 + annualRate, 1 / periodsPerYear) - 1;
}

/** An empty per-asset record. */
const zeroAssets = (): Record<AssetKey, number> =>
  ASSET_KEYS.reduce((acc, k) => ({ ...acc, [k]: 0 }), {} as Record<AssetKey, number>);

/**
 * Run the model. Contributions are split across assets at the target
 * weights; each asset compounds at its own nominal return; the portfolio is
 * rebalanced to target at each year end, which is what makes Σ wᵢRᵢ the
 * governing return and keeps the decomposition interpretable.
 *
 * Invalid allocations still compute, because a reader who has dragged the
 * weights to 93% should be able to see what that implies rather than face a
 * blank chart. The share that is not allocated is carried as non-earning
 * residual cash so that every rupee contributed is accounted for somewhere;
 * weights summing above 100% produce a negative residual, which is a
 * borrowing position and is labelled as one. Nothing is renormalised.
 */
export function calculateScenario(inputs: Figure2Inputs): Figure2Result {
  const validation = validateAllocation(inputs.allocation);
  const portfolioReturn = calculatePortfolioReturn(inputs.allocation, inputs.returns);
  const m = PERIODS_PER_YEAR[inputs.frequency];
  const years = Math.max(0, Math.floor(inputs.years));

  const perPeriodContribution = inputs.annualSaving / m;
  const rate = periodicRate(portfolioReturn, m);

  const totalWeight = validation.total;
  const residualWeight = 1 - totalWeight;

  let balances = zeroAssets();
  for (const k of ASSET_KEYS) balances[k] = inputs.startingCapital * (inputs.allocation[k] ?? 0);
  let residual = inputs.startingCapital * residualWeight;

  let contributed = inputs.startingCapital;
  const rows: YearRow[] = [];

  const contribute = () => {
    for (const k of ASSET_KEYS) balances[k] += perPeriodContribution * (inputs.allocation[k] ?? 0);
    residual += perPeriodContribution * residualWeight;
    contributed += perPeriodContribution;
  };

  for (let y = 1; y <= years; y += 1) {
    for (let p = 0; p < m; p += 1) {
      if (inputs.timing === 'start') contribute();

      // Each asset earns its own return over the period. The residual earns
      // nothing — that is what makes it a residual rather than an asset.
      for (const k of ASSET_KEYS) {
        const assetPeriodRate = periodicRate(inputs.returns[k] ?? 0, m);
        balances[k] *= 1 + assetPeriodRate;
      }

      if (inputs.timing === 'end') contribute();
    }

    // Annual rebalance back to the target mix. Weights are divided by their
    // own sum so the *relative* mix the reader specified is preserved; when
    // they already sum to 1 this is exactly a rebalance to target.
    const invested = ASSET_KEYS.reduce((s, k) => s + balances[k], 0);
    const rebalanced = zeroAssets();
    if (totalWeight !== 0) {
      for (const k of ASSET_KEYS) rebalanced[k] = invested * ((inputs.allocation[k] ?? 0) / totalWeight);
    }
    balances = rebalanced;

    const total = invested + residual;
    rows.push({
      year: y,
      value: total,
      contributed,
      gain: total - contributed,
      byAsset: { ...rebalanced },
      residual,
    });
  }

  const finalValue = rows.length ? rows[rows.length - 1].value : inputs.startingCapital;
  const totalContributed = inputs.startingCapital + inputs.annualSaving * years;

  return {
    inputs,
    validation,
    portfolioReturn,
    assetReturn: totalWeight === 0 ? 0 : portfolioReturn / totalWeight,
    residualWeight,
    residualValue: rows.length ? rows[rows.length - 1].residual : inputs.startingCapital * residualWeight,
    periodicRate: rate,
    periodsPerYear: m,
    rows,
    totalContributed,
    finalValue,
    investmentGain: finalValue - totalContributed,
    wealthMultiple: totalContributed > 0 ? finalValue / totalContributed : 0,
  };
}

/** Baseline vs reader scenario (spec §22). */
export function compareScenarios(
  baselineInputs: Figure2Inputs,
  scenarioInputs: Figure2Inputs,
): ScenarioComparison {
  const baseline = calculateScenario(baselineInputs);
  const scenario = calculateScenario(scenarioInputs);
  const difference = scenario.finalValue - baseline.finalValue;
  return {
    baseline,
    scenario,
    difference,
    percentDifference: baseline.finalValue > 0 ? (difference / baseline.finalValue) * 100 : 0,
    returnDifference: scenario.portfolioReturn - baseline.portfolioReturn,
  };
}

/**
 * Shift weight from one asset to another, keeping the allocation at exactly
 * 100%. Used by the one-slider experiment ("financial assets 5% → 20%"),
 * where the offsetting change must come from somewhere explicit.
 */
export function reallocate(
  allocation: Allocation,
  from: AssetKey,
  to: AssetKey,
  targetWeightForTo: number,
): Allocation {
  const delta = targetWeightForTo - (allocation[to] ?? 0);
  const next: Allocation = { ...allocation };
  next[to] = targetWeightForTo;
  next[from] = (allocation[from] ?? 0) - delta;
  return next;
}
