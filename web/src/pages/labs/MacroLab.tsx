import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
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
  StatusPill,
  axis,
  fmt,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import D from '../../data/labs/macro.json';
import { labBySlug } from '../../labs/registry';

const lab = labBySlug('macro')!;
type Monthly = { indicator: string; reference_period: string; value: number; unit: string; base: string | null; release_type: string | null; status: string; source: string; note: string | null };
type Decision = { effective_date: string; policy_repo_rate_pct: number; change_bp: number; stance: string | null; status: string; source: string; note: string | null };
const MONTHLY = D.monthly as unknown as Monthly[];
const DEC = (D.decisions as unknown as Decision[]).sort((a, b) => a.effective_date.localeCompare(b.effective_date));
const S = D.wdi.series as unknown as Record<string, Record<string, [number, number][]>>;
const NAMES = D.wdi.countries as Record<string, string>;
const META = D.wdiMeta as Record<string, { label: string; unit: string }>;
const CODES = Object.keys(META);
const PEERS = Object.keys(NAMES).filter((i) => i !== 'IND').sort((a, b) => NAMES[a].localeCompare(NAMES[b]));

const LABEL: Record<string, string> = {
  CPI_COMBINED_YOY: 'CPI inflation, combined',
  CPI_RURAL_YOY: 'CPI inflation, rural',
  CPI_URBAN_YOY: 'CPI inflation, urban',
  IIP_GENERAL_YOY: 'Industrial production (IIP)',
  IIP_MANUFACTURING_YOY: 'IIP · manufacturing',
  IIP_ELECTRICITY_YOY: 'IIP · electricity',
  IIP_MINING_YOY: 'IIP · mining',
  HH_INFLATION_EXPECTATION_3M: 'Household inflation expectation, 3 months',
  HH_INFLATION_EXPECTATION_1Y: 'Household inflation expectation, 1 year',
  HH_INFLATION_PERCEPTION: 'Household inflation perception, current',
};

const latestOf = (ind: string) =>
  MONTHLY.filter((m) => m.indicator === ind && /^\d{4}-\d{2}$/.test(m.reference_period)).sort((a, b) => b.reference_period.localeCompare(a.reference_period))[0];

const indLatest = (code: string) => {
  const s = S[code]?.IND ?? [];
  return s.length ? { year: s[s.length - 1][0], value: s[s.length - 1][1], prev: s.length > 1 ? s[s.length - 2][1] : null } : null;
};

const fmtW = (code: string, v: number | null | undefined) => {
  if (v === null || v === undefined) return '—';
  if (code === 'FI.RES.TOTL.CD') return `$${(v / 1e9).toFixed(0)} bn`;
  if (code === 'NY.GDP.PCAP.PP.KD') return `$${Math.round(v).toLocaleString()}`;
  if (code === 'PA.NUS.FCRF') return `₹${v.toFixed(2)}`;
  if (code === 'SI.POV.GINI') return v.toFixed(1);
  return `${v.toFixed(1)}%`;
};

function repoSteps() {
  const out: { date: string; rate: number }[] = [];
  DEC.forEach((d, i) => {
    if (i > 0) out.push({ date: d.effective_date, rate: DEC[i - 1].policy_repo_rate_pct });
    out.push({ date: d.effective_date, rate: d.policy_repo_rate_pct });
  });
  out.push({ date: D.retrieved, rate: DEC[DEC.length - 1].policy_repo_rate_pct });
  return out;
}

export function MacroLab() {
  const [code, setCode] = useState('NY.GDP.MKTP.KD.ZG');
  const [peers, setPeers] = useState<string[]>(D.defaultPeers as string[]);
  const [overlay, setOverlay] = useState<'on' | 'off'>('on');
  const [from, setFrom] = useState(2000);
  const [cmp, setCmp] = useState('NY.GDP.PCAP.PP.KD');

  const line = useMemo(() => {
    const isos = ['IND', ...(overlay === 'on' ? peers : [])];
    const ys = [...new Set(isos.flatMap((i) => (S[code]?.[i] ?? []).map(([y]) => y)))].filter((y) => y >= from).sort((a, b) => a - b);
    return ys.map((y) => {
      const row: Record<string, number | null> = { year: y };
      for (const i of isos) row[i] = S[code]?.[i]?.find(([yy]) => yy === y)?.[1] ?? null;
      return row;
    });
  }, [code, peers, overlay, from]);

  const bars = useMemo(
    () =>
      ['IND', ...PEERS]
        .map((i) => {
          const s = S[cmp]?.[i];
          return s?.length ? { iso: i, name: NAMES[i], year: s[s.length - 1][0], value: s[s.length - 1][1] } : null;
        })
        .filter((x): x is { iso: string; name: string; year: number; value: number } => !!x)
        .sort((a, b) => b.value - a.value),
    [cmp],
  );

  const cpi = MONTHLY.filter((m) => m.indicator.startsWith('CPI_') && /^\d{4}-\d{2}$/.test(m.reference_period));
  const cpiRows = [...new Set(cpi.map((m) => m.reference_period))].sort().map((p) => ({
    p,
    combined: cpi.find((m) => m.reference_period === p && m.indicator === 'CPI_COMBINED_YOY')?.value ?? null,
    rural: cpi.find((m) => m.reference_period === p && m.indicator === 'CPI_RURAL_YOY')?.value ?? null,
    urban: cpi.find((m) => m.reference_period === p && m.indicator === 'CPI_URBAN_YOY')?.value ?? null,
  }));
  const iip = ['IIP_GENERAL_YOY', 'IIP_MANUFACTURING_YOY', 'IIP_ELECTRICITY_YOY', 'IIP_MINING_YOY'].map((k) => ({ k, label: LABEL[k].replace('IIP · ', '').replace('Industrial production (IIP)', 'General'), r: latestOf(k) })).filter((x) => x.r);
  const lastDec = DEC[DEC.length - 1];
  const nowCards = ['CPI_COMBINED_YOY', 'IIP_GENERAL_YOY', 'HH_INFLATION_EXPECTATION_1Y'].map((k) => ({ k, r: latestOf(k) })).filter((x) => x.r);

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            The newest monthly prints — CPI, industrial production, household inflation expectations — and every RBI policy
            decision since 2018. Then twelve World Bank indicators for India against {PEERS.length} peers, snapshotted{' '}
            {D.wdi.retrieved} so the page never depends on the API being up.
          </>
        }
        stats={[
          { label: 'Policy repo rate', value: `${lastDec.policy_repo_rate_pct.toFixed(2)}%`, sub: `${lastDec.change_bp > 0 ? '+' : ''}${lastDec.change_bp} bp on ${lastDec.effective_date}` },
          ...nowCards.slice(0, 2).map(({ k, r }) => ({ label: LABEL[k], value: fmt.pct(r!.value, 2), sub: `${r!.reference_period} · ${r!.release_type ?? ''}` })),
        ]}
        figure={{
          name: 'Cabinet',
          label: 'A rack of twelve blades; each is one World Bank indicator for India.',
          idle: 'Move up and down the rack: each blade is one indicator for India.',
          caption: (read) => {
            const m = /blade (\d+)/.exec(read);
            if (!m) return null;
            const c = CODES[Number(m[1]) - 1];
            const l = c ? indLatest(c) : null;
            return c ? `${META[c].label.toUpperCase()}\nIndia ${l ? `${fmtW(c, l.value)} (${l.year})` : 'no data'}` : null;
          },
        }}
      />

      <LabSection index="N" title="Now — India’s latest monthly releases" lede="Each figure carries its status and source exactly as recorded; scheduled releases are listed but never entered as values before they are published.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title="CPI inflation, % y/y" subtitle="combined, rural and urban" source="MoSPI CPI press releases (base 2024 = 100).">
            <ResponsiveContainer>
              <BarChart data={cpiRows} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} vertical={false} />
                <XAxis dataKey="p" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmt.pct(Number(v), 2))} />
                <Legend {...legend} />
                <Bar dataKey="combined" name="Combined" fill="var(--accent)" />
                <Bar dataKey="rural" name="Rural" fill="#6fae4f" />
                <Bar dataKey="urban" name="Urban" fill="#4d6ff0" />
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title={`Industrial production, % y/y · ${iip[0]?.r?.reference_period ?? ''}`} source="MoSPI IIP quick estimates (base 2022-23 = 100).">
            <ResponsiveContainer>
              <BarChart data={iip.map((x) => ({ label: x.label, value: x.r!.value }))} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} vertical={false} />
                <XAxis dataKey="label" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => `${v}%`} width={40} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 1)} />
                <Bar dataKey="value">
                  {iip.map((x, i) => (
                    <Cell key={x.k} fill={i === 0 ? 'var(--accent)' : SERIES[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <ChartFrame title="RBI policy repo rate" subtitle={`${DEC.length} decisions since ${DEC[0].effective_date}`} source="RBI MPC resolutions (as recorded in the lab’s decision table; status PARTIAL where primary releases were not opened).">
            <ResponsiveContainer>
              <LineChart data={repoSteps()} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="date" {...axis} minTickGap={50} tickFormatter={(d: string) => d.slice(0, 7)} />
                <YAxis {...axis} domain={[3.5, 7]} tickFormatter={(v) => `${v}%`} width={44} />
                <Tooltip {...tooltip} formatter={(v) => fmt.pct(Number(v), 2)} />
                <Line type="linear" dataKey="rate" stroke="var(--accent)" strokeWidth={2.4} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <Stat label={`Latest decision · ${lastDec.effective_date}`} value={`${lastDec.policy_repo_rate_pct.toFixed(2)}%`} sub={`${lastDec.change_bp > 0 ? '+' : ''}${lastDec.change_bp} bp · ${lastDec.stance ?? 'stance not recorded'}`} />
            {lastDec.note && <Callout title="Note">{lastDec.note}</Callout>}
            {(D.calendar as { indicator: string; reference_period: string; scheduled_release_date: string; note: string }[]).map((c) => (
              <Callout key={c.indicator + c.reference_period} tone="accent" title="Scheduled release">
                {c.indicator} for {c.reference_period}, due {c.scheduled_release_date}. {c.note}
              </Callout>
            ))}
          </div>
        </div>
        <div className="mt-6">
          <DataTable
            maxHeight={300}
            columns={[
              { key: 'indicator', label: 'Indicator', format: (v) => LABEL[v as string] ?? (v as string) },
              { key: 'reference_period', label: 'Period' },
              { key: 'value', label: 'Value', align: 'right', format: (v, r) => `${(v as number).toLocaleString('en-IN')} ${String(r.unit)}` },
              { key: 'release_type', label: 'Release' },
              { key: 'status', label: 'Status', format: (v) => <StatusPill status={v as string} /> },
            ]}
            rows={MONTHLY as unknown as Record<string, unknown>[]}
          />
        </div>
      </LabSection>

      <LabSection index="A" title="India — latest published value" lede={`Twelve World Bank WDI indicators, each at its most recent year with an India value.`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
          {CODES.map((c, i) => {
            const l = indLatest(c);
            const d = l && l.prev !== null ? l.value - l.prev : null;
            return (
              <button key={c} type="button" onClick={() => { setCode(c); document.getElementById('one-indicator')?.scrollIntoView({ behavior: 'smooth' }); }} className="text-left">
                <Stat label={META[c].label} value={fmtW(c, l?.value)} sub={l ? `${l.year}${d !== null && c !== 'FI.RES.TOTL.CD' && c !== 'NY.GDP.PCAP.PP.KD' ? ` · ${d >= 0 ? '+' : ''}${d.toFixed(1)} vs prior` : ''}` : 'no India value'} tone={SERIES[i % SERIES.length]} />
              </button>
            );
          })}
        </div>
      </LabSection>

      <LabSection id="one-indicator" index="B" title="One indicator over time">
        <Controls className="md:grid-cols-3">
          <Field label="Indicator">
            <Select value={code} onChange={setCode} options={CODES.map((c) => ({ value: c, label: META[c].label }))} />
          </Field>
          <Field label="From">
            <Select value={String(from)} onChange={(v) => setFrom(Number(v))} options={['1990', '2000', '2010', '2015']} />
          </Field>
          <Field label="Peers">
            <Segmented value={overlay} onChange={setOverlay} options={[{ value: 'on', label: 'Overlay' }, { value: 'off', label: 'India only' }]} />
          </Field>
        </Controls>
        {overlay === 'on' && (
          <div className="mt-4">
            <ChipMulti values={peers} onChange={setPeers} options={PEERS} max={6} colour={(i) => SERIES[(peers.indexOf(i) + 1) % SERIES.length]} />
          </div>
        )}
        <div className="mt-6">
          <ChartFrame title={META[code].label} subtitle={META[code].unit} source={`World Bank WDI ${code}, retrieved ${D.wdi.retrieved}.`} height={380}>
            <ResponsiveContainer>
              <LineChart data={line} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="year" {...axis} />
                <YAxis {...axis} width={64} tickFormatter={(v) => fmtW(code, Number(v))} />
                <Tooltip {...tooltip} formatter={(v) => (v === null ? '—' : fmtW(code, Number(v)))} />
                <Legend {...legend} />
                {['IND', ...(overlay === 'on' ? peers : [])].map((i) => (
                  <Line key={i} dataKey={i} name={NAMES[i]} stroke={i === 'IND' ? 'var(--accent)' : SERIES[(peers.indexOf(i) + 1) % SERIES.length]} strokeWidth={i === 'IND' ? 3 : 1.6} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="C" title="India against its peers — latest year for each">
        <div className="max-w-md">
          <Field label="Compare on">
            <Select value={cmp} onChange={setCmp} options={CODES.map((c) => ({ value: c, label: META[c].label }))} />
          </Field>
        </div>
        <div className="mt-6">
          <ChartFrame title={META[cmp].label} subtitle="each economy at its most recent available year (shown in the tooltip)" height={Math.max(320, bars.length * 26)}>
            <ResponsiveContainer>
              <BarChart data={bars} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 4 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => fmtW(cmp, Number(v))} />
                <YAxis type="category" dataKey="name" {...axis} width={110} interval={0} />
                <Tooltip {...tooltip} formatter={(v, _n, p) => [`${fmtW(cmp, Number(v))} (${(p.payload as { year: number }).year})`, META[cmp].label]} />
                <Bar dataKey="value">
                  {bars.map((b) => (
                    <Cell key={b.iso} fill={b.iso === 'IND' ? 'var(--accent)' : 'rgba(245,240,230,0.28)'} />
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

export default MacroLab;
