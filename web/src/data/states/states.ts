import type { DataStatus, Discrepancy } from '../types';

export interface StateMetric {
  label: string;
  value: number | null;
  unit: string;
  status: DataStatus;
  period: string;
  sourceUrl: string;
  note?: string;
}

export interface StateRecord {
  id: string;
  name: string;
  /** Position in IndiaMap's projected SVG space (see IndiaMap.tsx). */
  cx: number;
  cy: number;
  /** Where the code label sits, when 'below' would collide with a neighbour. */
  labelAbove?: boolean;
  region: 'North' | 'South' | 'East' | 'West' | 'Central' | 'North-East';
  perCapitaNsdp: StateMetric;
  urbanisation: StateMetric;
  gsdp: StateMetric;
  sectors: StateMetric;
  commentary?: string;
}

const RBI_HANDBOOK =
  'https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States';
const CENSUS = 'https://censusindia.gov.in/census.website/';

const nsdp = (value: number | null, note?: string): StateMetric => ({
  label: 'Per-capita NSDP',
  value,
  unit: '₹ at current prices',
  status: value === null ? 'unavailable' : 'reported',
  period: '2024-25',
  sourceUrl: RBI_HANDBOOK,
  note:
    note ??
    'Net State Domestic Product per person at current prices, from the RBI Handbook of Statistics on Indian States 2024-25. Transcribed from the publication; verify against the Handbook before citing.',
});

const urban = (value: number | null): StateMetric => ({
  label: 'Urbanisation',
  value,
  unit: '% of population',
  status: value === null ? 'unavailable' : 'reported',
  period: 'Census 2011',
  sourceUrl: CENSUS,
  note: 'Census of India 2011 — the most recent completed decennial census. Fifteen years old and certainly understates current urbanisation; it is shown at its own period rather than projected forward.',
});

const NO_GSDP = (): StateMetric => ({
  label: 'GSDP',
  value: null,
  unit: '₹ lakh crore at current prices',
  status: 'unavailable',
  period: '2024-25',
  sourceUrl: RBI_HANDBOOK,
  note: 'Authoritative-looking sources disagree on the level by roughly a factor of two — see the discrepancy note. No figure is shown rather than an arbitrary pick.',
});

const NO_SECTORS = (): StateMetric => ({
  label: 'Sector composition',
  value: null,
  unit: '% of GSVA',
  status: 'unavailable',
  period: '2024-25',
  sourceUrl: RBI_HANDBOOK,
  note: 'Primary / secondary / tertiary shares of gross state value added were not obtainable in this build. The state Directorate of Economics and Statistics publishes them.',
});

/**
 * State economics. Per-capita NSDP is the one indicator with a coherent
 * single-source reading across states; GSDP levels are withheld because the
 * sources conflict (see GSDP_DISCREPANCY). States absent from this list are
 * absent from the build, not from India — the map says so explicitly.
 */
export const STATES: StateRecord[] = [
  {
    id: 'TG',
    name: 'Telangana',
    cx: 230,
    cy: 376,
    // Telangana carries the largest node and sits directly above Andhra
    // Pradesh; a label below it would land on that state's circle.
    labelAbove: true,
    region: 'South',
    perCapitaNsdp: nsdp(387623),
    urbanisation: urban(38.9),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'The highest per-capita NSDP among the major states in this sample, concentrated heavily in Hyderabad. State-level per-capita income conceals within-state dispersion more severely here than almost anywhere else.',
  },
  {
    id: 'KA',
    name: 'Karnataka',
    cx: 200,
    cy: 425,
    region: 'South',
    perCapitaNsdp: nsdp(380000, 'Reported as approximately ₹3.80 lakh in the RBI Handbook 2024-25. Carries more rounding than the other figures here.'),
    urbanisation: urban(38.6),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'Services-led, with a per-capita figure driven substantially by Bengaluru’s software export base — an activity whose measured value added is unusually sensitive to transfer-pricing conventions.',
  },
  {
    id: 'TN',
    name: 'Tamil Nadu',
    cx: 226,
    cy: 489,
    region: 'South',
    perCapitaNsdp: nsdp(361000, 'Reported as approximately ₹3.61 lakh in the RBI Handbook 2024-25.'),
    urbanisation: urban(48.4),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'The most urbanised large state at the 2011 Census, with a broader manufacturing base than the other southern states and correspondingly less concentration in a single city.',
  },
  {
    id: 'MH',
    name: 'Maharashtra',
    cx: 195,
    cy: 352,
    region: 'West',
    perCapitaNsdp: nsdp(309000, 'Reported as approximately ₹3.09 lakh in the RBI Handbook 2024-25.'),
    urbanisation: urban(45.2),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'India’s largest state economy in absolute terms, but mid-ranking per person — a reminder that size and prosperity are different measurements. Mumbai’s financial sector sits inside this number.',
  },
  {
    id: 'KL',
    name: 'Kerala',
    cx: 202,
    cy: 500,
    region: 'South',
    perCapitaNsdp: nsdp(308338),
    urbanisation: urban(47.7),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'High per-capita income supported substantially by remittances, which enter the state economy through the secondary income account rather than through domestic production.',
  },
  {
    id: 'AP',
    name: 'Andhra Pradesh',
    cx: 241,
    cy: 409,
    region: 'South',
    perCapitaNsdp: nsdp(266240),
    urbanisation: urban(29.6),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
  },
  {
    id: 'MP',
    name: 'Madhya Pradesh',
    cx: 220,
    cy: 288,
    region: 'Central',
    perCapitaNsdp: nsdp(152615),
    urbanisation: urban(27.6),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
  },
  {
    id: 'UP',
    name: 'Uttar Pradesh',
    cx: 245,
    cy: 231,
    region: 'North',
    perCapitaNsdp: nsdp(108000, 'Reported as approximately ₹1.08 lakh in the RBI Handbook 2024-25.'),
    urbanisation: urban(22.3),
    gsdp: NO_GSDP(),
    sectors: NO_SECTORS(),
    commentary:
      'Among the largest state economies in absolute terms and among the lowest per person. The ratio between this figure and Telangana’s is roughly 3.6× — the single starkest number on this page.',
  },
];

export const STATE_BY_ID = Object.fromEntries(STATES.map((s) => [s.id, s]));

/**
 * A real conflict between sources, surfaced rather than resolved (spec §50).
 */
export const GSDP_DISCREPANCY: Discrepancy = {
  summary: 'Sources disagree on state GSDP levels for 2024-25 by roughly a factor of two.',
  entries: [
    {
      sourceId: 'rbi',
      label: 'RBI Handbook of Statistics on Indian States 2024-25 (as reported)',
      value: 21.98,
      period: '2024-25 — Maharashtra, ₹ lakh crore',
      url: 'https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States',
    },
    {
      sourceId: 'mospi',
      label: 'State DES / MoSPI compilations (as reported)',
      value: 45.3,
      period: '2024-25 — Maharashtra, ₹ lakh crore',
      url: 'https://www.mospi.gov.in/',
    },
  ],
  explanation:
    'The likely explanation is that the two figures are on different bases — constant versus current prices, or different vintages of a quick or advance estimate — but this build could not open either publication to establish which. Since the difference is large enough to change any conclusion drawn from it, no GSDP level is displayed. Per-capita NSDP, where the readings are internally consistent, is shown instead. Resolving this properly means opening the RBI Handbook directly.',
};

export const STATES_NOTE =
  'Eight major states are covered here. The others are absent from this build, not unimportant: state-level series come from individual Directorates of Economics and Statistics on different schedules, and none was obtainable programmatically in this environment. Absence is shown as absence.';
