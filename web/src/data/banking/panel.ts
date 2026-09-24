import type { BankObservation, IndicatorKey, Observations } from '../../models/bfpi/types';
import { RETRIEVED_ON } from '../sources';
import type { DataStatus } from '../types';

/**
 * BFPI reference panel — FY2025 (year ended 31 March 2025).
 *
 * Every field carries its own status, source and basis. Nothing is filled
 * in: where a bank's disclosure for an indicator was not obtainable, the
 * value is null and the model treats it as missing rather than as zero.
 *
 * Basis. Banks disclose these ratios on different consolidation bases —
 * whole bank, standalone, consolidated, group. Mixing them is a real
 * limitation of any cross-bank composite and it is recorded per field
 * rather than glossed over (spec §56).
 */

export interface Bank {
  id: string;
  name: string;
  shortName: string;
  ownership: 'public' | 'private';
  sourceId: string;
  /** The bank's own disclosure page — the authority for these figures. */
  disclosureUrl: string;
  note?: string;
}

export const BANKS: Bank[] = [
  {
    id: 'sbi',
    name: 'State Bank of India',
    shortName: 'SBI',
    ownership: 'public',
    sourceId: 'sbi',
    disclosureUrl: 'https://sbi.bank.in/web/corporate-governance/corporate-governance',
  },
  {
    id: 'hdfcbank',
    name: 'HDFC Bank',
    shortName: 'HDFC',
    ownership: 'private',
    sourceId: 'hdfcbank',
    disclosureUrl: 'https://www.hdfc.bank.in/about-us/investor-relations',
    note: 'FY2025 is the second full year after the merger with HDFC Ltd, which lowered the reported margin by adding a large book of mortgage assets.',
  },
  {
    id: 'icicibank',
    name: 'ICICI Bank',
    shortName: 'ICICI',
    ownership: 'private',
    sourceId: 'icicibank',
    disclosureUrl: 'https://www.icici.bank.in/about-us/qfr',
  },
  {
    id: 'axisbank',
    name: 'Axis Bank',
    shortName: 'AXIS',
    ownership: 'private',
    sourceId: 'axisbank',
    disclosureUrl: 'https://www.axis.bank.in/quarterly-results/2024-2025/q4/index.html',
  },
  {
    id: 'kotak',
    name: 'Kotak Mahindra Bank',
    shortName: 'KOTAK',
    ownership: 'private',
    sourceId: 'kotak',
    disclosureUrl: 'https://www.kotak.bank.in/en/investor-relations.html',
    note: 'FY2025 profit and ROE include a one-off gain on the divestment of Kotak General Insurance. Excluding it, ROE was 13.12%.',
  },
  {
    id: 'bob',
    name: 'Bank of Baroda',
    shortName: 'BOB',
    ownership: 'public',
    sourceId: 'bob',
    disclosureUrl: 'https://bankofbaroda.bank.in/shareholders-corner/financial-reports',
  },
  {
    id: 'pnb',
    name: 'Punjab National Bank',
    shortName: 'PNB',
    ownership: 'public',
    sourceId: 'pnb',
    disclosureUrl: 'https://pnb.bank.in/financials-current.html',
  },
];

export const BANK_BY_ID = Object.fromEntries(BANKS.map((b) => [b.id, b]));

/** Provenance for one bank-indicator-period cell. */
export interface FieldProvenance {
  value: number | null;
  status: DataStatus;
  /** Consolidation basis as disclosed. */
  basis: string;
  sourceUrl: string;
  note?: string;
}

export type BankFields = Record<IndicatorKey, FieldProvenance>;

export interface BankPanelRow {
  bankId: string;
  periodLabel: string;
  periodEndsOn: string;
  fields: BankFields;
}

const gap = (why: string): FieldProvenance => ({
  value: null,
  status: 'unavailable',
  basis: '—',
  sourceUrl: '',
  note: why,
});

const PROVISIONS_GAP =
  'Credit-loss provisions as a share of average advances were not obtainable for any bank in this sample. The indicator is therefore absent for every bank uniformly, so no bank is advantaged or penalised by its absence — see the treatment note on the methodology page.';

export const FY2025_PANEL: BankPanelRow[] = [
  {
    bankId: 'sbi',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: {
        value: 3.09,
        status: 'reported',
        basis: 'Whole bank, full year',
        sourceUrl: 'https://sbi.bank.in/web/corporate-governance/corporate-governance',
        note: 'Domestic NIM was 3.22%; the whole-bank figure is used for comparability.',
      },
      roe: { value: 19.87, status: 'reported', basis: 'Full year', sourceUrl: 'https://sbi.bank.in/corporate/SBIAR2425/chairmans-message.html' },
      capital: {
        value: 10.81,
        status: 'reported',
        basis: 'CET1, as at 31 March 2025',
        sourceUrl: 'https://sbi.bank.in/corporate/SBIAR2425/chairmans-message.html',
        note: 'Total CAR 14.25% (CET1 10.81% + AT1 1.30% + Tier 2 2.14%).',
      },
      npl: { value: 1.82, status: 'reported', basis: 'Gross NPA, as at 31 March 2025', sourceUrl: 'https://sbi.bank.in/web/corporate-governance/corporate-governance' },
      provisions: gap(PROVISIONS_GAP),
      lcr: {
        value: 132.83,
        status: 'reported',
        basis: 'Consolidated group, average of Jan–Mar 2025',
        sourceUrl:
          'https://sbi.bank.in/documents/17826/33694/03052025_Group+LCR+WEB+DISCLOSURE.pdf/04d1af8d-fec0-0919-eee4-bd3247f6550d',
        note: 'Group basis. The whole-bank (solo) disclosure exists separately and was not obtainable here — a basis mismatch against the bank-level figures used for Axis.',
      },
    },
  },
  {
    bankId: 'hdfcbank',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: {
        value: 3.5,
        status: 'reported',
        basis: 'Full year, on interest-earning assets',
        sourceUrl:
          'https://www.hdfcbank.com/content/bbp/repositories/723fb80a-2dde-42a3-9793-7ae1be57c87f/?path=/Footer/About+Us/About+Investor+Relations/pdf/2024/march/Q4FY25-Earnings-Presentation.pdf',
        note: 'Held in a 3.4–3.5% band through the year; Q4 3.44% reported, 3.46% on a core basis.',
      },
      roe: {
        value: 14.4,
        status: 'reported',
        basis: 'Q4 FY2025 annualised',
        sourceUrl:
          'https://www.hdfcbank.com/content/bbp/repositories/723fb80a-2dde-42a3-9793-7ae1be57c87f/?path=/Footer/About+Us/About+Investor+Relations/pdf/2024/march/Q4FY25-Earnings-Presentation.pdf',
        note: 'Quarterly rather than full-year basis — a mismatch against the full-year ROE used for the other banks.',
      },
      capital: {
        value: 17.2,
        status: 'reported',
        basis: 'CET1, as at 31 March 2025',
        sourceUrl:
          'https://www.hdfcbank.com/content/bbp/repositories/723fb80a-2dde-42a3-9793-7ae1be57c87f/?path=/Footer/About+Us/About+Investor+Relations/pdf/2024/march/Q4FY25-Earnings-Presentation.pdf',
        note: 'Total CAR 19.6%.',
      },
      npl: {
        value: 1.33,
        status: 'reported',
        basis: 'Gross NPA, as at 31 March 2025',
        sourceUrl:
          'https://www.hdfcbank.com/content/bbp/repositories/723fb80a-2dde-42a3-9793-7ae1be57c87f/?path=/Footer/About+Us/About+Investor+Relations/pdf/2024/march/Q4FY25-Earnings-Presentation.pdf',
      },
      provisions: gap(PROVISIONS_GAP),
      lcr: {
        value: 119.04,
        status: 'reported',
        basis: 'Consolidated, average for the quarter ended 31 March 2025',
        sourceUrl:
          'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/regulatory-disclosures/2025/liquidity-coverage-ratio-disclosure-as-at-june-30-2025.pdf',
      },
    },
  },
  {
    bankId: 'icicibank',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: { value: 4.4, status: 'reported', basis: 'Full year', sourceUrl: 'https://www.icici.bank.in/ms/aboutus/annual-reports/2024-25/html/the-bank-at-a-glance.html' },
      roe: { value: 18.0, status: 'reported', basis: 'Full year', sourceUrl: 'https://www.icici.bank.in/ms/aboutus/annual-reports/2024-25/html/the-bank-at-a-glance.html' },
      capital: {
        value: 16.5,
        status: 'reported',
        basis: 'CET1, as at 31 March 2025',
        sourceUrl: 'https://www.icici.bank.in/ms/aboutus/annual-reports/2024-25/html/the-bank-at-a-glance.html',
      },
      npl: {
        value: 1.67,
        status: 'reported',
        basis: 'Gross NPA, as at 31 March 2025',
        sourceUrl: 'https://www.icici.bank.in/about-us/news-room/2025/performance-review-quarter-ended-march-31-2025',
        note: 'Net NPA 0.42%; provision coverage 91%.',
      },
      provisions: gap(PROVISIONS_GAP),
      lcr: {
        value: 125.1,
        status: 'reported',
        basis: 'Group, three months ended 31 March 2025',
        sourceUrl: 'https://www.icici.bank.in/content/dam/icicibank/missing-assets/consolidated-lcr-disclosure-mar-25.pdf',
        note: 'Group basis — a mismatch against bank-level figures elsewhere in the sample.',
      },
    },
  },
  {
    bankId: 'axisbank',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: { value: 3.98, status: 'reported', basis: 'Full year', sourceUrl: 'https://www.axis.bank.in/docs/default-source/press-releases/press-release-q4fy25.pdf' },
      roe: {
        value: 16.52,
        status: 'reported',
        basis: 'Standalone bank, full year',
        sourceUrl: 'https://www.axis.bank.in/docs/default-source/press-releases/press-release-q4fy25.pdf',
        note: 'Consolidated ROE was 16.89%; the standalone figure is used to match the standalone capital and asset-quality ratios.',
      },
      capital: {
        value: 14.67,
        status: 'reported',
        basis: 'CET1, as at 31 March 2025',
        sourceUrl: 'https://www.axis.bank.in/docs/default-source/press-releases/press-release-q4fy25.pdf',
        note: 'Total CAR 17.07%.',
      },
      npl: { value: 1.28, status: 'reported', basis: 'Gross NPA, as at 31 March 2025', sourceUrl: 'https://www.axis.bank.in/docs/default-source/press-releases/press-release-q4fy25.pdf', note: 'Net NPA 0.33%.' },
      provisions: gap(PROVISIONS_GAP),
      lcr: {
        value: 118,
        status: 'reported',
        basis: 'Bank level, average for Q4 FY2025',
        sourceUrl: 'https://www.axis.bank.in/docs/default-source/press-releases/press-release-q4fy25.pdf',
        note: 'Disclosed as approximately 118% for the quarter; carries more rounding than the other LCR figures here.',
      },
    },
  },
  {
    bankId: 'kotak',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: { value: 4.96, status: 'reported', basis: 'Full year', sourceUrl: 'https://www.kotak.bank.in/content/dam/Kotak/others/FY-2025/q4/PressRelease/Q4FY25-Press-Release.pdf' },
      roe: {
        value: 15.19,
        status: 'reported',
        basis: 'Full year, including the gain on divestment of Kotak General Insurance',
        sourceUrl: 'https://www.kotak.bank.in/content/dam/Kotak/others/FY-2025/q4/PressRelease/Q4FY25-Press-Release.pdf',
        note: 'Excluding the one-off gain, ROE was 13.12%. The stress-test panel lets you substitute that figure and watch the composite move.',
      },
      capital: {
        value: 21.1,
        status: 'reported',
        basis: 'CET1, standalone, as at 31 March 2025',
        sourceUrl: 'https://www.kotak.bank.in/content/dam/Kotak/others/FY-2025/q4/PressRelease/Q4FY25-Press-Release.pdf',
        note: 'Standalone CAR 22.2%.',
      },
      npl: { value: 1.42, status: 'reported', basis: 'Gross NPA, as at 31 March 2025', sourceUrl: 'https://www.kotak.bank.in/content/dam/Kotak/others/FY-2025/q4/PressRelease/Q4FY25-Press-Release.pdf', note: 'Net NPA 0.31%; provision coverage 78%.' },
      provisions: gap(PROVISIONS_GAP),
      lcr: {
        value: 135.46,
        status: 'reported',
        basis: 'Consolidated, daily average for the quarter ended 31 March 2025',
        sourceUrl:
          'https://www.kotak.bank.in/content/dam/Kotak/investor-relation/Financial-Result/Regulatory-Disclosure/FY-2025/Liquidity-Coverage-Ratio-for-period-ending-31st-march-2025.pdf',
      },
    },
  },
  {
    bankId: 'bob',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: {
        value: 3.0,
        status: 'reported',
        basis: 'Full year',
        sourceUrl: 'https://bankofbaroda.bank.in/shareholders-corner/financial-reports',
        note: 'Down from 3.2% in FY2024.',
      },
      roe: gap('Full-year FY2025 ROE was not obtainable from the bank’s own disclosure in this build. Analyst estimates exist but are not a primary source and have not been substituted.'),
      capital: gap(
        'CET1 as at 31 March 2025 was not obtainable. Total CAR was 17.2%, but CAR and CET1 are different ratios and one has not been used in place of the other.',
      ),
      npl: gap('Gross NPA as at 31 March 2025 was not obtainable from the bank’s own disclosure in this build.'),
      provisions: gap(PROVISIONS_GAP),
      lcr: gap('The daily-average LCR disclosure for the quarter ended 31 March 2025 was not obtainable in this build.'),
    },
  },
  {
    bankId: 'pnb',
    periodLabel: 'FY2025',
    periodEndsOn: '2025-03-31',
    fields: {
      nim: { value: 2.81, status: 'reported', basis: 'Full year', sourceUrl: 'https://pnb.bank.in/financials-current.html' },
      roe: gap(
        'A full-year FY2025 ROE was not obtainable. A Q4 FY2025 figure of 19.23% was disclosed, but a single quarter is not comparable with the full-year ROE used for the rest of the sample, so it has not been substituted.',
      ),
      capital: gap('CET1 as at 31 March 2025 was not obtainable from the bank’s own disclosure in this build.'),
      npl: {
        value: 3.95,
        status: 'reported',
        basis: 'Gross NPA, as at 31 March 2025',
        sourceUrl: 'https://pnb.bank.in/financials-current.html',
        note: 'Improved by 178 basis points year on year from 5.73%.',
      },
      provisions: gap(PROVISIONS_GAP),
      lcr: { value: 141.67, status: 'reported', basis: 'As disclosed for FY2025', sourceUrl: 'https://pnb.bank.in/financials-current.html' },
    },
  },
];

export const PANEL_PERIODS = ['FY2025'];

export const fieldsToObservations = (fields: BankFields): Observations =>
  ({
    nim: fields.nim.value,
    roe: fields.roe.value,
    capital: fields.capital.value,
    npl: fields.npl.value,
    provisions: fields.provisions.value,
    lcr: fields.lcr.value,
  }) satisfies Observations;

export const toObservation = (row: BankPanelRow): BankObservation => ({
  bankId: row.bankId,
  periodLabel: row.periodLabel,
  values: fieldsToObservations(row.fields),
});

export const rowFor = (bankId: string, period = 'FY2025'): BankPanelRow | undefined =>
  FY2025_PANEL.find((r) => r.bankId === bankId && r.periodLabel === period);

/**
 * What a reader needs to know before quoting any BFPI score from the
 * shipped panel. Surfaced on the BFPI page, the methodology page and every
 * provenance panel that touches banking data.
 */
export const PANEL_CAVEATS: string[] = [
  'FY2025 means the year ended 31 March 2025 for every bank in this sample. No period has been shifted to align.',
  'Ratios are disclosed on different consolidation bases — whole bank, standalone, consolidated and group all appear here. The basis is recorded on each cell and is a genuine limitation of any cross-bank composite.',
  'HDFC Bank’s ROE is a Q4 annualised figure rather than a full-year one, because the full-year figure was not obtainable. It is not comparable on the same footing as the rest.',
  'Credit-loss provisions are absent for every bank, so Asset Quality is computed from the NPL ratio alone throughout. The absence is uniform, so it does not tilt the ranking, but it does narrow what the pillar measures.',
  'Bank of Baroda and Punjab National Bank have too few indicators for a defensible composite. Their scores are withheld rather than computed on a thin base.',
  'Figures were transcribed from each bank’s published results; this build could not open the filings directly. Verify against the linked disclosure before citing.',
];

export const PANEL_RETRIEVED = RETRIEVED_ON;
