import type { Source } from './types';

/**
 * Source registry. Primary publishers only — where RBI, MoSPI or a bank's
 * own filing publishes a number, IEIL cites that, never a summary of it
 * (spec §44).
 */
export const SOURCES: Record<string, Source> = {
  rbi: {
    id: 'rbi',
    name: 'RBI',
    fullName: 'Reserve Bank of India',
    url: 'https://www.rbi.org.in/',
    tier: 'india-official',
  },
  mospi: {
    id: 'mospi',
    name: 'MoSPI',
    fullName: 'Ministry of Statistics and Programme Implementation / National Statistical Office',
    url: 'https://www.mospi.gov.in/',
    tier: 'india-official',
  },
  pib: {
    id: 'pib',
    name: 'PIB',
    fullName: 'Press Information Bureau, Government of India',
    url: 'https://www.pib.gov.in/',
    tier: 'india-official',
  },
  minfin: {
    id: 'minfin',
    name: 'Ministry of Finance',
    fullName: 'Ministry of Finance, Government of India — Union Budget',
    url: 'https://www.indiabudget.gov.in/',
    tier: 'india-official',
  },
  amfi: {
    id: 'amfi',
    name: 'AMFI',
    fullName: 'Association of Mutual Funds in India',
    url: 'https://www.amfiindia.com/',
    tier: 'financial',
  },
  sebi: {
    id: 'sebi',
    name: 'SEBI',
    fullName: 'Securities and Exchange Board of India',
    url: 'https://www.sebi.gov.in/',
    tier: 'india-official',
  },
  nsdl: {
    id: 'nsdl',
    name: 'NSDL',
    fullName: 'National Securities Depository Limited',
    url: 'https://nsdl.co.in/',
    tier: 'financial',
  },
  cdsl: {
    id: 'cdsl',
    name: 'CDSL',
    fullName: 'Central Depository Services (India) Limited',
    url: 'https://www.cdslindia.com/publications/periodicstats.aspx',
    tier: 'financial',
  },
  nse: {
    id: 'nse',
    name: 'NSE',
    fullName: 'National Stock Exchange of India',
    url: 'https://www.nseindia.com/',
    tier: 'financial',
  },
  sbi: {
    id: 'sbi',
    name: 'State Bank of India',
    fullName: 'State Bank of India — investor disclosures',
    url: 'https://sbi.bank.in/web/corporate-governance/corporate-governance',
    tier: 'issuer',
  },
  hdfcbank: {
    id: 'hdfcbank',
    name: 'HDFC Bank',
    fullName: 'HDFC Bank Limited — investor relations',
    url: 'https://www.hdfc.bank.in/about-us/investor-relations',
    tier: 'issuer',
  },
  icicibank: {
    id: 'icicibank',
    name: 'ICICI Bank',
    fullName: 'ICICI Bank Limited — quarterly financial results',
    url: 'https://www.icici.bank.in/about-us/qfr',
    tier: 'issuer',
  },
  axisbank: {
    id: 'axisbank',
    name: 'Axis Bank',
    fullName: 'Axis Bank Limited — quarterly results',
    url: 'https://www.axis.bank.in/quarterly-results/2024-2025/q4/index.html',
    tier: 'issuer',
  },
  kotak: {
    id: 'kotak',
    name: 'Kotak Mahindra Bank',
    fullName: 'Kotak Mahindra Bank Limited — media releases and regulatory disclosures',
    url: 'https://www.kotak.bank.in/en/investor-relations.html',
    tier: 'issuer',
  },
  bob: {
    id: 'bob',
    name: 'Bank of Baroda',
    fullName: 'Bank of Baroda — shareholders’ corner',
    url: 'https://bankofbaroda.bank.in/shareholders-corner/financial-reports',
    tier: 'issuer',
  },
  pnb: {
    id: 'pnb',
    name: 'Punjab National Bank',
    fullName: 'Punjab National Bank — financial disclosures',
    url: 'https://pnb.bank.in/financials-current.html',
    tier: 'issuer',
  },
  imf: {
    id: 'imf',
    name: 'IMF',
    fullName: 'International Monetary Fund',
    url: 'https://www.imf.org/en/Data',
    tier: 'international',
  },
  worldbank: {
    id: 'worldbank',
    name: 'World Bank',
    fullName: 'World Bank Open Data',
    url: 'https://data.worldbank.org/country/india',
    tier: 'international',
  },
  bis: {
    id: 'bis',
    name: 'BIS',
    fullName: 'Bank for International Settlements',
    url: 'https://www.bis.org/statistics/',
    tier: 'international',
  },
};

export const SOURCE_TIER_LABEL: Record<Source['tier'], string> = {
  'india-official': 'India — official statistics',
  international: 'International organisation',
  financial: 'Financial market infrastructure',
  academic: 'Peer-reviewed / research institution',
  issuer: 'Issuer disclosure (audited or regulatory filing)',
};

export const getSource = (id: string): Source =>
  SOURCES[id] ?? {
    id,
    name: id,
    fullName: id,
    url: '#',
    tier: 'india-official',
  };

/**
 * The date on which the values in this build were retrieved. Every record
 * carries it so a reader can tell how stale the lab is (spec §47).
 */
export const RETRIEVED_ON = '2026-09-24';

/**
 * How data got here, stated once and linked from every provenance panel.
 * This build runs in a sandbox whose egress proxy blocks rbi.org.in,
 * mospi.gov.in, pib.gov.in and the banks' investor-relations hosts, so
 * figures were transcribed from those publishers' releases rather than
 * fetched programmatically. Records carry `reported` rather than
 * `verified` wherever that distinction matters, and every one links to the
 * document that is the authority.
 */
export const RETRIEVAL_NOTE =
  'Values in this build were transcribed from the publishers’ own releases and filings. The environment this lab was built in cannot reach rbi.org.in, mospi.gov.in, pib.gov.in or the banks’ investor-relations hosts directly, so nothing here was fetched by machine. Each record links to the document that is the authority; VERIFIED marks a figure traced to a specific primary release, REPORTED marks one transcribed from an issuer disclosure this build could not open. Check the linked source before citing.';
