/** BFPI — Bank Financial Performance Index. Model types. */

export const INDICATOR_KEYS = ['nim', 'roe', 'capital', 'npl', 'provisions', 'lcr'] as const;
export type IndicatorKey = (typeof INDICATOR_KEYS)[number];

export const PILLAR_KEYS = ['profitability', 'capital', 'assetQuality', 'liquidity'] as const;
export type PillarKey = (typeof PILLAR_KEYS)[number];

/** +1 higher-is-better, −1 lower-is-better. */
export type Direction = 1 | -1;

export interface IndicatorSpec {
  key: IndicatorKey;
  label: string;
  short: string;
  pillar: PillarKey;
  direction: Direction;
  unit: string;
  /** Plausibility bounds used by validation, in the indicator's own unit. */
  min: number;
  max: number;
  step: number;
  rationale: string;
}

export interface PillarSpec {
  key: PillarKey;
  label: string;
  weight: number;
  indicators: IndicatorKey[];
  rationale: string;
}

/** One bank's observations for one reporting period. Nulls are real gaps. */
export type Observations = Record<IndicatorKey, number | null>;

export interface BankObservation {
  bankId: string;
  periodLabel: string;
  values: Observations;
}

export interface IndicatorStat {
  key: IndicatorKey;
  /** Sample mean μᵢ across banks with a value for this indicator. */
  mean: number;
  /** Population standard deviation σᵢ. */
  sd: number;
  n: number;
  direction: Direction;
}

export type SampleStats = Partial<Record<IndicatorKey, IndicatorStat>>;

export interface IndicatorScore {
  key: IndicatorKey;
  raw: number | null;
  mean: number | null;
  sd: number | null;
  direction: Direction;
  /** zᵢ = dᵢ (Xᵢ − μᵢ) / σᵢ */
  z: number | null;
  available: boolean;
  /** Why a score is missing, when it is. */
  note?: string;
}

export interface PillarScore {
  key: PillarKey;
  label: string;
  weight: number;
  /** Mean of the available indicator z-scores in this pillar. */
  z: number | null;
  /** The pillar on the same 0–100 presentation scale as BFPI. */
  scaled: number | null;
  indicators: IndicatorScore[];
  available: boolean;
  /** Set when some but not all of the pillar's indicators were available. */
  partial: boolean;
  note?: string;
}

export interface BFPIResult {
  bankId: string;
  periodLabel: string;
  pillars: PillarScore[];
  /** Composite in z units: Σ wₖ Pₖ. */
  compositeZ: number | null;
  /** Presentation scale: 50 + 10 · Z_BFPI, clamped to [0, 100]. */
  bfpi: number | null;
  /** True when the composite was formed from fewer than four pillars. */
  partial: boolean;
  /** Indicators that had no value for this bank and period. */
  missing: IndicatorKey[];
  /** Plain-language account of any treatment applied. */
  treatment: string | null;
}

export interface BFPIBand {
  min: number;
  max: number;
  label: string;
  tone: string;
}

export interface ValidationIssue {
  bankId: string;
  key: IndicatorKey;
  value: number;
  message: string;
}
