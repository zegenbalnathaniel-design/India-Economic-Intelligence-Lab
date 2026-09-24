import type { AuditEntry } from './types';
import { RETRIEVED_ON } from './sources';

/**
 * Data audit log (spec §55). One row per dataset shipped in this build:
 * where it came from, what was done to it, what was checked and what its
 * overall status is. Surfaced on the Data page rather than kept internal.
 */
export const AUDIT_LOG: AuditEntry[] = [
  {
    dataset: 'Macro indicators (Economic Pulse)',
    sourceId: 'mospi / rbi / minfin / amfi',
    version: 'Build 2026-09-24',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation: 'None. Values are carried at the unit and reporting period of the publishing release.',
    validation:
      'Reporting periods preserved verbatim; vintages recorded where a statistic has been revised; one unresolved source conflict flagged on CPI.',
    status: 'mixed',
    notes: '12 indicators. 9 verified against a primary release, 3 reported from an industry body.',
  },
  {
    dataset: 'BFPI reference panel — FY2025',
    sourceId: 'issuer disclosures (7 banks)',
    version: 'FY2025 (year ended 31 March 2025)',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation:
      'None applied to values. Consolidation basis recorded per cell. Missing cells left null and excluded from sample statistics.',
    validation:
      'Range checks on all six indicators; period alignment confirmed at 31 March 2025 for every bank; basis mismatches documented per cell; two banks withheld for insufficient pillar coverage.',
    status: 'reported',
    notes: '7 banks × 6 indicators = 42 cells. 26 populated, 16 unavailable. Credit-loss provisions absent for all 7 uniformly.',
  },
  {
    dataset: 'Figure 2 allocation',
    sourceId: 'rbi',
    version: 'Household Finance Committee, July 2017',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation: 'Other-physical share derived as the residual of the three reported shares.',
    validation:
      'Weights sum to exactly 1. Cross-checked independently against AIDIS 2019 financial-asset shares (4.6% rural, 9.3% urban).',
    status: 'verified',
  },
  {
    dataset: 'Figure 2 return assumptions',
    sourceId: 'rbi / nse',
    version: 'Build 2026-09-24',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation:
      'Each assumed return set at or below its cited historical anchor. No return is an observation.',
    validation: 'Every assumption carries its anchor, the anchor’s source and the reason for the gap between them.',
    status: 'assumption',
  },
  {
    dataset: 'State economics',
    sourceId: 'rbi / censusindia',
    version: 'RBI Handbook 2024-25; Census of India 2011',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation: 'None. GSDP levels withheld pending resolution of a source conflict.',
    validation:
      'Per-capita NSDP internally consistent across the eight states shown. GSDP levels differ by roughly 2× between sources and are therefore not displayed.',
    status: 'mixed',
    notes: '8 states. Urbanisation is Census 2011 and is labelled at that period rather than projected forward.',
  },
  {
    dataset: 'Economic timeline',
    sourceId: 'rbi / mospi / gstcouncil',
    version: 'Build 2026-09-24',
    retrieved: RETRIEVED_ON,
    updated: RETRIEVED_ON,
    transformation: 'None. Institutional facts and dates are a matter of record; quantitative claims carry their own status.',
    validation:
      'No growth impact attributed to demonetisation, because credible estimates disagree — the cell is marked unavailable rather than filled.',
    status: 'mixed',
  },
];
