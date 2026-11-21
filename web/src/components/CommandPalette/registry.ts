import { MACRO_INDICATORS } from '../../data/macro/indicators';
import { BANKS } from '../../data/banking/panel';
import { GLOSSARY } from '../../data/glossary/terms';
import { LIBRARY } from '../../data/research/library';
import { STATES } from '../../data/states/states';
import { TIMELINE } from '../../data/timeline/events';
import { GREAT_INDIAN_PROMISE } from '../../data/research/greatIndianPromise';

export type CommandKind = 'action' | 'indicator' | 'bank' | 'term' | 'research' | 'state' | 'page' | 'event';

export interface Command {
  id: string;
  kind: CommandKind;
  title: string;
  subtitle?: string;
  /** Extra strings matched against the query but not displayed. */
  keywords?: string;
  to: string;
  /** Verb-style entries ("> Open BFPI") sort above plain matches. */
  verb?: string;
}

export const KIND_LABEL: Record<CommandKind, string> = {
  action: 'Command',
  indicator: 'Indicator',
  bank: 'Bank',
  term: 'Glossary',
  research: 'Research',
  state: 'State',
  page: 'Page',
  event: 'Timeline',
};

const PAGES: Command[] = [
  { id: 'p-home', kind: 'page', title: 'Home', to: '/' },
  { id: 'p-research', kind: 'page', title: 'Research', subtitle: 'Papers and methodology notes', to: '/research' },
  { id: 'p-data', kind: 'page', title: 'Data', subtitle: 'Macro, banking and states', to: '/data' },
  { id: 'p-models', kind: 'page', title: 'Models', subtitle: 'The IEIL Model Lab', to: '/models' },
  { id: 'p-fig2', kind: 'page', title: 'Figure 2 — Household Wealth Accumulation', to: '/models/figure-2' },
  { id: 'p-bfpi', kind: 'page', title: 'BFPI — Bank Financial Performance Index', to: '/models/bfpi' },
  { id: 'p-bfpi-method', kind: 'page', title: 'BFPI Methodology', to: '/models/bfpi/methodology' },
  { id: 'p-exp', kind: 'page', title: 'Experiments', to: '/experiments' },
  { id: 'p-india', kind: 'page', title: 'India', subtitle: 'Economic map and timeline', to: '/india' },
  { id: 'p-glossary', kind: 'page', title: 'Glossary', to: '/glossary' },
  { id: 'p-about', kind: 'page', title: 'About', to: '/about' },
];

const ACTIONS: Command[] = [
  { id: 'a-bfpi', kind: 'action', verb: '> Open BFPI', title: 'Open BFPI', subtitle: 'Bank Financial Performance Index', to: '/models/bfpi', keywords: 'bank index composite pillar' },
  { id: 'a-fig2', kind: 'action', verb: '> Open Figure 2', title: 'Open Figure 2', subtitle: 'Household wealth accumulation model', to: '/models/figure-2', keywords: 'wealth compounding portfolio' },
  { id: 'a-inflation', kind: 'action', verb: '> Show inflation', title: 'Show inflation', subtitle: 'CPI inflation in the Data explorer', to: '/data?indicator=cpi-inflation', keywords: 'cpi prices' },
  { id: 'a-gdp', kind: 'action', verb: '> Show GDP', title: 'Show GDP', subtitle: 'Real GDP growth, all vintages', to: '/data?indicator=gdp-growth', keywords: 'growth output' },
  { id: 'a-compare', kind: 'action', verb: '> Compare banks', title: 'Compare banks', subtitle: 'The BFPI bank explorer', to: '/models/bfpi#explorer', keywords: 'comparison peer' },
  { id: 'a-wealth', kind: 'action', verb: '> Run wealth experiment', title: 'Run wealth experiment', subtitle: 'Shift the portfolio and watch the curve', to: '/experiments#wealth', keywords: 'scenario simulate' },
  { id: 'a-stress', kind: 'action', verb: '> Stress the bank', title: 'Stress the bank', subtitle: 'Propagate a shock through the BFPI pillars', to: '/experiments#banking', keywords: 'npl shock scenario' },
  { id: 'a-nim', kind: 'action', verb: '> Explain NIM', title: 'Explain NIM', subtitle: 'Net Interest Margin — glossary', to: '/glossary?term=nim', keywords: 'margin spread' },
  { id: 'a-method', kind: 'action', verb: '> Read the methodology', title: 'Read the methodology', subtitle: 'How BFPI is constructed', to: '/models/bfpi/methodology' },
  { id: 'a-paper', kind: 'action', verb: '> Read the research', title: 'Read the research', subtitle: 'The Great Indian Promise', to: '/research/the-great-indian-promise' },
  { id: 'a-provenance', kind: 'action', verb: '> Show data sources', title: 'Show data sources', subtitle: 'Source registry and audit log', to: '/data#provenance' },
];

export function buildRegistry(): Command[] {
  return [
    ...ACTIONS,
    ...PAGES,
    ...MACRO_INDICATORS.map<Command>((d) => ({
      id: `i-${d.id}`,
      kind: 'indicator',
      title: d.indicator,
      subtitle: `${d.value === null ? 'unavailable' : `${d.value}${d.unitShort ?? ''}`} · ${d.period.label}`,
      keywords: `${d.dataset ?? ''} ${d.sourceId}`,
      to: `/data?indicator=${d.id}`,
    })),
    ...BANKS.map<Command>((b) => ({
      id: `b-${b.id}`,
      kind: 'bank',
      title: b.name,
      subtitle: `${b.ownership === 'public' ? 'Public sector' : 'Private sector'} · BFPI explorer`,
      keywords: b.shortName,
      to: `/models/bfpi?bank=${b.id}`,
    })),
    ...GLOSSARY.map<Command>((t) => ({
      id: `g-${t.id}`,
      kind: 'term',
      title: t.abbreviation ? `${t.term} (${t.abbreviation})` : t.term,
      subtitle: t.short,
      keywords: `${t.category} ${t.abbreviation ?? ''}`,
      to: `/glossary?term=${t.id}`,
    })),
    ...LIBRARY.filter((e) => e.to).map<Command>((e) => ({
      id: `r-${e.id}`,
      kind: 'research',
      title: e.title,
      subtitle: e.category,
      keywords: e.tags.join(' '),
      to: e.to!,
    })),
    ...GREAT_INDIAN_PROMISE.sections.map<Command>((s) => ({
      id: `s-${s.id}`,
      kind: 'research',
      title: s.title,
      subtitle: 'The Great Indian Promise',
      keywords: 'paper section',
      to: `/research/the-great-indian-promise#${s.id}`,
    })),
    ...STATES.map<Command>((s) => ({
      id: `st-${s.id}`,
      kind: 'state',
      title: s.name,
      subtitle: `${s.region} · state economics`,
      to: `/india?state=${s.id}`,
    })),
    ...TIMELINE.map<Command>((e) => ({
      id: `t-${e.id}`,
      kind: 'event',
      title: `${e.year} — ${e.title}`,
      subtitle: e.kicker,
      to: `/india?event=${e.id}#timeline`,
    })),
  ];
}

/**
 * Ranking. Prefix matches beat word-boundary matches beat substring
 * matches, and verb-style commands get a lift so "> Open BFPI" surfaces
 * above every incidental mention of BFPI.
 */
export function scoreCommand(c: Command, q: string): number {
  if (!q) return c.kind === 'action' ? 100 : 0;
  const needle = q.toLowerCase().replace(/^>\s*/, '');
  if (!needle) return c.verb ? 100 : 0;

  const hay = [c.verb ?? '', c.title, c.subtitle ?? '', c.keywords ?? ''].join(' ').toLowerCase();
  const title = c.title.toLowerCase();
  const verb = (c.verb ?? '').toLowerCase();

  let score = 0;
  if (verb.includes(needle)) score += 70;
  if (title === needle) score += 100;
  else if (title.startsWith(needle)) score += 60;
  else if (new RegExp(`\\b${needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`).test(title)) score += 40;
  else if (title.includes(needle)) score += 22;
  else if (hay.includes(needle)) score += 10;
  else {
    // All tokens must appear somewhere for a fuzzy pass.
    const tokens = needle.split(/\s+/).filter(Boolean);
    if (tokens.length > 1 && tokens.every((t) => hay.includes(t))) score += 8;
    else return 0;
  }
  if (c.kind === 'action') score += 6;
  return score;
}
