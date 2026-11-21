/**
 * σ- and β-convergence across Indian states, ported from
 * analysis/convergence.py. Pure functions over a long panel of
 * [state, financialYear, value] rows.
 */
import { clean, mean, percentile, rankDescMin, sd } from '../stats/describe';
import { trySimpleOLS, type SeType } from '../stats/regression';

export type MeasureKey = 'sd_log' | 'cv' | 'gini' | 'max_min' | 'p90_p10';
export const STABLE_THRESHOLD_PCT = 5;

export type Row = readonly [state: string, fy: string, value: number | null, method?: string];

/** '2004-05' -> 2004 */
export const fyStart = (fy: string) => parseInt(fy.slice(0, 4), 10);

export type Wide = Map<string, Map<string, number>>;

export function widePanel(rows: readonly Row[], states?: readonly string[]): { wide: Wide; years: string[] } {
  const keep = states ? new Set(states) : null;
  const wide: Wide = new Map();
  const years = new Set<string>();
  for (const [s, fy, v] of rows) {
    if (keep && !keep.has(s)) continue;
    years.add(fy);
    if (!wide.has(s)) wide.set(s, new Map());
    if (typeof v === 'number' && Number.isFinite(v)) wide.get(s)!.set(fy, v);
  }
  return { wide, years: [...years].sort((a, b) => fyStart(a) - fyStart(b)) };
}

export const yearsBetween = (years: readonly string[], start: string, end: string) => {
  let [a, b] = [fyStart(start), fyStart(end)];
  if (b < a) [a, b] = [b, a];
  return years.filter((y) => fyStart(y) >= a && fyStart(y) <= b);
};

export function dispersion(values: readonly number[], measure: MeasureKey): number {
  const x = clean(values);
  if (x.length < 2 || x.some((v) => v <= 0)) return NaN;
  switch (measure) {
    case 'sd_log':
      return sd(x.map(Math.log));
    case 'cv':
      return (sd(x) / mean(x)) * 100;
    case 'gini': {
      let d = 0;
      for (const a of x) for (const b of x) d += Math.abs(a - b);
      return d / (2 * x.length ** 2 * mean(x));
    }
    case 'max_min':
      return Math.max(...x) / Math.min(...x);
    case 'p90_p10':
      return percentile(x, 90) / percentile(x, 10);
  }
}

export function classifyTrend(pct: number, threshold = STABLE_THRESHOLD_PCT) {
  if (!Number.isFinite(pct)) return 'insufficient data' as const;
  if (Math.abs(pct) < threshold) return 'stable' as const;
  return pct < 0 ? ('falling' as const) : ('rising' as const);
}

export interface SigmaResult {
  byYear: { fy: string; value: number; n: number }[];
  included: string[];
  excluded: { state: string; reason: string }[];
  slope: number;
  slopeP: number;
  trendChange: number;
  trendPctOfMean: number;
  first: number;
  last: number;
  verdict: ReturnType<typeof classifyTrend>;
  compositionChanges: boolean;
}

export function sigma(
  rows: readonly Row[],
  start: string,
  end: string,
  measure: MeasureKey = 'sd_log',
  balanced = true,
  states?: readonly string[],
  minStates = 5,
): SigmaResult {
  const { wide, years: all } = widePanel(rows, states);
  const years = yearsBetween(all, start, end);
  const included: string[] = [];
  const excluded: { state: string; reason: string }[] = [];
  for (const [s, m] of [...wide.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const missing = years.filter((y) => !m.has(y));
    if (balanced && missing.length) excluded.push({ state: s, reason: `no value in ${missing.join(', ')}` });
    else if (!balanced && years.every((y) => !m.has(y))) continue;
    else included.push(s);
  }
  const byYear: SigmaResult['byYear'] = [];
  const sets = new Set<string>();
  for (const y of years) {
    const vals = included.map((s) => wide.get(s)!.get(y)).filter((v): v is number => v !== undefined);
    if (vals.length >= minStates) {
      byYear.push({ fy: y, value: dispersion(vals, measure), n: vals.length });
      sets.add(included.filter((s) => wide.get(s)!.has(y)).join('|'));
    }
  }
  const res: SigmaResult = {
    byYear,
    included,
    excluded,
    slope: NaN,
    slopeP: NaN,
    trendChange: NaN,
    trendPctOfMean: NaN,
    first: NaN,
    last: NaN,
    verdict: 'insufficient data',
    compositionChanges: sets.size > 1,
  };
  const valid = byYear.filter((r) => Number.isFinite(r.value));
  if (valid.length < 2) return res;
  const t = valid.map((r) => fyStart(r.fy));
  const v = valid.map((r) => r.value);
  const fit = trySimpleOLS(t, v);
  if (!fit) return res;
  const span = Math.max(...t) - Math.min(...t);
  res.slope = fit.slope;
  res.slopeP = fit.p;
  res.trendChange = fit.slope * span;
  res.trendPctOfMean = (res.trendChange / mean(v)) * 100;
  res.first = v[0];
  res.last = v[v.length - 1];
  res.verdict = classifyTrend(res.trendPctOfMean);
  return res;
}

export function speedOfConvergence(slopePct: number, years: number): { speed: number; halfLife: number; note: string } {
  if (!Number.isFinite(slopePct) || years <= 0) return { speed: NaN, halfLife: NaN, note: 'slope or window undefined' };
  if (slopePct >= 0) return { speed: NaN, halfLife: NaN, note: 'slope is not negative, so no speed of convergence is implied' };
  const b = slopePct / 100;
  const inside = 1 + b * years;
  if (inside <= 0)
    return { speed: NaN, halfLife: NaN, note: '1 + b·T ≤ 0 — the formula is undefined for a slope this steep over this window' };
  const lam = -Math.log(inside) / years;
  return { speed: lam, halfLife: Math.log(2) / lam, note: '' };
}

export interface BetaPoint {
  state: string;
  initial: number;
  final: number;
  logInitial: number;
  growth: number;
}

export function beta(rows: readonly Row[], start: string, end: string, seType: SeType = 'nonrobust', states?: readonly string[]) {
  const { wide } = widePanel(rows, states);
  const T = fyStart(end) - fyStart(start);
  const points: BetaPoint[] = [];
  const excluded: { state: string; reason: string }[] = [];
  for (const [s, m] of [...wide.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const v0 = m.get(start);
    const v1 = m.get(end);
    const miss = [v0 === undefined ? start : null, v1 === undefined ? end : null].filter(Boolean);
    if (miss.length) {
      excluded.push({ state: s, reason: `no value in ${miss.join(' and ')}` });
      continue;
    }
    if (v0! <= 0 || v1! <= 0) {
      excluded.push({ state: s, reason: 'non-positive value (log undefined)' });
      continue;
    }
    points.push({
      state: s,
      initial: v0!,
      final: v1!,
      logInitial: Math.log(v0!),
      growth: ((Math.log(v1!) - Math.log(v0!)) / T) * 100,
    });
  }
  const fit = T > 0 && points.length >= 5 ? trySimpleOLS(points.map((p) => p.logInitial), points.map((p) => p.growth), seType) : null;
  const speed = fit ? speedOfConvergence(fit.slope, T) : { speed: NaN, halfLife: NaN, note: 'insufficient data' };
  return { start, end, years: T, points, excluded, fit, ...speed };
}

export function rankChanges(rows: readonly Row[], start: string, end: string, states?: readonly string[]) {
  const { wide } = widePanel(rows, states);
  const both = [...wide.entries()].filter(([, m]) => m.has(start) && m.has(end));
  const r0 = rankDescMin(both.map(([, m]) => m.get(start)!));
  const r1 = rankDescMin(both.map(([, m]) => m.get(end)!));
  return both
    .map(([s], i) => ({ state: s, rankStart: r0[i], rankEnd: r1[i], places: r0[i] - r1[i] }))
    .sort((a, b) => b.places - a.places || a.state.localeCompare(b.state));
}

/** Each state's series ÷ its own base-year value × 100. */
export function indexToBase(wide: Wide, years: readonly string[], base: string) {
  const out = new Map<string, Map<string, number>>();
  const reasons: Record<string, string> = {};
  for (const [s, m] of wide) {
    const b = m.get(base);
    if (b === undefined || b <= 0) {
      reasons[s] = `no value in base year ${base}`;
      continue;
    }
    out.set(s, new Map(years.filter((y) => m.has(y)).map((y) => [y, (m.get(y)! / b) * 100])));
  }
  return { indexed: out, reasons };
}

/** Year-on-year % change, only between consecutive financial years. */
export function annualGrowth(m: Map<string, number>, years: readonly string[]) {
  const out: { fy: string; growth: number }[] = [];
  years.forEach((cur, i) => {
    if (!i) return;
    const prev = years[i - 1];
    if (fyStart(cur) - fyStart(prev) !== 1) return;
    const a = m.get(prev);
    const b = m.get(cur);
    if (a !== undefined && b !== undefined && a > 0) out.push({ fy: cur, growth: (b / a - 1) * 100 });
  });
  return out;
}

export function cagr(first: number, last: number, years: number): number {
  if (!(first > 0) || !(last > 0) || years <= 0) return NaN;
  return ((last / first) ** (1 / years) - 1) * 100;
}
