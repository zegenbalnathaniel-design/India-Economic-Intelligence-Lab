import { motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Callout,
  ChartFrame,
  Controls,
  DataTable,
  Field,
  LabHero,
  LabSection,
  LabShell,
  Range,
  Segmented,
  SERIES,
  Stat,
  StatRow,
  axis,
  fmt,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import INEQ from '../../data/labs/inequality.json';
import W from '../../data/labs/wealth.json';
import { labBySlug } from '../../labs/registry';
import { EASE_OUT } from '../../lib/motion';
import {
  allocationRanking,
  annuityPath,
  compositionEffect,
  equityMix,
  impliedExcessGrowth,
  monteCarlo,
  realReturn,
  singleAsset,
} from '../../models/wealth/engine';

const lab = labBySlug('wealth')!;
const KEYS = W.assetKeys;
const LABEL = W.assetLabels as Record<string, string>;
const LIQ = W.liquidity as Record<string, string>;
const PR = W.paperR as Record<string, number>;
const ASSET_COLOUR: Record<string, string> = {
  property: '#f04a32',
  gold: '#f3c542',
  equities: '#24a6a1',
  gov_bonds: '#4d6ff0',
  bank_deposits: '#8b8d99',
  cash: '#f5f0e6',
};
const PAPER_COLOUR: Record<string, string> = {
  'Listed equity': '#24a6a1',
  'Residential property': '#f04a32',
  Gold: '#f3c542',
  'Typical household portfolio': '#4d6ff0',
  'Bank deposits': '#8b8d99',
};
const fact = (metric: string, period: string) =>
  (INEQ.facts as { metric: string; period: string; value: number }[]).find((f) => f.metric === metric && f.period === period)?.value ?? NaN;
const W95 = fact('Wealth-to-income ratio', '1995');
const W22 = fact('Wealth-to-income ratio', '2022');
const WEALTH_SHARES = INEQ.wealthShares as { year: number; top_1: number }[];

const LADDER = [
  ['CAPABILITY', 'Education, skills, health, freedoms', 'Education, health, networks and institutional access set the ceiling on earnings potential: inequality of capability precedes inequality of income.', true],
  ['EMPLOYMENT', 'Capability put to economic use', 'Formal employment brings stable earnings and access to credit. India’s large informal share limits savings capacity at the bottom.', true],
  ['INCOME', 'A flow — earned, taxed, largely spent', 'Income is a flow. On its own it does not accumulate: two households with identical income can end with very different wealth.', true],
  ['OWNERSHIP', 'Equity, business, property, financial assets', 'The choice to hold assets rather than consume the flow is where inequality begins to compound. Ownership rates vary sharply across the distribution.', false],
  ['WEALTH', 'A compounding, appreciating stock', 'Wealth compounds through returns on capital. What is held matters at least as much as how much is saved — see the simulator below.', false],
  ['ECONOMIC FREEDOM', 'Income independent of labour; optionality', 'A wealth cushion buys the ability to bear risk, invest in education, absorb shocks or start a business.', false],
  ['INTERGENERATIONAL MOBILITY', 'Freedom transmitted across generations', 'Bequests, education spending and networks pass every stage above to the next generation.', false],
] as const;

const inr = (v: number) => fmt.inr(v);
const cr = (v: number) => `₹${(v / 1e7).toFixed(2)} cr`;

export function WealthLab() {
  // B · composition effect
  const [contrib, setContrib] = useState(100000);
  const [years, setYears] = useState(30);
  const [infl, setInfl] = useState(5);
  const [rebal, setRebal] = useState<'on' | 'off'>('on');
  const [alloc, setAlloc] = useState<Record<string, number>>(Object.fromEntries(KEYS.map((k) => [k, Math.round((W.defaultAllocation as Record<string, number>)[k] * 100)])));
  const [rets, setRets] = useState<Record<string, number>>(Object.fromEntries(KEYS.map((k) => [k, +((W.defaultReturns as Record<string, number>)[k] * 100).toFixed(2)])));
  const allocSum = KEYS.reduce((s, k) => s + alloc[k], 0);
  const r = useMemo(() => Object.fromEntries(KEYS.map((k) => [k, rets[k] / 100])), [rets]);
  const comp = useMemo(
    () => (allocSum > 0 ? compositionEffect(contrib, years, alloc, r, KEYS, infl / 100, rebal === 'on') : null),
    [contrib, years, alloc, r, infl, rebal, allocSum],
  );
  const compRows = comp ? comp.years.map((y, i) => ({ year: y, nominal: comp.nominal[i], real: comp.real[i], contributed: comp.contributions[i], ...comp.byAsset[i] })) : [];

  // C · Monte Carlo
  const [paths, setPaths] = useState(2000);
  const [seed, setSeed] = useState(7);
  const [vols, setVols] = useState<Record<string, number>>(Object.fromEntries(KEYS.map((k) => [k, +((W.defaultVolatility as Record<string, number>)[k] * 100).toFixed(1)])));
  const [corrMode, setCorrMode] = useState<'none' | 'uniform'>('none');
  const [rhoAll, setRhoAll] = useState(0.3);
  const [fat, setFat] = useState<'normal' | 'fat'>('normal');
  const [df, setDf] = useState(5);
  const mc = useMemo(() => {
    if (!comp) return { res: null, err: '' };
    try {
      const corr = corrMode === 'uniform' ? KEYS.map((_, i) => KEYS.map((__, j) => (i === j ? 1 : rhoAll))) : null;
      return {
        res: monteCarlo({
          contribution: contrib,
          years,
          alloc,
          rets: r,
          vols: Object.fromEntries(KEYS.map((k) => [k, vols[k] / 100])),
          keys: KEYS,
          inflation: infl / 100,
          paths,
          seed,
          correlation: corr,
          tDf: fat === 'fat' ? df : null,
        }),
        err: '',
      };
    } catch (e) {
      return { res: null, err: e instanceof Error ? e.message : String(e) };
    }
  }, [comp, contrib, years, alloc, r, vols, infl, paths, seed, corrMode, rhoAll, fat, df]);
  const fan = mc.res ? mc.res.bands.map((b, i) => ({ ...b, band90: [b.p05, b.p95], band50: [b.p25, b.p75], det: comp!.nominal[i] })) : [];
  const finalDet = comp?.nominal[years - 1] ?? NaN;
  const shareBelow = mc.res ? mc.res.finalNominal.filter((v) => v < finalDet).length / mc.res.finalNominal.length : NaN;

  // D · single asset
  const single = KEYS.map((k) => ({ key: k, asset: LABEL[k], r: r[k], real: realReturn(r[k], infl / 100), liquidity: LIQ[k], ...singleAsset(contrib, years, r[k], infl / 100) })).sort((a, b) => b.finalNominal - a.finalNominal);

  // E · r − g
  const [rNom, setRNom] = useState(+(PR['Typical household portfolio'] * 100).toFixed(2));
  const [pi, setPi] = useState(6.5);
  const [g, setG] = useState(6.5);
  const rReal = realReturn(rNom / 100, pi / 100);
  const gap = rReal - g / 100;
  const assetGaps = Object.entries(PR).map(([asset, nom]) => ({ asset, real: realReturn(nom, pi / 100) * 100, gap: (realReturn(nom, pi / 100) - g / 100) * 100 }));
  const [horizon, setHorizon] = useState(30);
  const divergence = Array.from({ length: horizon + 1 }, (_, t) => {
    const row: Record<string, number> = { t, Income: 100 * (1 + g / 100) ** t };
    for (const [a, nom] of Object.entries(PR)) row[a] = 100 * (1 + realReturn(nom, pi / 100)) ** t;
    return row;
  });
  const excess = impliedExcessGrowth(W95, W22, 2022 - 1995);

  // F · Figure 2
  const [myEq, setMyEq] = useState(40);
  const [eYears, setEYears] = useState(30);
  const [eInfl, setEInfl] = useState(6.5);
  const fig2 = useMemo(() => {
    const series = ['Listed equity', 'Residential property', 'Gold', 'Typical household portfolio'];
    const paths = Object.fromEntries(series.map((s) => [s, annuityPath(100000, PR[s], 30)]));
    const saving = annuityPath(100000, 0, 30);
    return Array.from({ length: 31 }, (_, t) => ({ t, ...Object.fromEntries(series.map((s) => [s, paths[s][t] / 1e7])), Saving: saving[t] / 1e7 }));
  }, []);
  const ranking = allocationRanking(
    {
      'All listed equity': PR['Listed equity'],
      '75% equity / 25% household mix': equityMix(0.75, PR['Listed equity'], PR['Typical household portfolio']),
      '50% equity / 50% household mix': equityMix(0.5, PR['Listed equity'], PR['Typical household portfolio']),
      [`Your mix: ${myEq}% equity`]: equityMix(myEq / 100, PR['Listed equity'], PR['Typical household portfolio']),
      'Typical household portfolio': PR['Typical household portfolio'],
      'Residential property only': PR['Residential property'],
      'Bank deposits only': PR['Bank deposits'],
    },
    100000,
    eYears,
    eInfl / 100,
  );
  const fig2Check = (W.figure2 as { series: string; nominal_return_pct: number; final_value_crore_stated: number }[]).map((f) => ({
    series: f.series,
    stated: f.final_value_crore_stated,
    computed: annuityPath(100000, f.nominal_return_pct / 100, 30)[30] / 1e7,
  }));

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Wealth is not income saved; it is income <i>turned into ownership</i> and compounded. This lab rebuilds the paper’s
            argument: the ladder from capability to mobility, a simulator for the composition effect, the risk around it, r − g,
            and Figure 2 — what ₹1 lakh a year became in different assets over 1991–2021.
          </>
        }
        stats={[
          { label: 'Equity vs household mix', value: `${(annuityPath(100000, PR['Listed equity'], 30)[30] / annuityPath(100000, PR['Typical household portfolio'], 30)[30]).toFixed(2)}×`, sub: '30 years of ₹1 lakh, paper returns' },
          { label: 'Wealth / income', value: `${W95}× → ${W22}×`, sub: 'India, 1995 → 2022 (WIL)' },
          { label: 'Wealth outgrew income', value: fmt.pct(excess * 100, 1), sub: 'a year, 1995–2022' },
        ]}
        figure={{
          name: 'Riffle',
          label: 'A tray of eight cards, one per population group, from the bottom 10% to the top 0.1%, each with its share of India’s income and wealth.',
          idle: 'Hover a card, or tab in and use the arrow keys.',
          caption: (read) => (!read || read === 'rest' ? null : ((INEQ.riffleCaptions as string[])[parseInt(read, 10) - 1] ?? null)),
        }}
      />

      <LabSection index="A" title="From capability to intergenerational mobility" lede="Figure 1 of the paper, redrawn. Teal rungs are about earning; red rungs are about owning. The dashed line is the binding constraint: rising incomes do not automatically become ownership of productive assets.">
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
          <ol className="grid gap-2">
            {LADDER.map(([title, sub, , earn], i) => (
              <motion.li
                key={title}
                initial={{ opacity: 0, x: -24 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-30px' }}
                transition={{ duration: 0.55, delay: i * 0.08, ease: EASE_OUT }}
              >
                <div className="border px-4 py-3 text-center" style={{ borderColor: earn ? '#24a6a1' : '#f04a32', background: earn ? 'rgba(36,166,161,0.08)' : 'rgba(240,74,50,0.08)' }}>
                  <div className="font-mono text-[12px] tracking-[0.14em]" style={{ color: earn ? '#24a6a1' : '#f04a32' }}>
                    {title}
                  </div>
                  <div className="mt-1 text-[12.5px] text-ink-300">{sub}</div>
                </div>
                {i === 2 ? (
                  <div className="my-3 text-center">
                    <div className="border-t border-dashed border-ink-200/60" />
                    <div className="-mt-2.5 inline-block bg-ink-950 px-3 font-mono text-[11px] text-[#f04a32]">▼ WEAK — income does not turn into ownership</div>
                  </div>
                ) : (
                  i < LADDER.length - 1 && <div className="text-center text-ink-500">▼</div>
                )}
              </motion.li>
            ))}
          </ol>
          <div className="grid content-start gap-3">
            {LADDER.map(([title, , text, earn]) => (
              <div key={title} className="border-l-2 bg-ink-900/50 px-4 py-2.5 text-[13px] leading-relaxed text-ink-300" style={{ borderLeftColor: earn ? '#24a6a1' : '#f04a32' }}>
                <b className="text-ink-50">{title.charAt(0) + title.slice(1).toLowerCase()}.</b> {text}
              </div>
            ))}
          </div>
        </div>
      </LabSection>

      <LabSection index="B" title="Composition-effect simulator" lede="Contribute at the start of each year, split by the target allocation; each asset compounds at its own return; optionally rebalance back to target at year-end. Defaults are illustrative long-run returns, not forecasts — every one is editable.">
        <Controls className="md:grid-cols-4">
          <Range label="Annual contribution" value={contrib} min={10000} max={1000000} step={10000} onChange={setContrib} format={inr} />
          <Range label="Horizon" value={years} min={5} max={50} onChange={setYears} format={(v) => `${v} yrs`} />
          <Range label="Inflation" value={infl} min={0} max={12} step={0.25} onChange={setInfl} format={(v) => `${v.toFixed(2)}%`} />
          <Field label="Annual rebalancing">
            <Segmented value={rebal} onChange={setRebal} options={[{ value: 'on', label: 'Rebalance' }, { value: 'off', label: 'Let it drift' }]} />
          </Field>
        </Controls>
        <div className="mt-4 grid gap-4 border border-white/[0.08] bg-ink-900/50 p-4 md:grid-cols-2">
          <div className="grid gap-3">
            <div className="label">Allocation · {allocSum}% (normalised to 100)</div>
            {KEYS.map((k) => (
              <Range key={k} label={LABEL[k]} value={alloc[k]} min={0} max={100} onChange={(v) => setAlloc({ ...alloc, [k]: v })} format={(v) => `${v}%`} />
            ))}
          </div>
          <div className="grid gap-3">
            <div className="label">Nominal return a year</div>
            {KEYS.map((k) => (
              <Range key={k} label={LABEL[k]} value={rets[k]} min={-2} max={20} step={0.25} onChange={(v) => setRets({ ...rets, [k]: v })} format={(v) => `${v.toFixed(2)}%`} />
            ))}
          </div>
        </div>
        {comp ? (
          <>
            <div className="mt-6">
              <StatRow>
                <Stat label="Final wealth (nominal)" value={cr(comp.nominal[years - 1])} sub={`after ${years} years`} />
                <Stat label="In today’s rupees" value={cr(comp.real[years - 1])} sub={`deflated at ${infl}%`} tone="#f5f0e6" />
                <Stat label="Contributed" value={cr(comp.contributions[years - 1])} sub={`gains ${cr(comp.gains[years - 1])}`} tone="#f5f0e6" />
                <Stat label="Portfolio return" value={fmt.pct(comp.r * 100, 2)} sub={`real ${fmt.pct(comp.rReal * 100, 2)}`} tone="#f5f0e6" />
              </StatRow>
            </div>
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <ChartFrame title="Wealth path" subtitle="nominal, real and the money put in" source="Simulation under the assumptions set on this page — not data.">
                <ResponsiveContainer>
                  <LineChart data={compRows} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                    <CartesianGrid {...grid} />
                    <XAxis dataKey="year" {...axis} />
                    <YAxis {...axis} tickFormatter={(v) => `${(Number(v) / 1e7).toFixed(1)}cr`} width={50} />
                    <Tooltip {...tooltip} formatter={(v) => cr(Number(v))} />
                    <Legend {...legend} />
                    <Line dataKey="nominal" name="Nominal" stroke="var(--accent)" strokeWidth={2.4} dot={false} />
                    <Line dataKey="real" name="Today’s rupees" stroke="#24a6a1" strokeWidth={2} dot={false} />
                    <Line dataKey="contributed" name="Contributed" stroke="#8b8d99" strokeDasharray="5 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartFrame>
              <ChartFrame title="What the wealth is made of" subtitle={rebal === 'on' ? 'rebalanced to target each year' : 'drifting toward the faster-growing assets'}>
                <ResponsiveContainer>
                  <AreaChart data={compRows} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                    <CartesianGrid {...grid} />
                    <XAxis dataKey="year" {...axis} />
                    <YAxis {...axis} tickFormatter={(v) => `${(Number(v) / 1e7).toFixed(1)}cr`} width={50} />
                    <Tooltip {...tooltip} formatter={(v) => cr(Number(v))} />
                    <Legend {...legend} />
                    {KEYS.map((k) => (
                      <Area key={k} dataKey={k} name={LABEL[k]} stackId="1" stroke={ASSET_COLOUR[k]} fill={ASSET_COLOUR[k]} fillOpacity={0.4} />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </ChartFrame>
            </div>
          </>
        ) : (
          <div className="mt-6">
            <Callout tone="warn">Give at least one asset a positive allocation.</Callout>
          </div>
        )}
      </LabSection>

      <LabSection index="C" title="How much does volatility change the picture?" lede="The same portfolio with random annual returns: each asset keeps its mean, gets a volatility you set, and the portfolio is rebalanced each year. Correlations and fat tails are your assumptions — the project holds no Indian asset-return history to estimate them.">
        <Controls className="md:grid-cols-4">
          <Range label="Paths" value={paths} min={200} max={5000} step={100} onChange={setPaths} />
          <Range label="Seed" value={seed} min={1} max={99} onChange={setSeed} />
          <Field label="Correlation between assets">
            <Segmented value={corrMode} onChange={setCorrMode} options={[{ value: 'none', label: 'Independent' }, { value: 'uniform', label: 'Common ρ' }]} />
          </Field>
          <Field label="Shocks">
            <Segmented value={fat} onChange={setFat} options={[{ value: 'normal', label: 'Normal' }, { value: 'fat', label: 'Fat tails (t)' }]} />
          </Field>
          {corrMode === 'uniform' && <Range label="ρ between every pair" value={rhoAll} min={-0.2} max={0.95} step={0.05} onChange={setRhoAll} format={(v) => v.toFixed(2)} />}
          {fat === 'fat' && <Range label="Degrees of freedom (lower = fatter)" value={df} min={3} max={30} onChange={setDf} />}
        </Controls>
        <div className="mt-4 grid grid-cols-2 gap-3 border border-white/[0.08] bg-ink-900/50 p-4 md:grid-cols-6">
          {KEYS.map((k) => (
            <Range key={k} label={`σ · ${LABEL[k]}`} value={vols[k]} min={0} max={40} step={0.5} onChange={(v) => setVols({ ...vols, [k]: v })} format={(v) => `${v}%`} />
          ))}
        </div>
        {mc.err && (
          <div className="mt-4">
            <Callout tone="warn" title="Correlations">{mc.err}</Callout>
          </div>
        )}
        {mc.res && (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_300px]">
            <ChartFrame title={`Fan of ${paths.toLocaleString()} paths`} subtitle="5–95% and 25–75% bands, median, and the deterministic path" source="Simulation under the assumptions set on this page — not data." height={380}>
              <ResponsiveContainer>
                <ComposedChart data={fan} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                  <CartesianGrid {...grid} />
                  <XAxis dataKey="year" {...axis} />
                  <YAxis {...axis} tickFormatter={(v) => `${(Number(v) / 1e7).toFixed(1)}cr`} width={50} />
                  <Tooltip {...tooltip} formatter={(v) => (Array.isArray(v) ? `${cr(v[0])} – ${cr(v[1])}` : cr(Number(v)))} />
                  <Legend {...legend} />
                  <Area dataKey="band90" name="5–95%" stroke="none" fill="var(--accent)" fillOpacity={0.14} />
                  <Area dataKey="band50" name="25–75%" stroke="none" fill="var(--accent)" fillOpacity={0.3} />
                  <Line dataKey="p50" name="Median" stroke="var(--accent)" strokeWidth={2.2} dot={false} />
                  <Line dataKey="det" name="Deterministic" stroke="#f5f0e6" strokeDasharray="5 4" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartFrame>
            <div className="grid content-start gap-3">
              <Stat label="5th percentile" value={cr(mc.res.bands[years - 1].p05)} sub="1 path in 20 ends below this" tone="#f04a32" />
              <Stat label="Median" value={cr(mc.res.bands[years - 1].p50)} />
              <Stat label="95th percentile" value={cr(mc.res.bands[years - 1].p95)} tone="#6fae4f" />
              <Stat label="Below the deterministic path" value={fmt.pct(shareBelow * 100, 0)} sub="volatility drag: compounding punishes swings" tone="#f5f0e6" />
            </div>
          </div>
        )}
      </LabSection>

      <LabSection index="D" title="What if the household held only one asset?" lede={`₹${contrib.toLocaleString('en-IN')} a year for ${years} years, all in one asset, at the returns set in B.`}>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <ChartFrame title="Final wealth by asset" height={300}>
            <ResponsiveContainer>
              <BarChart data={single} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => `${(Number(v) / 1e7).toFixed(1)}cr`} />
                <YAxis type="category" dataKey="asset" {...axis} width={120} />
                <Tooltip {...tooltip} formatter={(v) => cr(Number(v))} />
                <Bar dataKey="finalNominal" name="Nominal">
                  {single.map((s) => (
                    <Cell key={s.key} fill={ASSET_COLOUR[s.key]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <DataTable
            columns={[
              { key: 'asset', label: 'Asset' },
              { key: 'r', label: 'Nominal', align: 'right', format: (v) => fmt.pct((v as number) * 100, 2) },
              { key: 'real', label: 'Real', align: 'right', format: (v) => fmt.pct((v as number) * 100, 2) },
              { key: 'finalNominal', label: 'Final', align: 'right', format: (v) => cr(v as number) },
              { key: 'finalReal', label: 'Today’s ₹', align: 'right', format: (v) => cr(v as number) },
              { key: 'liquidity', label: 'Liquidity' },
            ]}
            rows={single as unknown as Record<string, unknown>[]}
          />
        </div>
      </LabSection>

      <LabSection index="E" title="r − g explorer" lede="Compare the real return on capital with real income growth on the same basis (Fisher-deflated). r > g means wealth already held grows faster than the incomes it is measured against — an identity about rates, not a causal claim about individuals.">
        <Controls>
          <Range label="Nominal return on capital r" value={rNom} min={0} max={20} step={0.1} onChange={setRNom} format={(v) => `${v.toFixed(1)}%`} />
          <Range label="Inflation π" value={pi} min={0} max={15} step={0.25} onChange={setPi} format={(v) => `${v.toFixed(2)}%`} />
          <Range label="Real income growth g" value={g} min={-5} max={15} step={0.25} onChange={setG} format={(v) => `${v.toFixed(2)}%`} />
        </Controls>
        <div className="mt-6">
          <StatRow>
            <Stat label="Real r" value={fmt.pct(rReal * 100, 2)} sub="(1 + r) / (1 + π) − 1" tone="#f5f0e6" />
            <Stat label="g" value={fmt.pct(g, 2)} tone="#f5f0e6" />
            <Stat label="r − g" value={fmt.pp(gap * 100, 2)} sub={gap > 0 ? 'capital outgrows income' : 'income outgrows capital'} tone={gap > 0 ? '#f04a32' : '#6fae4f'} />
            <Stat label="India, 1995–2022" value={`${fmt.pct(excess * 100, 1)} a yr`} sub={`wealth outgrew income: ${W95}× → ${W22}×`} />
          </StatRow>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ChartFrame title="Which assets beat the economy?" subtitle={`real return − g, at π = ${pi}% and g = ${g}%`} source="Author’s paper, Table 1 (returns 1991–2021).">
            <ResponsiveContainer>
              <BarChart data={assetGaps} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} vertical={false} />
                <XAxis dataKey="asset" {...axis} interval={0} tick={{ ...axis.tick, fontSize: 9.5 }} />
                <YAxis {...axis} tickFormatter={(v) => `${v}pp`} width={44} />
                <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                <Tooltip {...tooltip} formatter={(v) => fmt.pp(Number(v), 2)} />
                <Bar dataKey="gap" name="r − g">
                  {assetGaps.map((a) => (
                    <Cell key={a.asset} fill={PAPER_COLOUR[a.asset]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="What a gap does over time" subtitle="₹100 of wealth in each asset vs ₹100 of income, real" actions={<div className="w-40"><Range label="Years" value={horizon} min={5} max={50} onChange={setHorizon} /></div>}>
            <ResponsiveContainer>
              <LineChart data={divergence} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="t" {...axis} />
                <YAxis {...axis} width={44} />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(0)} />
                <Legend {...legend} />
                <Line dataKey="Income" stroke="#f5f0e6" strokeWidth={2.4} strokeDasharray="6 4" dot={false} />
                {Object.keys(PR).map((a) => (
                  <Line key={a} dataKey={a} stroke={PAPER_COLOUR[a]} strokeWidth={1.8} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
        <div className="mt-4">
          <Callout title="What the data show for India as a whole">
            National wealth rose from {W95}× to {W22}× national income between 1995 and 2022 (World Inequality Lab): wealth grew
            about {fmt.pct(excess * 100, 1)} a year faster than income for 27 years. The gains went to whoever held the fast-growing
            assets — the Top 1% wealth share went from {fmt.pct(WEALTH_SHARES.find((w) => w.year === 1991)?.top_1, 1)} (1991) to{' '}
            {fmt.pct(WEALTH_SHARES.find((w) => w.year === 2022)?.top_1, 1)} (2022).
          </Callout>
        </div>
      </LabSection>

      <LabSection index="F" title="Which allocation built the most wealth, 1991–2021?" lede="The paper’s Figure 2, rebuilt: ₹1 lakh saved at the end of every year for 30 years, compounding at each asset’s 1991–2021 return.">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <ChartFrame title="Figure 2 — future value of ₹1 lakh a year" subtitle="₹ crore" source="Author’s paper, Figure 2 (Wahengbam 2023 returns; RBI 2017 asset shares)." height={360}>
            <ResponsiveContainer>
              <LineChart data={fig2} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="t" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => Number(v).toFixed(1)} width={36} />
                <Tooltip {...tooltip} formatter={(v) => `₹${Number(v).toFixed(2)} cr`} />
                <Legend {...legend} />
                {['Listed equity', 'Residential property', 'Gold', 'Typical household portfolio'].map((s) => (
                  <Line key={s} dataKey={s} name={`${s} — ${(PR[s] * 100).toFixed(1)}%`} stroke={PAPER_COLOUR[s]} strokeWidth={2.2} dot={false} />
                ))}
                <Line dataKey="Saving" name="Cumulative saving" stroke="#8b8d99" strokeDasharray="4 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <DataTable
            columns={[
              { key: 'series', label: 'Series' },
              { key: 'stated', label: 'Paper (₹ cr)', align: 'right', format: (v) => (v as number).toFixed(2) },
              { key: 'computed', label: 'Recomputed', align: 'right', format: (v) => (v as number).toFixed(2) },
            ]}
            rows={fig2Check as unknown as Record<string, unknown>[]}
          />
        </div>
        <Controls className="mt-6">
          <Range label="Your mix: share in listed equity" value={myEq} min={0} max={100} step={5} onChange={setMyEq} format={(v) => `${v}%`} />
          <Range label="Years of saving" value={eYears} min={5} max={30} onChange={setEYears} format={(v) => `${v} yrs`} />
          <Range label="Inflation for today’s rupees" value={eInfl} min={0} max={12} step={0.5} onChange={setEInfl} format={(v) => `${v}%`} />
        </Controls>
        <div className="mt-6">
          <ChartFrame title="Rank the options" subtitle={`final value of ₹1 lakh a year for ${eYears} years, in today’s rupees`} height={320}>
            <ResponsiveContainer>
              <BarChart data={ranking} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => `${(Number(v) / 1e7).toFixed(1)}cr`} />
                <YAxis type="category" dataKey="allocation" {...axis} width={210} interval={0} tick={{ ...axis.tick, fontSize: 10.5 }} />
                <Tooltip {...tooltip} formatter={(v, _n, p) => [`${cr(Number(v))} (${(p.payload as { multiple: number }).multiple.toFixed(2)}× the last)`, 'today’s ₹']} />
                <Bar dataKey="finalReal">
                  {ranking.map((x, i) => (
                    <Cell key={x.allocation} fill={x.allocation.startsWith('Your mix') ? 'var(--accent)' : SERIES[i % SERIES.length]} fillOpacity={x.allocation.startsWith('Your mix') ? 1 : 0.55} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>
    </LabShell>
  );
}

export default WealthLab;
