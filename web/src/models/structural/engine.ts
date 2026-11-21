/**
 * Output-vs-employment sector shares and relative labour productivity,
 * ported from analysis/structural.py.
 */

export const SECTORS = {
  Agriculture: ['NV.AGR.TOTL.ZS', 'SL.AGR.EMPL.ZS'],
  Industry: ['NV.IND.TOTL.ZS', 'SL.IND.EMPL.ZS'],
  Services: ['NV.SRV.TOTL.ZS', 'SL.SRV.EMPL.ZS'],
} as const;
export type Sector = keyof typeof SECTORS;
export const SECTOR_NAMES = Object.keys(SECTORS) as Sector[];

export type Series = Record<string, Record<string, [number, number][]>>;

export const valueAt = (series: Series, code: string, iso: string, year: number): number | null => {
  const s = series[code]?.[iso];
  const hit = s?.find(([y]) => y === year);
  return hit ? hit[1] : null;
};

export interface SectorRow {
  sector: Sector;
  va: number | null;
  emp: number | null;
  gap: number | null;
  rlp: number | null;
  vaRescaled: number | null;
  rlpRescaled: number | null;
}

export function snapshot(series: Series, iso: string, year: number) {
  const rows = SECTOR_NAMES.map((sector) => {
    const [vc, ec] = SECTORS[sector];
    return { sector, va: valueAt(series, vc, iso, year), emp: valueAt(series, ec, iso, year) };
  });
  const vaSum = rows.every((r) => r.va !== null) ? rows.reduce((s, r) => s + (r.va as number), 0) : null;
  const empSum = rows.every((r) => r.emp !== null) ? rows.reduce((s, r) => s + (r.emp as number), 0) : null;
  const out: SectorRow[] = rows.map((r) => {
    const resc = r.va !== null && vaSum ? (100 * r.va) / vaSum : null;
    const ok = (a: number | null, b: number | null) => (a !== null && b !== null && b > 0 ? a / b : null);
    return {
      ...r,
      gap: r.va !== null && r.emp !== null ? r.va - r.emp : null,
      rlp: ok(r.va, r.emp),
      vaRescaled: resc,
      rlpRescaled: ok(resc, r.emp),
    };
  });
  return { rows: out, vaSum, empSum, vaResidual: vaSum !== null ? 100 - vaSum : null };
}

/** Years in which a country has all three VA and all three employment shares. */
export function completeYears(series: Series, iso: string): number[] {
  const years = new Set<number>();
  for (const [vc] of Object.values(SECTORS)) for (const [y] of series[vc]?.[iso] ?? []) years.add(y);
  return [...years]
    .filter((y) => {
      const s = snapshot(series, iso, y);
      return s.vaSum !== null && s.empSum !== null && s.rows.every((r) => r.rlp !== null);
    })
    .sort((a, b) => a - b);
}

export function weightedRlp(rows: readonly SectorRow[], rescaled = false): number {
  const col = rescaled ? 'rlpRescaled' : 'rlp';
  if (rows.some((r) => r[col] === null || r.emp === null)) return NaN;
  return rows.reduce((s, r) => s + (r[col] as number) * (r.emp as number), 0) / 100;
}
