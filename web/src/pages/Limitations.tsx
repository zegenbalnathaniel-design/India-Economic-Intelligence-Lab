import { motion } from 'framer-motion';
import { Callout, DataTable } from '../components/Lab/LabKit';
import L from '../data/labs/library.json';
import { EASE_OUT } from '../lib/motion';
import { PageHeader } from './PageHeader';

type Lim = { limitation: string; where: string; mitigation: string };

function robustnessText() {
  const rob = L.sigmaRobustness as { panel: string; end: string; n_states: number; measure: string; verdict: string }[];
  const full = rob.filter((r) => r.panel.startsWith('full'));
  const alt = rob.filter((r) => r.panel.startsWith('all states'));
  if (!full.length || !alt.length) return 'Balanced panel by default; the all-states comparison is shown in the State Economy Lab';
  const nAll = alt[0].n_states;
  const nBal = full[0].n_states;
  const rising = alt.filter((r) => r.verdict === 'rising').length;
  const cv = alt.find((r) => r.measure === 'cv')?.verdict ?? 'n/a';
  return `Headline uses the balanced panel (${nBal} states with data in every year to ${full[0].end}); ${nAll - nBal} states are dropped for missing the last year. Keeping all ${nAll} states to ${alt[0].end}, ${rising} of ${alt.length} dispersion measures rise and the CV is ${cv} — both comparisons are shown`;
}

const SECTIONS: { title: string; rows: Lim[] }[] = [
  {
    title: 'Wealth & inequality',
    rows: [
      { limitation: 'Historical returns are not future returns', where: 'Composition effect, asset allocation comparison', mitigation: 'Every return is user-editable; the Monte Carlo shows dispersion' },
      { limitation: 'Deterministic returns (default view)', where: 'Final wealth is a central tendency, not a forecast', mitigation: 'The Monte Carlo renders the 5–95% band' },
      { limitation: 'Correlations and tail heaviness are assumptions, not estimates', where: 'Monte Carlo band width depends on the correlation and t degrees of freedom you set', mitigation: 'Correlated and fat-tailed draws are checked for consistency; estimating correlations needs Indian asset-return history' },
      { limitation: 'No fees, taxes or transaction costs', where: 'Final wealth is overstated relative to net-of-costs reality', mitigation: 'Documented; a natural extension' },
      { limitation: 'Gini is a lower bound', where: 'Built from five published group shares, so inequality within each group is ignored', mitigation: 'Labelled as a lower bound; a full Gini needs AIDIS / NSS household microdata' },
      { limitation: 'No figures for the Bottom 10% or P10–P50', where: 'The two lowest Riffle cards and table rows', mitigation: 'Shown as DATA REQUIRED; WID.world downloads for p0p10 and p10p50 would fill them' },
      { limitation: 'Top-tail wealth undercoverage in Indian survey data', where: 'Any Gini or top-share statistic', mitigation: 'WIL combines AIDIS with Forbes rich lists; the authors still describe results as a lower bound' },
      { limitation: 'Asset-valuation uncertainty (property, gold)', where: 'Household wealth is measured with error', mitigation: 'The model uses target values, not marked-to-market' },
    ],
  },
  {
    title: 'Banking & monetary policy',
    rows: [
      { limitation: 'Illustrative panel in this build', where: 'iBFPI levels and the ρ estimate reflect the synthetic generator', mitigation: 'The panel is CSV-replaceable; the loader has no hard-coded values' },
      { limitation: 'Small sample (n ≈ 26 quarters)', where: 'Regime-conditional ρ has n well below rules of thumb', mitigation: 'n reported alongside every ρ; p-values shown' },
      { limitation: 'Autocorrelation in quarterly series', where: 'Spearman p-values understate uncertainty', mitigation: 'Newey–West (HAC) errors in the robustness regression; Spearman p-values themselves are unadjusted' },
      { limitation: 'No macro controls in the fixed-effects regression', where: 'The repo-rate slope may pick up the business cycle', mitigation: 'Stated next to the table; needs quarterly GDP and CPI series' },
      { limitation: 'Cross-bank accounting differences', where: 'IND-AS transitions create structural breaks', mitigation: 'Per-bank standardisation absorbs level differences but not slope breaks' },
      { limitation: 'Regime threshold (±25 bp on a 3-quarter change) is a modelling choice', where: 'Other thresholds re-label periods and change ρ per regime', mitigation: 'Documented' },
      { limitation: 'Survivorship bias in the bank subset', where: 'Only five large extant banks are in the panel', mitigation: 'Scope is stated as five specific banks' },
    ],
  },
  {
    title: 'States, housing and structural change',
    rows: [
      { limitation: 'The convergence verdict depends on which states are compared', where: 'σ-convergence headline (State Economy Lab, Research Library)', mitigation: robustnessText() },
      { limitation: 'Unweighted across states', where: 'σ and β treat a small state the same as Uttar Pradesh', mitigation: 'Stated on the page; population weighting needs a state population series (DATA REQUIRED)' },
      { limitation: 'Spliced constant-price series', where: 'Real per-capita NSDP across the 2004-05 and 2011-12 bases', mitigation: 'Splice method documented and every row’s method is recorded' },
      { limitation: 'β regression is a small cross-section with no controls', where: 'β slope, speed of convergence, half-life', mitigation: 'n, SE (classical or HC1), CI and p shown' },
      { limitation: 'City household income is an average, for 28 of the 50 RESIDEX cities', where: 'Price-to-income and EMI-to-income', mitigation: 'Averages understate a typical household’s burden; other cities can only use state proxies. RESIDEX prices are assessment prices, not transactions' },
      { limitation: 'Employment shares are ILO modelled estimates, not PLFS', where: 'Structural Transformation Lab: RLP and sector gaps', mitigation: 'Labelled ILO modelled; value-added shares are of GDP at market prices, so the residual is shown' },
      { limitation: 'World Bank series are a dated snapshot', where: 'Structural Transformation, Inequality & Financialisation, India Macro & World', mitigation: `Retrieved from the WDI API at build time (${L.retrieved}) and labelled with that date; re-export to refresh. No values are invented for missing years` },
    ],
  },
  {
    title: 'Financialisation, the simulator and the regression workbench',
    rows: [
      { limitation: 'No household-group breakdown of financial assets', where: 'Whether financial gains are broad-based', mitigation: 'AIDIS by wealth group, AMFI folios/SIPs and NSDL/CDSL demat data are DATA REQUIRED' },
      { limitation: 'Billionaire lists and WIL top shares are not independent', where: 'Correlation of Forbes wealth with the Top 0.1% share', mitigation: 'Stated next to the result; WIL uses rich lists for the top tail' },
      { limitation: 'Simulator parameters come from different studies, periods and methods', where: 'Every Macro Transmission Simulator output', mitigation: 'Labelled HYPOTHETICAL; links are added up linearly with no general-equilibrium consistency' },
      { limitation: 'Simulator citations were checked through search results, not source documents', where: 'All cited defaults', mitigation: 'Each row records the quote and how it was checked; unconfirmed values were removed (DATA REQUIRED)' },
      { limitation: 'Regression workbench is OLS on short samples', where: 'Coefficients, p-values, R²', mitigation: 'Robust (HC1, Newey–West) errors, diagnostics and a levels-vs-differences check; no causal or panel methods' },
      { limitation: 'Research Library text is generated by fixed rules', where: 'Findings and interpretation in each investigation', mitigation: 'Every sentence is built from computed values; nothing claims cause and effect' },
    ],
  },
];

const KINDS = [
  ['Data', 'what’s missing, proxied, or a single cross-section'],
  ['Measurement', 'what a number is actually counting'],
  ['Causality', 'what a correlation cannot tell you'],
  ['Assumptions', 'what a user-set slider is standing in for'],
  ['External validity', 'what a result does and doesn’t generalise to'],
  ['Time', 'what’s current, what’s dated, what’s a single snapshot'],
];

export function Limitations() {
  return (
    <>
      <PageHeader
        label="Limitations"
        title="What this lab cannot tell you"
        lede="Six kinds of limits, not one — stated plainly, by module, not buried in a tooltip."
        figure={{
          name: 'Vault',
          accent: '#f04a32',
          label: 'A vault door with a combination dial; turning it to the combination opens the bolts.',
          idle: 'Turn the dial.',
          caption: (read) => (!read || read === 'rest' ? null : read.includes('open') ? 'A model is not reality. It is a way of asking questions about reality.' : 'Keep turning…'),
        }}
      />
      <div className="mx-auto max-w-[1400px] px-5 py-14 md:px-10 md:py-20">
        <div className="grid gap-px border border-white/[0.09] bg-white/[0.09] sm:grid-cols-2 lg:grid-cols-3">
          {KINDS.map(([k, d], i) => (
            <motion.div key={k} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.06, ease: EASE_OUT }} className="bg-ink-950 p-5">
              <div className="label-accent">{k}</div>
              <div className="mt-2 text-[13.5px] text-ink-300">{d}</div>
            </motion.div>
          ))}
        </div>
        <div className="mt-10">
          <Callout tone="warn" title="Cross-cutting">
            Correlation is not causation. No coefficient on this site — Spearman ρ, regime-conditional ρ, an OLS slope — is a causal
            estimate. Causal claims require an identification strategy this lab does not implement.
          </Callout>
        </div>
        {SECTIONS.map((s, i) => (
          <motion.section key={s.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-40px' }} transition={{ duration: 0.7, ease: EASE_OUT }} className="mt-14">
            <motion.div aria-hidden className="rule-draw mb-6" initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 1.1, ease: EASE_OUT }} />
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-[2rem] font-light" style={{ color: 'var(--accent)' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <h2 className="display text-[1.8rem] md:text-[2.3rem]">{s.title}</h2>
            </div>
            <div className="mt-6">
              <DataTable
                maxHeight={1000}
                columns={[
                  { key: 'limitation', label: 'Limitation', format: (v) => <span className="text-ink-50">{v as string}</span> },
                  { key: 'where', label: 'Where it bites' },
                  { key: 'mitigation', label: 'Mitigation' },
                ]}
                rows={s.rows as unknown as Record<string, unknown>[]}
              />
            </div>
          </motion.section>
        ))}
        <section className="mt-14">
          <h2 className="display text-[1.8rem] md:text-[2.3rem]">What the site does not claim</h2>
          <ul className="mt-5 grid gap-2 md:grid-cols-2">
            {[
              'It does not identify the causal effect of monetary policy on bank performance.',
              'It does not claim that any specific asset is universally better.',
              'It does not claim r > g mechanically produces individual inequality.',
              'It does not provide personalised financial advice.',
              'It does not present iBFPI as an established or industry-standard index.',
              'It does not forecast: the Macro Transmission Simulator shows hypothetical shocks with cited sensitivities, not predictions.',
            ].map((t) => (
              <li key={t} className="border-l-2 bg-ink-900/50 px-4 py-3 text-[13.5px] text-ink-200" style={{ borderLeftColor: '#f04a32' }}>
                {t}
              </li>
            ))}
          </ul>
          <p className="mt-8 font-mono text-[11px] text-ink-500">This is a research showcase. If a claim looks stronger than the evidence should permit, flag it — a research portfolio should surface uncertainty, not hide it.</p>
        </section>
      </div>
    </>
  );
}

export default Limitations;
