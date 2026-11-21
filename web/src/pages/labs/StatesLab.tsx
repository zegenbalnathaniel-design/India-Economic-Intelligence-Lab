import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ChartFrame,
  ChipMulti,
  Callout,
  Controls,
  DataTable,
  Field,
  LabHero,
  LabSection,
  LabShell,
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
import data from '../../data/labs/states.json';
import { labBySlug } from '../../labs/registry';
import {
  annualGrowth,
  beta,
  cagr,
  fyStart,
  indexToBase,
  rankChanges,
  sigma,
  widePanel,
  type MeasureKey,
  type Row,
} from '../../models/convergence/engine';

const lab = labBySlug('states')!;
const ROWS = data.spliced as unknown as Row[];
const PANEL = data.panel as [string, string, string, number | null][];
type IndKey = keyof typeof data.indicators;
const IND = data.indicators as Record<string, { key: string; label: string; unit: string; status: string; source: string; explainer: string }>;
const MEASURES = data.measures as Record<MeasureKey, { key: MeasureKey; label: string; unit: string; formula: string; reading: string }>;

const { wide: WIDE, years: YEARS } = widePanel(ROWS);
const ALL_STATES = [...WIDE.keys()].sort();
const LATEST = YEARS[YEARS.length - 1];

const periodsFor = (ind: string) =>
  [...new Set(PANEL.filter((r) => r[1] === ind && r[3] !== null).map((r) => r[2]))].sort((a, b) => fyStart(a) - fyStart(b));
const valuesFor = (ind: string, period: string) =>
  new Map(PANEL.filter((r) => r[1] === ind && r[2] === period && r[3] !== null).map((r) => [r[0], r[3] as number]));

// Hero: Branches — main line = highest latest per-capita NSDP, branch = fastest average growth.
const heroMain = ALL_STATES.filter((s) => WIDE.get(s)!.has(LATEST))
  .sort((a, b) => WIDE.get(b)!.get(LATEST)! - WIDE.get(a)!.get(LATEST)!)
  .slice(0, 8);
const heroBranch = ALL_STATES.map((s) => {
  const m = WIDE.get(s)!;
  const ys = YEARS.filter((y) => m.has(y));
  return { s, g: ys.length > 1 ? cagr(m.get(ys[0])!, m.get(ys[ys.length - 1])!, fyStart(ys[ys.length - 1]) - fyStart(ys[0])) : NaN };
})
  .filter((x) => Number.isFinite(x.g))
  .sort((a, b) => b.g - a.g)
  .slice(0, 3);

function shade(t: number, accent = '#6fae4f') {
  const a = [30, 34, 48];
  const b = [parseInt(accent.slice(1, 3), 16), parseInt(accent.slice(3, 5), 16), parseInt(accent.slice(5, 7), 16)];
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * Math.max(0, Math.min(1, t))));
  return `rgb(${c.join(',')})`;
}

export function StatesLab() {
  // σ / β window
  const [start, setStart] = useState(YEARS[0]);
  const [end, setEnd] = useState(LATEST);
  const [measure, setMeasure] = useState<MeasureKey>('sd_log');
  const [balanced, setBalanced] = useState<'balanced' | 'unbalanced'>('balanced');
  const [se, setSe] = useState<'nonrobust' | 'HC1'>('nonrobust');

  const sig = useMemo(() => sigma(ROWS, start, end, measure, balanced === 'balanced'), [start, end, measure, balanced]);
  const bet = useMemo(() => beta(ROWS, start, end, se), [start, end, se]);
  const ranks = useMemo(() => rankChanges(ROWS, start, end), [start, end]);
  const fitLine = useMemo(() => {
    if (!bet.fit) return [];
    const xs = bet.points.map((p) => p.logInitial);
    const lo = Math.min(...xs);
    const hi = Math.max(...xs);
    return [lo, hi].map((x) => ({ logInitial: x, fitted: bet.fit!.intercept + bet.fit!.slope * x }));
  }, [bet]);

  // Tile map + ranking
  const indKeys = Object.keys(IND) as IndKey[];
  const [tileInd, setTileInd] = useState<string>('nsdp_pc_constant_spliced');
  const tilePeriods = useMemo(() => periodsFor(tileInd), [tileInd]);
  const [tilePeriod, setTilePeriod] = useState<string>(LATEST);
  const tp = tilePeriods.includes(tilePeriod) ? tilePeriod : tilePeriods[tilePeriods.length - 1];
  const tileVals = useMemo(() => valuesFor(tileInd, tp), [tileInd, tp]);
  const [hoverTile, setHoverTile] = useState<string | null>(null);

  const [rankInd, setRankInd] = useState<string>('nsdp_pc_current_rbi');
  const rankPeriods = useMemo(() => periodsFor(rankInd), [rankInd]);
  const [rankPeriod, setRankPeriod] = useState<string>('');
  const rp = rankPeriods.includes(rankPeriod) ? rankPeriod : rankPeriods[rankPeriods.length - 1];
  const [order, setOrder] = useState<'desc' | 'asc'>('desc');
  const rankRows = useMemo(() => {
    const m = valuesFor(rankInd, rp);
    return [...m.entries()].map(([state, value]) => ({ state, value })).sort((a, b) => (order === 'desc' ? b.value - a.value : a.value - b.value));
  }, [rankInd, rp, order]);

  // Workbench
  const [wbStates, setWbStates] = useState<string[]>(['Bihar', 'Gujarat', 'Kerala', 'Tamil Nadu', 'Uttar Pradesh'].filter((s) => WIDE.has(s)));
  const [wbBase, setWbBase] = useState(YEARS[0]);
  const wbIndex = useMemo(() => {
    const sub = new Map(wbStates.map((s) => [s, WIDE.get(s)!]));
    const { indexed } = indexToBase(sub, YEARS, wbBase);
    return YEARS.filter((y) => fyStart(y) >= fyStart(wbBase)).map((y) => {
      const row: Record<string, number | string | null> = { fy: y };
      for (const s of wbStates) row[s] = indexed.get(s)?.get(y) ?? null;
      return row;
    });
  }, [wbStates, wbBase]);
  const wbGrowth = useMemo(
    () =>
      wbStates.map((s) => {
        const g = annualGrowth(WIDE.get(s)!, YEARS).filter((r) => fyStart(r.fy) > fyStart(wbBase));
        const avg = g.length ? g.reduce((a, r) => a + r.growth, 0) / g.length : NaN;
        return { state: s, avg };
      }),
    [wbStates, wbBase],
  );
  const colourOf = (s: string) => SERIES[wbStates.indexOf(s) % SERIES.length];

  const m = MEASURES[measure];
  const tileMax = Math.max(...tileVals.values());
  const tileMin = Math.min(...tileVals.values());

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Real per-capita Net State Domestic Product for {ALL_STATES.length} states and union territories, {YEARS[0]} to {LATEST}, on
            the RBI Handbook’s two base years linked by overlap-year factors. Every statistic below is recomputed in your browser
            from that panel as you move the controls.
          </>
        }
        stats={[
          { label: 'States / UTs', value: ALL_STATES.length, sub: 'spliced constant-price series' },
          { label: 'σ verdict', value: sig.verdict, sub: `${m.label.toLowerCase()}, ${start} → ${end}` },
          { label: 'β slope', value: bet.fit ? `${bet.fit.slope.toFixed(2)}` : '—', sub: bet.fit ? `${fmt.p(bet.fit.p)}, n = ${bet.fit.n}` : 'insufficient data' },
        ]}
        figure={{
          name: 'Branches',
          label: 'A commit graph: the main line is the highest-income states, the branch is the fastest-growing states.',
          idle: 'Main line: highest per-capita NSDP. Branch: fastest-growing states. Hover the graph.',
          caption: (read) => {
            const mm = /^(main|feature) · (\d+)$/.exec(read);
            if (!mm) return null;
            const i = Number(mm[2]) - 1;
            if (mm[1] === 'main') {
              const s = heroMain[i];
              return s ? `${s}\n${fmt.inr(WIDE.get(s)!.get(LATEST))} per person, ${LATEST} (constant prices) — among the highest` : null;
            }
            const b = heroBranch[i];
            return b ? `${b.s}\n${b.g.toFixed(2)}% a year average real growth — among the fastest` : null;
          },
        }}
      />

      <LabSection
        index="A"
        title="σ-convergence: is the spread across states narrowing?"
        lede={
          <>
            {m.reading} <span className="text-ink-500">{data.sigmaRule.replace(/\*\*/g, '')}</span>
          </>
        }
      >
        <Controls className="md:grid-cols-4">
          <Field label="Initial year">
            <Select value={start} onChange={setStart} options={YEARS.slice(0, -1)} />
          </Field>
          <Field label="Final year">
            <Select value={end} onChange={setEnd} options={YEARS.filter((y) => fyStart(y) > fyStart(start))} />
          </Field>
          <Field label="Dispersion measure">
            <Select value={measure} onChange={setMeasure} options={Object.values(MEASURES).map((x) => ({ value: x.key, label: x.label }))} />
          </Field>
          <Field label="Panel">
            <Segmented value={balanced} onChange={setBalanced} options={[{ value: 'balanced', label: 'Balanced' }, { value: 'unbalanced', label: 'All reporting' }]} />
          </Field>
        </Controls>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_300px]">
          <ChartFrame
            title={`${m.label} across states`}
            subtitle={<code className="font-mono text-[11px]">{m.formula}</code>}
            source="RBI Handbook of Statistics on Indian States, Table 26 (spliced). Unweighted: each state counts once."
          >
            <ResponsiveContainer>
              <LineChart data={sig.byYear} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="fy" {...axis} />
                <YAxis {...axis} domain={['auto', 'auto']} tickFormatter={(v) => Number(v).toFixed(measure === 'cv' ? 0 : 2)} width={52} />
                <Tooltip {...tooltip} formatter={(v) => [Number(v).toFixed(4), m.label]} />
                <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2.2} dot={{ r: 2.5, fill: 'var(--accent)' }} isAnimationActive />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <Stat label="Verdict" value={sig.verdict} sub={`threshold ±5% of the window mean`} />
            <Stat label="First → last" value={`${fmt.n(sig.first, 3)} → ${fmt.n(sig.last, 3)}`} sub={m.unit} tone="#f5f0e6" />
            <Stat label="Trend change" value={fmt.pct(sig.trendPctOfMean, 1)} sub={`OLS slope ${fmt.n(sig.slope, 4)} / yr, ${fmt.p(sig.slopeP)}`} tone="#f5f0e6" />
            <Stat label="States in panel" value={sig.included.length} sub={sig.excluded.length ? `${sig.excluded.length} excluded for gaps` : 'none excluded'} tone="#f5f0e6" />
          </div>
        </div>
        {sig.compositionChanges && (
          <div className="mt-4">
            <Callout tone="warn" title="Composition changes">
              The set of reporting states changes between years in this window, so part of any trend can be an artefact of who is
              in the sample. Switch to the balanced panel to compare the same states every year.
            </Callout>
          </div>
        )}
        <div className="mt-4">
          <Callout title="Weighting">{data.populationCaveat.replace(/\*\*/g, '')}</Callout>
        </div>
      </LabSection>

      <LabSection
        index="B"
        title="β-convergence: did initially poorer states grow faster?"
        lede={
          <>
            Average annual real growth over the window against the log of initial income. A negative slope means poorer states
            grew faster. <span className="text-ink-500">{data.speedFormula}</span>
          </>
        }
      >
        <div className="mb-5 flex flex-wrap items-center gap-4">
          <span className="label">Standard errors</span>
          <Segmented value={se} onChange={setSe} options={[{ value: 'nonrobust', label: 'Classical' }, { value: 'HC1', label: 'HC1 robust' }]} />
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <ChartFrame
            title={`Growth ${start} → ${end} vs initial income`}
            subtitle="Each dot is a state; the line is the OLS fit."
            source="RBI Handbook Table 26, spliced; growth = 100·(ln y_end − ln y_start)/T."
            height={380}
          >
            <ResponsiveContainer>
              <ComposedChart margin={{ top: 8, right: 16, bottom: 18, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis
                  type="number"
                  dataKey="logInitial"
                  {...axis}
                  domain={['auto', 'auto']}
                  tickFormatter={(v) => Number(v).toFixed(1)}
                  label={{ value: `ln per-capita NSDP, ${start}`, position: 'insideBottom', offset: -10, fill: '#6b6f80', fontSize: 11 }}
                />
                <YAxis type="number" dataKey="growth" {...axis} tickFormatter={(v) => `${Number(v).toFixed(1)}%`} width={52} />
                <Tooltip
                  {...tooltip}
                  content={({ payload }) => {
                    const p = payload?.[0]?.payload as { state?: string; growth?: number; initial?: number } | undefined;
                    if (!p?.state) return null;
                    return (
                      <div style={tooltip.contentStyle} className="px-3 py-2">
                        <div className="text-ink-50">{p.state}</div>
                        <div>initial {fmt.inr(p.initial)}</div>
                        <div>growth {fmt.pct(p.growth, 2)} a year</div>
                      </div>
                    );
                  }}
                />
                <Scatter data={bet.points} fill="var(--accent)" fillOpacity={0.85} />
                <Line data={fitLine} dataKey="fitted" stroke="#f5f0e6" strokeDasharray="5 4" dot={false} strokeWidth={1.4} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <Stat label="Slope (pp per log point)" value={bet.fit ? bet.fit.slope.toFixed(3) : '—'} sub={bet.fit ? `SE ${bet.fit.se.toFixed(3)} (${se === 'HC1' ? 'HC1' : 'classical'}), ${fmt.p(bet.fit.p)}` : ''} />
            <Stat label="95% CI" value={bet.fit ? `[${bet.fit.ciLow.toFixed(2)}, ${bet.fit.ciHigh.toFixed(2)}]` : '—'} tone="#f5f0e6" />
            <Stat label="R²" value={bet.fit ? bet.fit.r2.toFixed(3) : '—'} sub={`n = ${bet.points.length} states`} tone="#f5f0e6" />
            <Stat
              label="Speed · half-life"
              value={Number.isFinite(bet.speed) ? `${(bet.speed * 100).toFixed(2)}% · ${bet.halfLife.toFixed(0)} yrs` : 'not implied'}
              sub={bet.note || 'λ = −ln(1 + b·T)/T'}
              tone="#f5f0e6"
            />
          </div>
        </div>
        <div className="mt-6">
          <Callout title="Research note — generated from the results above">
            Over {start} to {end} ({bet.years} years), the spread of real per-capita NSDP across the {sig.included.length} states with
            complete data is <b className="text-ink-50">{sig.verdict}</b> on the {m.label.toLowerCase()} ({fmt.n(sig.first, 3)} →{' '}
            {fmt.n(sig.last, 3)}). The β slope is {bet.fit ? bet.fit.slope.toFixed(2) : 'n/a'}
            {bet.fit && (bet.fit.p < 0.05 ? ', statistically significant at 5%' : ', not statistically significant at 5%')}:{' '}
            {bet.fit && bet.fit.slope < 0
              ? 'initially poorer states grew faster on average — unconditional β-convergence.'
              : 'initially poorer states did not grow faster on average — no unconditional β-convergence.'}{' '}
            σ and β can disagree: β-convergence is necessary but not sufficient for σ-convergence.
          </Callout>
        </div>
      </LabSection>

      <LabSection index="C" title="Schematic tile map" lede={data.tileCaption}>
        <Controls className="md:grid-cols-2">
          <Field label="Indicator">
            <Select value={tileInd} onChange={setTileInd} options={indKeys.map((k) => ({ value: k, label: IND[k].label }))} />
          </Field>
          <Field label="Year">
            <Select value={tp} onChange={setTilePeriod} options={tilePeriods} />
          </Field>
        </Controls>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="ticked border border-white/[0.08] bg-ink-900/50 p-4 md:p-6">
            <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(10, minmax(0, 1fr))' }}>
              {Object.entries(data.tileGrid as Record<string, number[]>).map(([state, [r, c]]) => {
                const v = tileVals.get(state);
                const t = v === undefined ? -1 : (v - tileMin) / (tileMax - tileMin || 1);
                return (
                  <button
                    key={state}
                    type="button"
                    onMouseEnter={() => setHoverTile(state)}
                    onFocus={() => setHoverTile(state)}
                    className="relative flex aspect-square flex-col items-center justify-center border text-center transition-transform duration-200 hover:z-10 hover:scale-110"
                    style={{
                      gridRow: r + 1,
                      gridColumn: c + 1,
                      background: v === undefined ? 'transparent' : shade(0.15 + 0.85 * t),
                      borderColor: hoverTile === state ? '#f5f0e6' : 'rgba(245,240,230,0.08)',
                      borderStyle: v === undefined ? 'dashed' : 'solid',
                    }}
                    title={state}
                  >
                    <span className={`font-mono text-[10px] md:text-[11px] ${t > 0.55 ? 'text-ink-950' : 'text-ink-100'}`}>
                      {(data.tileAbbr as Record<string, string>)[state]}
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="mt-5 flex items-center gap-3">
              <span className="font-mono text-[10px] text-ink-500">{fmt.n(tileMin, 0)}</span>
              <div className="h-1.5 flex-1" style={{ background: `linear-gradient(90deg, ${shade(0.15)}, ${shade(1)})` }} />
              <span className="font-mono text-[10px] text-ink-500">{fmt.n(tileMax, 0)}</span>
            </div>
          </div>
          <div className="grid content-start gap-3">
            <Stat
              label={hoverTile ?? 'Hover a tile'}
              value={hoverTile && tileVals.has(hoverTile) ? fmt.n(tileVals.get(hoverTile)!, IND[tileInd].unit === '%' ? 1 : 0) : '—'}
              sub={hoverTile && !tileVals.has(hoverTile) ? 'no value in this source and year' : `${IND[tileInd].unit} · ${tp}`}
            />
            <div className="border border-white/[0.08] bg-ink-900/50 p-4 text-[12.5px] leading-relaxed text-ink-300">
              <div className="mb-2 flex items-center gap-2">
                <StatusPill status={IND[tileInd].status} />
              </div>
              {IND[tileInd].explainer.split('\n\n')[0].replace(/\*\*/g, '')}
              <div className="mt-2 text-ink-500">{IND[tileInd].source}</div>
            </div>
          </div>
        </div>
      </LabSection>

      <LabSection index="D" title="Rank every state by one indicator">
        <Controls>
          <Field label="Indicator">
            <Select value={rankInd} onChange={setRankInd} options={indKeys.map((k) => ({ value: k, label: IND[k].label }))} />
          </Field>
          <Field label="Year">
            <Select value={rp} onChange={setRankPeriod} options={rankPeriods} />
          </Field>
          <Field label="Order">
            <Segmented value={order} onChange={setOrder} options={[{ value: 'desc', label: 'Highest first' }, { value: 'asc', label: 'Lowest first' }]} />
          </Field>
        </Controls>
        <div className="mt-6">
          <ChartFrame title={`${IND[rankInd].label}, ${rp}`} subtitle={`${rankRows.length} states/UTs with a value`} source={IND[rankInd].source} height={Math.max(320, rankRows.length * 19)}>
            <ResponsiveContainer>
              <BarChart data={rankRows} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 8 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => fmt.n(Number(v), 0)} />
                <YAxis type="category" dataKey="state" {...axis} width={150} interval={0} tick={{ ...axis.tick, fontSize: 10.5 }} />
                <Tooltip {...tooltip} formatter={(v) => [fmt.n(Number(v), 1), IND[rankInd].unit]} />
                <Bar dataKey="value" radius={0} isAnimationActive>
                  {rankRows.map((r, i) => (
                    <Cell key={r.state} fill={i < 3 ? 'var(--accent)' : 'rgba(111,174,79,0.45)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="E" title="State comparison workbench" lede="Pick two to five states. Each series is indexed to its own base-year value (= 100), so the lines compare growth paths, not levels.">
        <div className="grid gap-5 border border-white/[0.08] bg-ink-900/50 p-4 md:p-5">
          <Field label={`States (${wbStates.length}/5)`}>
            <ChipMulti values={wbStates} onChange={setWbStates} options={ALL_STATES} max={5} colour={colourOf} />
          </Field>
          <div className="max-w-xs">
            <Field label="Index base year (= 100)">
              <Select value={wbBase} onChange={setWbBase} options={YEARS.slice(0, -2)} />
            </Field>
          </div>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <ChartFrame title={`Real per-capita NSDP, ${wbBase} = 100`} source="RBI Handbook Table 26, spliced.">
            <ResponsiveContainer>
              <LineChart data={wbIndex} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="fy" {...axis} />
                <YAxis {...axis} width={44} />
                <Tooltip {...tooltip} formatter={(v) => (typeof v === 'number' ? v.toFixed(1) : v)} />
                <Legend {...legend} />
                {wbStates.map((s) => (
                  <Line key={s} type="monotone" dataKey={s} stroke={colourOf(s)} strokeWidth={2} dot={false} connectNulls={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Average annual real growth" subtitle={`consecutive years after ${wbBase}`}>
            <ResponsiveContainer>
              <BarChart data={wbGrowth} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} vertical={false} />
                <XAxis dataKey="state" {...axis} tick={{ ...axis.tick, fontSize: 10 }} interval={0} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => [fmt.pct(Number(v), 2), 'avg growth']} />
                <Bar dataKey="avg">
                  {wbGrowth.map((g) => (
                    <Cell key={g.state} fill={colourOf(g.state)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="F" title="Who moved up, who slipped" lede={`Rank by real per-capita NSDP in ${start} and ${end}, among states reporting both years (1 = highest).`}>
        <StatRow>
          <Stat label="Biggest climber" value={ranks[0]?.state ?? '—'} sub={ranks[0] ? `${ranks[0].rankStart} → ${ranks[0].rankEnd}` : ''} />
          <Stat label="Biggest fall" value={ranks[ranks.length - 1]?.state ?? '—'} sub={ranks.length ? `${ranks[ranks.length - 1].rankStart} → ${ranks[ranks.length - 1].rankEnd}` : ''} tone="#f04a32" />
          <Stat label="Unchanged" value={ranks.filter((r) => r.places === 0).length} sub="states" tone="#f5f0e6" />
          <Stat label="Compared" value={ranks.length} sub="states with both years" tone="#f5f0e6" />
        </StatRow>
        <div className="mt-5">
          <DataTable
            columns={[
              { key: 'state', label: 'State / UT' },
              { key: 'rankStart', label: `Rank ${start}`, align: 'right' },
              { key: 'rankEnd', label: `Rank ${end}`, align: 'right' },
              {
                key: 'places',
                label: 'Places',
                align: 'right',
                format: (v) => {
                  const n = v as number;
                  return <span style={{ color: n > 0 ? '#6fae4f' : n < 0 ? '#f04a32' : '#8b8d99' }}>{n > 0 ? `▲ ${n}` : n < 0 ? `▼ ${-n}` : '—'}</span>;
                },
              },
            ]}
            rows={ranks as unknown as Record<string, unknown>[]}
          />
        </div>
      </LabSection>
    </LabShell>
  );
}

export default StatesLab;
