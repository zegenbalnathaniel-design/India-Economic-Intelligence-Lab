/**
 * Macro transmission chains, ported from analysis/transmission.py. Linear,
 * partial-equilibrium arithmetic: each link multiplies a shock by cited
 * coefficients. Link metadata (labels, equations, assumptions) is exported
 * from the Python; only the arithmetic lives here.
 */

export const QUANTIFIED = 'quantified';
export const NEEDS_PARAMETER = 'needs parameter';
export const QUALITATIVE = 'qualitative';
export const NOT_APPLICABLE = 'not applied in this regime';
export type Status = typeof QUANTIFIED | typeof NEEDS_PARAMETER | typeof QUALITATIVE | typeof NOT_APPLICABLE;

export interface Link {
  scenario: string;
  id: string;
  source: string;
  target: string;
  label: string;
  unit: string;
  horizon: string;
  params: string[];
  equation: string;
  assumptions: string[];
  regime: string | null;
}

export type Params = Record<string, number | null | undefined>;

export interface Result {
  link: Link;
  value: number | null;
  status: Status;
  missing: string[];
}

const get = (p: Params, k: string): number | null => {
  const v = p[k];
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
};

export function tradeBalanceChange(deprPct: number, exportsGdp: number, importsGdp: number, epsX: number, epsM: number) {
  const d = deprPct / 100;
  return d * (exportsGdp * epsX - importsGdp * (1 - epsM));
}

export function marshallLerner(epsX: number | null, epsM: number | null): boolean | null {
  if (epsX === null || epsM === null) return null;
  return Math.abs(epsX) + Math.abs(epsM) > 1;
}

function compute(link: Link, s: number, p: Params): number {
  const g = (k: string) => get(p, k) as number;
  switch (link.scenario) {
    case 'policy': {
      const r = s / 100;
      switch (link.id) {
        case 'walr_fresh':
          return g('repo_to_walr_fresh') * r;
        case 'walr_outstanding':
          return g('repo_to_walr_outstanding') * r;
        case 'credit_growth':
          return g('repo_to_credit_growth') * r;
        case 'investment_rate':
          return g('real_rate_to_investment_rate') * g('repo_to_walr_fresh') * r;
        case 'gdp_growth':
          return g('real_rate_to_gdp_growth') * g('repo_to_walr_fresh') * r;
        case 'cpi':
          return g('policy_to_cpi_cumulative') * r;
      }
      break;
    }
    case 'oil': {
      if (link.id === 'import_bill_mech') return (g('oil_import_share_gdp') * s) / 100;
      if (link.id === 'cpi') return ((g('oil_cpi_bps_per_10pct') / 100) * s) / 10;
      if (link.id === 'gdp_growth') return ((g('oil_gdp_growth_bps_per_10pct') / 100) * s) / 10;
      const dUsd = (g('baseline_crude_usd') * s) / 100;
      if (link.id === 'cad') return (g('oil_cad_pct_gdp_per_10usd') * dUsd) / 10;
      if (link.id === 'cad_usd') return (g('oil_cad_usd_bn_per_10usd') * dUsd) / 10;
      if (link.id === 'fiscal') return (g('oil_fiscal_pct_gdp_per_10usd') * dUsd) / 10;
      break;
    }
    case 'rupee': {
      if (link.id === 'import_prices') return s;
      if (link.id === 'cpi') return ((g('inr_cpi_bps_per_5pct_depr') / 100) * s) / 5;
      if (link.id === 'gdp_growth') return ((g('inr_gdp_bps_per_5pct_depr') / 100) * s) / 5;
      if (link.id === 'trade_balance_sr' || link.id === 'trade_balance_lr') {
        const h = link.id.endsWith('sr') ? 'sr' : 'lr';
        return tradeBalanceChange(s, g('exports_gdp'), g('imports_gdp'), g(`export_price_elasticity_${h}`), g(`import_price_elasticity_${h}`));
      }
      break;
    }
    case 'capex': {
      if (link.id === 'demand') return g('capex_multiplier') * s;
      if (link.id === 'deficit_gross') return s;
      if (link.id === 'deficit_net') return s - (g('revenue_gdp_ratio') / 100) * g('capex_multiplier') * s;
      break;
    }
  }
  throw new Error(`unknown link ${link.scenario}.${link.id}`);
}

export function run(links: readonly Link[], shock: number, params: Params, regime: string): Result[] {
  return links.map((link) => {
    if (link.regime && link.regime !== regime) return { link, value: null, status: NOT_APPLICABLE, missing: [] };
    const missing = link.params.filter((k) => get(params, k) === null);
    if (missing.length) return { link, value: null, status: NEEDS_PARAMETER, missing };
    return { link, value: compute(link, shock, params) + 0, status: QUANTIFIED, missing: [] };
  });
}

export function formatValue(value: number | null, status: Status, unit: string): string {
  if (status === NEEDS_PARAMETER) return 'needs parameter';
  if (status === NOT_APPLICABLE) return 'not applied';
  if (value === null) return '—';
  const v = `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
  if (unit === '%') return `${v}%`;
  return `${v} ${unit}`;
}

/** Diagram edges: quantified links (best status per pair) plus the scenario's qualitative links. */
export function diagramEdges(results: readonly Result[], qualitative: readonly (readonly string[])[]) {
  const rank: Record<string, number> = { [QUANTIFIED]: 0, [NEEDS_PARAMETER]: 1, [NOT_APPLICABLE]: 2, [QUALITATIVE]: 3 };
  const edges = new Map<string, { source: string; target: string; status: Status; label: string; value: number | null; unit: string }>();
  for (const r of results) {
    const key = `${r.link.source}→${r.link.target}`;
    const e = { source: r.link.source, target: r.link.target, status: r.status, label: r.link.label, value: r.value, unit: r.link.unit };
    if (!edges.has(key) || rank[r.status] < rank[edges.get(key)!.status]) edges.set(key, e);
  }
  for (const [src, tgt, why] of qualitative) {
    const key = `${src}→${tgt}`;
    if (!edges.has(key)) edges.set(key, { source: src, target: tgt, status: QUALITATIVE, label: why, value: null, unit: '' });
  }
  return [...edges.values()];
}
