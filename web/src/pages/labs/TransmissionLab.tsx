import { motion } from 'framer-motion';
import { Download, RotateCcw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  Callout,
  ChartFrame,
  Controls,
  Field,
  LabHero,
  LabSection,
  LabShell,
  Range,
  Segmented,
  StatusPill,
  axis,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import D from '../../data/labs/transmission.json';
import { labBySlug } from '../../labs/registry';
import { useReducedMotionPref } from '../../lib/motion';
import {
  NEEDS_PARAMETER,
  NOT_APPLICABLE,
  QUALITATIVE,
  QUANTIFIED,
  diagramEdges,
  formatValue,
  marshallLerner,
  run,
  type Link,
  type Params,
  type Status,
} from '../../models/transmission/engine';

const lab = labBySlug('transmission')!;
interface Scenario {
  key: string;
  title: string;
  shockLabel: string;
  shockUnit: string;
  slider: [number, number, number, number];
  nodes: string[];
  qualitative: [string, string, string][];
}
interface ParamRow {
  parameter: string;
  param_set: string;
  value: number | null;
  unit: string;
  horizon: string;
  source_citation: string;
  url: string;
  quote_or_context: string;
  verified_via: string;
  status: string;
}
const SCN = D.scenarios as unknown as Record<string, Scenario>;
const LINKS = D.links as unknown as Record<string, Link[]>;
const SPECS = D.specs as Record<string, { label: string; scenario: string; step: number; isDataInput: boolean }>;
const ROWS = D.parameters as unknown as ParamRow[];
const DEF_A = D.defaultsA as Params;
const DEF_B = D.defaultsB as Params;
const KEYS = Object.keys(SCN);
const REGIMES = D.regimes as string[];
const STATUS_COLOUR: Record<Status, string> = {
  [QUANTIFIED]: '#f0663f',
  [NEEDS_PARAMETER]: '#f3c542',
  [NOT_APPLICABLE]: '#4b5064',
  [QUALITATIVE]: '#8b8d99',
};
const citation = (k: string, set: 'A' | 'B') => ROWS.find((r) => r.parameter === k && r.param_set === set) ?? ROWS.find((r) => r.parameter === k && r.param_set === 'A');

function Diagram({ scenario, results }: { scenario: Scenario; results: ReturnType<typeof run> }) {
  const reduced = useReducedMotionPref();
  const edges = diagramEdges(results, scenario.qualitative);
  const depth = new Map<string, number>([[scenario.nodes[0], 0]]);
  for (let pass = 0; pass < scenario.nodes.length; pass++)
    for (const e of edges) if (depth.has(e.source)) depth.set(e.target, Math.max(depth.get(e.target) ?? 0, depth.get(e.source)! + 1));
  scenario.nodes.forEach((n) => depth.has(n) || depth.set(n, 1));
  const cols = Math.max(...depth.values()) + 1;
  const byCol: string[][] = Array.from({ length: cols }, () => []);
  scenario.nodes.forEach((n) => byCol[depth.get(n)!].push(n));
  const W = 1000;
  const rowH = 92;
  const H = Math.max(...byCol.map((c) => c.length)) * rowH + 40;
  const pos = new Map<string, { x: number; y: number }>();
  byCol.forEach((col, ci) => col.forEach((n, ri) => pos.set(n, { x: 70 + (ci * (W - 230)) / Math.max(1, cols - 1), y: (H - col.length * rowH) / 2 + ri * rowH + rowH / 2 })));
  const valueOf = (n: string) => results.find((r) => r.link.target === n && r.status === QUANTIFIED);

  return (
    <div className="overflow-x-auto" data-lenis-prevent>
      <svg viewBox={`0 0 ${W} ${H}`} className="min-w-[720px]" role="img" aria-label={`Causal chain for the ${scenario.title.toLowerCase()}`}>
        <defs>
          {Object.entries(STATUS_COLOUR).map(([s, c]) => (
            <marker key={s} id={`arr-${s.replace(/\W/g, '')}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill={c} />
            </marker>
          ))}
        </defs>
        {edges.map((e, i) => {
          const a = pos.get(e.source);
          const b = pos.get(e.target);
          if (!a || !b) return null;
          const x1 = a.x + 75;
          const x2 = b.x - 80;
          const mx = (x1 + x2) / 2;
          const d = `M${x1},${a.y} C${mx},${a.y} ${mx},${b.y} ${x2},${b.y}`;
          const c = STATUS_COLOUR[e.status];
          const q = e.status === QUANTIFIED;
          return (
            <g key={i}>
              <title>{`${e.source} → ${e.target}: ${e.label}`}</title>
              <path d={d} fill="none" stroke={c} strokeOpacity={q ? 0.9 : 0.55} strokeWidth={q ? 1.8 : 1.2} strokeDasharray={q ? undefined : '4 5'} markerEnd={`url(#arr-${e.status.replace(/\W/g, '')})`} />
              {q && !reduced && (
                <motion.path d={d} fill="none" stroke="#f5f0e6" strokeWidth={2.2} strokeLinecap="round" strokeDasharray="6 160" initial={{ strokeDashoffset: 166 }} animate={{ strokeDashoffset: 0 }} transition={{ duration: 2.4, repeat: Infinity, ease: 'linear', delay: i * 0.18 }} />
              )}
            </g>
          );
        })}
        {[...pos.entries()].map(([n, p], i) => {
          const r = valueOf(n);
          const root = n === scenario.nodes[0];
          return (
            <motion.g key={n} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * i, duration: 0.5 }}>
              <rect x={p.x - 78} y={p.y - 28} width={156} height={56} fill={root ? 'rgba(240,102,63,0.16)' : '#141720'} stroke={root || r ? '#f0663f' : 'rgba(245,240,230,0.16)'} strokeWidth={root ? 1.4 : 1} />
              <text x={p.x} y={p.y - (r ? 6 : -4)} textAnchor="middle" fill="#e6e0d3" fontSize={11.5} fontFamily="Inter, sans-serif">
                {n.length > 26 ? `${n.slice(0, 25)}…` : n}
              </text>
              {r && (
                <text x={p.x} y={p.y + 14} textAnchor="middle" fill="#f0663f" fontSize={12} fontFamily='"JetBrains Mono", monospace'>
                  {formatValue(r.value, r.status, r.link.unit)}
                </text>
              )}
            </motion.g>
          );
        })}
      </svg>
    </div>
  );
}

function download(name: string, text: string, type: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function TransmissionLab() {
  const [scn, setScn] = useState('policy');
  const S = SCN[scn];
  const [shocks, setShocks] = useState<Record<string, number>>(Object.fromEntries(KEYS.map((k) => [k, SCN[k].slider[2]])));
  const shock = shocks[scn];
  const [regime, setRegime] = useState(REGIMES[0]);
  const [pa, setPa] = useState<Params>({ ...DEF_A });
  const [pb, setPb] = useState<Params>({ ...DEF_B });

  const links = LINKS[scn];
  const resA = useMemo(() => run(links, shock, pa, regime), [links, shock, pa, regime]);
  const resB = useMemo(() => run(links, shock, pb, regime), [links, shock, pb, regime]);
  const used = [...new Set(links.flatMap((l) => l.params))];

  const bars = resA.map((r, i) => ({ effect: r.link.label.replace(/^Δ /, ''), unit: r.link.unit, A: r.value, B: resB[i].value }));
  const jcurve = scn === 'rupee' ? resA.filter((r) => r.link.id.startsWith('trade_balance')) : [];
  const ml = scn === 'rupee' ? marshallLerner(pa.export_price_elasticity_lr ?? null, pa.import_price_elasticity_lr ?? null) : null;

  const headline = (k: string) => {
    const r = run(LINKS[k], SCN[k].slider[2], DEF_A, REGIMES[0]).find((x) => x.status === QUANTIFIED && /cpi|gdp/.test(x.link.id));
    return r ? `${r.link.label}: ${formatValue(r.value, r.status, r.link.unit)}` : '';
  };

  const exportRun = (kind: 'json' | 'csv') => {
    const payload = {
      label: D.label,
      generated_at_utc: new Date().toISOString(),
      scenario: { key: scn, title: S.title, shock, shock_unit: S.shockUnit, oil_regime: scn === 'oil' ? regime : null },
      outputs: resA.map((r, i) => ({ effect: r.link.label, from: r.link.source, to: r.link.target, unit: r.link.unit, horizon: r.link.horizon, set_A: r.value, status_A: r.status, set_B: resB[i].value, status_B: resB[i].status })),
      parameters: used.map((k) => ({ parameter: k, set_A: pa[k] ?? null, set_B: pb[k] ?? null, default_A: DEF_A[k] ?? null, citation: citation(k, 'A')?.source_citation ?? '', url: citation(k, 'A')?.url ?? '' })),
    };
    if (kind === 'json') download(`transmission-${scn}.json`, JSON.stringify(payload, null, 2), 'application/json');
    else {
      const head = `# ${D.label}\n# scenario: ${S.title}; shock ${shock} ${S.shockUnit}\n`;
      const rows = ['section,effect,unit,horizon,set_A,status_A,set_B,status_B', ...payload.outputs.map((o) => ['output', JSON.stringify(o.effect), o.unit, JSON.stringify(o.horizon), o.set_A ?? '', o.status_A, o.set_B ?? '', o.status_B].join(','))];
      download(`transmission-${scn}.csv`, head + rows.join('\n'), 'text/csv');
    }
  };

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Linear, partial-equilibrium transmission chains for four shocks to India’s economy. Every coefficient carries its
            citation, the horizon it applies to and how it was verified; links with no verifiable India estimate are drawn but
            left unquantified. <b className="text-ink-50">{D.label}.</b>
          </>
        }
        stats={KEYS.slice(0, 3).map((k) => ({ label: SCN[k].title, value: `${SCN[k].slider[2] > 0 ? '+' : ''}${SCN[k].slider[2]}${SCN[k].shockUnit === 'bps' ? ' bps' : SCN[k].shockUnit === '%' ? '%' : ` ${SCN[k].shockUnit}`}`, sub: headline(k) }))}
        figure={{
          name: 'Dish',
          label: 'A dish antenna the pointer aims; each direction is one of the four shock scenarios.',
          idle: 'Aim the dish: each quarter of the sky is one shock scenario.',
          caption: (read) => {
            const m = /az (\d+)/.exec(read);
            if (!m) return null;
            const k = KEYS[Math.min(KEYS.length - 1, Math.floor((Number(m[1]) / 90) * KEYS.length))];
            return `${SCN[k].title.toUpperCase()}\n${headline(k)}`;
          },
        }}
      />

      <LabSection index="1" title="Choose a shock">
        <div className="grid gap-3 md:grid-cols-4">
          {KEYS.map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setScn(k)}
              className="group relative border p-4 text-left transition-colors"
              style={{ borderColor: k === scn ? 'var(--accent)' : 'rgba(245,240,230,0.1)', background: k === scn ? 'rgba(240,102,63,0.08)' : 'rgba(17,19,26,0.5)' }}
            >
              <div className="label" style={{ color: k === scn ? 'var(--accent)' : undefined }}>
                Scenario
              </div>
              <div className="mt-2 text-[15px] text-ink-50">{SCN[k].title}</div>
              <div className="mt-1 text-[12px] text-ink-400">{SCN[k].shockLabel}</div>
            </button>
          ))}
        </div>
        <Controls className="mt-5 md:grid-cols-2">
          <Range
            label={`${S.shockLabel} (${S.shockUnit})`}
            value={shock}
            min={S.slider[0]}
            max={S.slider[1]}
            step={S.slider[3]}
            onChange={(val) => setShocks({ ...shocks, [scn]: val })}
            format={(val) => `${val > 0 ? '+' : ''}${val} ${S.shockUnit}`}
          />
          {scn === 'oil' && (
            <Field label="Who bears the oil shock?">
              <Segmented value={regime} onChange={setRegime} options={REGIMES} />
            </Field>
          )}
        </Controls>
      </LabSection>

      <LabSection index="2" title={`The chain — ${S.title.toLowerCase()}`} lede="Solid, animated links are quantified from cited coefficients; amber links need a parameter that has none; grey dashed links are real channels with no cited India coefficient.">
        <div className="ticked border border-white/[0.08] bg-ink-900/50 p-4 md:p-6">
          <Diagram scenario={S} results={resA} />
          <div className="mt-4 flex flex-wrap gap-4">
            {Object.entries(STATUS_COLOUR).map(([s, c]) => (
              <span key={s} className="inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.12em] text-ink-400">
                <span className="h-px w-6" style={{ background: c, height: 2 }} /> {s}
              </span>
            ))}
          </div>
        </div>
      </LabSection>

      <LabSection index="3" title="Baseline vs scenario, set A vs set B" lede="The baseline (no shock) is zero by construction for every link. Set B uses alternative cited values where they exist and falls back to set A elsewhere — edit either below.">
        <ChartFrame title={`Effects of ${shock > 0 ? '+' : ''}${shock} ${S.shockUnit}`} subtitle="units differ by row; hover for each effect’s unit" height={Math.max(260, bars.length * 54)}>
          <ResponsiveContainer>
            <BarChart data={bars} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
              <CartesianGrid {...grid} horizontal={false} />
              <XAxis type="number" {...axis} />
              <YAxis type="category" dataKey="effect" {...axis} width={260} interval={0} tick={{ ...axis.tick, fontSize: 10.5 }} />
              <ReferenceLine x={0} stroke="rgba(245,240,230,0.35)" />
              <Tooltip {...tooltip} formatter={(val, n, p) => [val === null ? 'not quantified' : `${Number(val) >= 0 ? '+' : ''}${Number(val).toFixed(3)} ${(p.payload as { unit: string }).unit}`, n]} />
              <Legend {...legend} />
              <Bar dataKey="A" name="Set A (cited defaults)" fill="var(--accent)" />
              <Bar dataKey="B" name="Set B (comparison)" fill="#4d6ff0" />
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>
        {scn === 'rupee' && (
          <div className="mt-5">
            <Callout tone="accent" title="Short run vs long run: the J-curve">
              Short run: {formatValue(jcurve[0]?.value ?? null, jcurve[0]?.status ?? NEEDS_PARAMETER, 'pp of GDP')}; long run: {formatValue(jcurve[1]?.value ?? null, jcurve[1]?.status ?? NEEDS_PARAMETER, 'pp of GDP')}. With low short-run elasticities the
              trade balance first worsens after a depreciation, then improves as volumes adjust. Marshall–Lerner (|ε_X| + |ε_M| &gt; 1, long run):{' '}
              {ml === null ? 'cannot be checked — an elasticity is missing' : ml ? 'satisfied' : 'not satisfied'}.
            </Callout>
          </div>
        )}
      </LabSection>

      <LabSection index="4" title="Parameters — cited defaults, editable" lede="Change any value to see its effect ripple through the chain. Edited values lose their citation in the export, and are labelled USER-SET.">
        <div className="mb-4 flex flex-wrap gap-2">
          <button type="button" className="btn" onClick={() => setPa({ ...DEF_A })}>
            <RotateCcw size={12} /> Reset set A
          </button>
          <button type="button" className="btn" onClick={() => setPb({ ...DEF_B })}>
            <RotateCcw size={12} /> Reset set B
          </button>
        </div>
        <div className="grid gap-3">
          {used.map((k) => {
            const ca = citation(k, 'A');
            const edited = (pa[k] ?? null) !== (DEF_A[k] ?? null) || (pb[k] ?? null) !== (DEF_B[k] ?? null);
            return (
              <div key={k} className="grid gap-4 border border-white/[0.08] bg-ink-900/50 p-4 md:grid-cols-[1.4fr_120px_120px_2fr]">
                <div>
                  <div className="text-[13.5px] text-ink-50">{SPECS[k]?.label ?? k}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <StatusPill status={edited ? 'USER-SET' : (ca?.status ?? 'DATA REQUIRED')} />
                    {SPECS[k]?.isDataInput && <span className="label">data input</span>}
                  </div>
                </div>
                {(['A', 'B'] as const).map((set) => {
                  const p = set === 'A' ? pa : pb;
                  const setter = set === 'A' ? setPa : setPb;
                  return (
                    <Field key={set} label={`Set ${set}`}>
                      <input
                        className="numfield"
                        type="number"
                        step={SPECS[k]?.step ?? 0.01}
                        value={p[k] ?? ''}
                        placeholder="needs value"
                        onChange={(e) => setter({ ...p, [k]: e.target.value === '' ? null : Number(e.target.value) })}
                      />
                    </Field>
                  );
                })}
                <div className="text-[11.5px] leading-relaxed text-ink-400">
                  {ca?.source_citation ? (
                    <>
                      <a href={ca.url} target="_blank" rel="noreferrer" className="text-ink-200 underline decoration-white/20 underline-offset-2 hover:decoration-[var(--accent)]">
                        {ca.source_citation}
                      </a>
                      <div className="mt-1 text-ink-500">{ca.horizon}</div>
                    </>
                  ) : (
                    <span className="text-[#f3c542]">DATA REQUIRED — no verifiable India estimate yet.</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </LabSection>

      <LabSection index="5" title="Equations, assumptions and sources — link by link">
        <div className="grid gap-3 lg:grid-cols-2">
          {links.map((l) => {
            const r = resA.find((x) => x.link.id === l.id)!;
            return (
              <div key={l.id} className="border border-white/[0.08] bg-ink-900/50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="label">
                    {l.source} → {l.target}
                  </span>
                  <span className="font-mono text-[12px]" style={{ color: STATUS_COLOUR[r.status] }}>
                    {formatValue(r.value, r.status, l.unit)}
                  </span>
                </div>
                <div className="mt-2 text-[14px] text-ink-50">{l.label}</div>
                <code className="mt-3 block overflow-x-auto whitespace-pre border border-white/[0.06] bg-ink-950 px-3 py-2 font-mono text-[11px] text-ink-300">{l.equation}</code>
                <ul className="mt-3 list-disc space-y-1 pl-4 text-[12px] leading-relaxed text-ink-400">
                  {l.assumptions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                  <li>Horizon: {l.horizon}.</li>
                </ul>
              </div>
            );
          })}
        </div>
        <div className="mt-6 grid gap-3">
          <div className="label">Qualitative links — real channels, no cited coefficient</div>
          {S.qualitative.map(([a, b, why]) => (
            <Callout key={a + b} title={`${a} → ${b}`}>
              {why}
            </Callout>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <button type="button" className="btn btn-primary" onClick={() => exportRun('json')}>
            <Download size={13} /> Export run · JSON
          </button>
          <button type="button" className="btn" onClick={() => exportRun('csv')}>
            <Download size={13} /> Export run · CSV
          </button>
        </div>
      </LabSection>
    </LabShell>
  );
}

export default TransmissionLab;
