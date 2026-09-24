import { RETRIEVED_ON } from '../sources';
import type { DataStatus } from '../types';

/**
 * India's external economic relationships, for the globe.
 *
 * Only figures traceable to the RBI balance-of-payments release for
 * Q1:2026-27 are carried as values. Bilateral partner flows are NOT
 * included: this build could not obtain partner-level trade data from
 * DGCI&S or the Ministry of Commerce, and inventing a plausible-looking
 * set of bilateral arcs would be exactly the fabrication the lab exists
 * to avoid. The globe therefore shows the aggregate composition of the
 * external account, positioned by trading region, and says what is missing.
 */

export interface ExternalFlow {
  id: string;
  label: string;
  /** Aggregate flow, US$ billion for the quarter. */
  value: number | null;
  direction: 'inflow' | 'outflow';
  /** Approximate lat/lon used only to place the arc endpoint. */
  lat: number;
  lon: number;
  status: DataStatus;
  note: string;
}

export const INDIA_COORD = { lat: 22.5, lon: 79 };

export const EXTERNAL_FLOWS: ExternalFlow[] = [
  {
    id: 'goods-imports',
    label: 'Merchandise imports',
    value: 218.0,
    direction: 'outflow',
    lat: 25,
    lon: 50,
    status: 'verified',
    note: 'US$218.0 bn in Q1:2026-27, up 20% year on year on higher energy prices. Placed toward West Asia because energy dominates the increase; the endpoint is illustrative of composition, not a bilateral figure.',
  },
  {
    id: 'goods-exports',
    label: 'Merchandise exports',
    value: 132.0,
    direction: 'inflow',
    lat: 40,
    lon: -80,
    status: 'verified',
    note: 'US$132.0 bn in Q1:2026-27, up 17.1% year on year.',
  },
  {
    id: 'services-surplus',
    label: 'Services surplus',
    value: 51.6,
    direction: 'inflow',
    lat: 52,
    lon: -2,
    status: 'verified',
    note: 'US$51.6 bn in Q1:2026-27, against US$47.9 bn a year earlier. The single largest offset to the goods deficit.',
  },
  {
    id: 'remittances',
    label: 'Secondary income (largely remittances)',
    value: 40.8,
    direction: 'inflow',
    lat: 24,
    lon: 54,
    status: 'verified',
    note: 'US$40.8 bn in Q1:2026-27, against US$30.9 bn a year earlier.',
  },
  {
    id: 'primary-income',
    label: 'Primary income deficit',
    value: 10.5,
    direction: 'outflow',
    lat: 1,
    lon: 104,
    status: 'verified',
    note: 'US$10.5 bn deficit in Q1:2026-27, narrowed from US$13.3 bn. Investment income paid abroad net of income received.',
  },
  {
    id: 'fdi',
    label: 'Foreign direct investment',
    value: null,
    direction: 'inflow',
    lat: 35,
    lon: 138,
    status: 'unavailable',
    note: 'Net FDI for Q1:2026-27 was not obtainable in this build. The RBI publishes it in the balance-of-payments release and the monthly bulletin. Nothing has been estimated in its place.',
  },
];

export const EXTERNAL_SUMMARY = {
  currentAccountUsdBn: -4.2,
  currentAccountPctGdp: -0.5,
  goodsDeficitUsdBn: -86.1,
  period: 'Q1:2026-27 (Apr–Jun 2026)',
  sourceUrl: 'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx',
  publicationDate: '2026-09-01',
  accessedDate: RETRIEVED_ON,
};

export const BILATERAL_NOTE =
  'Partner-level trade and investment flows are not shown. This build could not obtain bilateral data from DGCI&S or the Ministry of Commerce, and drawing arcs between India and named countries without it would be a fabrication. What is shown is the composition of the aggregate external account for the quarter, with endpoints placed by the region each component is most associated with rather than by a measured bilateral value.';
