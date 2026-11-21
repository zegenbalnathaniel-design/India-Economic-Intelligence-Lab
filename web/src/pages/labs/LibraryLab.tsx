import { motion } from 'framer-motion';
import { Download } from 'lucide-react';
import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  Callout,
  ChartFrame,
  DataTable,
  LabHero,
  LabSection,
  LabShell,
  SERIES,
  StatusPill,
  axis,
  grid,
  legend,
  tooltip,
} from '../../components/Lab/LabKit';
import L from '../../data/labs/library.json';
import { labBySlug } from '../../labs/registry';
import { EASE_OUT } from '../../lib/motion';

const lab = labBySlug('library')!;
type Row = Record<string, string | number | null>;
interface Inv {
  key: string;
  id: string;
  title: string;
  question: string;
  motivation: string;
  data: string[];
  method: string;
  tables: Record<string, Row[]>;
  facts: string[];
  statistics: string[];
  interpretation: string[];
  hypotheses: string[];
  limitations: string[];
  furtherQuestions: string[];
  charts: { table: string; x: string; y: string | string[]; kind: 'line' | 'bar'; title: string }[];
  settings: Record<string, string>;
}
const INVS = L.investigations as unknown as Inv[];
const SOURCES = L.sources as Record<string, { name: string; publisher: string; url: string; status: string; period: string; limitations: string }>;
const md = (s: string) => s.replace(/\*\*/g, '').replace(/`/g, '');
const num = (v: unknown) => (typeof v === 'number' ? (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-IN') : Number(v.toPrecision(4)).toString()) : v === null ? '—' : String(v));

function download(name: string, text: string, type: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function csv(inv: Inv) {
  return Object.entries(inv.tables)
    .map(([name, rows]) => {
      if (!rows.length) return `# ${name}\n`;
      const cols = Object.keys(rows[0]);
      return [`# ${name}`, cols.join(','), ...rows.map((r) => cols.map((c) => JSON.stringify(r[c] ?? '')).join(','))].join('\n');
    })
    .join('\n\n');
}

function brief(inv: Inv) {
  const list = (xs: string[]) => `<ul>${xs.map((x) => `<li>${md(x)}</li>`).join('')}</ul>`;
  const tables = Object.entries(inv.tables)
    .map(([n, rows]) => {
      if (!rows.length) return '';
      const cols = Object.keys(rows[0]);
      return `<h4>${n}</h4><table><tr>${cols.map((c) => `<th>${c}</th>`).join('')}</tr>${rows.map((r) => `<tr>${cols.map((c) => `<td>${num(r[c])}</td>`).join('')}</tr>`).join('')}</table>`;
    })
    .join('');
  return `<!doctype html><meta charset="utf-8"><title>IEIL brief — ${inv.title}</title>
<style>body{font:15px/1.6 Georgia,serif;max-width:760px;margin:40px auto;padding:0 16px;color:#1b1d24}h1{font-weight:400}h2{border-top:1px solid #ccc;padding-top:12px;font:600 13px/1.4 monospace;letter-spacing:.12em;text-transform:uppercase}table{border-collapse:collapse;font:12px monospace;margin:8px 0}td,th{border:1px solid #ddd;padding:3px 6px;text-align:right}</style>
<p style="font:12px monospace">India Economics Intelligence Lab · Research Library · generated ${new Date().toISOString()}</p>
<h1>${inv.title}</h1>
<h2>1 · Research question</h2><p>${md(inv.question)}</p>
<h2>2 · Economic motivation</h2><p>${md(inv.motivation)}</p>
<h2>3 · Data sources</h2>${list(inv.data.map((d) => `${SOURCES[d]?.name ?? d} — ${SOURCES[d]?.publisher ?? ''} (${SOURCES[d]?.status ?? ''})`))}
<h2>4 · Methodology</h2><p>${md(inv.method)}</p>
<h2>5 · Results</h2><h3>Observed facts</h3>${list(inv.facts)}<h3>Statistical results</h3>${list(inv.statistics)}${tables}
<h2>6 · Interpretation</h2>${list(inv.interpretation)}<p><i>Descriptive and correlational only — no causal claim is made.</i></p><h3>Hypotheses requiring further testing</h3>${list(inv.hypotheses)}
<h2>7 · Limitations</h2>${list(inv.limitations)}
<h2>8 · Further research questions</h2>${list(inv.furtherQuestions)}
<h2>Settings</h2><pre>${JSON.stringify({ investigation: inv.id, ...inv.settings }, null, 2)}</pre>`;
}

function Bullets({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-ink-500">None.</p>;
  return (
    <ul className="space-y-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-3 text-[13.5px] leading-relaxed text-ink-200">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full" style={{ background: 'var(--accent)' }} />
          <span>{md(t)}</span>
        </li>
      ))}
    </ul>
  );
}

function Part({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-30px' }} transition={{ duration: 0.6, ease: EASE_OUT }} className="grid gap-4 border-t border-white/[0.08] py-6 md:grid-cols-[220px_1fr]">
      <div className="label">
        <span className="font-mono text-[1.4rem] font-light" style={{ color: 'var(--accent)' }}>
          {n}
        </span>{' '}
        · {title}
      </div>
      <div>{children}</div>
    </motion.div>
  );
}

export function LibraryLab() {
  const [key, setKey] = useState(INVS[0].key);
  const inv = INVS.find((i) => i.key === key)!;

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Each investigation asks one question and answers it only with data already in this project. Facts, statistical results,
            interpretation and hypotheses are kept apart, every sentence is built from computed values, and nothing claims cause and
            effect.
          </>
        }
        stats={[
          { label: 'Investigations', value: INVS.length, sub: 'computed from the lab’s data' },
          { label: 'Sources cited', value: Object.keys(SOURCES).length, sub: 'evidence-ledger records' },
          { label: 'Not yet possible', value: L.notYetPossible.length, sub: 'listed, not approximated' },
        ]}
        figure={{
          name: 'Rail',
          label: 'A rail of hangers; each is one investigation in the library.',
          idle: 'Hover the rail: each hanger is one investigation.',
          caption: (read) => {
            const m = /^hanger (\d+)/.exec(read);
            if (!m) return null;
            const i = INVS[Number(m[1]) - 1];
            return i ? `${i.title.toUpperCase()}\n${md(i.question)}` : `NOT YET POSSIBLE\n${L.notYetPossible[(Number(m[1]) - INVS.length - 1) % L.notYetPossible.length]?.[0] ?? ''}`;
          },
        }}
      />

      <LabSection index="§" title="Choose an investigation">
        <div className="grid gap-3 md:grid-cols-5">
          {INVS.map((i, k) => (
            <button
              key={i.key}
              type="button"
              onClick={() => setKey(i.key)}
              className="border p-4 text-left transition-colors"
              style={{ borderColor: i.key === key ? SERIES[k] : 'rgba(245,240,230,0.1)', background: i.key === key ? `${SERIES[k]}14` : 'rgba(17,19,26,0.5)' }}
            >
              <div className="font-mono text-[1.6rem] font-light" style={{ color: SERIES[k] }}>
                {String(k + 1).padStart(2, '0')}
              </div>
              <div className="mt-2 text-[14px] leading-snug text-ink-50">{i.title}</div>
            </button>
          ))}
        </div>

        <div className="mt-10">
          <h3 className="display text-[2rem] leading-tight md:text-[2.6rem]">{inv.title}</h3>
          <div className="mt-6">
            <Part n={1} title="Research question">
              <p className="font-display text-[1.25rem] italic leading-snug text-ink-50">{md(inv.question)}</p>
            </Part>
            <Part n={2} title="Economic motivation">
              <p className="text-[14px] leading-relaxed text-ink-200">{md(inv.motivation)}</p>
            </Part>
            <Part n={3} title="Data sources">
              <div className="grid gap-2">
                {inv.data.map((d) => {
                  const s = SOURCES[d];
                  return (
                    <div key={d} className="border border-white/[0.08] bg-ink-900/50 p-3 text-[12.5px] leading-relaxed">
                      <div className="flex flex-wrap items-center gap-2">
                        {s?.url ? (
                          <a href={s.url} target="_blank" rel="noreferrer" className="text-ink-50 underline decoration-white/20 underline-offset-2">
                            {s?.name ?? d}
                          </a>
                        ) : (
                          <span className="text-ink-50">{s?.name ?? d}</span>
                        )}
                        {s && <StatusPill status={s.status} />}
                      </div>
                      {s && (
                        <div className="mt-1 text-ink-400">
                          {s.publisher} · {s.period}
                        </div>
                      )}
                      {s?.limitations && <div className="mt-1 text-ink-500">{md(s.limitations)}</div>}
                    </div>
                  );
                })}
              </div>
            </Part>
            <Part n={4} title="Methodology">
              <p className="text-[14px] leading-relaxed text-ink-200">{md(inv.method)}</p>
            </Part>
            <Part n={5} title="Results">
              <div className="grid gap-6">
                {inv.charts.map((c, ci) => {
                  const rows = inv.tables[c.table] ?? [];
                  const ys = Array.isArray(c.y) ? c.y : [c.y];
                  return (
                    <ChartFrame key={ci} title={c.title} height={c.kind === 'bar' ? Math.max(300, rows.length * 16) : 320}>
                      <ResponsiveContainer>
                        {c.kind === 'bar' ? (
                          <BarChart data={[...rows].filter((r) => r[ys[0]] !== null).sort((a, b) => Number(b[ys[0]]) - Number(a[ys[0]]))} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
                            <CartesianGrid {...grid} horizontal={false} />
                            <XAxis type="number" {...axis} tickFormatter={(v) => num(v)} />
                            <YAxis type="category" dataKey={c.x} {...axis} width={170} interval={0} tick={{ ...axis.tick, fontSize: 10 }} />
                            <Tooltip {...tooltip} formatter={(v) => num(v)} />
                            <Bar dataKey={ys[0]} fill="var(--accent)" />
                          </BarChart>
                        ) : (
                          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                            <CartesianGrid {...grid} />
                            <XAxis dataKey={c.x} {...axis} minTickGap={24} />
                            <YAxis {...axis} width={52} tickFormatter={(v) => num(v)} />
                            <Tooltip {...tooltip} formatter={(v) => num(v)} />
                            <Legend {...legend} />
                            {ys.map((y, i) => (
                              <Line key={y} dataKey={y} stroke={SERIES[i % SERIES.length]} strokeWidth={2} dot={{ r: 2 }} />
                            ))}
                          </LineChart>
                        )}
                      </ResponsiveContainer>
                    </ChartFrame>
                  );
                })}
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <div className="label mb-3">Observed facts</div>
                    <Bullets items={inv.facts} />
                  </div>
                  <div>
                    <div className="label mb-3">Statistical results</div>
                    <Bullets items={inv.statistics} />
                  </div>
                </div>
                {Object.entries(inv.tables).map(([name, rows]) =>
                  rows.length ? (
                    <details key={name} className="border border-white/[0.08] bg-ink-900/40 p-3">
                      <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.14em] text-ink-400">
                        Table · {name} ({rows.length} rows)
                      </summary>
                      <div className="mt-3">
                        <DataTable
                          maxHeight={300}
                          columns={Object.keys(rows[0]).map((c) => ({ key: c, label: c.replace(/_/g, ' '), align: typeof rows[0][c] === 'number' ? ('right' as const) : ('left' as const), format: (v: unknown) => num(v) }))}
                          rows={rows}
                        />
                      </div>
                    </details>
                  ) : null,
                )}
              </div>
            </Part>
            <Part n={6} title="Interpretation">
              <Bullets items={inv.interpretation} />
              <p className="mt-3 text-[12px] italic text-ink-500">Descriptive and correlational only — no causal claim is made.</p>
              <div className="label mb-3 mt-5">Hypotheses requiring further testing</div>
              <Bullets items={inv.hypotheses} />
            </Part>
            <Part n={7} title="Limitations">
              <Bullets items={inv.limitations} />
            </Part>
            <Part n={8} title="Further research questions">
              <Bullets items={inv.furtherQuestions} />
            </Part>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" className="btn btn-primary" onClick={() => download(`ieil-brief-${inv.id}.html`, brief(inv), 'text/html')}>
              <Download size={13} /> Research brief (HTML)
            </button>
            <button type="button" className="btn" onClick={() => download(`ieil-${inv.id}-tables.csv`, csv(inv), 'text/csv')}>
              <Download size={13} /> Result tables (CSV)
            </button>
            <button type="button" className="btn" onClick={() => download(`ieil-${inv.id}-settings.json`, JSON.stringify({ investigation: inv.id, ...inv.settings }, null, 2), 'application/json')}>
              <Download size={13} /> Settings (JSON)
            </button>
          </div>
        </div>
      </LabSection>

      <LabSection index="∅" title="Not yet possible with the data in this project" lede="Part of the research programme, but they need data the project does not hold. Listed rather than approximated.">
        <div className="grid gap-3 md:grid-cols-2">
          {(L.notYetPossible as [string, string][]).map(([t, need]) => (
            <Callout key={t} title={t}>
              {need}
            </Callout>
          ))}
        </div>
      </LabSection>
    </LabShell>
  );
}

export default LibraryLab;
