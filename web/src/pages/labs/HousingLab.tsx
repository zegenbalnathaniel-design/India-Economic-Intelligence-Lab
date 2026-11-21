import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
  ChipMulti,
  Controls,
  DataTable,
  Field,
  LabHero,
  LabSection,
  LabShell,
  Range,
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
import raw from '../../data/labs/housing.json';
import { labBySlug } from '../../labs/registry';
import {
  affordabilityAcross,
  cityAffordability,
  emi,
  rpipi,
  stressIndex,
  type HousingData,
  type IncomeSource,
} from '../../models/housing/engine';

const lab = labBySlug('housing')!;
const D = raw as unknown as HousingData & {
  caveats: Record<IncomeSource, string>;
  rateDisclosure: string;
  baseQuarter: string;
  defaultUnitSqm: number;
};
const CITIES = Object.keys(D.prices).filter((c) => D.cityToState[c]).sort();
const LATEST_Q = D.quarters[D.quarters.length - 1];
const INCOME_LABEL: Record<IncomeSource, string> = {
  nsdp: 'State per-capita NSDP',
  mpce: 'Urban MPCE × 12',
  city: 'City household income',
};
const heroBase = { unitSqm: D.defaultUnitSqm, downPayment: 0.2, rate: 0.085, tenure: 20, incomeSource: 'nsdp' as IncomeSource };
const HERO = affordabilityAcross(D, heroBase).slice(0, 12);

export function HousingLab() {
  const [sel, setSel] = useState<string[]>(['Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Chennai', 'Kolkata'].filter((c) => CITIES.includes(c)));
  const [src, setSrc] = useState<IncomeSource>('nsdp');
  const [unit, setUnit] = useState(D.defaultUnitSqm);
  const [dp, setDp] = useState(20);
  const [rate, setRate] = useState(8.5);
  const [tenure, setTenure] = useState(20);
  const a = useMemo(() => ({ unitSqm: unit, downPayment: dp / 100, rate: rate / 100, tenure, incomeSource: src }), [unit, dp, rate, tenure, src]);

  const trend = useMemo(
    () =>
      D.quarters.map((q) => {
        const row: Record<string, string | number | null> = { q };
        for (const c of sel) {
          const r = D.prices[c]?.find((x) => x[0] === q);
          row[c] = typeof r?.[1] === 'number' ? r[1] : null;
        }
        return row;
      }),
    [sel],
  );

  const all = useMemo(() => affordabilityAcross(D, a), [a]);

  const [city, setCity] = useState('Mumbai');
  const [customIncome, setCustomIncome] = useState<string>('');
  const one = cityAffordability(D, city, a);
  const income = customIncome ? Number(customIncome) * 1e5 : one?.income ?? null;
  const emiOne = one ? emi(one.unitPrice * (1 - a.downPayment), a.rate, a.tenure) : null;
  const [cmpA, setCmpA] = useState('Mumbai');
  const [cmpB, setCmpB] = useState(CITIES.includes('Pune') ? 'Pune' : CITIES[1]);
  const ca = cityAffordability(D, cmpA, a);
  const cb = cityAffordability(D, cmpB, a);

  const [rCity, setRCity] = useState('Mumbai');
  const rp = useMemo(() => rpipi(D, rCity), [rCity]);

  const [lo, setLo] = useState(5);
  const [hi, setHi] = useState(95);
  const stress = useMemo(() => stressIndex(D, { ...a, quarter: LATEST_Q }, lo, hi), [a, lo, hi]);

  const colour = (c: string) => SERIES[sel.indexOf(c) % SERIES.length];
  const medianEmi = all.length ? all.map((c) => c.emiPct).sort((x, y) => x - y)[Math.floor(all.length / 2)] : NaN;

  return (
    <LabShell lab={lab}>
      <LabHero
        lab={lab}
        lede={
          <>
            Quarterly NHB RESIDEX price levels for {CITIES.length} cities ({D.quarters[0]} – {LATEST_Q}), set against three
            disclosed income measures. No city-level household income exists for most cities, so every result names the proxy it
            uses and what that proxy gets wrong.
          </>
        }
        stats={[
          { label: 'Cities', value: CITIES.length, sub: `RESIDEX, latest ${LATEST_Q}` },
          { label: 'Highest PTI', value: HERO[0] ? `${HERO[0].pti.toFixed(1)}×` : '—', sub: HERO[0] ? `${HERO[0].city}, 70 m² vs state NSDP` : '' },
          { label: 'Median EMI / income', value: fmt.pct(medianEmi, 0), sub: 'at the assumptions in B' },
        ]}
        figure={{
          name: 'Lockers',
          label: 'A bank of twelve lockers, one per city with the highest price-to-income ratio.',
          idle: 'Hover a locker to open one city.',
          caption: (read) => {
            const m = /(\d+)/.exec(read);
            if (!m || read === 'rest') return null;
            const c = HERO[Number(m[1]) - 1];
            return c
              ? `${c.city}, ${c.state}\nprice ${c.pti.toFixed(1)}× income · ${fmt.inr(c.unitPrice)} for 70 m² · EMI ${c.emiPct.toFixed(0)}% of income`
              : 'No city for this locker.';
          },
        }}
      />

      <LabSection index="A" title="Real housing prices, city by city" lede={`Composite RESIDEX price in ₹ per sq ft, every quarter. Index base ${D.baseQuarter} (inferred empirically; see DATA_REGISTRY.md).`}>
        <Field label={`Cities (${sel.length}/8)`}>
          <ChipMulti values={sel} onChange={setSel} options={CITIES} max={8} colour={colour} />
        </Field>
        <div className="mt-6">
          <ChartFrame title="Composite price, ₹ per sq ft" source="National Housing Bank, RESIDEX city price levels." height={380}>
            <ResponsiveContainer>
              <LineChart data={trend} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="q" {...axis} minTickGap={40} />
                <YAxis {...axis} tickFormatter={(v) => `₹${(Number(v) / 1000).toFixed(0)}k`} width={56} />
                <Tooltip {...tooltip} formatter={(v) => (typeof v === 'number' ? `₹${v.toLocaleString('en-IN')}` : String(v))} />
                <Legend {...legend} />
                {sel.map((c) => (
                  <Line key={c} type="monotone" dataKey={c} stroke={colour(c)} strokeWidth={2} dot={false} connectNulls={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>
      </LabSection>

      <LabSection index="B" title="Price-to-income, every city" lede="How many years of income a reference home costs, and what share of monthly income its mortgage would take, under assumptions you set.">
        <Controls className="md:grid-cols-5">
          <Field label="Income measure">
            <Select value={src} onChange={setSrc} options={(Object.keys(INCOME_LABEL) as IncomeSource[]).map((k) => ({ value: k, label: INCOME_LABEL[k] }))} />
          </Field>
          <Range label="Dwelling size" value={unit} min={40} max={150} step={5} onChange={setUnit} format={(v) => `${v} m²`} />
          <Range label="Down payment" value={dp} min={0} max={50} onChange={setDp} format={(v) => `${v}%`} />
          <Range label="Mortgage rate" value={rate} min={5} max={14} step={0.25} onChange={setRate} format={(v) => `${v.toFixed(2)}%`} />
          <Range label="Tenure" value={tenure} min={5} max={30} onChange={setTenure} format={(v) => `${v} yrs`} />
        </Controls>
        <div className="mt-4">
          <Callout tone="warn" title={`Income proxy · ${INCOME_LABEL[src]}`}>
            {D.caveats[src]}
          </Callout>
        </div>
        <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_1fr]">
          <ChartFrame title={`Price-to-income ratio, ${LATEST_Q}`} subtitle={`${all.length} cities with a price and an income figure`} height={Math.max(360, all.length * 17)}>
            <ResponsiveContainer>
              <BarChart data={all} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 4 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" {...axis} tickFormatter={(v) => `${v}×`} />
                <YAxis type="category" dataKey="city" {...axis} width={110} interval={0} tick={{ ...axis.tick, fontSize: 10.5 }} />
                <Tooltip {...tooltip} formatter={(v) => [`${Number(v).toFixed(1)}× income`, 'price-to-income']} />
                <Bar dataKey="pti">
                  {all.map((c) => (
                    <Cell key={c.city} fill={c.emiPct > 50 ? '#f04a32' : c.emiPct > 30 ? '#f3c542' : '#6fae4f'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
          <DataTable
            maxHeight={Math.max(360, all.length * 17) + 60}
            columns={[
              { key: 'city', label: 'City' },
              { key: 'unitPrice', label: 'Home', align: 'right', format: (v) => fmt.inr(v as number) },
              { key: 'income', label: 'Income', align: 'right', format: (v) => fmt.inr(v as number) },
              { key: 'pti', label: 'PTI', align: 'right', format: (v) => `${(v as number).toFixed(1)}×` },
              {
                key: 'emiPct',
                label: 'EMI / inc.',
                align: 'right',
                format: (v) => <span style={{ color: (v as number) > 50 ? '#f04a32' : (v as number) > 30 ? '#f3c542' : '#6fae4f' }}>{fmt.pct(v as number, 0)}</span>,
              },
            ]}
            rows={all as unknown as Record<string, unknown>[]}
          />
        </div>
      </LabSection>

      <LabSection index="C" title="EMI calculator" lede="One city in detail, then two side by side. Override the income proxy with your own household income if you know it.">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="grid content-start gap-4 border border-white/[0.08] bg-ink-900/50 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="City">
                <Select value={city} onChange={setCity} options={CITIES} />
              </Field>
              <Field label="Your annual income (₹ lakh, optional)">
                <input className="numfield" inputMode="decimal" placeholder={one ? (one.income / 1e5).toFixed(2) : ''} value={customIncome} onChange={(e) => setCustomIncome(e.target.value.replace(/[^0-9.]/g, ''))} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Reference home" value={fmt.inr(one?.unitPrice)} sub={one ? `${unit} m² at ₹${one.perSqft.toLocaleString('en-IN')}/sq ft` : 'no price'} />
              <Stat label="Monthly EMI" value={fmt.inrFull(emiOne)} sub={`${100 - dp}% loan, ${rate}% for ${tenure} yrs`} tone="#f5f0e6" />
              <Stat label="EMI / income" value={income && emiOne ? fmt.pct((emiOne / (income / 12)) * 100, 0) : '—'} sub={customIncome ? 'your income' : INCOME_LABEL[src]} />
              <Stat label="Price / income" value={income && one ? `${(one.unitPrice / income).toFixed(1)}×` : '—'} sub="years of income" tone="#f5f0e6" />
            </div>
          </div>
          <div className="grid content-start gap-4 border border-white/[0.08] bg-ink-900/50 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="City A">
                <Select value={cmpA} onChange={setCmpA} options={CITIES} />
              </Field>
              <Field label="City B">
                <Select value={cmpB} onChange={setCmpB} options={CITIES} />
              </Field>
            </div>
            <StatRow>
              <Stat label={`${cmpA} · PTI`} value={ca ? `${ca.pti.toFixed(1)}×` : '—'} />
              <Stat label={`${cmpB} · PTI`} value={cb ? `${cb.pti.toFixed(1)}×` : '—'} tone="#4d6ff0" />
              <Stat label={`${cmpA} · EMI`} value={ca ? fmt.pct(ca.emiPct, 0) : '—'} />
              <Stat label={`${cmpB} · EMI`} value={cb ? fmt.pct(cb.emiPct, 0) : '—'} tone="#4d6ff0" />
            </StatRow>
            <p className="text-[12.5px] leading-relaxed text-ink-400">
              {ca && cb
                ? `A ${unit} m² home costs ${(ca.unitPrice / cb.unitPrice).toFixed(2)}× as much in ${cmpA} as in ${cmpB}; against each city’s income proxy that is ${ca.pti.toFixed(1)} vs ${cb.pti.toFixed(1)} years of income.`
                : 'One of these cities has no income figure for the selected measure.'}
            </p>
          </div>
        </div>
      </LabSection>

      <LabSection
        index="D"
        title="RPIPI — price-to-income pressure over time"
        lede="RPIPI = 100 · (HPI_t / HPI_0) ÷ (Y_t / Y_0). Above 100, house prices have outpaced income since the base year; below 100, income has caught up. Computed entirely from the real RESIDEX index and state per-capita NSDP at current prices."
      >
        <div className="max-w-xs">
          <Field label="City">
            <Select value={rCity} onChange={setRCity} options={CITIES.filter((c) => D.index[c])} />
          </Field>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_280px]">
          <ChartFrame title={`RPIPI, ${rCity}`} subtitle={rp ? `base ${rp.base} = 100 · income proxy: ${rp.state} per-capita NSDP` : 'no overlapping years'} source="NHB RESIDEX composite index (annual mean of quarters); RBI per-capita NSDP, current prices.">
            <ResponsiveContainer>
              <LineChart data={rp?.series ?? []} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="fy" {...axis} />
                <YAxis {...axis} width={44} domain={['auto', 'auto']} />
                <ReferenceLine y={100} stroke="rgba(245,240,230,0.35)" strokeDasharray="4 4" />
                <Tooltip {...tooltip} formatter={(v) => Number(v).toFixed(1)} />
                <Line type="monotone" dataKey="rpipi" name="RPIPI" stroke="var(--accent)" strokeWidth={2.4} dot={{ r: 3, fill: 'var(--accent)' }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
          <div className="grid content-start gap-3">
            <Stat label={`Latest (${rp?.latest.fy ?? '—'})`} value={rp ? rp.latest.rpipi.toFixed(1) : '—'} sub={rp ? (rp.latest.rpipi > 100 ? 'prices outpaced income' : 'income outpaced prices') : ''} />
            <Stat label="Price index change" value={rp ? fmt.pct((rp.latest.price / rp.series[0].price - 1) * 100, 0) : '—'} tone="#f5f0e6" />
            <Stat label="Income change" value={rp ? fmt.pct((rp.latest.income / rp.series[0].income - 1) * 100, 0) : '—'} tone="#f5f0e6" />
          </div>
        </div>
      </LabSection>

      <LabSection index="E" title="ICHASI — affordability stress, 0 to 100" lede="Each city’s price-to-income ratio is clipped to the chosen percentile band of all cities and rescaled, so one extreme city cannot compress every other score toward zero. Raw PTI stays in the tooltip.">
        <Controls className="md:grid-cols-2">
          <Range label="Lower clip percentile" value={lo} min={0} max={25} onChange={(v) => setLo(Math.min(v, hi - 5))} format={(v) => `P${v}`} />
          <Range label="Upper clip percentile" value={hi} min={75} max={100} onChange={(v) => setHi(Math.max(v, lo + 5))} format={(v) => `P${v}`} />
        </Controls>
        <div className="mt-4">
          <Callout title="Rate disclosure">{D.rateDisclosure}</Callout>
        </div>
        <div className="mt-6">
          <ChartFrame title={`Stress score, ${stress?.quarter ?? LATEST_Q}`} subtitle={stress ? `PTI clipped to [${stress.lo.toFixed(1)}×, ${stress.hi.toFixed(1)}×]` : ''} height={Math.max(360, (stress?.scores.length ?? 20) * 17)}>
            <ResponsiveContainer>
              <BarChart data={stress?.scores ?? []} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 4 }}>
                <CartesianGrid {...grid} horizontal={false} />
                <XAxis type="number" domain={[0, 100]} {...axis} />
                <YAxis type="category" dataKey="city" {...axis} width={110} interval={0} tick={{ ...axis.tick, fontSize: 10.5 }} />
                <Tooltip {...tooltip} formatter={(v, _n, p) => [`${Number(v).toFixed(0)} (PTI ${(p.payload as { pti: number }).pti.toFixed(1)}×)`, 'stress']} />
                <Bar dataKey="score">
                  {(stress?.scores ?? []).map((c) => (
                    <Cell key={c.city} fill={`rgba(243,197,66,${0.25 + 0.75 * (c.score / 100)})`} />
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

export default HousingLab;
