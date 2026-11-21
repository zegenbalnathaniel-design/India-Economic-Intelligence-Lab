export interface GlossaryTerm {
  id: string;
  term: string;
  abbreviation?: string;
  category: 'Measurement' | 'Banking' | 'Monetary' | 'Fiscal' | 'Distribution' | 'External' | 'Method';
  short: string;
  full: string;
  formula?: { ascii: string; latex: string };
  caution?: string;
  related?: string[];
  sourceLabel?: string;
  sourceUrl?: string;
}

export const GLOSSARY: GlossaryTerm[] = [
  {
    id: 'gini',
    term: 'Gini coefficient',
    category: 'Distribution',
    short: 'A single number summarising how unequally something is distributed, from 0 (everyone equal) to 1 (one person holds everything).',
    full: 'The Gini coefficient is twice the area between the Lorenz curve — cumulative share of income or wealth against cumulative share of population — and the 45° line of perfect equality. Its appeal is that it compresses an entire distribution into one comparable number; its weakness is the same thing. Two distributions with very different shapes can share a Gini, and the coefficient is least sensitive exactly where policy attention usually falls, at the top and bottom tails.',
    formula: { ascii: 'G = A / (A + B)', latex: 'G=\\frac{A}{A+B}' },
    caution:
      'Wealth Ginis computed from Indian household surveys understate concentration, because survey instruments systematically under-reach the top tail.',
    related: ['lorenz'],
  },
  {
    id: 'lorenz',
    term: 'Lorenz curve',
    category: 'Distribution',
    short: 'A plot of cumulative share of income or wealth against cumulative share of population, ordered from poorest to richest.',
    full: 'The Lorenz curve is the object the Gini coefficient summarises. Reading the curve rather than the summary tells you where inequality sits: a curve that hugs the diagonal until the last decile describes a very different society from one that departs from it immediately, even when both yield the same Gini.',
    related: ['gini'],
  },
  {
    id: 'nim',
    term: 'Net Interest Margin',
    abbreviation: 'NIM',
    category: 'Banking',
    short: 'Net interest income as a share of average interest-earning assets — the spread a bank earns on intermediation.',
    full: 'NIM measures what is left of interest income after interest expense, relative to the assets generating it. It isolates the core intermediation business from fee income and from credit costs, which makes it a cleaner read on how a bank is run than profit alone. Structurally it reflects funding mix — a large low-cost current and savings account base lifts NIM directly — and asset mix, since unsecured retail lending carries a wider spread than mortgages.',
    formula: { ascii: 'NIM = Net interest income / Average interest-earning assets', latex: 'NIM=\\frac{\\text{Net interest income}}{\\text{Average interest-earning assets}}' },
    caution:
      'A wide NIM is not unambiguously good. It can reflect a riskier loan book whose credit costs arrive later, which is why BFPI pairs it with ROE and with asset quality rather than reading it alone.',
    related: ['roe', 'npl'],
  },
  {
    id: 'roe',
    term: 'Return on Equity',
    abbreviation: 'ROE',
    category: 'Banking',
    short: 'Profit after tax as a share of average shareholders’ equity.',
    full: 'ROE answers what the capital committed to the bank earned. It is the natural companion to NIM, because a bank can hold a wide spread and convert it poorly — through operating costs, credit losses or an inefficient capital structure. ROE is mechanically raised by leverage, so a bank with thin capital can post a high ROE precisely because it holds less of the buffer that protects depositors.',
    formula: { ascii: 'ROE = Profit after tax / Average shareholders’ equity', latex: 'ROE=\\frac{\\text{PAT}}{\\text{Average equity}}' },
    caution:
      'Because leverage raises ROE, reading it without the capital ratio inverts the risk picture. BFPI weights Capital equally with Profitability for exactly this reason.',
    related: ['nim', 'cet1'],
  },
  {
    id: 'npl',
    term: 'Non-Performing Loan ratio',
    abbreviation: 'NPL / GNPA',
    category: 'Banking',
    short: 'Gross non-performing loans as a share of gross advances — the stock of credit that has already gone wrong.',
    full: 'A loan is classified non-performing when interest or principal is overdue beyond a supervisory threshold, generally 90 days in India. The gross ratio measures the stock before provisions; the net ratio measures what is left after them. The gross ratio is the more informative of the two for cross-bank comparison, because provisioning policy varies.',
    caution:
      'A falling NPL ratio can reflect genuine recovery, or write-offs, or rapid growth in the denominator. The direction alone does not distinguish them, which is why the flow measure — credit-loss provisions — belongs alongside it.',
    related: ['provisions'],
  },
  {
    id: 'provisions',
    term: 'Credit-loss provisions',
    category: 'Banking',
    short: 'The charge a bank takes in a period against expected loan losses — the flow counterpart to the NPL stock.',
    full: 'Provisions are the income-statement recognition of credit deterioration. Read against the NPL ratio they separate a bank working down a legacy book, where the stock is high but the flow is falling, from one accumulating new problems, where the stock still looks acceptable but the flow is rising.',
    related: ['npl'],
  },
  {
    id: 'cet1',
    term: 'Common Equity Tier 1 ratio',
    abbreviation: 'CET1',
    category: 'Banking',
    short: 'The highest-quality loss-absorbing capital as a share of risk-weighted assets.',
    full: 'CET1 is ordinary shares and retained earnings — capital that absorbs losses immediately and without triggering default — divided by assets weighted for their riskiness. It is the ratio Basel III places at the centre of the capital framework and the first number a supervisor looks at. Total capital adequacy (CAR) adds Additional Tier 1 and Tier 2 instruments, which absorb losses later and less cleanly.',
    formula: { ascii: 'CET1 = CET1 capital / Risk-weighted assets', latex: 'CET1=\\frac{\\text{CET1 capital}}{\\text{RWA}}' },
    caution:
      'CET1 and CAR are different ratios and one is never a substitute for the other. Where a bank in the BFPI panel disclosed only CAR, the CET1 cell is left empty rather than filled with it.',
    related: ['roe', 'lcr'],
  },
  {
    id: 'lcr',
    term: 'Liquidity Coverage Ratio',
    abbreviation: 'LCR',
    category: 'Banking',
    short: 'High-quality liquid assets against projected net cash outflows over a 30-day stress scenario.',
    full: 'LCR asks a different question from every other prudential ratio: not whether the bank is solvent, but whether it can meet outflows for thirty days without selling assets into a falling market. The regulatory minimum is 100%. The scenario is prescribed by the supervisor, so the ratio is comparable across banks in a way that internal liquidity models are not.',
    formula: { ascii: 'LCR = HQLA / 30-day net cash outflows', latex: 'LCR=\\frac{\\text{HQLA}}{\\text{30-day net cash outflows}}' },
    caution:
      'Banks disclose LCR on different consolidation bases — bank level, consolidated and group. Comparing across bases, as any cross-bank composite must, introduces noise that is not in the underlying liquidity position.',
    related: ['cet1'],
  },
  {
    id: 'repo',
    term: 'Policy repo rate',
    category: 'Monetary',
    short: 'The rate at which the RBI lends overnight to banks against government securities.',
    full: 'The repo rate is the operating instrument of Indian monetary policy, set by the Monetary Policy Committee. It anchors the short end of the yield curve and transmits — imperfectly and with a lag — to deposit and lending rates. The corridor around it matters: the standing deposit facility sets the floor and the marginal standing facility the ceiling for overnight money.',
    caution: 'A change in the repo rate is not a change in the rate households and firms face. Transmission depends on bank funding mix, competitive conditions and the share of loans on external benchmarks.',
    related: ['transmission', 'inflation'],
  },
  {
    id: 'transmission',
    term: 'Monetary transmission',
    category: 'Monetary',
    short: 'The process by which a change in the policy rate reaches output and prices.',
    full: 'Transmission runs through several channels at once: bank lending rates, asset prices, the exchange rate and expectations. In India it is generally found to be slower and more incomplete than in economies with deeper bond markets and a larger share of floating-rate credit, though the shift toward external-benchmark-linked lending has shortened the lag on the credit channel.',
    related: ['repo'],
  },
  {
    id: 'inflation',
    term: 'Inflation',
    category: 'Monetary',
    short: 'The rate at which the general price level rises, measured here by the Consumer Price Index.',
    full: 'India’s monetary policy framework targets CPI inflation at 4%, with a tolerance band of ±2 percentage points. Headline CPI includes food and fuel, which are volatile and weigh heavily in the Indian basket; core inflation strips them out and is the better guide to underlying pressure, though it is not what the framework targets.',
    caution:
      'The CPI was rebased to 2024=100 during 2026. Readings on the new base are not directly comparable with those on 2012=100, because the basket weights changed.',
    related: ['deflator', 'repo'],
  },
  {
    id: 'deflator',
    term: 'GDP deflator',
    category: 'Measurement',
    short: 'The ratio of nominal to real GDP — the broadest measure of economy-wide price change.',
    full: 'The deflator covers everything in GDP, including investment and government spending, rather than a fixed consumption basket. It therefore diverges from CPI, sometimes substantially: a terms-of-trade shift that changes import prices moves the two in opposite directions, because imports enter GDP negatively.',
    formula: { ascii: 'Deflator = (Nominal GDP / Real GDP) × 100', latex: '\\text{Deflator}=\\frac{\\text{Nominal GDP}}{\\text{Real GDP}}\\times 100' },
    related: ['realgdp', 'inflation'],
  },
  {
    id: 'realgdp',
    term: 'Real GDP',
    category: 'Measurement',
    short: 'Output valued at the prices of a fixed base year, so that growth reflects volume rather than price.',
    full: 'India’s national accounts use a 2011-12 base. Real growth is the number quoted as "GDP growth"; nominal growth includes price change and is the relevant denominator for ratios such as debt-to-GDP. Estimates are published in vintages — advance, revised, provisional — and the differences between them are often larger than the differences between years.',
    caution:
      'A financial-year figure is never the same as a calendar-year figure. FY2025-26 runs from April 2025 to March 2026 and is not "2026".',
    related: ['deflator'],
  },
  {
    id: 'fiscalmultiplier',
    term: 'Fiscal multiplier',
    category: 'Fiscal',
    short: 'The change in output produced by a one-rupee change in government spending or taxation.',
    full: 'The multiplier is not a constant. It varies with the state of the economy — larger when there is slack and when monetary policy is not offsetting — with the type of spending, capital expenditure generally carrying a higher multiplier than transfers, and with the openness of the economy, since imports leak demand abroad. Estimates for India vary widely across studies and methods.',
    caution: 'Any single quoted multiplier is conditional on the method, period and specification that produced it.',
    related: ['fiscaldeficit'],
  },
  {
    id: 'fiscaldeficit',
    term: 'Fiscal deficit',
    category: 'Fiscal',
    short: 'Total government expenditure less revenue receipts and non-debt capital receipts, usually as a share of GDP.',
    full: 'The fiscal deficit measures the government’s borrowing requirement. The Union Budget figure covers the central government only; adding state deficits gives the general government position, which roughly doubles the number and is the figure comparable to headline deficits quoted internationally.',
    caution: 'A central-government deficit is not the general-government deficit. The two are routinely compared across countries as though they were the same measurement.',
    related: ['fiscalmultiplier'],
  },
  {
    id: 'currentaccount',
    term: 'Current account',
    category: 'External',
    short: 'Trade in goods and services, plus primary and secondary income, with the rest of the world.',
    full: 'The current account records the flow of goods, services, income on investments and transfers such as remittances. India characteristically runs a large goods deficit offset by a services surplus and remittance inflows, which is why a merchandise trade deficit of US$86 billion in a quarter coexists with a current account deficit of half a percent of GDP.',
    caution: 'A current account deficit is a financing statement, not a verdict. It records that the country is importing capital, which may be funding investment or consumption.',
    related: ['capitalaccount'],
  },
  {
    id: 'capitalaccount',
    term: 'Capital and financial account',
    category: 'External',
    short: 'Cross-border transactions in assets — direct investment, portfolio flows, loans and reserves.',
    full: 'The financial account mirrors the current account by construction: a current account deficit must be financed by net capital inflows or by drawing down reserves. The composition of that financing matters more than its size — direct investment is stickier than portfolio flows, which can reverse quickly.',
    related: ['currentaccount'],
  },
  {
    id: 'zscore',
    term: 'z-score',
    category: 'Method',
    short: 'How many standard deviations an observation lies from the mean of its sample.',
    full: 'Standardising puts variables measured in different units — percent, ratios, rupees — on a common scale so they can be combined. The z-score is the basis of the BFPI composite. A direction coefficient of −1 is applied to variables where a higher raw value is worse, so that a higher z always means better performance.',
    formula: { ascii: 'z = d · (X − μ) / σ', latex: 'z_i=d_i\\frac{X_i-\\mu_i}{\\sigma_i}' },
    caution:
      'A z-score is relative to its sample. Change the sample and every score changes, which is why BFPI is a statement about a bank’s position within a selected set and period, never about the bank in isolation.',
    related: ['bfpi'],
  },
  {
    id: 'bfpi',
    term: 'Bank Financial Performance Index',
    abbreviation: 'BFPI',
    category: 'Method',
    short: 'An original composite index constructed by IEIL across profitability, capital, asset quality and liquidity.',
    full: 'BFPI standardises six indicators within a selected sample, averages them into four equally-weighted pillars, and presents the composite on a 0–100 scale centred at 50. It is an analytical construction, not an official measure, not a rating and not a prediction.',
    formula: { ascii: 'BFPI = 50 + 10 · (0.25P + 0.25C + 0.25A + 0.25L)', latex: 'BFPI=50+10Z_{BFPI}' },
    caution: 'Results depend on the sample, period, indicators, standardisation and weighting chosen. Change any of them and the scores change.',
    related: ['zscore', 'nim', 'cet1'],
    sourceLabel: 'BFPI methodology',
    sourceUrl: '/models/bfpi/methodology',
  },
  {
    id: 'compounding',
    term: 'Compounding',
    category: 'Method',
    short: 'Earning returns on previously earned returns, so that value grows geometrically rather than linearly.',
    full: 'Compounding is why a 60-basis-point difference in annual return becomes a 28% difference in terminal wealth over thirty years. It is also why the difference between an asset that reinvests automatically and one that does not is larger than the headline returns suggest: an asset yielding nothing until sale forgoes the reinvestment entirely.',
    formula: { ascii: 'FV = C · [ (1+r)ⁿ − 1 ] / r', latex: 'FV=C\\frac{(1+r)^n-1}{r}' },
    related: ['realgdp'],
    sourceLabel: 'Figure 2 — Household Wealth Accumulation',
    sourceUrl: '/models/figure-2',
  },
];

export const GLOSSARY_BY_ID = Object.fromEntries(GLOSSARY.map((t) => [t.id, t]));
export const GLOSSARY_CATEGORIES = Array.from(new Set(GLOSSARY.map((t) => t.category))).sort();
