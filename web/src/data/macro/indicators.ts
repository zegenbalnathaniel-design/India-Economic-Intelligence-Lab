import { RETRIEVED_ON } from '../sources';
import type { DataPoint } from '../types';

const A = RETRIEVED_ON;

/**
 * Economic Pulse — the macro cross-section.
 *
 * Reporting periods are preserved exactly as the publisher labels them.
 * FY2025-26 is never written as 2026; Q1:2026-27 is never written as
 * "this quarter". Where successive official vintages of the same statistic
 * exist, all of them are carried on the record (spec §48, §49).
 */
export const MACRO_INDICATORS: DataPoint[] = [
  {
    id: 'gdp-growth',
    indicator: 'Real GDP Growth',
    value: 7.7,
    unit: '% year on year',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'financial-year', label: 'FY2025-26', endsOn: '2026-03-31' },
    sourceId: 'mospi',
    sourceUrl: 'https://www.mospi.gov.in/',
    dataset: 'National Accounts Statistics — Provisional Estimates',
    publicationDate: '2026-05-29',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Gross Domestic Product at constant (2011-12) prices, measured as the percentage change over the preceding financial year. Compiled by the National Statistical Office from the production and expenditure sides and reconciled.',
    change: { value: 1.2, label: 'vs FY2024-25 (6.5%)', better: 'up' },
    vintages: [
      {
        label: 'First Advance Estimate',
        value: 7.4,
        releasedOn: '2026-01-07',
        note: 'Released alongside nominal GDP growth of 8.0% for the same year.',
      },
      { label: 'Revised Estimate', value: 7.6, releasedOn: '2026-02-27' },
      { label: 'Provisional Estimate', value: 7.7, releasedOn: '2026-05-29', note: 'Latest official vintage. Q4 growth 7.8%.' },
    ],
    // Back series on the latest available vintage of each year. Earlier
    // years are marked `reported` rather than `verified`: they have been
    // revised more than once since first release and this build could not
    // open the National Accounts back series to confirm the current vintage.
    series: [
      { periodLabel: 'FY2019-20', endsOn: '2020-03-31', value: 3.9, status: 'reported' },
      { periodLabel: 'FY2020-21', endsOn: '2021-03-31', value: -5.8, status: 'reported', note: 'Covid-19 contraction.' },
      { periodLabel: 'FY2021-22', endsOn: '2022-03-31', value: 9.7, status: 'reported' },
      { periodLabel: 'FY2022-23', endsOn: '2023-03-31', value: 7.6, status: 'reported' },
      { periodLabel: 'FY2023-24', endsOn: '2024-03-31', value: 9.2, status: 'reported' },
      { periodLabel: 'FY2024-25', endsOn: '2025-03-31', value: 6.5, status: 'verified' },
      { periodLabel: 'FY2025-26', endsOn: '2026-03-31', value: 7.7, status: 'verified', note: 'Provisional Estimate.' },
    ],
    analysis:
      'Three vintages of the same year sit on this record because the number moved: 7.4% at the First Advance Estimate in January, 7.6% at the Revised Estimate, 7.7% provisionally at the end of May. The revisions are not noise — advance estimates extrapolate from partial-year indicators, and the gap between them and the provisional figure is a reasonable measure of how much of a growth print is genuinely known when it is first published. Quoting the January number today would be quoting a superseded vintage.',
  },
  {
    id: 'cpi-inflation',
    indicator: 'CPI Inflation',
    value: 4.45,
    unit: '% year on year',
    unitShort: '%',
    decimals: 2,
    country: 'India',
    period: { kind: 'month', label: 'July 2026', endsOn: '2026-07-31' },
    sourceId: 'pib',
    sourceUrl: 'https://www.mospi.gov.in/cpi',
    dataset: 'All India Consumer Price Index (Base 2024=100)',
    publicationDate: '2026-08-12',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Year-on-year change in the All India Consumer Price Index (Combined), base 2024=100, as published provisionally by the NSO. The index was rebased from 2012=100 during 2026, so readings on the two bases are not directly comparable.',
    note: 'Provisional. Within the RBI’s 4% ± 2 percentage-point tolerance band.',
    series: [
      { periodLabel: 'May 2026', endsOn: '2026-05-31', value: 3.93, note: 'Provisional.' },
      { periodLabel: 'July 2026', endsOn: '2026-07-31', value: 4.45, note: 'Provisional.' },
      { periodLabel: 'August 2026', endsOn: '2026-08-31', value: null, status: 'unavailable', note: 'Release exists; not verified in this build. See the discrepancy note.' },
    ],
    discrepancy: {
      summary: 'The August 2026 print could not be verified against its primary release.',
      entries: [
        {
          sourceId: 'pib',
          label: 'MoSPI / PIB — CPI release for August 2026',
          value: NaN,
          period: 'August 2026',
          url: 'https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2310058&reg=48&lang=1',
        },
        {
          sourceId: 'worldbank',
          label: 'Secondary aggregators (unverified)',
          value: 4.82,
          period: 'August 2026',
          url: 'https://www.mospi.gov.in/cpi',
        },
      ],
      explanation:
        'The PIB release for August 2026 exists and is linked above, but this build cannot open pib.gov.in, so its headline figure was not read directly. Secondary aggregators report roughly 4.8% for the month. Rather than print an unverified number as the current reading, the pulse shows the last figure traced to a primary release — July 2026 at 4.45% — and flags the gap here. Open the PIB release to resolve it.',
    },
    analysis:
      'Headline CPI has run inside the tolerance band through 2026, drifting up from under 4% in the spring as energy prices firmed. The rebasing to 2024=100 matters more than it looks: a rebased index changes the weight of food and fuel in the basket, so a like-for-like comparison with pre-2026 prints is not available from the headline rate alone.',
  },
  {
    id: 'repo-rate',
    indicator: 'Policy Repo Rate',
    value: 5.5,
    unit: '% per annum',
    unitShort: '%',
    decimals: 2,
    country: 'India',
    period: { kind: 'date', label: 'As of 24 September 2026', endsOn: '2026-09-24' },
    sourceId: 'rbi',
    sourceUrl: 'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx',
    dataset: 'Monetary Policy Committee resolutions',
    publicationDate: '2026-08-05',
    accessedDate: A,
    status: 'verified',
    methodology:
      'The rate at which the RBI lends overnight to banks against government securities under the Liquidity Adjustment Facility. Set by the six-member Monetary Policy Committee, which meets roughly every two months.',
    note: 'Unchanged at the August 2026 MPC. Stance: neutral. SDF 5.25%, MSF and Bank Rate 5.75%.',
    change: { value: 0, label: 'at the August 2026 MPC', better: 'neutral' },
    analysis:
      'The corridor matters as much as the headline. With the standing deposit facility at 5.25% and the marginal standing facility at 5.75%, the operating band is 50 basis points wide and the repo sits at its centre. A neutral stance means the committee has not committed to a direction — it is not the same as a pause, which would be a statement about the next meeting.',
  },
  {
    id: 'unemployment',
    indicator: 'Unemployment Rate',
    value: 3.2,
    unit: '% of labour force, 15 years and above',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'financial-year', label: 'PLFS 2024-25', endsOn: '2025-06-30' },
    sourceId: 'mospi',
    sourceUrl: 'https://www.mospi.gov.in/',
    dataset: 'Periodic Labour Force Survey — Annual Report',
    publicationDate: '2025-09-01',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Usual Status (principal + subsidiary) unemployment rate for persons aged 15 and above: the share of the labour force without work and seeking it, measured over a 365-day reference period. Current Weekly Status yields a different and generally higher rate — the two are not interchangeable.',
    note: 'Rural 2.5%, urban 5.1%. Unchanged from PLFS 2023-24.',
    analysis:
      'A 3.2% unemployment rate in a country with India’s income level is not the reassuring number it looks like in a high-income context. Usual Status counts anyone with subsidiary economic activity over the year as employed, so it captures very little underemployment, and the labour force participation rate — not the unemployment rate — is where the informative variation sits.',
  },
  {
    id: 'fiscal-deficit',
    indicator: 'Fiscal Deficit',
    value: 4.3,
    unit: '% of GDP',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'financial-year', label: 'FY2026-27 (Budget Estimate)', endsOn: '2027-03-31' },
    sourceId: 'minfin',
    sourceUrl: 'https://www.indiabudget.gov.in/doc/bh1.pdf',
    dataset: 'Union Budget 2026-27 — Budget at a Glance',
    publicationDate: '2026-02-01',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Union government fiscal deficit — total expenditure less revenue receipts and non-debt capital receipts — as a share of GDP at current market prices. Central government only; it excludes state deficits, so it understates the general government position.',
    change: { value: -0.1, label: 'vs FY2025-26 Revised Estimate (4.4%)', better: 'down' },
    vintages: [
      { label: 'FY2025-26 Revised Estimate', value: 4.4, releasedOn: '2026-02-01' },
      { label: 'FY2026-27 Budget Estimate', value: 4.3, releasedOn: '2026-02-01' },
    ],
    analysis:
      'The consolidation is real but slow, and this is the central government alone. Adding state deficits roughly doubles the general government number, which is the figure comparable to the headline deficits quoted for most other economies.',
  },
  {
    id: 'govt-debt',
    indicator: 'Central Government Debt',
    value: 55.6,
    unit: '% of GDP',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'financial-year', label: 'FY2026-27 (Budget Estimate)', endsOn: '2027-03-31' },
    sourceId: 'minfin',
    sourceUrl: 'https://www.indiabudget.gov.in/doc/bh1.pdf',
    dataset: 'Union Budget 2026-27 — fiscal policy statements',
    publicationDate: '2026-02-01',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Central government debt stock as a share of GDP at current market prices, on the definition used in the Budget’s fiscal policy statements. Excludes state government debt.',
    change: { value: -0.5, label: 'vs FY2025-26 Revised Estimate (56.1%)', better: 'down' },
    vintages: [
      { label: 'FY2025-26 Revised Estimate', value: 56.1, releasedOn: '2026-02-01' },
      { label: 'FY2026-27 Budget Estimate', value: 55.6, releasedOn: '2026-02-01' },
    ],
  },
  {
    id: 'current-account',
    indicator: 'Current Account Balance',
    value: -0.5,
    unit: '% of GDP',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'quarter', label: 'Q1:2026-27 (Apr–Jun 2026)', endsOn: '2026-06-30' },
    sourceId: 'rbi',
    sourceUrl: 'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx',
    dataset: 'Developments in India’s Balance of Payments',
    publicationDate: '2026-09-01',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Current account balance — goods and services trade, primary income and secondary income — as a share of GDP for the quarter. A negative figure is a deficit.',
    note: 'US$4.2 bn deficit. Goods trade deficit US$86.1 bn; services surplus US$51.6 bn; secondary income (largely remittances) US$40.8 bn.',
    change: { value: -0.1, label: 'vs Q1:2025-26 (−0.4%, US$3.4 bn)', better: 'neutral' },
    analysis:
      'The composition is the story. A goods deficit of US$86.1 bn would be alarming on its own; it is offset to within half a percent of GDP by a services surplus of US$51.6 bn and remittances of US$40.8 bn. India runs a large merchandise deficit financed by exporting services and labour, and the widening this quarter came from a 20% jump in imports on higher energy prices rather than from any deterioration in the offsets.',
  },
  {
    id: 'household-savings',
    indicator: 'Household Net Financial Savings',
    value: 7.0,
    unit: '% of GNDI',
    unitShort: '%',
    decimals: 1,
    country: 'India',
    period: { kind: 'financial-year', label: 'FY2024-25', endsOn: '2025-03-31' },
    sourceId: 'rbi',
    sourceUrl: 'https://www.rbi.org.in/Scripts/AnnualReportMainDisplay.aspx',
    dataset: 'RBI Annual Report 2024-25',
    publicationDate: '2025-05-29',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Gross household financial savings less household financial liabilities, as a share of Gross National Disposable Income. Households here include unincorporated enterprises, which is why the aggregate behaves partly like a business-sector series.',
    note: 'Gross financial savings 11.8% of GNDI; financial liabilities 4.8%. Gross domestic savings 34.2% of GNDI.',
    change: { value: 1.2, label: 'vs FY2023-24 (5.8%)', better: 'up' },
    analysis:
      'Net financial savings rose while gross financial savings fell — from 12.1% to 11.8% of GNDI. The improvement came entirely from the liability side, where household borrowing dropped from 6.4% to 4.8% of GNDI. Households did not save more; they borrowed less. That distinction changes what the number implies about the next few years.',
  },
  {
    id: 'mf-aum',
    indicator: 'Mutual Fund Assets Under Management',
    value: 87.08,
    unit: '₹ lakh crore',
    unitShort: '₹ lakh crore',
    decimals: 2,
    country: 'India',
    period: { kind: 'month', label: 'August 2026', endsOn: '2026-08-31' },
    sourceId: 'amfi',
    sourceUrl: 'https://www.amfiindia.com/indian-mutual',
    dataset: 'AMFI monthly industry data',
    publicationDate: '2026-09-09',
    accessedDate: A,
    status: 'reported',
    methodology:
      'Net assets under management of the Indian mutual fund industry at month end, aggregated by AMFI across all fund houses and categories.',
    note: 'Up roughly ₹1.3 lakh crore on the month.',
    analysis:
      'AUM growth blends flows with market returns, so a rising AUM is not by itself evidence of rising participation. The SIP series below separates the two: it is a flow measure and moves with household behaviour rather than with index levels.',
  },
  {
    id: 'sip-flows',
    indicator: 'Monthly SIP Contributions',
    value: 32297,
    unit: '₹ crore per month',
    unitShort: '₹ crore',
    decimals: 0,
    country: 'India',
    period: { kind: 'month', label: 'August 2026', endsOn: '2026-08-31' },
    sourceId: 'amfi',
    sourceUrl: 'https://www.amfiindia.com/indian-mutual',
    dataset: 'AMFI monthly SIP data',
    publicationDate: '2026-09-09',
    accessedDate: A,
    status: 'reported',
    methodology:
      'Total contributions received through Systematic Investment Plans during the month, as reported by AMFI. A flow, not a stock.',
    note: 'Contributing SIP accounts crossed 10 crore.',
    analysis:
      'This is the single most direct measure of the shift the Figure 2 model is about. A monthly flow above ₹32,000 crore is roughly ₹3.9 lakh crore a year moving into financial assets through a disciplined, automatic channel — the mechanism by which the household financial-asset share can move at all.',
  },
  {
    id: 'demat-accounts',
    indicator: 'Demat Accounts',
    value: 23,
    unit: 'crore accounts',
    unitShort: 'crore',
    decimals: 0,
    country: 'India',
    period: { kind: 'date', label: 'Mid-2026', endsOn: '2026-05-31' },
    sourceId: 'cdsl',
    sourceUrl: 'https://www.cdslindia.com/publications/periodicstats.aspx',
    dataset: 'Depository periodic statistics (CDSL + NSDL)',
    publicationDate: '2026-06-15',
    accessedDate: A,
    status: 'reported',
    methodology:
      'Sum of demat accounts serviced by the two depositories. Counts accounts, not people: an investor may hold accounts at both depositories or several with different brokers, so this overstates unique participants.',
    note: 'CDSL 18.38 crore (end-May 2026); NSDL 4.51 crore (May 2026).',
    analysis:
      'Account counts are the most over-read statistic in Indian household finance. Duplicates, dormant accounts and accounts opened for a single allotment all sit inside this number. It establishes that access has widened; it does not establish that 23 crore people hold equities.',
  },
  {
    id: 'household-portfolio-financial',
    indicator: 'Financial Assets in Household Wealth',
    value: 5,
    unit: '% of household assets',
    unitShort: '%',
    decimals: 0,
    country: 'India',
    period: { kind: 'range', label: 'RBI Household Finance Committee, 2017', endsOn: '2017-07-31' },
    sourceId: 'rbi',
    sourceUrl:
      'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    dataset: 'Report of the Household Finance Committee — Indian Household Finance',
    publicationDate: '2017-08-24',
    accessedDate: A,
    status: 'verified',
    methodology:
      'Share of the average Indian household’s asset portfolio held in financial assets, from the Committee’s analysis of household balance sheets. Real estate 77%, gold 11%, financial assets 5%, other physical assets 7%.',
    note: 'This is the allocation the Figure 2 model uses as its observed baseline.',
    analysis:
      'This single number is the premise of The Great Indian Promise. A household portfolio that is 88% physical and 5% financial does not compound: property and gold are lumpy, illiquid and — over the horizons the paper examines — lower-returning than the financial assets households barely hold.',
  },
];

export const MACRO_BY_ID = Object.fromEntries(MACRO_INDICATORS.map((d) => [d.id, d]));

/** Indicators shown on the home-page pulse, in reading order. */
export const PULSE_ORDER = [
  'gdp-growth',
  'cpi-inflation',
  'repo-rate',
  'unemployment',
  'fiscal-deficit',
  'current-account',
  'govt-debt',
  'household-savings',
  'sip-flows',
  'mf-aum',
  'demat-accounts',
  'household-portfolio-financial',
];
