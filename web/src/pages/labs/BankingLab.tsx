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
import B from '../../data/labs/banking.json';
import { labBySlug } from '../../labs/registry';
import {
  aggregate,
  computeIbfpi,
  directionFlips,
  fixedEffects,
  leaveOneOut,
  mergeRepo,
  regimes,
  rho,
  weightSensitivity,
  type Row,
} from '../../models/banking/engine';

const lab = labBySlug('banking')!;
const IND = B.indicators;
const LABELS = B.labels as Record<string, string>;
const DIR = B.directions as Record<string, number>;
const ROWS: Row[] = (B.panel as (string | number)[][]).map((r) => ({
  bank: r[0] as string,
  period: r[1] as string,
  values: Object.fromEntries(IND.map((c, i) => [c, r[2 + i] as number])),
}));
const REPO = B.repo as [string, number][];
const BANKS = [...new Set(ROWS.map((r) => r.bank))].sort();
const ASSET_WEIGHTS: Record<string, number> = { 'State Bank of India': 55, 'HDFC Bank': 32, 'ICICI Bank': 17, 'Axis Bank': 12, 'Kotak Mahindra Bank': 5 };
const REGIME_COLOUR = { rising: '#f04a32', falling: '#6fae4f', stable: '#8b8d99' } as const;
const DEC = B.latestDecision as { policy_repo_rate_pct: number; effective_date: string };
const q = (p: string) => `${p.slice(0, 4)} Q${Math.ceil(Number(p.slice(5, 7)) / 3)}`;

// Hero captions use the default construction.
const HERO = regimes(mergeRepo(aggregate(computeIbfpi(ROWS, IND, DIR)), REPO));

export function BankingLab() {
  const [banks, setBanks] = useState<string[]>(BANKS);
  const [bankW, setBankW] = useState<'equal' | 'assets'>('equal');
  const [indW, setIndW] = useState<'equal' | 'custom'>('equal');
  const [weights, setWeights] = useState<Record<string, number>>(Object.fromEntries(IND.map((c) => [c, 0.2])));
  const rows = useMemo(() => ROWS.filter((r) => banks.includes(r.bank)), [banks]);
  const scored = useMemo(() => (rows.length ? computeIbfpi(rows, IND, DIR, indW === 'custom' ? weights : null) : []), [rows, indW, weights]);
  const sys = useMemo(
    () => aggregate(scored, bankW === 'assets' ? Object.fromEntries(banks.map((b) => [b, ASSET_WEIGHTS[b] ?? 0])) : null),
    [scored, bankW, banks],
  );
  const merged = useMemo(() => mergeRepo(sys, REPO), [sys]);
  const corr = rho(merged.map((r) => r.repo), merged.map((r) => r.ibfpi));
  const reg = useMemo(() => regimes(merged), [merged]);

  const perBank = useMemo(() => {
    const ps = [...new Set(scored.map((r) => r.period))].sort();
    return ps.map((p) => ({ period: q(p), ...Object.fromEntries(scored.filter((r) => r.period === p).map((r) => [r.bank, r.ibfpi])) }));
  }, [scored]);
  const [comp, setComp] = useState(IND[0]);
  const components = useMemo(() => {
    const ps = [...new Set(rows.map((r) => r.period))].sort();
    return ps.map((p) => ({ period: q(p), ...Object.fromEntries(rows.filter((r) => r.period === p).map((r) => [r.bank, r.values[comp]])) }));
  }, [rows, comp]);
  const dual = merged.map((r) => ({ period: q(r.period), ibfpi: r.ibfpi, repo: r.repo }));

  const robust = useMemo(() => {
    if (rows.length < 10) return null;
    const sc = computeIbfpi(rows, IND, DIR);
    const sens = weightSensitivity(rows, REPO, IND, DIR, 300).map((d) => d.rho).filter(Number.isFinite);
    const bins = Array.from({ length: 20 }, (_, i) => ({ x: -1 + i * 0.1 + 0.05, n: 0 }));
    sens.forEach((v) => bins[Math.min(19, Math.max(0, Math.floor((v + 1) / 0.1)))].n++);
    return {
      fe: fixedEffects(sc, REPO),
      loo: leaveOneOut(rows, REPO, IND, DIR, LABELS),
      flips: directionFlips(rows, REPO, IND, DIR, LABELS),
      sens,
      bins,
      base: rho(mergeRepo(aggregate(sc), REPO).map((r) => r.repo), mergeRepo(aggregate(sc), REPO).map((r) => r.ibfpi)).rho,
    };
  }, [rows]);
  const colour = (b: string) => SERIES[BANKS.indexOf(b) % SERIES.length];

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            The BFPI methodology from the accompanying JP Morgan / Federal Reserve paper, adapted to five Indian banks as the{' '}
            <b className="text-ink-50">iBFPI</b>: each of five indicators becomes a robust z-score against the bank’s own history,
            and the composite is compared with the RBI repo rate, 2018–2024.
          </>
        }
        stats={[
          { label: 'Repo rate today', value: `${DEC.policy_repo_rate_pct.toFixed(2)}%`, sub: `since ${DEC.effective_date}` },
          { label: 'Spearman ρ, repo vs iBFPI', value: corr.rho.toFixed(2), sub: `${fmt.p(corr.p)}, n = ${corr.n} quarters` },
          { label: 'Data', value: 'ILLUSTRATIVE', sub: 'synthetic bank panel; real repo rate' },
        ]}
        figure={{
          name: 'Drawer',
          label: 'Three drawers, one per rate regime: rising, stable and falling.',
          idle: 'Open a drawer: each is one rate regime and how bank performance moved within it.',
          caption: (read) => {
            const m = /^drawer (\d)/.exec(read);
            if (!m) return null;
            const k = (['rising', 'stable', 'falling'] as const)[Number(m[1]) - 1];
            const c = HERO[k];
            return `${k.toUpperCase()} RATES\nρ(repo, iBFPI) = ${Number.isFinite(c.rho) ? c.rho.toFixed(2) : 'n/a'}, n = ${c.n} quarters`;
          },
        }}
      />

      <div className="mx-auto max-w-[1400px] px-5 pt-10 md:px-10">
        <Callout tone="warn" title="Illustrative data">
          The bank panel in this build is <b>illustrative and synthetic</b> — constructed to demonstrate the methodology end to end.
          Replace <code>data/processed/bank_panel.csv</code> with values from bank annual reports and Basel III disclosures to
          reproduce it with real numbers. The repo rate it is compared with is real: the rate in force at each quarter end.
        </Callout>
      </div>

      <LabSection index="A" title="Construction of iBFPI" lede={<>Z* = D · (X − median) / (1.4826 · MAD), per bank so that each bank’s own history is the reference; iBFPI = the mean of the five Z* (or a weighted sum, if you set weights). 1.4826 makes the robust z consistent with a standard normal.</>}>
        <Controls className="md:grid-cols-3">
          <Field label="Banks">
            <ChipMulti values={banks} onChange={(v) => v.length && setBanks(v)} options={BANKS} colour={colour} />
          </Field>
          <Field label="Across banks">
            <Segmented value={bankW} onChange={setBankW} options={[{ value: 'equal', label: 'Equal-weighted' }, { value: 'assets', label: 'Asset-weighted (illustrative)' }]} />
          </Field>
          <Field label="Across indicators">
            <Segmented value={indW} onChange={setIndW} options={[{ value: 'equal', label: 'Equal (published)' }, { value: 'custom', label: 'Set weights' }]} />
          </Field>
        </Controls>
        {indW === 'custom' && (
          <div className="mt-4 grid gap-4 border border-white/[0.08] bg-ink-900/50 p-4 md:grid-cols-5">
            {IND.map((c) => (
              <Range key={c} label={LABELS[c]} value={weights[c]} min={0} max={1} step={0.05} onChange={(v) => setWeights({ ...weights, [c]: v })} format={(v) => v.toFixed(2)} />
            ))}
          </div>
        )}
        <div className="mt-6">
          <DataTable
            columns={[
              { key: 'label', label: 'Indicator' },
              { key: 'd', label: 'Direction D', align: 'right', format: (v) => <span style={{ color: (v as number) > 0 ? '#6fae4f' : '#f04a32' }}>{(v as number) > 0 ? '+1 (higher is better)' : '−1 (higher is worse)'}</span> },
            ]}
            rows={IND.map((c) => ({ label: LABELS[c], d: DIR[c] }))}
          />
        </div>
      </LabSection>

      <LabSection index="B" title="iBFPI over time" lede="Zero is each bank’s own typical quarter: the scale is relative, not absolute.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame title="Aggregate iBFPI" source="ILLUSTRATIVE synthetic bank panel; calculations on this site.">
            <ResponsiveContainer>
              <LineChart data={dual} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="period" {...axis} minTickGap={30} />
                <YAxis {...axis} width={40} />
                <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(3)} />
                <Line dataKey="ibfpi" name="iBFPI (system)" stroke="var(--accent)" strokeWidth={2.4} dot={{ r: 2.5 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="iBFPI by bank">
            <ResponsiveContainer>
              <LineChart data={perBank} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="period" {...axis} minTickGap={30} />
                <YAxis {...axis} width={40} />
                <ReferenceLine y={0} stroke="rgba(245,240,230,0.35)" />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(3)} />
                <Legend {...legend} />
                {banks.map((b) => (
                  <Line key={b} dataKey={b} stroke={colour(b)} strokeWidth={1.6} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
        <div className="mt-6">
          <ChartFrame title={`Component · ${LABELS[comp]}`} subtitle={`raw values; direction D = ${DIR[comp] > 0 ? '+1' : '−1'}`} actions={<div className="w-56"><Select value={comp} onChange={setComp} options={IND.map((c) => ({ value: c, label: LABELS[c] }))} /></div>} height={300}>
            <ResponsiveContainer>
              <LineChart data={components} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="period" {...axis} minTickGap={30} />
                <YAxis {...axis} width={52} tickFormatter={(v) => Number(v).toPrecision(3)} />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toPrecision(4)} />
                <Legend {...legend} />
                {banks.map((b) => (
                  <Line key={b} dataKey={b} stroke={colour(b)} strokeWidth={1.6} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="C" title="RBI repo rate vs iBFPI" lede="A rank correlation over quarters, then the same split by rate regime: a three-quarter change in the repo rate above +25 bp is rising, below −25 bp falling, otherwise stable.">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <ChartFrame title="Repo rate and system iBFPI" source="RBI repo rate at quarter end (real); iBFPI from the ILLUSTRATIVE panel.">
            <ResponsiveContainer>
              <ComposedChart data={dual} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="period" {...axis} minTickGap={30} />
                <YAxis yAxisId="i" {...axis} width={40} />
                <YAxis yAxisId="r" orientation="right" {...axis} width={44} tickFormatter={(v) => `${v}%`} domain={[3.5, 7]} />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(2)} />
                <Legend {...legend} />
                <Line yAxisId="i" dataKey="ibfpi" name="iBFPI" stroke="var(--accent)" strokeWidth={2.2} dot={false} />
                <Line yAxisId="r" dataKey="repo" name="Repo rate" type="stepAfter" stroke="#f3c542" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartFrame>
          <ChartFrame title="By regime" subtitle="each dot a quarter">
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis type="number" dataKey="repo" domain={['auto', 'auto']} {...axis} tickFormatter={(v) => `${v}%`} />
                <YAxis type="number" dataKey="ibfpi" {...axis} width={40} />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(2)} />
                <Legend {...legend} />
                {(['rising', 'stable', 'falling'] as const).map((k) => (
                  <Scatter key={k} name={k} data={reg.labelled.filter((r) => r.regime === k)} fill={REGIME_COLOUR[k]} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
        <div className="mt-6">
          <StatRow>
            <Stat label="All quarters" value={`ρ = ${corr.rho.toFixed(2)}`} sub={`${fmt.p(corr.p)}, n = ${corr.n}`} />
            {(['rising', 'stable', 'falling'] as const).map((k) => (
              <Stat key={k} label={`${k} rates`} value={Number.isFinite(reg[k].rho) ? `ρ = ${reg[k].rho.toFixed(2)}` : 'n/a'} sub={`${fmt.p(reg[k].p)}, n = ${reg[k].n}${reg[k].n < 10 ? ' — very small' : ''}`} tone={REGIME_COLOUR[k]} />
            ))}
          </StatRow>
        </div>
        <div className="mt-4">
          <Callout title="Reading it">
            Spearman ρ is a rank association, not a causal effect, and quarterly series are serially correlated, so these
            p-values understate the uncertainty. The regime samples are small; n is shown next to every ρ.
          </Callout>
        </div>
      </LabSection>

      <LabSection index="D" title="How much does the result depend on the choices?" lede="The same question asked four more ways: a bank fixed-effects regression, 300 random indicator weightings, dropping each indicator, and reversing each direction coefficient.">
        {robust ? (
          <div className="grid gap-6">
            <DataTable
              columns={[
                { key: 'label', label: 'Model' },
                { key: 'slope', label: 'Slope (iBFPI per pp of repo)', align: 'right', format: (v) => (v as number).toFixed(3) },
                { key: 'se', label: 'SE', align: 'right', format: (v) => (v as number).toFixed(3) },
                { key: 'p', label: 'p', align: 'right', format: (v) => fmt.p(v as number) },
                { key: 'ciLow', label: '95% CI', align: 'right', format: (v, r) => `[${(v as number).toFixed(2)}, ${(r.ciHigh as number).toFixed(2)}]` },
                { key: 'n', label: 'n', align: 'right' },
                { key: 'seType', label: 'Errors' },
              ]}
              rows={robust.fe as unknown as Record<string, unknown>[]}
            />
            <Callout tone="warn">No macro controls: quarterly GDP and CPI series are not in this project, so the slope may pick up the business cycle.</Callout>
            <div className="grid gap-6 lg:grid-cols-2">
              <ChartFrame title="ρ under 300 random indicator weightings" subtitle={`${fmt.pct((robust.sens.filter((v) => v < 0).length / robust.sens.length) * 100, 0)} of draws negative · dashed line = equal weights`} height={300}>
                <ResponsiveContainer>
                  <BarChart data={robust.bins} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                    <CartesianGrid {...grid} vertical={false} />
                    <XAxis dataKey="x" type="number" domain={[-1, 1]} {...axis} tickFormatter={(v) => Number(v).toFixed(1)} />
                    <YAxis {...axis} width={32} />
                    <ReferenceLine x={robust.base} stroke="#f5f0e6" strokeDasharray="4 4" />
                    <Tooltip {...tooltip} formatter={(v) => [v, 'draws']} labelFormatter={(l) => `ρ ≈ ${Number(l).toFixed(2)}`} />
                    <Bar dataKey="n" barSize={14}>
                      {robust.bins.map((b) => (
                        <Cell key={b.x} fill={b.x < 0 ? 'var(--accent)' : '#f04a32'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartFrame>
              <div className="grid content-start gap-4">
                <DataTable
                  maxHeight={260}
                  columns={[
                    { key: 'variant', label: 'Variant' },
                    { key: 'rho', label: 'ρ', align: 'right', format: (v) => (v as number).toFixed(3) },
                    { key: 'p', label: 'p', align: 'right', format: (v) => fmt.p(v as number) },
                  ]}
                  rows={[...robust.loo, ...robust.flips] as unknown as Record<string, unknown>[]}
                />
              </div>
            </div>
          </div>
        ) : (
          <Callout tone="warn">Select at least two banks to run the robustness checks.</Callout>
        )}
        <div className="mt-6 flex flex-wrap items-center gap-2 text-[12px] text-ink-400">
          <StatusPill status="ILLUSTRATIVE" /> bank panel · <StatusPill status="PARTIAL" /> repo-rate decisions (primary RBI releases not opened in this build)
        </div>
      </LabSection>
    </LabShell>
  );
}

export default BankingLab;
