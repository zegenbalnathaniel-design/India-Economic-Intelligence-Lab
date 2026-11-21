/**
 * Probability distributions needed by the labs' statistics: Student's t,
 * chi-square, F and the normal. Pure functions, no dependencies.
 *
 * The special functions are the standard numerical recipes (Lanczos log-gamma,
 * Lentz continued fraction for the incomplete beta, series / continued
 * fraction for the incomplete gamma). Tests pin them to scipy.stats values.
 */

const LANCZOS = [
  676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059, 12.507343278686905,
  -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
];

export function lnGamma(z: number): number {
  if (z < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * z))) - lnGamma(1 - z);
  const x0 = z - 1;
  let a = 0.99999999999980993;
  const t = x0 + 7.5;
  for (let i = 0; i < LANCZOS.length; i++) a += LANCZOS[i] / (x0 + i + 1);
  return 0.5 * Math.log(2 * Math.PI) + (x0 + 0.5) * Math.log(t) - t + Math.log(a);
}

function betaContinuedFraction(a: number, b: number, x: number): number {
  const TINY = 1e-300;
  const qab = a + b;
  const qap = a + 1;
  const qam = a - 1;
  let c = 1;
  let d = 1 - (qab * x) / qap;
  if (Math.abs(d) < TINY) d = TINY;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 500; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < TINY) d = TINY;
    c = 1 + aa / c;
    if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d;
    h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < TINY) d = TINY;
    c = 1 + aa / c;
    if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 1e-15) break;
  }
  return h;
}

/** Regularised incomplete beta I_x(a, b). */
export function incompleteBeta(x: number, a: number, b: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const lbt = lnGamma(a + b) - lnGamma(a) - lnGamma(b) + a * Math.log(x) + b * Math.log(1 - x);
  const bt = Math.exp(lbt);
  if (x < (a + 1) / (a + b + 2)) return (bt * betaContinuedFraction(a, b, x)) / a;
  return 1 - (bt * betaContinuedFraction(b, a, 1 - x)) / b;
}

/** Regularised upper incomplete gamma Q(s, x). */
export function upperGamma(s: number, x: number): number {
  if (x <= 0) return 1;
  const gln = lnGamma(s);
  if (x < s + 1) {
    let sum = 1 / s;
    let del = sum;
    let ap = s;
    for (let n = 0; n < 1000; n++) {
      ap += 1;
      del *= x / ap;
      sum += del;
      if (Math.abs(del) < Math.abs(sum) * 1e-16) break;
    }
    return 1 - sum * Math.exp(-x + s * Math.log(x) - gln);
  }
  const TINY = 1e-300;
  let b = x + 1 - s;
  let c = 1 / TINY;
  let d = 1 / b;
  let h = d;
  for (let i = 1; i < 1000; i++) {
    const an = -i * (i - s);
    b += 2;
    d = an * d + b;
    if (Math.abs(d) < TINY) d = TINY;
    c = b + an / c;
    if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 1e-16) break;
  }
  return Math.exp(-x + s * Math.log(x) - gln) * h;
}

/** P(T > t) for Student's t with `df` degrees of freedom. */
export function tSf(t: number, df: number): number {
  if (!Number.isFinite(t)) return t > 0 ? 0 : 1;
  const p = 0.5 * incompleteBeta(df / (df + t * t), df / 2, 0.5);
  return t >= 0 ? p : 1 - p;
}

export function tCdf(t: number, df: number): number {
  return 1 - tSf(t, df);
}

/** Two-sided p-value of a t statistic. */
export function tPValue(t: number, df: number): number {
  if (!Number.isFinite(t)) return Number.isNaN(t) ? NaN : 0;
  return incompleteBeta(df / (df + t * t), df / 2, 0.5);
}

/** Quantile of Student's t (bisection on the CDF; ~1e-12 accuracy). */
export function tPpf(p: number, df: number): number {
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  if (p === 0.5) return 0;
  let lo = -1;
  let hi = 1;
  while (tCdf(lo, df) > p) lo *= 2;
  while (tCdf(hi, df) < p) hi *= 2;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (tCdf(mid, df) < p) lo = mid;
    else hi = mid;
    if (hi - lo < 1e-13) break;
  }
  return (lo + hi) / 2;
}

/** P(X > x), X ~ chi-square(k). */
export function chi2Sf(x: number, k: number): number {
  if (x <= 0) return 1;
  return upperGamma(k / 2, x / 2);
}

/** P(F > f), F ~ F(d1, d2). */
export function fSf(f: number, d1: number, d2: number): number {
  if (!(f > 0)) return 1;
  return incompleteBeta(d2 / (d2 + d1 * f), d2 / 2, d1 / 2);
}

function erf(x: number): number {
  // Abramowitz–Stegun 7.1.26 is too coarse for p-values; use the complementary
  // incomplete gamma identity erf(x) = 1 − Q(1/2, x²).
  const v = 1 - upperGamma(0.5, x * x);
  return x >= 0 ? v : -v;
}

export function normCdf(z: number): number {
  return 0.5 * (1 + erf(z / Math.SQRT2));
}

/** Inverse standard-normal CDF (bisection; used for QQ plots only). */
export function normPpf(p: number): number {
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  let lo = -10;
  let hi = 10;
  for (let i = 0; i < 120; i++) {
    const mid = (lo + hi) / 2;
    if (normCdf(mid) < p) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}
