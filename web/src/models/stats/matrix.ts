/** Small dense-matrix helpers for regression (k is always tiny here). */

export type Matrix = number[][];

export const transpose = (a: Matrix): Matrix => a[0].map((_, j) => a.map((row) => row[j]));

export function matMul(a: Matrix, b: Matrix): Matrix {
  const n = a.length;
  const m = b[0].length;
  const k = b.length;
  const out: Matrix = Array.from({ length: n }, () => new Array<number>(m).fill(0));
  for (let i = 0; i < n; i++)
    for (let p = 0; p < k; p++) {
      const v = a[i][p];
      if (v === 0) continue;
      for (let j = 0; j < m; j++) out[i][j] += v * b[p][j];
    }
  return out;
}

export const matVec = (a: Matrix, v: readonly number[]): number[] =>
  a.map((row) => row.reduce((s, x, j) => s + x * v[j], 0));

/** Inverse by Gauss–Jordan with partial pivoting; null when singular. */
export function inverse(a: Matrix): Matrix | null {
  const n = a.length;
  const m = a.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  const scale = Math.max(1e-300, ...a.flat().map(Math.abs));
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(m[r][c]) > Math.abs(m[p][c])) p = r;
    if (Math.abs(m[p][c]) < 1e-12 * scale) return null;
    [m[c], m[p]] = [m[p], m[c]];
    const piv = m[c][c];
    for (let j = 0; j < 2 * n; j++) m[c][j] /= piv;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = m[r][c];
      if (f === 0) continue;
      for (let j = 0; j < 2 * n; j++) m[r][j] -= f * m[c][j];
    }
  }
  return m.map((row) => row.slice(n));
}

/** Numerical rank via Gaussian elimination on a column-scaled copy. */
export function rank(a: Matrix): number {
  const rows = a.length;
  const cols = a[0]?.length ?? 0;
  const norms = Array.from({ length: cols }, (_, j) => Math.sqrt(a.reduce((s, r) => s + r[j] ** 2, 0)) || 1);
  const m = a.map((r) => r.map((v, j) => v / norms[j]));
  let rk = 0;
  for (let c = 0; c < cols && rk < rows; c++) {
    let p = rk;
    for (let r = rk + 1; r < rows; r++) if (Math.abs(m[r][c]) > Math.abs(m[p][c])) p = r;
    if (Math.abs(m[p][c]) < 1e-10) continue;
    [m[rk], m[p]] = [m[p], m[rk]];
    for (let r = rk + 1; r < rows; r++) {
      const f = m[r][c] / m[rk][c];
      for (let j = c; j < cols; j++) m[r][j] -= f * m[rk][j];
    }
    rk++;
  }
  return rk;
}
