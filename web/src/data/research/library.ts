export type EntryStatus = 'published' | 'methodology' | 'in-preparation';

export interface LibraryEntry {
  id: string;
  title: string;
  summary: string;
  category: string;
  tags: string[];
  status: EntryStatus;
  to?: string;
  date?: string;
  readingMinutes?: number;
  note?: string;
}

export const RESEARCH_CATEGORIES = [
  'Wealth',
  'Inequality',
  'Banking',
  'Monetary policy',
  'Fiscal policy',
  'Growth',
  'Development',
  'Labour',
  'International economics',
];

/**
 * The library lists what exists. Entries still being written are marked
 * "In preparation" and have no link — a research programme stated honestly
 * rather than a catalogue padded with placeholders.
 */
export const LIBRARY: LibraryEntry[] = [
  {
    id: 'great-indian-promise',
    title: 'The Great Indian Promise',
    summary:
      'Income can rise without wealth accumulating at the same pace. Using the household portfolio measured by the RBI’s Household Finance Committee, this paper argues the gap is a composition gap rather than a saving gap, and makes the arithmetic testable.',
    category: 'Wealth',
    tags: ['wealth', 'household finance', 'ownership', 'savings'],
    status: 'published',
    to: '/research/the-great-indian-promise',
    date: '2026-09-24',
    readingMinutes: 18,
  },
  {
    id: 'bfpi-methodology',
    title: 'BFPI — construction of a bank performance composite',
    summary:
      'Why these six indicators, why equal weights, why z-scores, and why a 0–100 presentation scale. The full methodology behind the Bank Financial Performance Index, including its treatment of missing data and the limits of what a composite can support.',
    category: 'Banking',
    tags: ['banking', 'index construction', 'method'],
    status: 'methodology',
    to: '/models/bfpi/methodology',
    date: '2026-09-24',
    readingMinutes: 12,
  },
  {
    id: 'composition-distribution',
    title: 'Portfolio composition across the wealth distribution',
    summary:
      'The composition effect in The Great Indian Promise describes a representative household. Composition in fact varies sharply across the distribution, which implies the effect widens wealth inequality rather than narrowing it. Quantifying that requires household-level ownership data.',
    category: 'Inequality',
    tags: ['inequality', 'wealth', 'distribution'],
    status: 'in-preparation',
    note: 'Requires AIDIS unit-level microdata. Not started.',
  },
  {
    id: 'transmission-deposit',
    title: 'Policy transmission through deposit pricing',
    summary:
      'How much of a repo-rate change reaches household deposit rates, how quickly, and whether the shift to external-benchmark-linked lending has changed the asymmetry between lending and deposit repricing.',
    category: 'Monetary policy',
    tags: ['monetary policy', 'banking', 'transmission'],
    status: 'in-preparation',
    note: 'Requires the RBI weighted-average deposit-rate series. Not started.',
  },
  {
    id: 'bfpi-timeseries',
    title: 'BFPI through a rate cycle',
    summary:
      'Extending the BFPI panel to a multi-year series to ask whether bank performance co-moves with the policy rate, and how much of any co-movement survives controlling for the credit cycle.',
    category: 'Banking',
    tags: ['banking', 'monetary policy', 'index construction'],
    status: 'in-preparation',
    note: 'Requires a full multi-year panel of bank disclosures. The current build covers FY2025 only.',
  },
  {
    id: 'services-external',
    title: 'Services exports and the merchandise deficit',
    summary:
      'India finances a goods trade deficit of roughly US$86 billion a quarter with services exports and remittances. What that structure implies for exchange-rate sensitivity and for external vulnerability.',
    category: 'International economics',
    tags: ['external', 'trade', 'services'],
    status: 'in-preparation',
    note: 'Requires the RBI balance-of-payments back series. Not started.',
  },
];

export const LIBRARY_BY_STATUS = (status: EntryStatus) => LIBRARY.filter((e) => e.status === status);
