import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
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
  Stat,
  StatRow,
  StatusPill,
  axis,
  fmt,
  grid,
  tooltip,
} from '../../components/Lab/LabKit';
import D from '../../data/labs/relationships.json';
import { labBySlug } from '../../labs/registry';
import { fyStart } from '../../models/convergence/engine';
import {
  ModelError,
  SE_LABELS,
  TRANSFORM_LABEL,
  applyRowTransform,
  availableTransforms,
  breuschPagan,
  durbinWatson,
  fitOLS,
  jarqueBera,
  laggedCorrelation,
  pearson,
  qqPoints,
  rollingCorrelation,
  spearman,
  trySimpleOLS,
  verdictLabel,
  vif,
  zscore,
  type OLSFit,
  type SeType,
  type Transform,
} from '../../models/stats/regression';

const lab = labBySlug('relationships')!;

type Key = string | number;
interface VarSpec {
  label: string;
  short: string;
  unit: string;
  status: string;
  source: string;
  period: string;
}
interface Hyp {
  id: string;
  group: string;
  question: string;
  rationale: string;
  kind: 'cross_section' | 'time_series';
  key: string;
  obsNoun: string;
  x: VarSpec;
  y: VarSpec;
  xData: [Key, number | null][];
  yData: [Key, number | null][];
  xTf: Transform;
  yTf: Transform;
  caveats: string[];
  caveatNote: string;
  exclude: Record<string, string>;
  tentativeKeys: Key[];
  periodWord: string;
  notes: string[];
}
interface CatVar {
  id: string;
  level: 'state' | 'india_annual';
  group: string;
  label: string;
  short: string;
  unit: string;
  status: string;
  source: string;
  periods: string[];
  defaultPeriod: string;
  tentative: [Key, string][];
  shareGroup: string;
  note: string;
  frames: Record<string, [Key, number | null][]>;
}
type OverviewRow = Record<string, string | number | null> & { id: string };

const HYPS = D.hypotheses as unknown as Hyp[];
const OVERVIEW = D.overview as unknown as OverviewRow[];
const CAT = D.catalogue as unknown as CatVar[];
const CAVEAT_TEXT = D.caveatText as Record<string, string>;
const LEVELS = D.levels as Record<string, string>;

/** Calendar position of a period key: years as-is, 'YYYY-YY' as its start year. */
const ordinal = (k: Key) => (typeof k === 'number' ? k : /^\d{4}-\d{2}$/.test(k) ? fyStart(k) : NaN);

function align(h: Hyp, includeTentative: boolean) {
  const y = new Map(h.yData.map(([k, v]) => [String(k), v]));
  const tentative = new Set(h.tentativeKeys.map(String));
  const kept: { key: Key; x: number; y: number }[] = [];
  const dropped: { key: string; reason: string }[] = [];
  let onlyX = 0;
  for (const [k, xv] of h.xData) {
    const ks = String(k);
    const yv = y.get(ks);
    if (yv === undefined) {
      onlyX++;
      continue;
    }
    if (xv === null || yv === null) {
      dropped.push({ key: ks, reason: 'missing value in a source' });
      continue;
    }
    if (ks in h.exclude && !(includeTentative && tentative.has(ks))) {
      dropped.push({ key: ks, reason: h.exclude[ks] });
      continue;
    }
    kept.push({ key: k, x: xv, y: yv });
  }
  const onlyY = h.yData.filter(([k]) => !h.xData.some(([kx]) => String(kx) === String(k))).length;
  if (h.kind === 'time_series') kept.sort((a, b) => ordinal(a.key) - ordinal(b.key));
  else kept.sort((a, b) => String(a.key).localeCompare(String(b.key)));
  return { kept, dropped, onlyX, onlyY };
}

function transformPair(rows: { key: Key; x: number; y: number }[], tx: Transform, ty: Transform) {
  const xr = ['log', 'pct_change'].includes(tx) ? applyRowTransform(rows.map((r) => r.x), tx) : rows.map((r) => r.x);
  const yr = ['log', 'pct_change'].includes(ty) ? applyRowTransform(rows.map((r) => r.y), ty) : rows.map((r) => r.y);
  let out = rows.map((r, i) => ({ key: r.key, xRaw: r.x, yRaw: r.y, x: xr[i], y: yr[i] })).filter((r) => Number.isFinite(r.x) && Number.isFinite(r.y));
  if (tx === 'zscore') {
    const z = zscore(out.map((r) => r.x));
    out = out.map((r, i) => ({ ...r, x: z[i] }));
  }
  if (ty === 'zscore') {
    const z = zscore(out.map((r) => r.y));
    out = out.map((r, i) => ({ ...r, y: z[i] }));
  }
  return out;
}

function firstDiffs(rows: { key: Key; x: number; y: number }[]) {
  const out: { key: Key; x: number; y: number }[] = [];
  for (let i = 1; i < rows.length; i++) {
    if (ordinal(rows[i].key) - ordinal(rows[i - 1].key) !== 1) continue;
    out.push({ key: rows[i].key, x: rows[i].x - rows[i - 1].x, y: rows[i].y - rows[i - 1].y });
  }
  return out;
}

function frameOf(v: CatVar, period?: string) {
  return v.frames[period ?? v.defaultPeriod] ?? v.frames[v.defaultPeriod] ?? [];
}

export function RelationshipsLab() {
  const narrow = typeof window !== 'undefined' && window.innerWidth < 768;
  // ---- Hypotheses ----------------------------------------------------------
  const [hid, setHid] = useState('inc_mpce');
  const h = HYPS.find((x) => x.id === hid)!;
  const [tent, setTent] = useState(false);
  const al = useMemo(() => align(h, tent), [h, tent]);
  const ts = h.kind === 'time_series';
  const txOpts = availableTransforms(al.kept.map((r) => r.x), ts);
  const tyOpts = availableTransforms(al.kept.map((r) => r.y), ts);
  const [tx, setTx] = useState<Transform>(h.xTf);
  const [ty, setTy] = useState<Transform>(h.yTf);
  const [lastH, setLastH] = useState(hid);
  if (lastH !== hid) {
    setLastH(hid);
    setTx(h.xTf);
    setTy(h.yTf);
    setTent(false);
  }
  const txE = txOpts.includes(tx) ? tx : 'none';
  const tyE = tyOpts.includes(ty) ? ty : 'none';
  const pair = useMemo(() => transformPair(al.kept, txE, tyE), [al, txE, tyE]);
  const xs = pair.map((p) => p.x);
  const ys = pair.map((p) => p.y);
  const sp = spearman(xs, ys);
  const pe = pearson(xs, ys);
  const ols = trySimpleOLS(xs, ys);
  const v = verdictLabel(sp.r, sp.p);
  const diffs = ts ? firstDiffs(pair) : [];
  const spD = ts ? spearman(diffs.map((d) => d.x), diffs.map((d) => d.y)) : null;
  const vD = spD ? verdictLabel(spD.r, spD.p) : null;
  const fitLine = ols ? [Math.min(...xs), Math.max(...xs)].map((x) => ({ x, fit: ols.intercept + ols.slope * x })) : [];
  const resid = ols ? pair.map((p, i) => ({ key: p.key, fitted: ols.fit.fitted[i], resid: ols.fit.residuals[i] })) : [];

  const [method, setMethod] = useState<'pearson' | 'spearman'>('pearson');
  const lags = ts ? laggedCorrelation(xs, ys, [-3, -2, -1, 0, 1, 2, 3], method) : [];
  const wMax = Math.max(4, Math.floor(pair.length / 2));
  const [win, setWin] = useState(8);
  const winE = Math.min(Math.max(4, win), wMax);
  const rolling = ts && pair.length >= 8 ? rollingCorrelation(pair.map((p) => p.key), xs, ys, winE, method) : [];

  const overviewData = OVERVIEW.map((o) => ({ id: o.id, q: String(o.Hypothesis), rho: Number(o['Spearman ρ']), p: Number(o['p-value']), group: String(o.Group) }));

  // ---- Workbench -----------------------------------------------------------
  const [level, setLevel] = useState<'state' | 'india_annual'>('india_annual');
  const vars = CAT.filter((c) => c.level === level);
  const [yId, setYId] = useState('in_b1_top_1');
  const [xIds, setXIds] = useState<string[]>(['in_c1_top_1', 'in_real_pc_nni']);
  const [seType, setSeType] = useState<SeType>('HC1');
  const [wbTent, setWbTent] = useState(false);
  const yVar = vars.find((c) => c.id === yId) ?? vars[0];
  const xVars = xIds.map((id) => vars.find((c) => c.id === id)).filter((c): c is CatVar => !!c && c.id !== yVar.id);
  const yearsAll = useMemo(() => {
    if (level !== 'india_annual') return [];
    const s = new Set<number>();
    for (const c of [yVar, ...xVars]) for (const [k, val] of frameOf(c)) if (val !== null) s.add(Number(k));
    return [...s].sort((a, b) => a - b);
  }, [level, yVar, xVars]);
  const [sample, setSample] = useState<[number, number]>([1980, 2023]);

  const wb = useMemo(() => {
    const maps = [yVar, ...xVars].map((c) => new Map(frameOf(c).map(([k, val]) => [String(k), val])));
    const tentKeys = new Set([yVar, ...xVars].flatMap((c) => c.tentative.map(([k]) => String(k))));
    const keys = [...maps[0].keys()].filter((k) => maps.every((m) => m.get(k) !== null && m.get(k) !== undefined));
    let used = keys.filter((k) => wbTent || !tentKeys.has(k));
    if (level === 'india_annual') used = used.filter((k) => Number(k) >= sample[0] && Number(k) <= sample[1]).sort((a, b) => Number(a) - Number(b));
    else used.sort();
    const Y = used.map((k) => maps[0].get(k) as number);
    const Xs = xVars.map((_, j) => used.map((k) => maps[j + 1].get(k) as number));
    let fit: OLSFit | null = null;
    let error = '';
    try {
      if (!xVars.length) throw new ModelError('choose at least one explanatory variable.');
      fit = fitOLS(Y, Xs, xVars.map((c) => c.short), seType);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
    const cols = [Y, ...Xs];
    const corr = cols.map((a) => cols.map((b) => pearson(a, b).r));
    const sameShare = xVars.length > 1 && new Set(xVars.map((c) => c.shareGroup).filter(Boolean)).size < xVars.filter((c) => c.shareGroup).length;
    return { keys: used, Y, Xs, fit, error, corr, dropped: keys.length - used.length, sameShare };
  }, [yVar, xVars, seType, wbTent, level, sample]);

  const diag = wb.fit
    ? [breuschPagan(wb.fit, level === 'state'), jarqueBera(wb.fit), ...(level === 'india_annual' ? [durbinWatson(wb.fit)] : [])]
    : [];
  const vifs = wb.fit ? vif(wb.fit) : [];
  const qq = wb.fit ? qqPoints(wb.fit.residuals) : [];

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            {HYPS.length} pre-specified hypotheses over real state, inequality and investment data, each with an alignment
            report, a Spearman verdict and — for time series — a first-difference check against spurious trend. Then a multiple-
            regression workbench over {CAT.length} catalogued variables with robust errors and diagnostics.
          </>
        }
        stats={[
          { label: 'Hypotheses', value: HYPS.length, sub: `${OVERVIEW.filter((o) => Number(o['p-value']) < 0.05).length} significant at 5% in levels` },
          { label: 'Survive differencing', value: OVERVIEW.filter((o) => o['Survives differencing?'] === 'survives').length, sub: `of ${HYPS.filter((x) => x.kind === 'time_series').length} time-series hypotheses` },
          { label: 'Workbench variables', value: CAT.length, sub: 'states and all-India annual' },
        ]}
        figure={{
          name: 'Plot',
          label: 'A bar plot that answers the pointer; each bar is one of the lab’s hypotheses.',
          idle: 'Hover the bars: each is one hypothesis and its verdict.',
          caption: (read) => {
            const m = /^bar (\d+)/.exec(read);
            if (!m) return null;
            const o = overviewData[(Number(m[1]) - 1) % overviewData.length];
            return o ? `${o.q}\nSpearman ρ = ${o.rho.toFixed(2)}, ${fmt.p(o.p)}` : null;
          },
        }}
      />

      <LabSection index="0" title="All hypotheses at a glance" lede="Spearman rank correlation for every hypothesis at its default settings. Solid bars are significant at 5%; faded bars are not. Click one to open it below.">
        <ChartFrame title="Spearman ρ by hypothesis" height={Math.max(360, overviewData.length * 26)}>
          <ResponsiveContainer>
            <BarChart data={overviewData} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }} onClick={(e) => { const id = (e as { activePayload?: { payload: { id: string } }[] })?.activePayload?.[0]?.payload.id; if (id) { setHid(id); document.getElementById('hypothesis')?.scrollIntoView({ behavior: 'smooth' }); } }}>
              <CartesianGrid {...grid} horizontal={false} />
              <XAxis type="number" domain={[-1, 1]} {...axis} />
              <YAxis type="category" dataKey="q" {...axis} width={narrow ? 140 : 360} interval={0} tick={{ ...axis.tick, fontSize: narrow ? 9 : 10.5 }} tickFormatter={(s: string) => { const n = narrow ? 22 : 58; return s.length > n ? `${s.slice(0, n - 2)}…` : s; }} />
              <ReferenceLine x={0} stroke="rgba(245,240,230,0.35)" />
              <Tooltip {...tooltip} formatter={(val, _n, p) => [`ρ = ${Number(val).toFixed(2)}, ${fmt.p((p.payload as { p: number }).p)}`, 'Spearman']} />
              <Bar dataKey="rho" cursor="pointer">
                {overviewData.map((o) => (
                  <Cell key={o.id} fill={o.rho >= 0 ? '#4d6ff0' : '#f04a32'} fillOpacity={o.p < 0.05 ? 0.95 : 0.3} stroke={o.id === hid ? '#f5f0e6' : 'none'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>
      </LabSection>

      <LabSection id="hypothesis" index="A" title="Choose a hypothesis" lede={h.rationale}>
        <Controls className="md:grid-cols-[2fr_1fr_1fr]">
          <Field label="Hypothesis">
            <Select value={hid} onChange={setHid} options={HYPS.map((x) => ({ value: x.id, label: `${x.group} · ${x.question}` }))} />
          </Field>
          <Field label={`X transform · ${h.x.short}`}>
            <Select value={txE} onChange={setTx} options={txOpts.map((t) => ({ value: t, label: TRANSFORM_LABEL[t] }))} />
          </Field>
          <Field label={`Y transform · ${h.y.short}`}>
            <Select value={tyE} onChange={setTy} options={tyOpts.map((t) => ({ value: t, label: TRANSFORM_LABEL[t] }))} />
          </Field>
        </Controls>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {(['x', 'y'] as const).map((k) => (
            <div key={k} className="border border-white/[0.08] bg-ink-900/50 p-4 text-[12.5px] leading-relaxed">
              <div className="mb-2 flex items-center gap-2">
                <span className="label-accent">{k.toUpperCase()}</span>
                <StatusPill status={h[k].status} />
              </div>
              <div className="text-ink-50">{h[k].label}</div>
              <div className="mt-1 text-ink-500">{h[k].source}</div>
            </div>
          ))}
        </div>
        {h.tentativeKeys.length > 0 && (
          <label className="mt-4 inline-flex cursor-pointer items-center gap-2 text-[12.5px] text-ink-300">
            <input type="checkbox" checked={tent} onChange={(e) => setTent(e.target.checked)} /> Include tentative observations ({h.tentativeKeys.join(', ')})
          </label>
        )}
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <Stat label="Matched" value={al.kept.length} sub={`${h.obsNoun} in both sources`} />
          <Stat label="Analysed" value={pair.length} sub={pair.length < al.kept.length ? 'after transforms' : 'all matched'} tone="#f5f0e6" />
          <Stat label="Excluded" value={al.dropped.length} sub="with a stated reason" tone="#f5f0e6" />
          <Stat label="In one source only" value={al.onlyX + al.onlyY} sub={`X only ${al.onlyX} · Y only ${al.onlyY}`} tone="#f5f0e6" />
        </div>
        {(h.caveats.length > 0 || al.dropped.length > 0) && (
          <div className="mt-4 grid gap-3">
            {h.caveats.map((c) => (
              <Callout key={c} tone="warn" title={c.replace(/_/g, ' ')}>
                {CAVEAT_TEXT[c] ?? c}
              </Callout>
            ))}
            {al.dropped.length > 0 && (
              <Callout title="Alignment report">
                {al.dropped.slice(0, 6).map((d) => (
                  <div key={d.key}>
                    <b className="text-ink-50">{d.key}</b> — {d.reason}
                  </div>
                ))}
                {al.dropped.length > 6 && <div>…and {al.dropped.length - 6} more.</div>}
              </Callout>
            )}
          </div>
        )}
      </LabSection>

      <LabSection index="B" title="Result, analysis and statistics" lede="The verdict rests on Spearman’s rank correlation: |ρ| < 0.3 weak, 0.3–0.6 moderate, ≥ 0.6 strong, significant at 5%. Pearson and the OLS slope describe the linear fit.">
        <div className="border border-l-2 bg-ink-900/60 px-5 py-4" style={{ borderColor: 'rgba(245,240,230,0.08)', borderLeftColor: 'var(--accent)' }}>
          <div className="display text-[1.5rem] md:text-[1.9rem]">
            {v.label}
            {!v.significant && v.label !== 'Not computable' && <span className="text-ink-500"> — not significant at 5%</span>}
          </div>
          <div className="mt-2 font-mono text-[12px] text-ink-300">
            Spearman ρ = {fmt.n(sp.r, 3)}, {fmt.p(sp.p)}, n = {pair.length}
            {pair.length <= 8 && ' (exact permutation p)'}
          </div>
        </div>
        <div className="mt-5">
          <StatRow>
            <Stat label="Pearson r" value={fmt.n(pe.r, 3)} sub={fmt.p(pe.p)} tone="#f5f0e6" />
            <Stat label="OLS slope" value={ols ? ols.slope.toPrecision(3) : '—'} sub={ols ? `95% CI [${ols.ciLow.toPrecision(3)}, ${ols.ciHigh.toPrecision(3)}]` : 'not computable'} />
            <Stat label="R²" value={ols ? ols.r2.toFixed(3) : '—'} sub={ols ? fmt.p(ols.p) : ''} tone="#f5f0e6" />
            {ts ? (
              <Stat label="First differences" value={spD ? fmt.n(spD.r, 2) : '—'} sub={vD ? `${vD.label.toLowerCase()}, n = ${diffs.length}` : ''} tone={spD && Math.abs(spD.r) < 0.3 && Math.abs(sp.r) >= 0.6 ? '#f04a32' : '#6fae4f'} />
            ) : (
              <Stat label="Sample" value={pair.length < 20 ? 'small' : 'adequate'} sub={pair.length < 20 ? 'n < 20: treat p-values with caution' : `n = ${pair.length}`} tone="#f5f0e6" />
            )}
          </StatRow>
        </div>
        {ts && spD && (
          <div className="mt-4">
            <Callout tone={Math.abs(sp.r) >= 0.6 && Math.abs(spD.r) < 0.3 ? 'warn' : 'accent'} title="Levels vs first differences">
              {Math.abs(sp.r) >= 0.6 && Math.abs(spD.r) < 0.3
                ? `The association in levels (ρ = ${sp.r.toFixed(2)}) vanishes in year-on-year changes (ρ = ${spD.r.toFixed(2)}): the two series mostly share a trend. Treat the levels result as likely spurious.`
                : `Year-on-year changes give ρ = ${spD.r.toFixed(2)} (${fmt.p(spD.p)}, n = ${diffs.length}), so the association is not only a shared trend. Only consecutive ${h.periodWord}s are differenced; gaps are never bridged.`}
            </Callout>
          </div>
        )}
      </LabSection>

      <LabSection index="C" title="Scatter and residuals">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title={`${h.y.short} vs ${h.x.short}`} subtitle={`${TRANSFORM_LABEL[tyE]} vs ${TRANSFORM_LABEL[txE]}; dashed line = OLS fit`} height={380}>
            <ResponsiveContainer>
              <ComposedChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis type="number" dataKey="x" domain={['auto', 'auto']} {...axis} tickFormatter={(val) => Number(val).toPrecision(3)} />
                <YAxis type="number" dataKey="y" domain={['auto', 'auto']} {...axis} tickFormatter={(val) => Number(val).toPrecision(3)} width={56} />
                <Tooltip
                  {...tooltip}
                  content={({ payload }) => {
                    const p = payload?.[0]?.payload as { key?: Key; xRaw?: number; yRaw?: number } | undefined;
                    if (p?.key === undefined) return null;
                    return (
                      <div style={tooltip.contentStyle} className="px-3 py-2">
                        <div className="text-ink-50">{String(p.key)}</div>
                        <div>X {p.xRaw?.toLocaleString('en-IN')}</div>
                        <div>Y {p.yRaw?.toLocaleString('en-IN')}</div>
                      </div>
                    );
                  }}
                />
                <Scatter data={pair} fill="var(--accent)" fillOpacity={0.85} />
                <Line data={fitLine} dataKey="fit" stroke="#f5f0e6" strokeDasharray="5 4" dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="Residuals vs fitted" subtitle="No pattern is what you want to see." height={380}>
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis type="number" dataKey="fitted" domain={['auto', 'auto']} {...axis} tickFormatter={(val) => Number(val).toPrecision(3)} />
                <YAxis type="number" dataKey="resid" {...axis} tickFormatter={(val) => Number(val).toPrecision(2)} width={56} />
                <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                <Tooltip {...tooltip} formatter={(val) => Number(val).toPrecision(4)} />
                <Scatter data={resid} fill="#4d6ff0" />
              </ScatterChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      {ts && (
        <LabSection index="D" title="Over time: lagged and rolling correlation" lede="Positive lag k means X leads Y by k periods. Shifting is by observation, so n shrinks as |k| grows.">
          <div className="mb-5 flex flex-wrap items-center gap-6">
            <Segmented value={method} onChange={setMethod} options={[{ value: 'pearson', label: 'Pearson' }, { value: 'spearman', label: 'Spearman' }]} />
            {pair.length >= 8 && (
              <div className="w-72">
                <Range label={`Rolling window (${h.periodWord}s)`} value={winE} min={4} max={wMax} onChange={setWin} />
              </div>
            )}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <ChartFrame title="Correlation by lag" height={300}>
              <ResponsiveContainer>
                <BarChart data={lags} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                  <CartesianGrid {...grid} vertical={false} />
                  <XAxis dataKey="lag" {...axis} />
                  <YAxis domain={[-1, 1]} {...axis} width={36} />
                  <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                  <Tooltip {...tooltip} formatter={(val, _n, p) => [`${Number(val).toFixed(2)} (n = ${(p.payload as { n: number }).n})`, 'r']} />
                  <Bar dataKey="r">
                    {lags.map((l) => (
                      <Cell key={l.lag} fill={l.lag === 0 ? 'var(--accent)' : l.p < 0.05 ? '#4d6ff0' : 'rgba(77,111,240,0.35)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
            <ChartFrame title={`Rolling ${winE}-${h.periodWord} correlation`} height={300}>
              <ResponsiveContainer>
                <LineChart data={rolling} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                  <CartesianGrid {...grid} />
                  <XAxis dataKey="key" {...axis} />
                  <YAxis domain={[-1, 1]} {...axis} width={36} />
                  <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                  <Tooltip {...tooltip} formatter={(val) => Number(val).toFixed(2)} />
                  <Line dataKey="r" stroke="var(--accent)" strokeWidth={2.2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartFrame>
          </div>
        </LabSection>
      )}

      <LabSection index={ts ? 'E' : 'D'} title="Regression workbench" lede="Multiple OLS over the catalogue, with classical, HC1 or Newey–West HAC standard errors, pairwise correlations, diagnostics and VIFs. Every p-value uses Student’s t on n − k − 1 degrees of freedom.">
        <Controls className="md:grid-cols-3">
          <Field label="Geographic level">
            <Select
              value={level}
              onChange={(l) => {
                setLevel(l);
                const first = CAT.filter((c) => c.level === l);
                setYId(l === 'state' ? 'st_unemployment' : 'in_b1_top_1');
                setXIds(l === 'state' ? ['st_mpce_urban', 'st_nsdp_current'] : ['in_c1_top_1', 'in_real_pc_nni']);
                if (!first.length) return;
              }}
              options={Object.entries(LEVELS).map(([value, label]) => ({ value: value as 'state' | 'india_annual', label }))}
            />
          </Field>
          <Field label="Dependent variable (Y)">
            <Select value={yVar.id} onChange={setYId} options={vars.map((c) => ({ value: c.id, label: c.label }))} />
          </Field>
          <Field label="Standard errors">
            <Select value={seType} onChange={setSeType} options={(Object.keys(SE_LABELS) as SeType[]).filter((s) => level === 'india_annual' || s !== 'HAC').map((s) => ({ value: s, label: SE_LABELS[s] }))} />
          </Field>
        </Controls>
        <div className="mt-4 border border-white/[0.08] bg-ink-900/50 p-4">
          <Field label={`Explanatory variables (X) — up to 4`}>
            <ChipMulti values={xIds} onChange={setXIds} options={vars.filter((c) => c.id !== yVar.id).map((c) => c.id)} max={4} />
          </Field>
          <div className="mt-2 text-[11.5px] text-ink-500">{xVars.map((c) => `${c.id} = ${c.label}`).join(' · ')}</div>
          {level === 'india_annual' && yearsAll.length > 2 && (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <Range label="Sample start" value={Math.max(sample[0], yearsAll[0])} min={yearsAll[0]} max={yearsAll[yearsAll.length - 1]} onChange={(s) => setSample([s, Math.max(s + 3, sample[1])])} />
              <Range label="Sample end" value={Math.min(sample[1], yearsAll[yearsAll.length - 1])} min={yearsAll[0]} max={yearsAll[yearsAll.length - 1]} onChange={(e) => setSample([Math.min(sample[0], e - 3), e])} />
            </div>
          )}
          {CAT.some((c) => c.tentative.length && (c.id === yVar.id || xIds.includes(c.id))) && (
            <label className="mt-3 inline-flex items-center gap-2 text-[12.5px] text-ink-300">
              <input type="checkbox" checked={wbTent} onChange={(e) => setWbTent(e.target.checked)} /> Include tentative observations
            </label>
          )}
        </div>
        {wb.sameShare && (
          <div className="mt-4">
            <Callout tone="warn" title="Parts of one total">Two of the chosen regressors are shares of the same total; their coefficients are hard to interpret separately and may be perfectly collinear.</Callout>
          </div>
        )}
        {wb.error ? (
          <div className="mt-6">
            <Callout tone="warn" title="Model not estimated">{wb.error}</Callout>
          </div>
        ) : (
          wb.fit && (
            <div className="mt-6 grid gap-6">
              <StatRow>
                <Stat label="Observations" value={wb.fit.n} sub={level === 'india_annual' ? `${wb.keys[0]}–${wb.keys[wb.keys.length - 1]}` : 'states / UTs'} />
                <Stat label="R² · adjusted" value={`${wb.fit.r2.toFixed(3)} · ${wb.fit.adjR2.toFixed(3)}`} tone="#f5f0e6" />
                <Stat label={seType === 'nonrobust' ? 'F-test' : 'Wald F'} value={wb.fit.f.toFixed(2)} sub={fmt.p(wb.fit.fP)} tone="#f5f0e6" />
                <Stat label="Standard errors" value={seType === 'HAC' ? `HAC (${wb.fit.hacLags})` : seType === 'HC1' ? 'HC1' : 'classical'} sub={SE_LABELS[seType]} tone="#f5f0e6" />
              </StatRow>
              <DataTable
                columns={[
                  { key: 'term', label: 'Term' },
                  { key: 'coef', label: 'Coefficient', align: 'right', format: (val) => (val as number).toPrecision(4) },
                  { key: 'se', label: 'Std. error', align: 'right', format: (val) => (val as number).toPrecision(3) },
                  { key: 't', label: 't', align: 'right', format: (val) => (val as number).toFixed(2) },
                  { key: 'p', label: 'p', align: 'right', format: (val) => <span style={{ color: (val as number) < 0.05 ? '#6fae4f' : '#8b8d99' }}>{fmt.p(val as number)}</span> },
                  { key: 'ciLow', label: '95% CI', align: 'right', format: (val, r) => `[${(val as number).toPrecision(3)}, ${(r.ciHigh as number).toPrecision(3)}]` },
                ]}
                rows={wb.fit.terms as unknown as Record<string, unknown>[]}
              />
              <div className="grid gap-6 lg:grid-cols-3">
                <ChartFrame title="Residuals vs fitted" height={260}>
                  <ResponsiveContainer>
                    <ScatterChart margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
                      <CartesianGrid {...grid} />
                      <XAxis type="number" dataKey="f" domain={['auto', 'auto']} {...axis} tickFormatter={(val) => Number(val).toPrecision(3)} />
                      <YAxis type="number" dataKey="e" {...axis} width={48} tickFormatter={(val) => Number(val).toPrecision(2)} />
                      <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                      <Scatter data={wb.fit.fitted.map((f, i) => ({ f, e: wb.fit!.residuals[i] }))} fill="var(--accent)" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </ChartFrame>
                <ChartFrame title="Normal QQ plot" subtitle="standardised residuals" height={260}>
                  <ResponsiveContainer>
                    <ComposedChart margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
                      <CartesianGrid {...grid} />
                      <XAxis type="number" dataKey="theo" domain={[-3, 3]} {...axis} />
                      <YAxis type="number" dataKey="sample" domain={[-3.5, 3.5]} {...axis} width={36} />
                      <Line data={[{ theo: -3, sample: -3 }, { theo: 3, sample: 3 }]} dataKey="sample" stroke="rgba(245,240,230,0.35)" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                      <Scatter data={qq} fill="#4d6ff0" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </ChartFrame>
                <div className="grid content-start gap-3">
                  {vifs.map((x) => (
                    <Stat key={x.term} label={`VIF · ${x.term}`} value={x.vif.toFixed(2)} sub={x.vif >= 10 ? 'high collinearity' : x.vif >= 5 ? 'notable' : 'fine'} tone={x.vif >= 10 ? '#f04a32' : x.vif >= 5 ? '#f3c542' : '#6fae4f'} />
                  ))}
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                {diag.map((d) => (
                  <div key={d.test} className="border border-white/[0.08] bg-ink-900/50 p-4 text-[12.5px] leading-relaxed text-ink-300">
                    <div className="label-accent">{d.test}</div>
                    <div className="mt-1 text-[15px] text-ink-50">{d.verdict}</div>
                    <div className="mt-1 font-mono text-[11px] text-ink-500">
                      {d.detail} = {d.statistic.toFixed(3)}
                      {Number.isFinite(d.p) && `, ${fmt.p(d.p)}`}
                    </div>
                    <p className="mt-2">{d.interpretation}</p>
                  </div>
                ))}
              </div>
              <div>
                <div className="label mb-3">Pairwise Pearson correlation in the analysis sample</div>
                <div className="overflow-x-auto">
                  <table className="border-collapse font-mono text-[11.5px]">
                    <thead>
                      <tr>
                        <th />
                        {[yVar, ...xVars].map((c) => (
                          <th key={c.id} className="px-3 py-2 text-left font-normal text-ink-400">
                            {c.id}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[yVar, ...xVars].map((c, i) => (
                        <tr key={c.id}>
                          <td className="px-3 py-2 text-ink-400">{c.id}</td>
                          {wb.corr[i].map((r, j) => (
                            <td key={j} className="px-3 py-2 text-center" style={{ background: `rgba(${r >= 0 ? '77,111,240' : '240,74,50'},${Math.abs(r) * 0.55})`, color: '#f5f0e6' }}>
                              {Number.isFinite(r) ? r.toFixed(2) : '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <Callout title="Association is not causation">{String(D.causationNote).replace(/\*\*/g, '')}</Callout>
            </div>
          )
        )}
      </LabSection>
    </LabShell>
  );
}

export default RelationshipsLab;
