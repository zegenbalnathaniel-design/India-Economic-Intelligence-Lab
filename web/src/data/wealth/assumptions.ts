import type { Allocation, AssetKey, Figure2Inputs, Returns } from '../../models/figure2/types';
import { RETRIEVED_ON } from '../sources';
import type { DataStatus } from '../types';

/**
 * Figure 2 — the research defaults.
 *
 * Every variable is classified (spec §57). The allocation is OBSERVED: it is
 * the household portfolio the RBI's Household Finance Committee measured.
 * The returns are ASSUMPTIONS anchored to observed history — which is not
 * the same thing, and the figure says so wherever it shows them.
 */

export interface AssetSpec {
  key: AssetKey;
  label: string;
  short: string;
  colour: string;
  description: string;
}

export const ASSETS: Record<AssetKey, AssetSpec> = {
  property: {
    key: 'property',
    label: 'Property',
    short: 'PROP',
    colour: '#e8933a',
    description:
      'Land and buildings, including the dwelling the household lives in. Indivisible, illiquid, and for most households bought once and held.',
  },
  gold: {
    key: 'gold',
    label: 'Gold',
    short: 'GOLD',
    colour: '#c9a227',
    description:
      'Bullion and ornaments. Liquid in a way property is not, and culturally embedded as a store of value and as collateral of last resort.',
  },
  financial: {
    key: 'financial',
    label: 'Financial Assets',
    short: 'FIN',
    colour: '#5b9bd5',
    description:
      'Deposits, provident and pension balances, insurance, mutual funds and direct equity. The only bucket that compounds without being sold.',
  },
  other: {
    key: 'other',
    label: 'Other Physical',
    short: 'OTHER',
    colour: '#6b7a82',
    description:
      'Durable goods, vehicles, livestock, machinery and business equipment. Productive for some households, depreciating for most.',
  },
};

/**
 * Observed household portfolio. RBI Household Finance Committee (July 2017):
 * real estate 77%, gold 11%, financial assets 5%, other physical 7%.
 */
export const DEFAULT_ALLOCATION: Allocation = {
  property: 0.77,
  gold: 0.11,
  financial: 0.05,
  other: 0.07,
};

/**
 * Assumed long-horizon nominal returns, in decimal fractions per annum.
 *
 * These are ASSUMPTIONS. Each is anchored to an observed long-run series,
 * cited below, and each is deliberately set at or below that anchor: a
 * 30-year projection that assumes the best three decades on record repeat
 * is a forecast dressed up as arithmetic. Every one is editable.
 */
export const DEFAULT_RETURNS: Returns = {
  property: 0.055,
  gold: 0.1,
  financial: 0.095,
  other: 0.0,
};

export interface VariableClassification {
  variable: string;
  value: string;
  status: DataStatus;
  classification: 'OBSERVED' | 'DERIVED' | 'ASSUMPTION' | 'SCENARIO';
  source: string;
  sourceUrl: string;
  basis: string;
}

export const FIGURE2_CLASSIFICATION: VariableClassification[] = [
  {
    variable: 'Property share',
    value: '77%',
    status: 'verified',
    classification: 'OBSERVED',
    source: 'RBI Household Finance Committee (2017)',
    sourceUrl:
      'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    basis: 'Share of the average Indian household asset portfolio held in real estate.',
  },
  {
    variable: 'Gold share',
    value: '11%',
    status: 'verified',
    classification: 'OBSERVED',
    source: 'RBI Household Finance Committee (2017)',
    sourceUrl:
      'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    basis: 'Share held in gold, bullion and ornaments.',
  },
  {
    variable: 'Financial-asset share',
    value: '5%',
    status: 'verified',
    classification: 'OBSERVED',
    source: 'RBI Household Finance Committee (2017)',
    sourceUrl:
      'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    basis: 'Residual share in financial assets — deposits, insurance, pensions, funds and equity.',
  },
  {
    variable: 'Other physical share',
    value: '7%',
    status: 'calculated',
    classification: 'DERIVED',
    source: 'Derived from the same report',
    sourceUrl:
      'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    basis:
      'The residual: 100% − 77% property − 11% gold − 5% financial. Durable goods, vehicles and productive equipment.',
  },
  {
    variable: 'Rural financial-asset share (cross-check)',
    value: '4.6%',
    status: 'calculated',
    classification: 'DERIVED',
    source: 'NSS 77th round, AIDIS 2019 (MoSPI)',
    sourceUrl: 'https://www.mospi.gov.in/sites/default/files/press_release/press_note-AIDIS-240821.pdf',
    basis:
      '₹72,608 average financial assets ÷ (₹15,19,771 physical + ₹72,608 financial) per rural household. An independent survey reaching nearly the same 5% figure.',
  },
  {
    variable: 'Urban financial-asset share (cross-check)',
    value: '9.3%',
    status: 'calculated',
    classification: 'DERIVED',
    source: 'NSS 77th round, AIDIS 2019 (MoSPI)',
    sourceUrl: 'https://www.mospi.gov.in/sites/default/files/press_release/press_note-AIDIS-240821.pdf',
    basis: '₹2,51,804 ÷ (₹24,65,277 + ₹2,51,804) per urban household.',
  },
  {
    variable: 'Property return',
    value: '5.5% p.a. nominal',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'Anchored to the RBI All-India House Price Index',
    sourceUrl: 'https://www.rbi.org.in/Scripts/PublicationsView.aspx',
    basis:
      'The HPI grew about 3.7% a year through 2017–2020 and 2.2% year on year in Q2:2025-26, after double-digit growth in the early 2010s. 5.5% sits between the two regimes. It is an assumption about the next thirty years, not a measurement of the last.',
  },
  {
    variable: 'Gold return',
    value: '10.0% p.a. nominal',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'Anchored to long-run rupee gold prices',
    sourceUrl: 'https://www.rbi.org.in/Scripts/PublicationsView.aspx',
    basis:
      'Rupee gold compounded at roughly 11–13% a year over the twenty years to 2026 — a period containing two exceptional bull runs. The default is set below that range deliberately.',
  },
  {
    variable: 'Financial-asset return',
    value: '9.5% p.a. nominal',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'Anchored to the Nifty 50 TRI and deposit rates',
    sourceUrl: 'https://www.nseindia.com/products-services/indices-nifty50-index',
    basis:
      'The Nifty 50 TRI returned about 12.4% a year over the twenty years to February 2026, but a household financial portfolio is mostly deposits, provident fund and insurance, not index equity. 9.5% reflects that blend rather than the equity line alone.',
  },
  {
    variable: 'Other physical return',
    value: '0.0% p.a. nominal',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'Modelling convention',
    sourceUrl: '',
    basis:
      'Durable goods depreciate; productive equipment yields a service flow rather than a capital gain. Treating the bucket as returning nothing nominally is conservative in both directions and avoids inventing a number. Editable.',
  },
  {
    variable: 'Annual saving',
    value: '₹1,00,000',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'The figure’s stated premise',
    sourceUrl: '',
    basis: 'A round sum chosen so the arithmetic is legible: ₹1 lakh a year for thirty years is ₹30,00,000 contributed.',
  },
  {
    variable: 'Horizon',
    value: '30 years',
    status: 'assumption',
    classification: 'ASSUMPTION',
    source: 'The figure’s stated premise',
    sourceUrl: '',
    basis: 'Approximately one working lifetime of accumulation.',
  },
  {
    variable: 'Anything you change below',
    value: '—',
    status: 'scenario',
    classification: 'SCENARIO',
    source: 'You',
    sourceUrl: '',
    basis:
      'Every result computed from an input you have moved is conditional on that input. It is a hypothetical, not a projection, and not advice.',
  },
];

export const BASELINE_INPUTS: Figure2Inputs = {
  annualSaving: 100_000,
  startingCapital: 0,
  years: 30,
  frequency: 'annual',
  timing: 'end',
  allocation: { ...DEFAULT_ALLOCATION },
  returns: { ...DEFAULT_RETURNS },
};

export const FIGURE2_CAVEAT =
  'Result is conditional on the assumptions entered by the user. Historical returns are not a guarantee of future performance, and nothing here is financial advice.';

export const FIGURE2_RETRIEVED = RETRIEVED_ON;
