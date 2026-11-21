import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
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
  Segmented,
  Select,
  SERIES,
  Stat,
  StatRow,
  axis,
  fmt,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import D from '../../data/labs/structural.json';
import { labBySlug } from '../../labs/registry';
import { SECTOR_NAMES, completeYears, snapshot, valueAt, weightedRlp, type Series } from '../../models/structural/engine';

const lab = labBySlug('structural')!;
const S = D.wdi.series as unknown as Series;
const NAMES = D.wdi.countries as Record<string, string>;
const META = D.meta as Record<string, { label: string; unit: string }>;
const ISOS = Object.keys(NAMES).sort((a, b) => (a === 'IND' ? -1 : b === 'IND' ? 1 : NAMES[a].localeCompare(NAMES[b])));
const PEERS = ISOS.filter((i) => i !== 'IND');
const SECTOR_COLOUR: Record<string, string> = { Agriculture: '#6fae4f', Industry: '#4d6ff0', Services: '#24a6a1' };
const IND_YEARS = completeYears(S, 'IND');
const IND_LATEST = snapshot(S, 'IND', IND_YEARS[IND_YEARS.length - 1]);
const MANUF_IND = S['NV.IND.MANF.ZS']?.IND ?? [];

const series = (code: string, iso: string) => S[code]?.[iso] ?? [];

export function StructuralLab() {
  const [focus, setFocus] = useState('IND');
  const years = useMemo(() => completeYears(S, focus), [focus]);
  const [year, setYear] = useState<number>(IND_YEARS[IND_YEARS.length - 1]);
  const fy = years.includes(year) ? year : years[years.length - 1];
  const snap = useMemo(() => (fy ? snapshot(S, focus, fy) : null), [focus, fy]);
  const [rescaled, setRescaled] = useState<'published' | 'rescaled'>('published');

  const overTime = useMemo(
    () =>
      years.map((y) => {
        const s = snapshot(S, focus, y);
        const row: Record<string, number | null> = { year: y };
        for (const r of s.rows) {
          row[`gap_${r.sector}`] = r.gap;
          row[`rlp_${r.sector}`] = rescaled === 'rescaled' ? r.rlpRescaled : r.rlp;
          row[`va_${r.sector}`] = r.va;
          row[`emp_${r.sector}`] = r.emp;
        }
        return row;
      }),
    [focus, years, rescaled],
  );

  const [peers, setPeers] = useState<string[]>(['CHN', 'IDN', 'BGD', 'VNM']);
  const manuf = useMemo(() => {
    const ys = [...new Set(['IND', ...peers].flatMap((i) => series('NV.IND.MANF.ZS', i).map(([y]) => y)))].sort((a, b) => a - b);
    return ys.map((y) => {
      const row: Record<string, number | null> = { year: y };
      for (const i of ['IND', ...peers]) row[i] = valueAt(S, 'NV.IND.MANF.ZS', i, y);
      return row;
    });
  }, [peers]);
  const lfp = useMemo(() => {
    const ys = [...new Set(series('SL.TLF.CACT.FE.ZS', focus).map(([y]) => y))].sort((a, b) => a - b);
    return ys.map((y) => ({
      year: y,
      female: valueAt(S, 'SL.TLF.CACT.FE.ZS', focus, y),
      male: valueAt(S, 'SL.TLF.CACT.MA.ZS', focus, y),
      vulnerable: valueAt(S, 'SL.EMP.VULN.ZS', focus, y),
    }));
  }, [focus]);

  const [showPaths, setShowPaths] = useState<'latest' | 'paths'>('paths');
  const scatter = useMemo(
    () =>
      ['IND', ...peers].map((iso) => {
        const agri = series('SL.AGR.EMPL.ZS', iso);
        const gdpw = new Map(series('SL.GDP.PCAP.EM.KD', iso));
        const pts = agri.filter(([y]) => gdpw.has(y)).map(([y, a]) => ({ iso, year: y, agri: a, gdpw: gdpw.get(y)! }));
        return { iso, pts: showPaths === 'paths' ? pts : pts.slice(-1) };
      }),
    [peers, showPaths],
  );

  const [stateView, setStateView] = useState<'rlp' | 'shares'>('rlp');
  const stateRows = D.stateShares as Record<string, number | string | null>[];
  const stateRlp = D.stateRlp as Record<string, number | string | null>[];

  const floors = [
    { name: 'Agriculture', ...IND_LATEST.rows[0] },
    { name: 'Industry', ...IND_LATEST.rows[1] },
    { name: 'Manufacturing', va: MANUF_IND.length ? MANUF_IND[MANUF_IND.length - 1][1] : null, emp: null, rlp: null },
    { name: 'Services', ...IND_LATEST.rows[2] },
  ];

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            The development path most economies took moves workers from farms into factories and then services, raising output
            per worker at every step. India’s path has been different. World Bank and ILO-modelled series for India and{' '}
            {PEERS.length} peers, snapshotted {D.wdi.retrieved}, plus state-level sector shares.
          </>
        }
        stats={[
          { label: 'Farm jobs vs farm output', value: `${fmt.pct(IND_LATEST.rows[0].emp, 0)} / ${fmt.pct(IND_LATEST.rows[0].va, 0)}`, sub: `India, ${IND_YEARS[IND_YEARS.length - 1]}` },
          { label: 'Services RLP', value: IND_LATEST.rows[2].rlp?.toFixed(2) ?? '—', sub: 'value-added share ÷ worker share' },
          { label: 'Manufacturing', value: fmt.pct(MANUF_IND[MANUF_IND.length - 1]?.[1], 1), sub: `of GDP, ${MANUF_IND[MANUF_IND.length - 1]?.[0] ?? ''}` },
        ]}
        figure={{
          name: 'Elevator',
          label: 'An elevator against four floors — agriculture, industry, manufacturing and services — the climb of structural transformation.',
          idle: 'Move the pointer up the shaft: the floors are the steps of structural transformation in India.',
          caption: (read) => {
            const idx = { ground: 0, 'floor 1': 1, 'floor 2': 2, 'floor 3': 3 }[read];
            if (idx === undefined) return null;
            const f = floors[idx];
            return `${['GROUND', 'FLOOR 1', 'FLOOR 2', 'FLOOR 3'][idx]} · ${f.name.toUpperCase()}\n${fmt.pct(f.va, 1)} of GDP${f.emp !== null ? ` · ${fmt.pct(f.emp, 1)} of workers · RLP ${f.rlp?.toFixed(2)}` : ' (part of industry)'}`;
          },
        }}
      />

      <LabSection index="A" title="Output shares against employment shares" lede="When a sector’s share of output is far below its share of workers, its workers produce less than the average. The size of the gap is the room structural transformation has to close it.">
        <Controls className="md:grid-cols-3">
          <Field label="Economy">
            <Select value={focus} onChange={setFocus} options={ISOS.map((i) => ({ value: i, label: NAMES[i] }))} />
          </Field>
          <Field label="Year (all six shares observed)">
            <Select value={String(fy ?? '')} onChange={(v) => setYear(Number(v))} options={years.map(String)} />
          </Field>
          <Field label="Value-added basis">
            <Segmented value={rescaled} onChange={setRescaled} options={[{ value: 'published', label: 'As published' }, { value: 'rescaled', label: 'Rescaled to 100' }]} />
          </Field>
        </Controls>
        {snap && (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
            <ChartFrame title={`${NAMES[focus]}, ${fy}`} subtitle="% of GDP (value added) vs % of total employment" source="World Bank WDI; employment shares are ILO modelled estimates.">
              <ResponsiveContainer>
                <BarChart data={snap.rows.map((r) => ({ sector: r.sector, va: rescaled === 'rescaled' ? r.vaRescaled : r.va, emp: r.emp }))} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                  <CartesianGrid {...grid} vertical={false} />
                  <XAxis dataKey="sector" {...axis} />
                  <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                  <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 1)} />
                  <Legend {...legend} />
                  <Bar dataKey="va" name="Share of output" fill="var(--accent)" />
                  <Bar dataKey="emp" name="Share of workers" fill="#f5f0e6" fillOpacity={0.55} />
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
            <div className="grid content-start gap-3">
              <StatRow>
                {snap.rows.map((r) => (
                  <Stat
                    key={r.sector}
                    label={`RLP · ${r.sector}`}
                    value={(rescaled === 'rescaled' ? r.rlpRescaled : r.rlp)?.toFixed(2) ?? '—'}
                    sub={`gap ${fmt.pp(r.gap, 1)}`}
                    tone={SECTOR_COLOUR[r.sector]}
                  />
                ))}
                <Stat label="VA residual" value={fmt.pct(snap.vaResidual, 1)} sub="net taxes & adjustments, not a sector" tone="#8b8d99" />
              </StatRow>
              <Callout title="Consistency check">
                Employment-weighted mean RLP = {weightedRlp(snap.rows, rescaled === 'rescaled').toFixed(3)} (
                {rescaled === 'rescaled' ? 'rescaled basis: should be ≈ 1' : `published basis: equals the VA sum ÷ 100 = ${((snap.vaSum ?? NaN) / 100).toFixed(3)}`}).
              </Callout>
            </div>
          </div>
        )}
      </LabSection>

      <LabSection index="B" title="Relative labour productivity, over time" lede="RLP = sector’s output share ÷ its worker share. 1 is the economy-wide average output per worker. Agriculture well below 1 and services well above is the signature of a dual economy.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title={`RLP by sector, ${NAMES[focus]}`} height={320}>
            <ResponsiveContainer>
              <LineChart data={overTime} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} width={36} />
                <ReferenceLine y={1} stroke="rgba(245,240,230,0.35)" strokeDasharray="4 4" />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(2)} />
                <Legend {...legend} />
                {SECTOR_NAMES.map((s) => (
                  <Line key={s} dataKey={`rlp_${s}`} name={s} stroke={SECTOR_COLOUR[s]} strokeWidth={2.2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Output gap by sector, pp" subtitle="value-added share − employment share" height={320}>
            <ResponsiveContainer>
              <LineChart data={overTime} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} width={36} />
                <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                <Tooltip {...tooltip} formatter={(v) => fmt.pp(Number(v), 1)} />
                <Legend {...legend} />
                {SECTOR_NAMES.map((s) => (
                  <Line key={s} dataKey={`gap_${s}`} name={s} stroke={SECTOR_COLOUR[s]} strokeWidth={2.2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="C" title="How the composition of employment changed" lede="The shares of workers in each sector, stacked to 100%. Manufacturing’s share of GDP, against peers, is a question rather than a claim: a falling share can mean a weak industrial base or a fast-growing services sector.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title={`Employment by sector, ${NAMES[focus]}`} height={320}>
            <ResponsiveContainer>
              <AreaChart data={overTime} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 1)} />
                <Legend {...legend} />
                {SECTOR_NAMES.map((s) => (
                  <Area key={s} dataKey={`emp_${s}`} name={s} stackId="1" stroke={SECTOR_COLOUR[s]} fill={SECTOR_COLOUR[s]} fillOpacity={0.35} />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Manufacturing value added, % of GDP" actions={<span className="label">India + peers</span>} height={320}>
            <ResponsiveContainer>
              <LineChart data={manuf} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmt.pct(Number(v), 1))} />
                <Legend {...legend} />
                {['IND', ...peers].map((i, k) => (
                  <Line key={i} dataKey={i} name={NAMES[i]} stroke={i === 'IND' ? 'var(--accent)' : SERIES[k % SERIES.length]} strokeWidth={i === 'IND' ? 3 : 1.6} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
        <div className="mt-5">
          <Field label="Peer economies">
            <ChipMulti values={peers} onChange={setPeers} options={PEERS} max={6} colour={(i) => SERIES[(peers.indexOf(i) + 1) % SERIES.length]} />
          </Field>
        </div>
      </LabSection>

      <LabSection index="D" title="Who is in the labour force, and in what kind of work" lede="Female labour-force participation is one of the starkest features of India’s labour market. Vulnerable employment — own-account and contributing family workers — measures how much work lies outside wage jobs.">
        <ChartFrame title={`Participation and vulnerable employment, ${NAMES[focus]}`} source="World Bank WDI (ILO modelled estimates)." height={340}>
          <ResponsiveContainer>
            <LineChart data={lfp} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
              <CartesianGrid {...grid} />
              <XAxis dataKey="year" {...axis} />
              <YAxis {...axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} width={40} />
              <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmt.pct(Number(v), 1))} />
              <Legend {...legend} />
              <Line dataKey="male" name="Male LFP" stroke="#4d6ff0" strokeWidth={2.2} dot={false} />
              <Line dataKey="female" name="Female LFP" stroke="#f04a32" strokeWidth={2.2} dot={false} />
              <Line dataKey="vulnerable" name="Vulnerable employment" stroke="#f3c542" strokeWidth={2} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      </LabSection>

      <LabSection index="E" title="India against its peers: farm jobs vs output per worker" lede="Each path is one economy over time. Moving left (fewer farm jobs) and up (more output per worker) is the classic route; the slope of India’s path against the others is the story.">
        <div className="mb-5 flex flex-wrap items-center gap-4">
          <Segmented value={showPaths} onChange={setShowPaths} options={[{ value: 'paths', label: 'Paths over time' }, { value: 'latest', label: 'Latest year only' }]} />
        </div>
        <ChartFrame title="Agricultural employment share vs GDP per person employed" subtitle="log scale on output per worker" source="World Bank WDI: SL.AGR.EMPL.ZS, SL.GDP.PCAP.EM.KD." height={420}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 18, left: 8 }}>
              <CartesianGrid {...grid} />
              <XAxis type="number" dataKey="agri" {...axis} reversed tickFormatter={(v) => `${v}%`} label={{ value: '← fewer farm jobs   ·   % of workers in agriculture', position: 'insideBottom', offset: -10, fill: '#6b6f80', fontSize: 11 }} />
              <YAxis type="number" dataKey="gdpw" scale="log" domain={['auto', 'auto']} {...axis} tickFormatter={(v) => `$${(Number(v) / 1000).toFixed(0)}k`} width={52} />
              <ZAxis range={[28, 28]} />
              <Tooltip
                {...tooltip}
                content={({ payload }) => {
                  const p = payload?.[0]?.payload as { iso: string; year: number; agri: number; gdpw: number } | undefined;
                  if (!p) return null;
                  return (
                    <div style={tooltip.contentStyle} className="px-3 py-2">
                      <div className="text-ink-50">
                        {NAMES[p.iso]} · {p.year}
                      </div>
                      <div>agriculture {fmt.pct(p.agri, 1)} of workers</div>
                      <div>${Math.round(p.gdpw).toLocaleString()} per worker</div>
                    </div>
                  );
                }}
              />
              <Legend {...legend} />
              {scatter.map((s, k) => (
                <Scatter
                  key={s.iso}
                  name={NAMES[s.iso]}
                  data={s.pts}
                  fill={s.iso === 'IND' ? 'var(--accent)' : SERIES[k % SERIES.length]}
                  line={showPaths === 'paths' ? { stroke: s.iso === 'IND' ? 'var(--accent)' : SERIES[k % SERIES.length], strokeWidth: s.iso === 'IND' ? 2.4 : 1.2 } : false}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartFrame>
      </LabSection>

      <LabSection index="F" title="State-level industrialisation and productivity" lede="Gross state value added by sector against PLFS worker shares, for the states in the author-supplied panel.">
        <div className="mb-5">
          <Segmented value={stateView} onChange={setStateView} options={[{ value: 'rlp', label: 'Relative labour productivity' }, { value: 'shares', label: 'Output vs worker shares' }]} />
        </div>
        <ChartFrame title={stateView === 'rlp' ? 'RLP by state and sector' : 'Agriculture: share of output vs share of workers'} source="RBI Handbook GSVA shares; PLFS worker shares (author-supplied file)." height={Math.max(320, stateRows.length * 26)}>
          <ResponsiveContainer>
            {stateView === 'rlp' ? (
              <BarChart data={stateRlp} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 4 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} />
                <YAxis type="category" dataKey="state" {...axis} width={120} interval={0} />
                <ReferenceLine x={1} stroke="rgba(245,240,230,0.35)" strokeDasharray="4 4" />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(2)} />
                <Legend {...legend} />
                <Bar dataKey="rlp_agri" name="Agriculture" fill={SECTOR_COLOUR.Agriculture} />
                <Bar dataKey="rlp_ind" name="Industry" fill={SECTOR_COLOUR.Industry} />
                <Bar dataKey="rlp_serv" name="Services" fill={SECTOR_COLOUR.Services} />
              </BarChart>
            ) : (
              <BarChart data={stateRows} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 4 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => `${v}%`} />
                <YAxis type="category" dataKey="state" {...axis} width={120} interval={0} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 1)} />
                <Legend {...legend} />
                <Bar dataKey="gsva_agri_pct" name="Share of output (GSVA)" fill="var(--accent)" />
                <Bar dataKey="plfs_agri_pct" name="Share of workers (PLFS)" fill="#f5f0e6" fillOpacity={0.55} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </ChartFrame>
      </LabSection>

      <LabSection index="G" title="Findings, generated from the data" lede="Written by the lab’s Python from the same World Bank snapshot — statements of fact about the series, not causal claims.">
        <ol className="grid gap-3 md:grid-cols-2">
          {(D.findings as string[]).map((f, i) => (
            <li key={i} className="flex gap-4 border border-white/[0.08] bg-ink-900/50 p-4 text-[13.5px] leading-relaxed text-ink-200">
              <span className="font-mono text-[12px]" style={{ color: 'var(--accent)' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <span>{f}</span>
            </li>
          ))}
        </ol>
        <div className="mt-8">
          <DataTable
            columns={[
              { key: 'code', label: 'WDI code' },
              { key: 'label', label: 'Indicator' },
              { key: 'unit', label: 'Unit' },
            ]}
            rows={Object.entries(META).map(([code, m]) => ({ code, label: m.label, unit: m.unit }))}
          />
        </div>
      </LabSection>
    </LabShell>
  );
}

export default StructuralLab;
