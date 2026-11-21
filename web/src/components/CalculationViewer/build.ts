import { ASSETS } from '../../data/wealth/assumptions';
import { ASSET_KEYS, type Figure2Result } from '../../models/figure2/types';
import { fractionAsPercent, rupees } from '../../lib/format';

/**
 * Show-your-work for Figure 2. Every line is recomputed from the live
 * result — there is no path by which the displayed working can disagree
 * with the displayed answer.
 */
export function buildCalculationText(r: Figure2Result): string {
  const L: string[] = [];
  L.push('FIGURE 2 — HOUSEHOLD WEALTH ACCUMULATION');
  L.push('India Economics Intelligence Lab');
  L.push('');
  L.push('INPUTS');
  L.push(`  Annual contribution      ${rupees(r.inputs.annualSaving)}`);
  L.push(`  Starting capital         ${rupees(r.inputs.startingCapital)}`);
  L.push(`  Years                    ${r.inputs.years}`);
  L.push(`  Contribution frequency   ${r.inputs.frequency} (${r.periodsPerYear}× per year)`);
  L.push(`  Contribution timing      ${r.inputs.timing} of period`);
  L.push('');
  L.push('PORTFOLIO WEIGHTS AND RETURNS');
  L.push('  Asset            Weight      Return    w × R');
  for (const k of ASSET_KEYS) {
    const w = r.inputs.allocation[k] ?? 0;
    const ret = r.inputs.returns[k] ?? 0;
    L.push(
      `  ${ASSETS[k].label.padEnd(16)} ${fractionAsPercent(w, 1).padStart(7)}  ${fractionAsPercent(ret, 2).padStart(8)}  ${fractionAsPercent(w * ret, 4).padStart(9)}`,
    );
  }
  L.push(`  ${'TOTAL'.padEnd(16)} ${fractionAsPercent(
    ASSET_KEYS.reduce((s, k) => s + (r.inputs.allocation[k] ?? 0), 0),
    1,
  ).padStart(7)}  ${''.padStart(8)}  ${fractionAsPercent(r.portfolioReturn, 4).padStart(9)}`);
  L.push('');
  L.push('WEIGHTED PORTFOLIO RETURN');
  L.push('  R_p = Σ wᵢ Rᵢ');
  L.push(
    `      = ${ASSET_KEYS.map(
      (k) => `${(r.inputs.allocation[k] ?? 0).toFixed(2)}×${((r.inputs.returns[k] ?? 0) * 100).toFixed(2)}%`,
    ).join(' + ')}`,
  );
  L.push(`      = ${fractionAsPercent(r.portfolioReturn, 4)}`);
  L.push('');
  if (r.periodsPerYear > 1) {
    L.push('PER-PERIOD RATE');
    L.push(`  r = (1 + R_p)^(1/${r.periodsPerYear}) − 1 = ${fractionAsPercent(r.periodicRate, 6)}`);
    L.push('');
  }
  L.push('FUTURE VALUE');
  L.push('  FV = C × [ (1 + r)ⁿ − 1 ] / r');
  L.push(
    `     = ${rupees(r.inputs.annualSaving / r.periodsPerYear)} × [ (1 + ${r.periodicRate.toFixed(6)})^${
      r.inputs.years * r.periodsPerYear
    } − 1 ] / ${r.periodicRate.toFixed(6)}`,
  );
  L.push(`     = ${rupees(r.finalValue)}`);
  L.push('');
  L.push('RESULT');
  L.push(`  Total contributed        ${rupees(r.totalContributed)}`);
  L.push(`  Final value              ${rupees(r.finalValue)}`);
  L.push(`  Investment gain          ${rupees(r.investmentGain)}`);
  L.push(`  Wealth multiple          ${r.wealthMultiple.toFixed(2)}×`);
  L.push('');
  L.push('Result is conditional on the assumptions entered by the user.');
  L.push('Returns are assumptions, not observations. Not financial advice.');
  return L.join('\n');
}

export function buildCsv(r: Figure2Result): string {
  const head = ['year', 'portfolio_value_inr', 'total_contributed_inr', 'investment_gain_inr', ...ASSET_KEYS.map((k) => `${k}_inr`)];
  const rows = r.rows.map((row) =>
    [
      row.year,
      row.value.toFixed(2),
      row.contributed.toFixed(2),
      row.gain.toFixed(2),
      ...ASSET_KEYS.map((k) => row.byAsset[k].toFixed(2)),
    ].join(','),
  );
  return [head.join(','), ...rows].join('\n');
}

export function buildScenarioJson(r: Figure2Result): string {
  return JSON.stringify(
    {
      model: 'IEIL Figure 2 — Household Wealth Accumulation',
      generated: new Date().toISOString(),
      inputs: r.inputs,
      derived: {
        portfolioReturn: r.portfolioReturn,
        periodicRate: r.periodicRate,
        periodsPerYear: r.periodsPerYear,
      },
      results: {
        totalContributed: r.totalContributed,
        finalValue: r.finalValue,
        investmentGain: r.investmentGain,
        wealthMultiple: r.wealthMultiple,
      },
      allocationValid: r.validation.valid,
      disclaimer:
        'Result is conditional on the assumptions entered by the user. Returns are assumptions, not observations. Not financial advice.',
    },
    null,
    2,
  );
}
