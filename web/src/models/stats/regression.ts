/**
 * Correlation and OLS, ported from analysis/relationships.py,
 * analysis/convergence.py and analysis/econometrics.py.
 *
 * Conventions match the Python (statsmodels `use_t=True`): every standard-error
 * type uses Student-t p-values and intervals on n − k − 1 degrees of freedom;
 * HC1 scales the sandwich by n / (n − k − 1); HAC is Newey–West with a Bartlett
 * kernel and no small-sample correction; with a robust covariance the overall
 * F is the corresponding Wald test.
 */
import { chi2Sf, fSf, normPpf, tPValue, tPpf } from './dist';
import { mean, rankAverage, sd, sum } from './describe';
import { inverse, matMul, matVec, rank, transpose, type Matrix } from './matrix';

export const MIN_OBS = 3;
export const ALPHA = 0.05;
export const WEAK_BELOW = 0.3;
export const STRONG_FROM = 0.6;
export const EXACT_SPEARMAN_MAX_N = 8;

// ---------------------------------------------------------------------------
// Correlation
// ---------------------------------------------------------------------------

export interface Corr {
  r: number;
  p: number;
}

function pearsonRaw(x: readonly number[], y: readonly number[]): number {
  const mx = mean(x);
  const my = mean(y);
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < x.length; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

const corrP = (r: number, n: number): number => {
  if (Math.abs(r) >= 1) return 0;
  const t = r * Math.sqrt((n - 2) / (1 - r * r));
  return tPValue(t, n - 2);
};

const degenerate = (x: readonly number[], y: readonly number[]) =>
  x.length < MIN_OBS || sd(x) === 0 || sd(y) === 0;

export function pearson(x: readonly number[], y: readonly number[]): Corr {
  if (degenerate(x, y)) return { r: NaN, p: NaN };
  const r = pearsonRaw(x, y);
  return { r, p: corrP(r, x.length) };
}

function permutations(n: number): number[][] {
  const out: number[][] = [];
  const a = Array.from({ length: n }, (_, i) => i);
  const c = new Array<number>(n).fill(0);
  out.push([...a]);
  let i = 0;
  while (i < n) {
    if (c[i] < i) {
      const j = i % 2 === 0 ? 0 : c[i];
      [a[j], a[i]] = [a[i], a[j]];
      out.push([...a]);
      c[i]++;
      i = 0;
    } else {
      c[i] = 0;
      i++;
    }
  }
  return out;
}

/** Exact two-sided permutation p-value for Spearman's rho (n ≤ 8). */
export function spearmanExactP(x: readonly number[], y: readonly number[]): number {
  const n = x.length;
  const rx = rankAverage(x).map((r) => r - (n + 1) / 2);
  const ry = rankAverage(y);
  const sxx = sum(rx.map((v) => v * v));
  const myr = mean(ry);
  const obs = Math.abs(sum(rx.map((v, i) => v * (ry[i] - myr))) / Math.sqrt(sxx * sum(ry.map((v) => (v - myr) ** 2))));
  let hits = 0;
  const perms = permutations(n);
  for (const perm of perms) {
    const py = perm.map((i) => ry[i]);
    const m = mean(py);
    const num = sum(rx.map((v, i) => v * (py[i] - m)));
    const rho = num / Math.sqrt(sxx * sum(py.map((v) => (v - m) ** 2)));
    if (Math.abs(rho) >= obs - 1e-12) hits++;
  }
  return hits / perms.length;
}

export function spearman(x: readonly number[], y: readonly number[], exactSmall = true): Corr {
  if (degenerate(x, y)) return { r: NaN, p: NaN };
  const rx = rankAverage(x);
  const ry = rankAverage(y);
  const r = pearsonRaw(rx, ry);
  const p = exactSmall && x.length <= EXACT_SPEARMAN_MAX_N ? spearmanExactP(x, y) : corrP(r, x.length);
  return { r, p };
}

export interface CorrelationSummary {
  pearson: Corr;
  spearman: Corr;
  n: number;
}

export function correlations(x: readonly number[], y: readonly number[]): CorrelationSummary {
  return { pearson: pearson(x, y), spearman: spearman(x, y), n: x.length };
}

export function classifyStrength(rho: number): 'weak' | 'moderate' | 'strong' | 'undetermined' {
  if (!Number.isFinite(rho)) return 'undetermined';
  const a = Math.abs(rho);
  return a < WEAK_BELOW ? 'weak' : a < STRONG_FROM ? 'moderate' : 'strong';
}

export function verdictLabel(rho: number, p: number): { label: string; significant: boolean } {
  const s = classifyStrength(rho);
  if (s === 'undetermined') return { label: 'Not computable', significant: false };
  const dir = rho > 0 ? 'positive' : rho < 0 ? 'negative' : 'no';
  const label = dir === 'no' ? 'No monotone association' : `${s[0].toUpperCase()}${s.slice(1)} ${dir} association`;
  return { label, significant: Number.isFinite(p) && p < ALPHA };
}

export const formatP = (p: number) => (!Number.isFinite(p) ? 'p n/a' : p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`);

/** Correlation of x_t with y_{t+k}; positive k = X leads Y. */
export function laggedCorrelation(
  x: readonly number[],
  y: readonly number[],
  lags: readonly number[],
  method: 'pearson' | 'spearman' = 'pearson',
) {
  return lags.map((k) => {
    const xs: number[] = [];
    const ys: number[] = [];
    for (let i = 0; i < x.length; i++) {
      const j = i + k;
      if (j < 0 || j >= y.length) continue;
      xs.push(x[i]);
      ys.push(y[j]);
    }
    const c = method === 'pearson' ? pearson(xs, ys) : spearman(xs, ys, false);
    return { lag: k, r: c.r, p: c.p, n: xs.length };
  });
}

export function rollingCorrelation(
  keys: readonly (string | number)[],
  x: readonly number[],
  y: readonly number[],
  window: number,
  method: 'pearson' | 'spearman' = 'pearson',
) {
  const out: { key: string | number; start: string | number; r: number }[] = [];
  for (let end = window - 1; end < x.length; end++) {
    const xs = x.slice(end - window + 1, end + 1);
    const ys = y.slice(end - window + 1, end + 1);
    const c = method === 'pearson' ? pearson(xs, ys) : spearman(xs, ys, false);
    out.push({ key: keys[end], start: keys[end - window + 1], r: c.r });
  }
  return out;
}

// ---------------------------------------------------------------------------
// Transforms
// ---------------------------------------------------------------------------

export type Transform = 'none' | 'log' | 'zscore' | 'pct_change' | 'diff';

export function availableTransforms(values: readonly number[], timeSeries: boolean): Transform[] {
  const out: Transform[] = ['none'];
  const positive = values.length > 0 && values.every((v) => v > 0);
  if (positive) out.push('log');
  if (values.length >= 2 && sd(values) > 0) out.push('zscore');
  if (timeSeries && positive && values.length >= 2) out.push('pct_change');
  return out;
}

/** Row-wise transforms (log, pct_change, diff); z-score is applied after alignment. */
export function applyRowTransform(values: readonly number[], kind: Transform): number[] {
  if (kind === 'log') return values.map(Math.log);
  if (kind === 'pct_change') return values.map((v, i) => (i === 0 ? NaN : (v / values[i - 1] - 1) * 100));
  if (kind === 'diff') return values.map((v, i) => (i === 0 ? NaN : v - values[i - 1]));
  return [...values];
}

export function zscore(values: readonly number[]): number[] {
  const m = mean(values);
  const s = sd(values, 1);
  return values.map((v) => (v - m) / s);
}

export const TRANSFORM_LABEL: Record<Transform, string> = {
  none: 'level',
  log: 'log',
  zscore: 'z-score',
  pct_change: '% change',
  diff: 'first difference',
};

// ---------------------------------------------------------------------------
// OLS
// ---------------------------------------------------------------------------

export type SeType = 'nonrobust' | 'HC1' | 'HAC';

export const SE_LABELS: Record<SeType, string> = {
  nonrobust: 'Classical (homoskedastic)',
  HC1: 'HC1 heteroskedasticity-robust',
  HAC: 'Newey–West HAC',
};

export interface OLSTerm {
  term: string;
  coef: number;
  se: number;
  t: number;
  p: number;
  ciLow: number;
  ciHigh: number;
}

export interface OLSFit {
  terms: OLSTerm[];
  n: number;
  k: number;
  dfResid: number;
  r2: number;
  adjR2: number;
  f: number;
  fP: number;
  seType: SeType;
  hacLags: number | null;
  fitted: number[];
  residuals: number[];
  exog: Matrix;
  y: number[];
  residualSE: number;
}

export class ModelError extends Error {}

/** L = ⌊4·(n/100)^(2/9)⌋, minimum 1. */
export const neweyWestLags = (n: number) => Math.max(1, Math.floor(4 * (n / 100) ** (2 / 9)));

/**
 * OLS of y on the columns of `xs` plus an intercept. `names` labels the
 * regressors. Throws ModelError where the Python raises it.
 */
export function fitOLS(
  y: readonly number[],
  xs: readonly (readonly number[])[],
  names: readonly string[],
  seType: SeType = 'nonrobust',
  hacLags?: number,
  ciLevel = 0.95,
): OLSFit {
  const n = y.length;
  const k = xs.length;
  if (!k) throw new ModelError('choose at least one explanatory variable.');
  if (n < k + 2)
    throw new ModelError(
      `only ${n} observations for ${k} regressor(s) plus an intercept — at least ${k + 2} are needed to leave one residual degree of freedom.`,
    );
  xs.forEach((col, j) => {
    if (sd(col) === 0) throw new ModelError(`${names[j]} is constant in this sample, so its coefficient is not identified.`);
  });
  const X: Matrix = Array.from({ length: n }, (_, i) => [1, ...xs.map((c) => c[i])]);
  if (rank(X) < k + 1)
    throw new ModelError(
      'perfect multicollinearity: at least one explanatory variable is an exact linear combination of the others (e.g. group shares that add up to 100%), so the coefficients are not separately identified.',
    );
  const Xt = transpose(X);
  const xtxInv = inverse(matMul(Xt, X));
  if (!xtxInv) throw new ModelError('the design matrix is singular.');
  const beta = matVec(xtxInv, matVec(Xt, y));
  const fitted = matVec(X, beta);
  const resid = y.map((v, i) => v - fitted[i]);
  const df = n - k - 1;
  const ssr = sum(resid.map((e) => e * e));
  const my = mean(y);
  const sst = sum(y.map((v) => (v - my) ** 2));
  const r2 = sst > 0 ? 1 - ssr / sst : NaN;
  const adjR2 = 1 - ((1 - r2) * (n - 1)) / df;

  let cov: Matrix;
  let lags: number | null = null;
  if (seType === 'nonrobust') {
    cov = xtxInv.map((row) => row.map((v) => (v * ssr) / df));
  } else {
    const p = k + 1;
    const S: Matrix = Array.from({ length: p }, () => new Array<number>(p).fill(0));
    const add = (i: number, j: number, w: number) => {
      for (let a = 0; a < p; a++)
        for (let b = 0; b < p; b++) S[a][b] += w * resid[i] * resid[j] * X[i][a] * X[j][b];
    };
    for (let i = 0; i < n; i++) add(i, i, 1);
    if (seType === 'HAC') {
      lags = hacLags ?? neweyWestLags(n);
      for (let l = 1; l <= lags; l++) {
        const w = 1 - l / (lags + 1);
        for (let t = l; t < n; t++) {
          add(t, t - l, w);
          add(t - l, t, w);
        }
      }
    }
    cov = matMul(matMul(xtxInv, S), xtxInv);
    if (seType === 'HC1') cov = cov.map((row) => row.map((v) => (v * n) / df));
  }

  const q = tPpf(0.5 + ciLevel / 2, df);
  const termNames = ['const', ...names];
  const terms = beta.map((b, j) => {
    const se = Math.sqrt(cov[j][j]);
    const t = se > 0 ? b / se : NaN;
    return { term: termNames[j], coef: b, se, t, p: tPValue(t, df), ciLow: b - q * se, ciHigh: b + q * se };
  });

  let f: number;
  if (seType === 'nonrobust') {
    f = r2 / k / ((1 - r2) / df);
  } else {
    const idx = Array.from({ length: k }, (_, i) => i + 1);
    const Vs = idx.map((a) => idx.map((b) => cov[a][b]));
    const inv = inverse(Vs);
    const bs = idx.map((i) => beta[i]);
    f = inv ? sum(bs.map((v, i) => v * sum(inv[i].map((w, j) => w * bs[j])))) / k : NaN;
  }

  return {
    terms,
    n,
    k,
    dfResid: df,
    r2,
    adjR2,
    f,
    fP: fSf(f, k, df),
    seType,
    hacLags: lags,
    fitted,
    residuals: resid,
    exog: X,
    y: [...y],
    residualSE: Math.sqrt(ssr / df),
  };
}

/** Simple y = a + b·x fit, as used by the σ/β convergence and the scatter plots. */
export function simpleOLS(x: readonly number[], y: readonly number[], seType: SeType = 'nonrobust') {
  const fit = fitOLS(y, [x], ['x'], seType);
  const b = fit.terms[1];
  const a = fit.terms[0];
  return {
    slope: b.coef,
    intercept: a.coef,
    se: b.se,
    t: b.t,
    p: b.p,
    ciLow: b.ciLow,
    ciHigh: b.ciHigh,
    r2: fit.r2,
    n: fit.n,
    fit,
  };
}

export function trySimpleOLS(x: readonly number[], y: readonly number[], seType: SeType = 'nonrobust') {
  try {
    return simpleOLS(x, y, seType);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

export interface Diagnostic {
  test: string;
  purpose: string;
  statistic: number;
  p: number;
  verdict: string;
  interpretation: string;
  detail: string;
}

/** Breusch–Pagan (Koenker studentised LM = n·R² of e² on the regressors). */
export function breuschPagan(fit: OLSFit, crossSection = true): Diagnostic {
  const e2 = fit.residuals.map((e) => e * e);
  const aux = fitOLS(
    e2,
    Array.from({ length: fit.k }, (_, j) => fit.exog.map((r) => r[j + 1])),
    Array.from({ length: fit.k }, (_, j) => `x${j}`),
  );
  const lm = fit.n * aux.r2;
  const p = chi2Sf(lm, fit.k);
  const fix = crossSection ? 'HC1 robust standard errors' : 'Newey–West HAC standard errors';
  const bad = p < ALPHA;
  return {
    test: 'Breusch–Pagan',
    purpose: 'heteroskedasticity',
    statistic: lm,
    p,
    verdict: bad ? 'Heteroskedasticity detected' : 'No evidence of heteroskedasticity',
    interpretation: bad
      ? `The residual spread changes systematically with the regressors (${formatP(p)}). Coefficients are still unbiased under the other assumptions, but classical standard errors are unreliable — use ${fix}.`
      : `No evidence at the 5% level that the residual spread depends on the regressors (${formatP(p)}). With n = ${fit.n} the test has limited power, so this is absence of evidence, not proof of constant variance.`,
    detail: `LM statistic, χ²(${fit.k})`,
  };
}

export function jarqueBera(fit: OLSFit): Diagnostic {
  const e = fit.residuals;
  const n = e.length;
  const m = mean(e);
  const m2 = sum(e.map((v) => (v - m) ** 2)) / n;
  const skew = sum(e.map((v) => (v - m) ** 3)) / n / m2 ** 1.5;
  const kurt = sum(e.map((v) => (v - m) ** 4)) / n / m2 ** 2;
  const jb = (n / 6) * (skew ** 2 + (kurt - 3) ** 2 / 4);
  const p = chi2Sf(jb, 2);
  const small =
    n < 30
      ? ` With n = ${n} (< 30) the chi-square approximation is rough and its power is low; read the QQ plot alongside it.`
      : '';
  const bad = p < ALPHA;
  return {
    test: 'Jarque–Bera',
    purpose: 'normality of residuals',
    statistic: jb,
    p,
    verdict: bad ? 'Residuals not normal' : 'No evidence against normality',
    interpretation:
      (bad
        ? `Residuals depart from normality (skewness ${skew.toFixed(2)}, kurtosis ${kurt.toFixed(2)}; ${formatP(p)}). In small samples t- and F-based p-values may be inaccurate; outliers are a common cause.`
        : `No evidence at the 5% level against normal residuals (skewness ${skew.toFixed(2)}, kurtosis ${kurt.toFixed(2)}; ${formatP(p)}).`) +
      small,
    detail: `skewness ${skew.toFixed(3)}, kurtosis ${kurt.toFixed(3)}`,
  };
}

export function durbinWatson(fit: OLSFit): Diagnostic {
  const e = fit.residuals;
  let num = 0;
  for (let i = 1; i < e.length; i++) num += (e[i] - e[i - 1]) ** 2;
  const dw = num / sum(e.map((v) => v * v));
  const verdict = dw < 1.5 ? 'Positive autocorrelation likely' : dw > 2.5 ? 'Negative autocorrelation likely' : 'No strong first-order autocorrelation';
  const text =
    dw < 1.5
      ? `DW = ${dw.toFixed(2)} is well below 2: residuals in neighbouring periods tend to share a sign. Classical standard errors are then too small — use Newey–West HAC errors, and consider first differences.`
      : dw > 2.5
        ? `DW = ${dw.toFixed(2)} is well above 2: residuals tend to alternate in sign, which often signals over-differencing.`
        : `DW = ${dw.toFixed(2)} is close to 2, consistent with little first-order autocorrelation (rule of thumb: 1.5–2.5).`;
  return { test: 'Durbin–Watson', purpose: 'first-order serial correlation', statistic: dw, p: NaN, verdict, interpretation: text, detail: 'rule of thumb; no p-value' };
}

/** Variance inflation factor per regressor: 1 / (1 − R²_j). */
export function vif(fit: OLSFit): { term: string; vif: number }[] {
  if (fit.k < 2) return fit.terms.slice(1).map((t) => ({ term: t.term, vif: 1 }));
  return fit.terms.slice(1).map((t, j) => {
    const target = fit.exog.map((r) => r[j + 1]);
    const others = Array.from({ length: fit.k }, (_, i) => i).filter((i) => i !== j);
    const aux = fitOLS(
      target,
      others.map((i) => fit.exog.map((r) => r[i + 1])),
      others.map((i) => `x${i}`),
    );
    return { term: t.term, vif: 1 / (1 - aux.r2) };
  });
}

/** Theoretical vs sample quantiles of standardised residuals. */
export function qqPoints(residuals: readonly number[]): { theo: number; sample: number }[] {
  const n = residuals.length;
  const m = mean(residuals);
  const s = sd(residuals, 1);
  const z = residuals.map((e) => (e - m) / s).sort((a, b) => a - b);
  return z.map((v, i) => ({ theo: normPpf((i + 1 - 0.375) / (n + 0.25)), sample: v }));
}
