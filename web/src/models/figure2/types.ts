/** Figure 2 — Household Wealth Accumulation. Model types. */

export const ASSET_KEYS = ['property', 'gold', 'financial', 'other'] as const;
export type AssetKey = (typeof ASSET_KEYS)[number];

export type ContributionFrequency = 'annual' | 'quarterly' | 'monthly';
export type ContributionTiming = 'end' | 'start';

/** Allocation weights as decimal fractions. Must sum to 1. */
export type Allocation = Record<AssetKey, number>;
/** Expected nominal returns as decimal fractions per annum. */
export type Returns = Record<AssetKey, number>;

export interface Figure2Inputs {
  /** Total saved per year, in rupees, before splitting across assets. */
  annualSaving: number;
  /** Wealth already held at t = 0. */
  startingCapital: number;
  years: number;
  frequency: ContributionFrequency;
  timing: ContributionTiming;
  allocation: Allocation;
  returns: Returns;
}

export interface AllocationValidation {
  valid: boolean;
  /** Sum of the weights as entered, as a decimal fraction. */
  total: number;
  /** Signed distance from 1, in percentage points. */
  offBy: number;
  message: string | null;
}

export interface YearRow {
  year: number;
  /** Portfolio value at the end of `year`. */
  value: number;
  /** Cumulative amount put in, including starting capital. */
  contributed: number;
  /** value − contributed. */
  gain: number;
  /** Per-asset balances at the end of `year` (annual rebalancing to target). */
  byAsset: Record<AssetKey, number>;
  /**
   * Contributions not covered by the allocation, held as non-earning cash.
   * Zero whenever the weights sum to exactly 100%; negative when they sum
   * to more than 100%, which is a borrowing position rather than a
   * portfolio. It exists so that money a reader contributes is always
   * accounted for somewhere, even while the allocation is invalid.
   */
  residual: number;
}

export interface Figure2Result {
  inputs: Figure2Inputs;
  validation: AllocationValidation;
  /** Weighted nominal portfolio return, Σ wᵢRᵢ. */
  portfolioReturn: number;
  /**
   * Growth rate of the invested portion alone, Σ wᵢRᵢ ÷ Σ wᵢ. Identical to
   * `portfolioReturn` when the allocation is valid; differs only while it
   * is not, because then part of the contribution is not invested at all.
   */
  assetReturn: number;
  /** 1 − Σ wᵢ. Zero when the allocation is valid. */
  residualWeight: number;
  /** Closing balance of the non-earning residual. */
  residualValue: number;
  /** Per-period rate actually compounded, given the contribution frequency. */
  periodicRate: number;
  periodsPerYear: number;
  rows: YearRow[];
  totalContributed: number;
  finalValue: number;
  investmentGain: number;
  /** finalValue ÷ totalContributed. */
  wealthMultiple: number;
}

export interface ScenarioComparison {
  baseline: Figure2Result;
  scenario: Figure2Result;
  difference: number;
  percentDifference: number;
  returnDifference: number;
}
