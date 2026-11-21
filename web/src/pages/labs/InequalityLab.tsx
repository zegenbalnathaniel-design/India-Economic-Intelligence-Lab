import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Callout,
  ChartFrame,
  ChipMulti,
  Controls,
  DataTable,
  Field,
  LabHero,
  LabSection,
  LabShell,
  Range,
  Segmented,
  Select,
  SERIES,
  Stat,
  StatRow,
  StatusPill,
  axis,
  fmt,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import D from '../../data/labs/inequality.json';
import { labBySlug } from '../../labs/registry';
import { alignTwo, giniLowerBound, lorenzPoints, redistribute, type Shares } from '../../models/inequality/engine';
import { pearson } from '../../models/stats/regression';

const lab = labBySlug('inequality')!;
const INCOME = D.incomeShares as unknown as Shares[];
const WEALTH = D.wealthShares as unknown as Shares[];
const WDI = D.wdi.series as unknown as Record<string, Record<string, [number, number][]>>;
const META = D.wdiMeta as Record<string, { label: string; unit: string; definition: string }>;
const ACCOUNT = D.accountCodes as string[];
const DEPTH = D.depthCodes as string[];
const VH = D.vhnwi as { year: number; forbes_wealth_pct_nni: number | null; hurun_wealth_pct_nni: number | null; forbes_count: number | null }[];

type Series = { id: string; label: string; source: string; data: [number, number][] };
const SHARE_KEYS: [keyof Shares, string][] = [
  ['bottom_50', 'Bottom 50%'],
  ['middle_40', 'Middle 40%'],
  ['top_10', 'Top 10%'],
  ['top_1', 'Top 1%'],
  ['top_0_1', 'Top 0.1%'],
];
const CATALOGUE: Series[] = [
  ...SHARE_KEYS.map(([k, l]) => ({
    id: `inc_${k}`,
    label: `WIL income share · ${l}`,
    source: 'WIL Table B.1',
    data: INCOME.map((r) => [r.year, r[k] as number] as [number, number]),
  })),
  ...SHARE_KEYS.map(([k, l]) => ({
    id: `wea_${k}`,
    label: `WIL wealth share · ${l}`,
    source: 'WIL Table C.1',
    data: WEALTH.filter((r) => !r.tentative).map((r) => [r.year, r[k] as number] as [number, number]),
  })),
  { id: 'forbes', label: 'Billionaire wealth (Forbes), % of NNI', source: 'WIL Table C.2', data: VH.filter((r) => r.forbes_wealth_pct_nni !== null).map((r) => [r.year, r.forbes_wealth_pct_nni!]) },
  ...Object.keys(WDI)
    .filter((c) => WDI[c].IND)
    .map((c) => ({ id: c, label: `${META[c].label} (WDI)`, source: `World Bank ${c}`, data: WDI[c].IND })),
];

const YEARS_INC = INCOME.map((r) => r.year);
const COMMON = YEARS_INC.filter((y) => WEALTH.some((w) => w.year === y));

export function InequalityLab() {
  const [measure, setMeasure] = useState<'income' | 'wealth'>('income');
  const table = measure === 'income' ? INCOME : WEALTH;
  const years = table.map((r) => String(r.year));
  const [lzYears, setLzYears] = useState<string[]>(['1951', '1980', '2000', '2022']);
  const chosen = (measure === 'income' ? lzYears : ['1961', '1981', '2002', '2012', '2023']).filter((y) => years.includes(y));
  const [wYears, setWYears] = useState<string[]>(['1961', '1991', '2012', '2023']);
  const activeYears = measure === 'income' ? chosen : wYears.filter((y) => years.includes(y));

  const lorenz = useMemo(() => {
    const xs = [0, 0.5, 0.9, 0.99, 0.999, 1];
    return xs.map((x, i) => {
      const row: Record<string, number> = { x: x * 100, equality: x * 100 };
      for (const y of activeYears) {
        const r = table.find((t) => String(t.year) === y);
        if (r) row[y] = lorenzPoints(r)[i][1] * 100;
      }
      return row;
    });
  }, [table, activeYears]);

  const gini = useMemo(() => {
    const ys = [...new Set([...INCOME.map((r) => r.year), ...WEALTH.map((r) => r.year)])].sort((a, b) => a - b);
    return ys.map((y) => {
      const i = INCOME.find((r) => r.year === y);
      const w = WEALTH.find((r) => r.year === y);
      return { year: y, income: i ? giniLowerBound(i) : null, wealth: w ? giniLowerBound(w) : null };
    });
  }, []);

  const [cYear, setCYear] = useState(String(COMMON[COMMON.length - 1]));
  const ci = INCOME.find((r) => String(r.year) === cYear)!;
  const cw = WEALTH.find((r) => String(r.year) === cYear)!;

  const [pp, setPp] = useState(5);
  const latestI = INCOME[INCOME.length - 1];
  const red = redistribute(latestI, Math.min(pp, latestI.top_1));

  const acct = useMemo(() => {
    const ys = [...new Set(ACCOUNT.flatMap((c) => (WDI[c]?.IND ?? []).map(([y]) => y)))].sort((a, b) => a - b);
    return ys.map((y) => {
      const row: Record<string, number | null> = { year: y };
      for (const c of ACCOUNT) row[c] = WDI[c]?.IND?.find(([yy]) => yy === y)?.[1] ?? null;
      return row;
    });
  }, []);
  const depth = useMemo(() => {
    const ys = [...new Set(DEPTH.flatMap((c) => (WDI[c]?.IND ?? []).map(([y]) => y)))].sort((a, b) => a - b);
    return ys.map((y) => {
      const row: Record<string, number | null> = { year: y };
      for (const c of DEPTH) row[c] = WDI[c]?.IND?.find(([yy]) => yy === y)?.[1] ?? null;
      return row;
    });
  }, []);

  const [aId, setAId] = useState('wea_top_1');
  const [bId, setBId] = useState('CM.MKT.LCAP.GD.ZS');
  const A = CATALOGUE.find((s) => s.id === aId)!;
  const B = CATALOGUE.find((s) => s.id === bId) ?? CATALOGUE[1];
  const aligned = useMemo(() => alignTwo(A.data, B.data, 1951, 2030), [A, B]);
  const r = pearson(aligned.map((p) => p.a), aligned.map((p) => p.b));
  const dA = aligned.slice(1).map((p, i) => p.a - aligned[i].a);
  const dB = aligned.slice(1).map((p, i) => p.b - aligned[i].b);
  const rd = pearson(dA, dB);

  const aidis = D.aidisHeadline as { metric: string; area: string; group: string; value: number; unit: string; status: string }[];

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Income shares since 1951 and wealth shares since 1961 from the World Inequality Lab’s India tables, what households
            hold and owe, and World Bank series on who has a bank account and how deep finance runs — snapshotted{' '}
            {D.wdi.retrieved}.
          </>
        }
        stats={[
          { label: 'Top 1% income share', value: fmt.pct(latestI.top_1, 1), sub: `${latestI.year} · ${fmt.pct(INCOME[0].top_1, 1)} in ${INCOME[0].year}` },
          { label: 'Top 10% wealth share', value: fmt.pct(cw.top_10, 1), sub: `${cw.year}${cw.tentative ? ' (tentative)' : ''}` },
          { label: 'Gini, lower bound', value: giniLowerBound(latestI).toFixed(3), sub: `income, ${latestI.year}` },
        ]}
        figure={{
          name: 'Riffle',
          label: 'A tray of eight cards, one per population group, from the bottom 10% to the top 0.1%, each with its share of India’s income and wealth.',
          idle: 'Hover a card, or tab in and use the arrow keys.',
          caption: (read) => {
            if (!read || read === 'rest') return null;
            return (D.riffleCaptions as string[])[parseInt(read, 10) - 1] ?? null;
          },
        }}
      />

      <LabSection index="A" title="Lorenz curves: how unequal, and how that changed" lede="Points at P50, P90, P99 and P99.9 are the published group shares; joining them with straight lines treats everyone inside a group as equal, so the Gini of this curve is a lower bound on the true Gini.">
        <Controls className="md:grid-cols-[auto_1fr]">
          <Field label="Distribution">
            <Segmented value={measure} onChange={setMeasure} options={[{ value: 'income', label: 'Income (B.1)' }, { value: 'wealth', label: 'Wealth (C.1)' }]} />
          </Field>
          <Field label="Years (up to 5)">
            <ChipMulti
              values={activeYears}
              onChange={measure === 'income' ? setLzYears : setWYears}
              options={measure === 'income' ? years.filter((y) => Number(y) % 10 === 0 || y === String(INCOME[INCOME.length - 1].year)) : years}
              max={5}
              colour={(y) => SERIES[activeYears.indexOf(y) % SERIES.length]}
            />
          </Field>
        </Controls>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ChartFrame title={`Lorenz curve · ${measure}`} subtitle="Cumulative share held by the poorest x% of adults" source={measure === 'income' ? 'WIL Table B.1' : 'WIL Table C.1 (2023 row tentative)'} height={380}>
            <ResponsiveContainer>
              <LineChart data={lorenz} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="x" type="number" domain={[0, 100]} {...axis} tickFormatter={(v) => `${v}%`} />
                <YAxis domain={[0, 100]} {...axis} tickFormatter={(v) => `${v}%`} width={44} />
                <Tooltip {...tooltip} formatter={(v) => `${Number(v).toFixed(1)}%`} labelFormatter={(l) => `Poorest ${l}%`} />
                <Legend {...legend} />
                <Line dataKey="equality" name="Perfect equality" stroke="rgba(245,240,230,0.35)" strokeDasharray="4 4" dot={false} />
                {activeYears.map((y, i) => (
                  <Line key={y} dataKey={y} stroke={SERIES[i % SERIES.length]} strokeWidth={2.2} dot={{ r: 2.5 }} type="linear" />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Lower-bound Gini over time" subtitle="Income and wealth, from the published shares" source="WIL Tables B.1 and C.1; Gini derived here." height={380}>
            <ResponsiveContainer>
              <LineChart data={gini} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis domain={[0.3, 0.9]} {...axis} width={40} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : Number(v).toFixed(3))} />
                <Legend {...legend} />
                <Line dataKey="income" name="Income" stroke="#4d6ff0" strokeWidth={2.2} dot={false} connectNulls />
                <Line dataKey="wealth" name="Wealth" stroke="var(--accent)" strokeWidth={2.2} dot={{ r: 3 }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="B" title="Income against wealth, the same year" lede="Wealth is always more concentrated than income: assets compound, and inheritance passes them on.">
        <div className="max-w-xs">
          <Field label="Year both tables report">
            <Select value={cYear} onChange={setCYear} options={COMMON.map(String)} />
          </Field>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <ChartFrame title={`Group shares, ${cYear}`} source="WIL Tables B.1 and C.1">
            <ResponsiveContainer>
              <BarChart data={SHARE_KEYS.map(([k, l]) => ({ g: l, income: ci[k] as number, wealth: cw[k] as number }))} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} vertical={false} />
                <XAxis dataKey="g" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 1)} />
                <Legend {...legend} />
                <Bar dataKey="income" name="Income share" fill="#4d6ff0" />
                <Bar dataKey="wealth" name="Wealth share" fill="var(--accent)" />
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <StatRow>
              <Stat label="Top 10% · income" value={fmt.pct(ci.top_10)} tone="#4d6ff0" />
              <Stat label="Top 10% · wealth" value={fmt.pct(cw.top_10)} />
              <Stat label="Gini LB · income" value={giniLowerBound(ci).toFixed(3)} tone="#4d6ff0" />
              <Stat label="Gini LB · wealth" value={giniLowerBound(cw).toFixed(3)} />
            </StatRow>
            {cw.tentative && <Callout tone="warn">The {cYear} wealth row is flagged tentative by the WIL authors.</Callout>}
          </div>
        </div>
      </LabSection>

      <LabSection index="C" title="A redistribution thought-experiment" lede={`Move points of national income from the Top 1% to the Bottom 50% in ${latestI.year} (the cut is proportional within the Top 1%) and watch the lower-bound Gini respond. Arithmetic on published shares — not a policy forecast.`}>
        <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          <div className="grid content-start gap-5 border border-white/[0.08] bg-ink-900/50 p-5">
            <Range label="Points moved" value={pp} min={0} max={Math.floor(latestI.top_1)} step={0.5} onChange={setPp} format={(v) => `${v.toFixed(1)} pp`} />
            <StatRow>
              <Stat label="Bottom 50%" value={fmt.pct(red.bottom_50)} sub={`from ${fmt.pct(latestI.bottom_50)}`} tone="#6fae4f" />
              <Stat label="Top 1%" value={fmt.pct(red.top_1)} sub={`from ${fmt.pct(latestI.top_1)}`} />
              <Stat label="Gini LB" value={giniLowerBound(red).toFixed(3)} sub={`from ${giniLowerBound(latestI).toFixed(3)}`} tone="#f5f0e6" />
              <Stat label="Back to year" value={(() => {
                const g = giniLowerBound(red);
                const hit = [...INCOME].reverse().find((r) => giniLowerBound(r) <= g);
                return hit ? hit.year : '< 1951';
              })()} sub="latest year with a Gini this low" tone="#f5f0e6" />
            </StatRow>
          </div>
          <ChartFrame title="Lorenz curve before and after" height={300}>
            <ResponsiveContainer>
              <AreaChart data={[0, 0.5, 0.9, 0.99, 0.999, 1].map((x, i) => ({ x: x * 100, before: lorenzPoints(latestI)[i][1] * 100, after: lorenzPoints(red)[i][1] * 100 }))} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="x" type="number" domain={[0, 100]} {...axis} tickFormatter={(v) => `${v}%`} />
                <YAxis domain={[0, 100]} {...axis} width={40} tickFormatter={(v) => `${v}%`} />
                <Tooltip {...tooltip} formatter={(v) => `${Number(v).toFixed(1)}%`} />
                <Legend {...legend} />
                <Area type="linear" dataKey="after" name="After" stroke="#6fae4f" fill="#6fae4f" fillOpacity={0.12} strokeWidth={2} />
                <Area type="linear" dataKey="before" name={`${latestI.year} as published`} stroke="var(--accent)" fill="transparent" strokeWidth={2} strokeDasharray="5 4" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="D" title="What households hold, and what they owe" lede="Indian household wealth is overwhelmingly physical: property and gold. Debt is common, especially in rural India.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title="Composition of household assets" subtitle="Share of total, with the return the paper states" source="Paper A Table 1; shares from RBI Household Finance Committee (2017).">
            <ResponsiveContainer>
              <BarChart data={D.composition as { asset: string; share_pct: number }[]} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => `${v}%`} />
                <YAxis type="category" dataKey="asset" {...axis} width={140} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 0)} />
                <Bar dataKey="share_pct" name="Share">
                  {(D.composition as unknown[]).map((_, i) => (
                    <Cell key={i} fill={SERIES[[2, 1, 4, 0][i] ?? 0]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <DataTable
            columns={[
              { key: 'metric', label: 'AIDIS 2019 (NSS 77th round)' },
              { key: 'area', label: 'Area' },
              { key: 'value', label: 'Value', align: 'right', format: (v, r) => `${(v as number).toLocaleString('en-IN')} ${String(r.unit).replace('% of households', '%').replace('Rs per household', '₹/hh')}` },
              { key: 'status', label: 'Status', format: (v) => <StatusPill status={v as string} /> },
            ]}
            rows={aidis.filter((a) => a.group === 'All households') as unknown as Record<string, unknown>[]}
          />
        </div>
      </LabSection>

      <LabSection index="E" title="Financialisation: is participation broadening?" lede={`World Bank Global Findex and WDI series for India, snapshotted ${D.wdi.retrieved}. Account ownership has soared; whether that means inclusive wealth creation is a separate question.`}>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title="Account ownership, % of adults 15+" source="World Bank Global Findex via WDI." height={320}>
            <ResponsiveContainer>
              <LineChart data={acct} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmt.pct(Number(v), 1))} />
                <Legend {...legend} />
                {ACCOUNT.map((c, i) => (
                  <Line key={c} dataKey={c} name={META[c].label} stroke={['#f5f0e6', '#24a6a1', '#f04a32', '#4d6ff0'][i]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Financial depth, % of GDP" source="World Bank WDI." height={320}>
            <ResponsiveContainer>
              <LineChart data={depth} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} minTickGap={24} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={44} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmt.pct(Number(v), 1))} />
                <Legend {...legend} />
                {DEPTH.map((c, i) => (
                  <Line key={c} dataKey={c} name={META[c].label} stroke={['#4d6ff0', '#24a6a1', '#f3c542'][i]} strokeWidth={2} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="F" title="Compare any two indicators" lede="Inequality against finance, or any pair. Correlation in levels is shown next to correlation in year-on-year changes, because two trending series always look related in levels.">
        <Controls className="md:grid-cols-2">
          <Field label="Indicator A (left axis)">
            <Select value={aId} onChange={setAId} options={CATALOGUE.map((s) => ({ value: s.id, label: s.label }))} />
          </Field>
          <Field label="Indicator B (right axis)">
            <Select value={bId} onChange={setBId} options={CATALOGUE.map((s) => ({ value: s.id, label: s.label }))} />
          </Field>
        </Controls>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_280px]">
          <ChartFrame title={`${A.label} vs ${B.label}`} source={`${A.source}; ${B.source}`} height={360}>
            <ResponsiveContainer>
              <LineChart data={aligned} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis yAxisId="a" {...axis} width={48} />
                <YAxis yAxisId="b" orientation="right" {...axis} width={48} />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(2)} />
                <Legend {...legend} />
                <Line yAxisId="a" dataKey="a" name={A.label} stroke="var(--accent)" strokeWidth={2.2} dot={{ r: 2.5 }} />
                <Line yAxisId="b" dataKey="b" name={B.label} stroke="#4d6ff0" strokeWidth={2.2} dot={{ r: 2.5 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <Stat label="Years in common" value={aligned.length} sub={aligned.length ? `${aligned[0].year}–${aligned[aligned.length - 1].year}` : 'no overlap'} />
            <Stat label="Pearson r · levels" value={Number.isFinite(r.r) ? r.r.toFixed(2) : '—'} sub={fmt.p(r.p)} tone="#f5f0e6" />
            <Stat label="Pearson r · changes" value={Number.isFinite(rd.r) ? rd.r.toFixed(2) : '—'} sub={`${fmt.p(rd.p)}, n = ${dA.length}`} tone="#f5f0e6" />
            {Number.isFinite(r.r) && Number.isFinite(rd.r) && Math.abs(r.r) > 0.6 && Math.abs(rd.r) < 0.3 && (
              <Callout tone="warn">Strong in levels, weak in changes: much of the levels correlation is likely shared trend.</Callout>
            )}
          </div>
        </div>
      </LabSection>
    </LabShell>
  );
}

export default InequalityLab;
