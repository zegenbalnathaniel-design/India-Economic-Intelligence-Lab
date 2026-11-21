import { AnimatePresence, motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import { useMemo, useState } from 'react';
import { GSDP_DISCREPANCY, STATES, STATES_NOTE, type StateRecord } from '../../data/states/states';
import { cn, rupees } from '../../lib/format';
import { EASE_OUT } from '../../lib/motion';
import { SourceDiscrepancy } from '../DataProvenance/DataProvenance';
import { Notice, StatusBadge, Unavailable } from '../ui';

/**
 * A schematic map. It is not a cartographic boundary file — this build had
 * no access to one — so the outline is a simplified silhouette and states
 * are positioned nodes sized by the indicator being shown. The legend says
 * so, because a schematic presented as a boundary map would misrepresent
 * both the geography and the coverage. Nothing here should be read as a
 * depiction of any border.
 *
 * Coordinates use a plain linear projection of the subcontinent's extent,
 * lon 66–98°E across x, lat 6–37°N down y:
 *   x = 100 + (lon − 66) · 10        y = 70 + (37 − lat) · 16.13
 */
const OUTLINE = [
  'M185,94',      // Kashmir, northern tip
  'L232,120',     // Ladakh
  'L252,176',     // Himalayan border
  'L286,198',
  'L322,224',     // eastern Nepal
  'L352,228',     // Bhutan
  'L378,214',
  'L410,210',     // Arunachal, eastern extremity
  'L398,248',
  'L386,268',
  'L378,300',
  'L368,320',     // Mizoram, southern tip
  'L356,310',
  'L350,268',     // up the eastern side of the Bengal delta
  'L334,242',     // the Siliguri corridor
  'L322,250',
  'L318,286',
  'L324,322',     // West Bengal coast
  'L306,346',     // Odisha
  'L282,376',
  'L258,404',     // Andhra coast
  'L248,432',
  'L240,460',     // Tamil Nadu coast
  'L230,502',
  'L214,540',     // Kanyakumari
  'L200,506',
  'L194,482',     // Kerala
  'L182,434',     // Karnataka coast
  'L178,416',     // Goa
  'L168,362',     // Konkan
  'L150,332',
  'L130,314',     // Saurashtra
  'L118,296',
  'L126,286',     // Kutch
  'L146,284',
  'L140,252',
  'L140,224',     // western Rajasthan
  'L162,190',
  'L180,152',     // Punjab
  'Z',
].join(' ');

export function IndiaMap() {
  const [selectedId, setSelectedId] = useState<string | null>('TN');
  const [hoverId, setHoverId] = useState<string | null>(null);

  const values = useMemo(
    () => STATES.map((s) => s.perCapitaNsdp.value).filter((v): v is number => v !== null),
    [],
  );
  const min = Math.min(...values);
  const max = Math.max(...values);

  const selected = selectedId ? STATES.find((s) => s.id === selectedId) : null;

  const radius = (s: StateRecord) => {
    if (s.perCapitaNsdp.value === null) return 6;
    const t = (s.perCapitaNsdp.value - min) / (max - min || 1);
    // Area, not radius, carries the value — and kept small enough that
    // adjacent states (Telangana and Andhra Pradesh especially) stay legible.
    return Math.sqrt(36 + t * 210);
  };

  const tone = (s: StateRecord) => {
    if (s.perCapitaNsdp.value === null) return '#5d6a72';
    const t = (s.perCapitaNsdp.value - min) / (max - min || 1);
    // Single-hue ramp: lightness carries the value, hue carries nothing.
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t);
    return `rgb(${mix(90, 232)},${mix(80, 147)},${mix(70, 58)})`;
  };

  return (
    <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="relative bg-ink-950 p-5 md:p-7">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <span className="label">Per-capita NSDP · 2024-25 · ₹ at current prices</span>
          <span className="font-mono text-2xs text-ink-600">Schematic — not a boundary map</span>
        </div>

        <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
          <svg
            viewBox="0 0 500 620"
            className="mx-auto h-auto w-full max-w-[430px]"
            role="img"
            aria-label="Schematic map of India with eight states positioned by location and sized by per-capita NSDP."
          >
            <path d={OUTLINE} fill="rgba(255,255,255,0.022)" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />

            {STATES.map((s) => {
              const active = s.id === selectedId;
              const hot = s.id === hoverId;
              return (
                <g
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  onMouseEnter={() => setHoverId(s.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(s.id)}
                  onBlur={() => setHoverId(null)}
                  tabIndex={0}
                  role="button"
                  aria-label={`${s.name}. Per-capita NSDP ${s.perCapitaNsdp.value === null ? 'unavailable' : rupees(s.perCapitaNsdp.value)}.`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedId(s.id);
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {(active || hot) && (
                    <circle cx={s.cx} cy={s.cy} r={radius(s) + 7} fill="none" stroke={tone(s)} strokeWidth={1} opacity={0.45} />
                  )}
                  <motion.circle
                    cx={s.cx}
                    cy={s.cy}
                    initial={false}
                    animate={{ r: radius(s) * (hot ? 1.12 : 1) }}
                    transition={{ type: 'spring', stiffness: 300, damping: 24 }}
                    fill={tone(s)}
                    fillOpacity={active ? 0.92 : 0.5}
                    stroke={tone(s)}
                    strokeWidth={active ? 1.5 : 1}
                  />
                  <text
                    x={s.cx}
                    y={s.labelAbove ? s.cy - radius(s) - 6 : s.cy + radius(s) + 12}
                    textAnchor="middle"
                    className={cn('font-mono', active ? 'fill-ink-100' : 'fill-ink-500')}
                    fontSize={10}
                  >
                    {s.id}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Ranked list. Ordering states by income per person is descriptive
              rather than evaluative, so unlike the bank explorer it sorts. */}
          <div className="self-start">
            <p className="label mb-3">Per person, ranked</p>
            <ul className="space-y-2.5">
              {[...STATES]
                .sort((a, b) => (b.perCapitaNsdp.value ?? -1) - (a.perCapitaNsdp.value ?? -1))
                .map((s) => {
                  const v = s.perCapitaNsdp.value;
                  const active = s.id === selectedId;
                  return (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(s.id)}
                        onMouseEnter={() => setHoverId(s.id)}
                        onMouseLeave={() => setHoverId(null)}
                        className="block w-full text-left"
                      >
                        <span className="flex items-baseline justify-between gap-2">
                          <span
                            className={cn(
                              'text-[0.8125rem] transition-colors',
                              active ? 'text-ink-50' : 'text-ink-400',
                            )}
                          >
                            {s.name}
                          </span>
                          <span className="metric text-2xs text-ink-400" data-numeric>
                            {v === null ? '—' : rupees(v)}
                          </span>
                        </span>
                        <span className="mt-1 block h-[3px] bg-ink-800">
                          <motion.span
                            className="block h-full"
                            style={{ background: tone(s) }}
                            initial={false}
                            animate={{ width: v === null ? '0%' : `${(v / max) * 100}%` }}
                            transition={{ type: 'spring', stiffness: 200, damping: 26 }}
                          />
                        </span>
                      </button>
                    </li>
                  );
                })}
            </ul>
          </div>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2">
          <span className="flex items-center gap-2 font-mono text-2xs text-ink-500">
            <span className="h-2 w-8" style={{ background: 'linear-gradient(90deg,rgb(90,80,70),rgb(232,147,58))' }} aria-hidden />
            {rupees(min)} → {rupees(max)}
          </span>
          <span className="font-mono text-2xs text-ink-600">Circle area scales with per-capita NSDP.</span>
        </div>

        <div className="mt-4">
          <Notice tone="missing" title="Coverage">
            {STATES_NOTE}
          </Notice>
        </div>
      </div>

      <aside className="bg-ink-900/70 p-5 md:p-6">
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: EASE_OUT }}
            >
              <span className="label-accent">{selected.region}</span>
              <h3 className="display mt-2 text-3xl">{selected.name}</h3>

              <dl className="mt-5 space-y-px border border-white/[0.07] bg-white/[0.07]">
                {[selected.perCapitaNsdp, selected.urbanisation, selected.gsdp, selected.sectors].map((m) => (
                  <div key={m.label} className="bg-ink-900 p-3.5">
                    <div className="flex items-baseline justify-between gap-3">
                      <dt className="label">{m.label}</dt>
                      <StatusBadge status={m.status} size="xs" withLabel={false} />
                    </div>
                    <dd className="mt-1.5">
                      {m.value === null ? (
                        <Unavailable reason={m.note} />
                      ) : (
                        <span className="metric text-xl" data-numeric>
                          {m.unit.startsWith('₹') ? rupees(m.value) : `${m.value}%`}
                        </span>
                      )}
                    </dd>
                    <p className="mt-1 font-mono text-2xs text-ink-600">{m.period}</p>
                    {m.note && <p className="mt-1.5 text-2xs leading-snug text-ink-600">{m.note}</p>}
                  </div>
                ))}
              </dl>

              {selected.commentary && (
                <p className="mt-4 border-l-2 border-[#e8933a] pl-3 text-[0.8125rem] leading-relaxed text-ink-300">
                  {selected.commentary}
                </p>
              )}

              <a
                href={selected.perCapitaNsdp.sourceUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="btn mt-5 inline-flex"
              >
                Open source <ExternalLink size={12} />
              </a>
            </motion.div>
          ) : (
            <p className="text-sm text-ink-500">Select a state.</p>
          )}
        </AnimatePresence>

        <div className="mt-6">
          <SourceDiscrepancy d={GSDP_DISCREPANCY} />
        </div>
      </aside>
    </div>
  );
}
