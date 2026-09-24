/**
 * BFPI engine — Bank Financial Performance Index.
 *
 * BFPI is an original composite index constructed for analytical purposes.
 * It is not an RBI measure, not a rating, and not a prediction. Every score
 * it produces is relative to the sample and period it was computed over.
 *
 *   zᵢ    = dᵢ (Xᵢ − μᵢ) / σᵢ            standardisation, dᵢ ∈ {+1, −1}
 *   P     = (z_NIM + z_ROE) / 2          profitability
 *   C     = z_CET1                       capital
 *   A     = (z_NPL + z_PROV) / 2         asset quality  (both dᵢ = −1)
 *   L     = z_LCR                        liquidity
 *   Z     = 0.25P + 0.25C + 0.25A + 0.25L
 *   BFPI  = 50 + 10Z                     presentation scale
 *
 * Missing data. A pillar is the mean of the indicator z-scores that exist
 * for that bank; a pillar with no available indicator is not computed, and
 * the composite is then formed over the remaining pillars with their
 * weights renormalised. That treatment is stated on every result it touches
 * (`partial`, `treatment`) and never silently applied. Nothing is ever
 * filled with a zero, a sample mean or a neighbouring value.
 */
import {
  INDICATOR_KEYS,
  PILLAR_KEYS,
  type BFPIBand,
  type BFPIResult,
  type BankObservation,
  type Direction,
  type IndicatorKey,
  type IndicatorScore,
  type IndicatorSpec,
  type Observations,
  type PillarKey,
  type PillarScore,
  type PillarSpec,
  type SampleStats,
  type ValidationIssue,
} from './types';

/* ------------------------------------------------------------------ *
 * Specification: what goes in, which way it points, and why.
 * ------------------------------------------------------------------ */

export const INDICATORS: Record<IndicatorKey, IndicatorSpec> = {
  nim: {
    key: 'nim',
    label: 'Net Interest Margin',
    short: 'NIM',
    pillar: 'profitability',
    direction: 1,
    unit: '%',
    min: 0,
    max: 12,
    step: 0.01,
    rationale:
      'Net interest income as a share of average earning assets. It isolates the spread a bank earns on intermediation itself, before fee income and before credit costs — the part of profitability that is most directly a function of how the bank is run rather than of one-off items.',
  },
  roe: {
    key: 'roe',
    label: 'Return on Equity',
    short: 'ROE',
    pillar: 'profitability',
    direction: 1,
    unit: '%',
    min: -30,
    max: 40,
    step: 0.01,
    rationale:
      'Profit after tax over average shareholders’ equity. Pairing ROE with NIM keeps the pillar from rewarding margin alone: a bank can hold a wide spread and still convert it poorly into returns for the capital committed to it.',
  },
  capital: {
    key: 'capital',
    label: 'CET1 Ratio',
    short: 'CET1',
    pillar: 'capital',
    direction: 1,
    unit: '%',
    min: 0,
    max: 40,
    step: 0.01,
    rationale:
      'Common Equity Tier 1 capital over risk-weighted assets — the highest-quality loss-absorbing capital under Basel III, and the ratio a supervisor looks at first. Where a bank discloses only total CAR, the substitution is recorded on the observation rather than hidden.',
  },
  npl: {
    key: 'npl',
    label: 'Gross NPL Ratio',
    short: 'NPL',
    pillar: 'assetQuality',
    direction: -1,
    unit: '%',
    min: 0,
    max: 30,
    step: 0.01,
    rationale:
      'Gross non-performing loans over gross advances: the stock of credit that has already deteriorated. Higher is worse, so the direction coefficient is −1.',
  },
  provisions: {
    key: 'provisions',
    label: 'Credit-Loss Provisions',
    short: 'PROV',
    pillar: 'assetQuality',
    direction: -1,
    unit: '% of advances',
    min: 0,
    max: 10,
    step: 0.01,
    rationale:
      'Provisions charged in the period over average advances — the flow counterpart to the NPL stock. Stock and flow together separate a bank working through a legacy book from one accumulating new problems. Higher is worse, so the direction coefficient is −1.',
  },
  lcr: {
    key: 'lcr',
    label: 'Liquidity Coverage Ratio',
    short: 'LCR',
    pillar: 'liquidity',
    direction: 1,
    unit: '%',
    min: 0,
    max: 400,
    step: 0.1,
    rationale:
      'High-quality liquid assets over projected net cash outflows in a 30-day stress scenario, LCR = HQLA / 30-day net cash outflows. It is the one pillar that asks whether the bank survives a month of stress rather than whether it earns well over a year.',
  },
};

export const PILLARS: Record<PillarKey, PillarSpec> = {
  profitability: {
    key: 'profitability',
    label: 'Profitability',
    weight: 0.25,
    indicators: ['nim', 'roe'],
    rationale: 'Can the bank generate returns from intermediation and from the capital committed to it?',
  },
  capital: {
    key: 'capital',
    label: 'Capital',
    weight: 0.25,
    indicators: ['capital'],
    rationale: 'How much loss can it absorb before depositors or the state are exposed?',
  },
  assetQuality: {
    key: 'assetQuality',
    label: 'Asset Quality',
    weight: 0.25,
    indicators: ['npl', 'provisions'],
    rationale: 'How much of what it has already lent has gone wrong, and at what rate is more going wrong?',
  },
  liquidity: {
    key: 'liquidity',
    label: 'Liquidity',
    weight: 0.25,
    indicators: ['lcr'],
    rationale: 'Can it meet outflows through a month of stress without selling assets into a falling market?',
  },
};

/**
 * Interpretation bands. These describe position within the selected sample
 * and period — nothing more. A bank is never "best", "safest" or "weakest"
 * on this evidence (spec §29).
 */
export const BFPI_BANDS: BFPIBand[] = [
  { min: 80, max: 100.0001, label: 'Very strong relative performance', tone: '#4fae86' },
  { min: 70, max: 80, label: 'Strong relative performance', tone: '#57a889' },
  { min: 60, max: 70, label: 'Above-average performance', tone: '#6ba088' },
  { min: 50, max: 60, label: 'Around-average performance', tone: '#8d9a8d' },
  { min: 40, max: 50, label: 'Below-average performance', tone: '#c08f5e' },
  { min: 30, max: 40, label: 'Weak relative performance', tone: '#cb7d51' },
  { min: 20, max: 30, label: 'Very weak relative performance', tone: '#d3675d' },
  { min: 0, max: 20, label: 'Extremely weak relative performance', tone: '#c2554c' },
];

export function bandFor(bfpi: number | null): BFPIBand | null {
  if (bfpi === null || !Number.isFinite(bfpi)) return null;
  return BFPI_BANDS.find((b) => bfpi >= b.min && bfpi < b.max) ?? BFPI_BANDS[BFPI_BANDS.length - 1];
}

/* ------------------------------------------------------------------ *
 * Standardisation
 * ------------------------------------------------------------------ */

export function mean(values: number[]): number {
  if (values.length === 0) return NaN;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/** Population standard deviation — the sample *is* the reference set. */
export function standardDeviation(values: number[]): number {
  if (values.length === 0) return NaN;
  const mu = mean(values);
  const variance = values.reduce((a, b) => a + (b - mu) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

/**
 * zᵢ = dᵢ (Xᵢ − μᵢ) / σᵢ
 *
 * A zero σ means every bank in the sample reported the same value: there is
 * no relative information to extract, so the z-score is 0 rather than
 * infinite. That is a real property of the sample, not a substituted value.
 */
export function calculateZScore(
  x: number,
  mu: number,
  sigma: number,
  direction: Direction,
): number {
  if (!Number.isFinite(x) || !Number.isFinite(mu) || !Number.isFinite(sigma)) return NaN;
  if (sigma === 0) return 0;
  return direction * ((x - mu) / sigma);
}

/** μ and σ per indicator, over the banks that reported it. */
export function computeSampleStats(sample: BankObservation[]): SampleStats {
  const stats: SampleStats = {};
  for (const key of INDICATOR_KEYS) {
    const values = sample
      .map((o) => o.values[key])
      .filter((v): v is number => v !== null && Number.isFinite(v));
    if (values.length === 0) continue;
    stats[key] = {
      key,
      mean: mean(values),
      sd: standardDeviation(values),
      n: values.length,
      direction: INDICATORS[key].direction,
    };
  }
  return stats;
}

/* ------------------------------------------------------------------ *
 * Pillars
 * ------------------------------------------------------------------ */

function scoreIndicator(key: IndicatorKey, values: Observations, stats: SampleStats): IndicatorScore {
  const spec = INDICATORS[key];
  const raw = values[key];
  const stat = stats[key];

  if (raw === null || !Number.isFinite(raw as number)) {
    return {
      key,
      raw: null,
      mean: stat?.mean ?? null,
      sd: stat?.sd ?? null,
      direction: spec.direction,
      z: null,
      available: false,
      note: 'No value reported for this bank and period. Nothing substituted.',
    };
  }
  if (!stat) {
    return {
      key,
      raw,
      mean: null,
      sd: null,
      direction: spec.direction,
      z: null,
      available: false,
      note: 'No other bank in the sample reported this indicator, so it cannot be standardised.',
    };
  }
  return {
    key,
    raw,
    mean: stat.mean,
    sd: stat.sd,
    direction: spec.direction,
    z: calculateZScore(raw, stat.mean, stat.sd, spec.direction),
    available: true,
    note: stat.sd === 0 ? 'σ = 0 across the sample: no relative variation to measure.' : undefined,
  };
}

function scorePillar(key: PillarKey, values: Observations, stats: SampleStats): PillarScore {
  const spec = PILLARS[key];
  const indicators = spec.indicators.map((k) => scoreIndicator(k, values, stats));
  const usable = indicators.filter((i) => i.available && i.z !== null);
  const z = usable.length ? mean(usable.map((i) => i.z as number)) : null;
  const partial = usable.length > 0 && usable.length < spec.indicators.length;

  return {
    key,
    label: spec.label,
    weight: spec.weight,
    z,
    scaled: z === null ? null : transformTo100Scale(z),
    indicators,
    available: z !== null,
    partial,
    note: partial
      ? `Computed from ${usable.length} of ${spec.indicators.length} indicators: ${usable
          .map((i) => INDICATORS[i.key].short)
          .join(', ')}.`
      : z === null
        ? 'No indicator in this pillar is available for this bank and period.'
        : undefined,
  };
}

export const calculateProfitability = (v: Observations, s: SampleStats) => scorePillar('profitability', v, s);
export const calculateCapital = (v: Observations, s: SampleStats) => scorePillar('capital', v, s);
export const calculateAssetQuality = (v: Observations, s: SampleStats) => scorePillar('assetQuality', v, s);
export const calculateLiquidity = (v: Observations, s: SampleStats) => scorePillar('liquidity', v, s);

/* ------------------------------------------------------------------ *
 * Composite
 * ------------------------------------------------------------------ */

/** BFPI = 50 + 10·Z, clamped to the presentation range. */
export function transformTo100Scale(z: number): number {
  if (!Number.isFinite(z)) return NaN;
  return Math.min(100, Math.max(0, 50 + 10 * z));
}

export interface BFPIOptions {
  /**
   * Minimum number of pillars that must be computable before a composite is
   * reported at all. Below it the result is withheld rather than published
   * on a thin base — a composite built from one pillar is not the same
   * measurement as one built from four, and averaging it into a league
   * table would imply otherwise. Default 1 (report whatever is available);
   * the shipped reference panel sets 3.
   */
  minPillars?: number;
}

export function calculateBFPI(
  observation: BankObservation,
  stats: SampleStats,
  options: BFPIOptions = {},
): BFPIResult {
  const pillars = PILLAR_KEYS.map((k) => scorePillar(k, observation.values, stats));
  const available = pillars.filter((p) => p.available && p.z !== null);
  const missing = INDICATOR_KEYS.filter(
    (k) => observation.values[k] === null || !Number.isFinite(observation.values[k] as number),
  );

  const minPillars = Math.max(1, options.minPillars ?? 1);

  if (available.length === 0) {
    return {
      bankId: observation.bankId,
      periodLabel: observation.periodLabel,
      pillars,
      compositeZ: null,
      bfpi: null,
      partial: true,
      missing,
      treatment:
        'No pillar could be computed for this bank and period. BFPI is not reported. No value has been substituted.',
    };
  }

  if (available.length < minPillars) {
    return {
      bankId: observation.bankId,
      periodLabel: observation.periodLabel,
      pillars,
      compositeZ: null,
      bfpi: null,
      partial: true,
      missing,
      treatment: `Only ${available.length} of the four pillars could be computed (${available
        .map((p) => p.label)
        .join(', ')}), below the minimum of ${minPillars} this sample requires. BFPI is withheld rather than reported on a thin base. The pillars that could be computed are shown individually below.`,
    };
  }

  // Equal weights over the four pillars; renormalised over those available.
  const weightSum = available.reduce((s, p) => s + p.weight, 0);
  const compositeZ = available.reduce((s, p) => s + p.weight * (p.z as number), 0) / weightSum;
  const partial = available.length < PILLAR_KEYS.length || pillars.some((p) => p.partial);

  const notes: string[] = [];
  if (available.length < PILLAR_KEYS.length) {
    const absent = pillars.filter((p) => !p.available).map((p) => p.label);
    notes.push(
      `${absent.join(' and ')} could not be computed; the remaining ${available.length} pillar${
        available.length === 1 ? '' : 's'
      } carry equal weight renormalised to 1.`,
    );
  }
  for (const p of pillars.filter((p) => p.partial)) notes.push(`${p.label}: ${p.note}`);

  return {
    bankId: observation.bankId,
    periodLabel: observation.periodLabel,
    pillars,
    compositeZ,
    bfpi: transformTo100Scale(compositeZ),
    partial,
    missing,
    treatment: notes.length ? notes.join(' ') : null,
  };
}

/** Score every bank in a sample against that same sample's statistics. */
export function calculateSample(
  sample: BankObservation[],
  options: BFPIOptions = {},
): {
  stats: SampleStats;
  results: BFPIResult[];
} {
  const stats = computeSampleStats(sample);
  return { stats, results: sample.map((o) => calculateBFPI(o, stats, options)) };
}

/* ------------------------------------------------------------------ *
 * Validation (spec §51)
 * ------------------------------------------------------------------ */

export function validateObservations(sample: BankObservation[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  for (const obs of sample) {
    for (const key of INDICATOR_KEYS) {
      const v = obs.values[key];
      if (v === null) continue;
      if (!Number.isFinite(v)) {
        issues.push({ bankId: obs.bankId, key, value: NaN, message: `${INDICATORS[key].short} is not a finite number.` });
        continue;
      }
      const spec = INDICATORS[key];
      if (v < spec.min || v > spec.max) {
        issues.push({
          bankId: obs.bankId,
          key,
          value: v,
          message: `${spec.short} = ${v}${spec.unit} is outside the plausible range ${spec.min}–${spec.max}${spec.unit}.`,
        });
      }
    }
  }
  return issues;
}

/** Contribution of one pillar to the composite, in BFPI points. */
export function pillarContribution(pillar: PillarScore, weightSum: number): number | null {
  if (pillar.z === null) return null;
  return (10 * pillar.weight * pillar.z) / weightSum;
}
