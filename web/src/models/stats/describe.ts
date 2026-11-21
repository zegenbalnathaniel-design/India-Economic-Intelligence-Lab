/** Descriptive statistics shared by the lab engines. */

export const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

export function clean(values: readonly (number | null | undefined)[]): number[] {
  return values.filter(isNum);
}

export function sum(x: readonly number[]): number {
  let s = 0;
  for (const v of x) s += v;
  return s;
}

export function mean(x: readonly number[]): number {
  return x.length ? sum(x) / x.length : NaN;
}

/** Standard deviation; `ddof` 0 = population (numpy default), 1 = sample (pandas default). */
export function sd(x: readonly number[], ddof = 0): number {
  const n = x.length;
  if (n - ddof <= 0) return NaN;
  const m = mean(x);
  let ss = 0;
  for (const v of x) ss += (v - m) ** 2;
  return Math.sqrt(ss / (n - ddof));
}

/** Percentile with numpy's default 'linear' method (Hyndman–Fan type 7). */
export function percentile(x: readonly number[], q: number): number {
  if (!x.length) return NaN;
  const s = [...x].sort((a, b) => a - b);
  const pos = ((s.length - 1) * q) / 100;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}

/** Ranks 1..n with ties given their average rank (scipy.stats.rankdata). */
export function rankAverage(x: readonly number[]): number[] {
  const idx = x.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
  const ranks = new Array<number>(x.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
    const r = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) ranks[idx[k][1]] = r;
    i = j + 1;
  }
  return ranks;
}

/** Ranks with 1 = highest, ties take the minimum (pandas rank(ascending=False, method='min')). */
export function rankDescMin(x: readonly number[]): number[] {
  return x.map((v) => 1 + x.filter((o) => o > v).length);
}

export function minMax(x: readonly number[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of x) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  return [lo, hi];
}
