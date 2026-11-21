/**
 * Number presentation. Indian digit grouping throughout (₹30,00,000 rather
 * than ₹3,000,000), tabular figures, and explicit handling of null so a
 * missing value can never render as a zero.
 */

const inr0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const inr2 = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const MISSING = '—';

/** ₹30,00,000 — Indian grouping, no decimals. */
export function rupees(value: number | null | undefined, opts?: { decimals?: boolean }): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  const n = opts?.decimals ? inr2.format(value) : inr0.format(Math.round(value));
  return `₹${n}`;
}

/** Compact rupees for dense tiles: ₹76.5 L, ₹1.24 Cr. */
export function rupeesCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  const abs = Math.abs(value);
  if (abs >= 1e7) return `₹${(value / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(value / 1e5).toFixed(2)} L`;
  if (abs >= 1e3) return `₹${inr0.format(Math.round(value))}`;
  return `₹${value.toFixed(0)}`;
}

/** Axis-scale rupees: 30L, 1.2Cr — shortest legible form. */
export function rupeesAxis(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e7) return `₹${(value / 1e7).toFixed(abs >= 1e8 ? 0 : 1)}Cr`;
  if (abs >= 1e5) return `₹${(value / 1e5).toFixed(0)}L`;
  if (abs >= 1e3) return `₹${(value / 1e3).toFixed(0)}k`;
  return `₹${value.toFixed(0)}`;
}

export function percent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  return `${value.toFixed(decimals)}%`;
}

/** A decimal fraction shown as a percentage: 0.0581 → "5.81%". */
export function fractionAsPercent(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  return `${(value * 100).toFixed(decimals)}%`;
}

export function signed(value: number | null | undefined, decimals = 1, suffix = ''): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  const s = value.toFixed(decimals);
  return `${value > 0 ? '+' : ''}${s}${suffix}`;
}

export function number(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  return value.toFixed(decimals);
}

export function multiple(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  return `${value.toFixed(2)}×`;
}

/** 24 September 2026 — never ambiguous between day-first and month-first. */
export function longDate(iso: string | undefined): string {
  if (!iso) return MISSING;
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}

export function shortDate(iso: string | undefined): string {
  if (!iso) return MISSING;
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

/** Clamp with NaN protection, used by every slider binding. */
export function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export const cn = (...parts: (string | false | null | undefined)[]): string =>
  parts.filter(Boolean).join(' ');

/**
 * Render an indicator's value the way its publisher quotes it. Decimal
 * places come from the record rather than from the magnitude, and values
 * of a thousand or more get Indian digit grouping.
 */
export function indicatorValue(
  value: number | null | undefined,
  decimals: number | undefined,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return MISSING;
  const dp = decimals ?? (Number.isInteger(value) ? 0 : 2);
  const grouped = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
  return grouped.format(value);
}
