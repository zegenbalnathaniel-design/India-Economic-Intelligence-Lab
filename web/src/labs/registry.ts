/**
 * The seven research labs ported from the Streamlit supplement, in the
 * order of its navigation. One accent colour per lab (the Streamlit
 * LAB_ACCENTS system), carried into the lab's hero figure, rules and charts.
 */
export type FigureName = 'Branches' | 'Lockers' | 'Riffle' | 'Elevator' | 'Exploded' | 'Plot' | 'Dish' | 'Cabinet' | 'Terrain' | 'Turntable';

export interface LabMeta {
  slug: string;
  n: string;
  title: string;
  short: string;
  group: 'Labs' | 'Models & tools';
  question: string;
  blurb: string;
  accent: string;
  figure: FigureName;
  keywords: string;
}

export const LABS: LabMeta[] = [
  {
    slug: 'states',
    n: '03',
    title: 'State Economy Lab',
    short: 'States',
    group: 'Labs',
    question: 'Are India’s states converging, or drifting apart?',
    blurb: 'σ- and β-convergence on the spliced RBI per-capita NSDP series, a schematic tile map, rankings, and a workbench for comparing up to five states.',
    accent: '#6fae4f',
    figure: 'Branches',
    keywords: 'convergence sigma beta nsdp tile map ranking divergence regional',
  },
  {
    slug: 'housing',
    n: '04',
    title: 'Housing Intelligence Lab',
    short: 'Housing',
    group: 'Labs',
    question: 'How far is a home from a household’s income, city by city?',
    blurb: 'Real NHB RESIDEX prices against three income measures: price-to-income, an EMI calculator, the RPIPI pressure index over time and the ICHASI stress score.',
    accent: '#f3c542',
    figure: 'Lockers',
    keywords: 'residex emi mortgage affordability price to income rpipi ichasi city',
  },
  {
    slug: 'inequality',
    n: '05',
    title: 'Inequality & Financialisation Lab',
    short: 'Inequality',
    group: 'Labs',
    question: 'Who holds India’s income and wealth, and is finance broadening it?',
    blurb: 'Lorenz curves and lower-bound Ginis from the World Inequality Lab tables, what households hold and owe, and Global Findex / WDI financial-depth series.',
    accent: '#f04a32',
    figure: 'Riffle',
    keywords: 'wil lorenz gini top 1% wealth income findex account ownership market cap aidis debt',
  },
  {
    slug: 'structural',
    n: '06',
    title: 'Structural Transformation Lab',
    short: 'Structural',
    group: 'Labs',
    question: 'Has India moved workers out of farming as fast as output moved?',
    blurb: 'Output vs employment shares, relative labour productivity, manufacturing’s share, labour-force participation and India against its peers — plus state-level sector shares.',
    accent: '#24a6a1',
    figure: 'Elevator',
    keywords: 'agriculture industry services employment productivity manufacturing lfp peers',
  },
  {
    slug: 'relationships',
    n: '07',
    title: 'Economic Relationships Lab',
    short: 'Relationships',
    group: 'Labs',
    question: 'Which economic variables actually move together — and does it survive scrutiny?',
    blurb: 'Fifteen pre-specified hypotheses with alignment reports, transforms, Spearman verdicts, first-difference checks, lag and rolling correlations — and a full multiple-regression workbench.',
    accent: '#4d6ff0',
    figure: 'Plot',
    keywords: 'correlation regression ols hypothesis spearman workbench robust hc1 hac diagnostics vif',
  },
  {
    slug: 'transmission',
    n: '08',
    title: 'Macro Transmission Simulator',
    short: 'Transmission',
    group: 'Models & tools',
    question: 'If the repo rate, oil, the rupee or capex moves — what follows, by how much?',
    blurb: 'Four shock scenarios propagated through linear chains whose every coefficient carries a citation, with two editable parameter sets side by side.',
    accent: '#f0663f',
    figure: 'Dish',
    keywords: 'repo rate oil crude rupee depreciation capex multiplier simulator shock cpi gdp cad',
  },
  {
    slug: 'macro',
    n: '09',
    title: 'India Macro & World',
    short: 'Macro & World',
    group: 'Models & tools',
    question: 'Where does India stand this month, and against its peers?',
    blurb: 'The latest monthly releases and RBI policy decisions, then twelve World Bank indicators for India against up to thirteen peer economies.',
    accent: '#5fd0c9',
    figure: 'Cabinet',
    keywords: 'cpi iip inflation repo mpc world bank peers gdp growth reserves exchange rate',
  },
];

export const labBySlug = (slug: string) => LABS.find((l) => l.slug === slug);
