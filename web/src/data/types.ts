/**
 * IEIL data contract.
 *
 * Every factual number rendered anywhere in the lab travels inside one of
 * these records. Nothing reaches a chart, a metric tile or a model without
 * a source, a reporting period and a status. This is what makes the
 * "Data Provenance" panel and the VERIFIED / CALCULATED / ASSUMPTION /
 * SCENARIO badges possible rather than decorative.
 */

/** Where a number came from and how much weight it can carry. */
export type DataStatus =
  /** Taken directly from an authoritative primary source. */
  | 'verified'
  /** Transcribed from a public disclosure this build could not fetch
   *  directly (the environment blocks outbound access to source hosts).
   *  The record carries the filing URL so a reader can verify it. */
  | 'reported'
  /** Derived arithmetically from other records in this dataset. */
  | 'calculated'
  /** An explicit modelling assumption. Not an observation. */
  | 'assumption'
  /** Produced by the reader moving a control. Hypothetical. */
  | 'scenario'
  /** Known to exist but not obtainable here. Never substituted. */
  | 'unavailable';

export interface StatusStyle {
  label: string;
  short: string;
  fg: string;
  bg: string;
  border: string;
  description: string;
}

export const STATUS_STYLE: Record<DataStatus, StatusStyle> = {
  verified: {
    label: 'VERIFIED',
    short: 'V',
    fg: '#4fae86',
    bg: 'rgba(79,174,134,0.10)',
    border: 'rgba(79,174,134,0.35)',
    description: 'Obtained directly from an authoritative primary source.',
  },
  reported: {
    label: 'REPORTED',
    short: 'R',
    fg: '#5b9bd5',
    bg: 'rgba(91,155,213,0.10)',
    border: 'rgba(91,155,213,0.35)',
    description:
      'Transcribed from a public disclosure by the issuer. This build could not fetch the filing directly — the linked source is the authority.',
  },
  calculated: {
    label: 'CALCULATED',
    short: 'C',
    fg: '#4aa5a8',
    bg: 'rgba(74,165,168,0.10)',
    border: 'rgba(74,165,168,0.35)',
    description: 'Derived mathematically from verified inputs. The derivation is shown.',
  },
  assumption: {
    label: 'ASSUMPTION',
    short: 'A',
    fg: '#e8933a',
    bg: 'rgba(232,147,58,0.10)',
    border: 'rgba(232,147,58,0.35)',
    description: 'An explicit modelling assumption, not an observation.',
  },
  scenario: {
    label: 'USER SCENARIO',
    short: 'S',
    fg: '#8b7fd4',
    bg: 'rgba(139,127,212,0.10)',
    border: 'rgba(139,127,212,0.35)',
    description: 'A hypothetical produced by the reader. Conditional on the inputs entered.',
  },
  unavailable: {
    label: 'UNAVAILABLE',
    short: '—',
    fg: '#818e96',
    bg: 'rgba(129,142,150,0.08)',
    border: 'rgba(129,142,150,0.28)',
    description: 'No value available for this period. Nothing has been substituted.',
  },
};

/** A citable publisher. */
export interface Source {
  id: string;
  name: string;
  fullName: string;
  /** Landing page or the specific document. */
  url: string;
  tier: 'india-official' | 'international' | 'financial' | 'academic' | 'issuer';
}

/** Reporting-period kinds are preserved — FY2025-26 is never flattened to 2026. */
export type PeriodKind = 'financial-year' | 'calendar-year' | 'quarter' | 'month' | 'date' | 'range';

export interface Period {
  kind: PeriodKind;
  /** Exactly as the publisher labels it, e.g. "FY2025-26", "Q1:2026-27". */
  label: string;
  /** ISO date of the period end, for ordering only. Never displayed as the period. */
  endsOn: string;
}

/** Successive official vintages of the same statistic (spec §49). */
export interface Vintage {
  label: string;
  value: number;
  releasedOn: string;
  note?: string;
}

export interface DataPoint {
  id: string;
  indicator: string;
  /** null means genuinely unavailable — never zero, never carried forward. */
  value: number | null;
  unit: string;
  /** Short unit for dense tiles, e.g. "%". */
  unitShort?: string;
  /**
   * Decimal places to display. Set per indicator rather than inferred: a
   * repo rate of 5.50% is quoted to two places by the RBI, while a demat
   * account count of 23 crore is not a measurement to two places at all.
   */
  decimals?: number;
  country?: string;
  period: Period;
  sourceId: string;
  /** Deep link to the exact document where possible. */
  sourceUrl: string;
  /** Dataset / release name within the source. */
  dataset?: string;
  publicationDate?: string;
  accessedDate: string;
  methodology?: string;
  status: DataStatus;
  /** Processing applied between the source and this value. */
  processing?: string;
  note?: string;
  /** Change vs the comparable prior period, in the unit's own terms. */
  change?: { value: number; label: string; better?: 'up' | 'down' | 'neutral' };
  vintages?: Vintage[];
  /** Populated when authoritative sources disagree (spec §50). */
  discrepancy?: Discrepancy;
  series?: SeriesPoint[];
  /** Longer analytical reading shown in the expanded panel. */
  analysis?: string;
}

export interface SeriesPoint {
  periodLabel: string;
  endsOn: string;
  value: number | null;
  status?: DataStatus;
  note?: string;
}

export interface Discrepancy {
  summary: string;
  entries: { sourceId: string; label: string; value: number; period: string; url: string }[];
  explanation: string;
}

/** One line of the internal data audit log (spec §55). */
export interface AuditEntry {
  dataset: string;
  sourceId: string;
  version: string;
  retrieved: string;
  updated: string;
  transformation: string;
  validation: string;
  status: DataStatus | 'mixed';
  notes?: string;
}

export const isPresent = (d: Pick<DataPoint, 'value'>): d is DataPoint & { value: number } =>
  d.value !== null && Number.isFinite(d.value);
