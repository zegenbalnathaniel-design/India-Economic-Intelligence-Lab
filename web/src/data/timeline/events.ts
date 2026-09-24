import type { DataStatus } from '../types';

export interface TimelineIndicator {
  label: string;
  value: string;
  status: DataStatus;
  note?: string;
}

export interface TimelineEvent {
  id: string;
  year: string;
  sortYear: number;
  title: string;
  kicker: string;
  context: string;
  consequence: string;
  indicators: TimelineIndicator[];
  relatedResearch?: { label: string; to: string };
  relatedIndicator?: string;
  sourceLabel: string;
  sourceUrl: string;
}

/**
 * Economic timeline. Each entry carries context, what changed in the data,
 * and what it does and does not establish. Dates and institutional facts are
 * a matter of record; quantitative consequences are attributed and marked.
 */
export const TIMELINE: TimelineEvent[] = [
  {
    id: 'liberalisation-1991',
    year: '1991',
    sortYear: 1991,
    title: 'Liberalisation',
    kicker: 'Balance-of-payments crisis, and the end of the licence regime',
    context:
      'By mid-1991 India’s foreign exchange reserves covered roughly two weeks of imports. The response — rupee devaluation, dismantling of industrial licensing, tariff reduction and the opening of sectors to foreign investment — was the largest single discontinuity in post-independence Indian economic policy.',
    consequence:
      'Growth in the three decades since has been faster and less volatile than in the three before. Attributing that entirely to 1991 is a causal claim the time series alone cannot support: the reforms coincided with demographic change, a global trade expansion and the arrival of information technology as an exportable service.',
    indicators: [
      { label: 'Policy change', value: 'Licensing dismantled', status: 'verified' },
      { label: 'Exchange regime', value: 'Devaluation, managed float', status: 'verified' },
    ],
    sourceLabel: 'RBI — History of the Reserve Bank of India',
    sourceUrl: 'https://www.rbi.org.in/scripts/Publications.aspx',
  },
  {
    id: 'gfc-2008',
    year: '2008',
    sortYear: 2008,
    title: 'Global Financial Crisis',
    kicker: 'A banking crisis India largely did not have',
    context:
      'India’s banks held little exposure to the securitised US mortgage assets at the centre of the crisis, and capital account restrictions limited the transmission channel. The shock arrived instead through trade, capital outflows and a sharp tightening of external credit.',
    consequence:
      'Growth slowed rather than collapsed, and the fiscal and monetary response was substantial. The episode is often read as vindication of India’s slower financial liberalisation; it is at least as much a statement about what a large domestic demand base does to external shocks.',
    indicators: [
      { label: 'Transmission channel', value: 'Trade and capital flows', status: 'verified' },
      { label: 'Direct subprime exposure', value: 'Limited', status: 'verified' },
    ],
    sourceLabel: 'RBI — Annual Report 2008-09',
    sourceUrl: 'https://www.rbi.org.in/Scripts/AnnualReportMainDisplay.aspx',
  },
  {
    id: 'demonetisation-2016',
    year: '2016',
    sortYear: 2016,
    title: 'Demonetisation',
    kicker: '₹500 and ₹1,000 notes withdrawn overnight',
    context:
      'On 8 November 2016 the government withdrew legal tender status from the two highest-denomination notes then in circulation, roughly 86% of currency by value. Stated objectives included countering counterfeiting, unaccounted wealth and terror financing.',
    consequence:
      'Almost all withdrawn currency was returned to the banking system, which bears on the unaccounted-wealth objective. Effects on growth are contested and hard to identify: the quarter in question also contained other shocks, and the counterfactual is unobservable. This entry deliberately reports no growth impact, because the credible estimates disagree.',
    indicators: [
      { label: 'Currency withdrawn', value: '~86% by value', status: 'verified' },
      { label: 'Growth impact', value: 'Contested', status: 'unavailable', note: 'Credible estimates disagree; no single figure is reported here.' },
    ],
    relatedIndicator: 'gdp-growth',
    sourceLabel: 'RBI — Annual Report 2016-17',
    sourceUrl: 'https://www.rbi.org.in/Scripts/AnnualReportMainDisplay.aspx',
  },
  {
    id: 'gst-2017',
    year: '2017',
    sortYear: 2017,
    title: 'Goods and Services Tax',
    kicker: 'One indirect tax in place of a patchwork',
    context:
      'From 1 July 2017 a destination-based value-added tax replaced a layered structure of central excise, state VAT, octroi and entry taxes. The design — a shared base administered jointly by the centre and the states through the GST Council — was as significant institutionally as it was fiscally.',
    consequence:
      'It created a national market for goods and a formalisation incentive, at the cost of substantial transitional disruption to small firms. Rate rationalisation continued for years afterwards, which complicates any clean before-and-after comparison of revenue or compliance.',
    indicators: [
      { label: 'Effective from', value: '1 July 2017', status: 'verified' },
      { label: 'Structure', value: 'Destination-based VAT', status: 'verified' },
    ],
    sourceLabel: 'GST Council',
    sourceUrl: 'https://gstcouncil.gov.in/',
  },
  {
    id: 'covid-2020',
    year: '2020',
    sortYear: 2020,
    title: 'Covid-19',
    kicker: 'The deepest contraction in the modern series',
    context:
      'A national lockdown from late March 2020 halted most economic activity. The contraction was concentrated in contact-intensive services and in the informal sector, where measurement is weakest and relief hardest to target.',
    consequence:
      'Real GDP contracted 5.8% in FY2020-21 on the current vintage. Household balance sheets deteriorated through the period, and the recovery in household financial savings that followed took several years to complete.',
    indicators: [
      { label: 'Real GDP growth, FY2020-21', value: '−5.8%', status: 'reported', note: 'Latest available vintage; revised more than once since first release.' },
    ],
    relatedIndicator: 'gdp-growth',
    sourceLabel: 'MoSPI — National Accounts Statistics',
    sourceUrl: 'https://www.mospi.gov.in/',
  },
  {
    id: 'recovery-2021',
    year: '2021–22',
    sortYear: 2021,
    title: 'Recovery and the retail shift',
    kicker: 'Output rebounds; household saving changes shape',
    context:
      'Real GDP grew 9.7% in FY2021-22 against the contracted base. Alongside the output recovery came a durable change in household behaviour: a sustained expansion in demat accounts, systematic investment plans and direct retail participation in equity markets.',
    consequence:
      'The flow shift is real and large — SIP contributions reached ₹32,297 crore a month by August 2026. Whether it re-weights the household balance sheet, which remains dominated by property and gold, is the question The Great Indian Promise takes up.',
    indicators: [
      { label: 'Real GDP growth, FY2021-22', value: '9.7%', status: 'reported' },
      { label: 'Monthly SIP flow, Aug 2026', value: '₹32,297 cr', status: 'reported' },
    ],
    relatedResearch: { label: 'The Great Indian Promise', to: '/research/the-great-indian-promise' },
    relatedIndicator: 'sip-flows',
    sourceLabel: 'MoSPI; AMFI',
    sourceUrl: 'https://www.amfiindia.com/indian-mutual',
  },
  {
    id: 'now-2026',
    year: '2026',
    sortYear: 2026,
    title: 'Where the data stands',
    kicker: 'Growth at 7.7%, inflation inside the band, policy on hold',
    context:
      'Real GDP grew 7.7% in FY2025-26 on the Provisional Estimate. CPI inflation has run inside the RBI’s 4% ± 2 percentage-point tolerance band through the year. The Monetary Policy Committee held the repo rate at 5.50% in August 2026 with a neutral stance.',
    consequence:
      'A high-growth, moderate-inflation configuration with the policy rate unchanged. The open questions sit elsewhere: in the composition of household balance sheets, in the merchandise trade deficit financed by services and remittances, and in whether the flow shift into financial assets reaches beyond the households already holding them.',
    indicators: [
      { label: 'Real GDP growth, FY2025-26', value: '7.7%', status: 'verified' },
      { label: 'Repo rate', value: '5.50%', status: 'verified' },
      { label: 'CPI inflation, July 2026', value: '4.45%', status: 'verified' },
    ],
    relatedIndicator: 'repo-rate',
    sourceLabel: 'MoSPI; RBI',
    sourceUrl: 'https://www.rbi.org.in/',
  },
];
