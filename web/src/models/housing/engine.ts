/**
 * Housing affordability, ported from analysis/housing.py: EMI, price-to-
 * income, the RPIPI time series and the ICHASI percentile-clipped stress
 * score. Inputs are the exported RESIDEX and income tables.
 */
import { mean, percentile } from '../stats/describe';

export type IncomeSource = 'nsdp' | 'mpce' | 'city';

export interface HousingData {
  quarters: string[];
  fyOfQuarter: Record<string, string>;
  cityToState: Record<string, string>;
  /** city -> [quarter, composite, ≤60 sqm, 60–110 sqm, >110 sqm] (₹/sq ft) */
  prices: Record<string, (string | number | null)[][]>;
  /** city -> [quarter, composite index] */
  index: Record<string, (string | number | null)[][]>;
  sqftPerSqm: number;
  nsdpCurrent: Record<string, [string, number][]>;
  mpce: Record<string, number>;
  cityIncome: { residex_city: string | null; avg_annual_household_income_lakh: number | null }[];
}

export function emi(principal: number, annualRate: number, years: number): number {
  const n = Math.round(years * 12);
  if (annualRate === 0) return principal / n;
  const r = annualRate / 12;
  const f = (1 + r) ** n;
  return (principal * r * f) / (f - 1);
}

export interface Assumptions {
  unitSqm: number;
  downPayment: number;
  rate: number;
  tenure: number;
  incomeSource: IncomeSource;
  quarter?: string;
}

export function incomeFor(d: HousingData, city: string, src: IncomeSource): number | null {
  const state = d.cityToState[city];
  if (!state) return null;
  if (src === 'nsdp') {
    const s = d.nsdpCurrent[state];
    return s?.length ? s[s.length - 1][1] : null;
  }
  if (src === 'mpce') return d.mpce[state] !== undefined ? d.mpce[state] * 12 : null;
  const row = d.cityIncome.find((c) => c.residex_city === city);
  return row?.avg_annual_household_income_lakh ? row.avg_annual_household_income_lakh * 1e5 : null;
}

export function priceAt(d: HousingData, city: string, quarter?: string): { quarter: string; perSqft: number } | null {
  const rows = d.prices[city];
  if (!rows?.length) return null;
  const row = quarter ? rows.find((r) => r[0] === quarter) : rows[rows.length - 1];
  if (!row || typeof row[1] !== 'number') return null;
  return { quarter: row[0] as string, perSqft: row[1] };
}

export interface CityAffordability {
  city: string;
  state: string;
  quarter: string;
  perSqft: number;
  unitPrice: number;
  income: number;
  pti: number;
  emiMonthly: number;
  emiPct: number;
}

export function cityAffordability(d: HousingData, city: string, a: Assumptions): CityAffordability | null {
  const p = priceAt(d, city, a.quarter);
  const income = incomeFor(d, city, a.incomeSource);
  if (!p || !income || income <= 0) return null;
  const unitPrice = p.perSqft * a.unitSqm * d.sqftPerSqm;
  const m = emi(unitPrice * (1 - a.downPayment), a.rate, a.tenure);
  return {
    city,
    state: d.cityToState[city],
    quarter: p.quarter,
    perSqft: p.perSqft,
    unitPrice,
    income,
    pti: unitPrice / income,
    emiMonthly: m,
    emiPct: (m / (income / 12)) * 100,
  };
}

export function affordabilityAcross(d: HousingData, a: Assumptions): CityAffordability[] {
  return Object.keys(d.prices)
    .map((c) => (d.cityToState[c] ? cityAffordability(d, c, a) : null))
    .filter((x): x is CityAffordability => x !== null)
    .sort((x, y) => y.pti - x.pti);
}

/** RPIPI_t = 100 · (HPI_t / HPI_0) / (Y_t / Y_0), annualised RESIDEX index. */
export function rpipi(d: HousingData, city: string) {
  const state = d.cityToState[city];
  const idx = d.index[city];
  const inc = d.nsdpCurrent[state];
  if (!state || !idx?.length || !inc?.length) return null;
  const byFy = new Map<string, number[]>();
  for (const [q, v] of idx) {
    if (typeof v !== 'number') continue;
    const fy = d.fyOfQuarter[q as string];
    if (!fy) continue;
    if (!byFy.has(fy)) byFy.set(fy, []);
    byFy.get(fy)!.push(v);
  }
  const incMap = new Map(inc);
  const merged = [...byFy.entries()]
    .filter(([fy]) => incMap.has(fy))
    .map(([fy, vals]) => ({ fy, price: mean(vals), income: incMap.get(fy)! }))
    .sort((a, b) => a.fy.localeCompare(b.fy));
  if (!merged.length) return null;
  const p0 = merged[0].price;
  const y0 = merged[0].income;
  const series = merged.map((r) => ({ ...r, rpipi: (100 * (r.price / p0)) / (r.income / y0) }));
  return { city, state, base: series[0].fy, latest: series[series.length - 1], series, ok: series.length >= 2 };
}

/** ICHASI cross-section: PTI clipped to [P_low, P_high] and rescaled to 0–100. */
export function stressIndex(d: HousingData, a: Assumptions, low = 5, high = 95) {
  const quarter = a.quarter ?? d.quarters[d.quarters.length - 1];
  const aff = affordabilityAcross(d, { ...a, quarter });
  if (aff.length < 3) return null;
  const pti = aff.map((c) => c.pti);
  const lo = percentile(pti, low);
  let hi = percentile(pti, high);
  if (hi <= lo) hi = lo + 1e-9;
  return {
    quarter,
    lo,
    hi,
    scores: aff
      .map((c) => {
        const clipped = Math.min(Math.max(c.pti, lo), hi);
        return { ...c, clipped, score: ((clipped - lo) / (hi - lo)) * 100 };
      })
      .sort((x, y) => y.score - x.score),
  };
}
