import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PANEL_CAVEATS } from '../data/banking/panel';
import { RETRIEVAL_NOTE } from '../data/sources';
import { BFPI_BANDS, INDICATORS, PILLARS } from '../models/bfpi/engine';
import { INDICATOR_KEYS, PILLAR_KEYS } from '../models/bfpi/types';
import { Notice } from '../components/ui';
import { PageHeader } from './PageHeader';

function Eq({ children, caption }: { children: string; caption?: string }) {
  return (
    <figure className="my-6 border-y border-white/[0.09] py-5 text-center">
      <p className="metric text-lg text-ink-50">{children}</p>
      {caption && (
        <figcaption className="mx-auto mt-3 max-w-xl text-2xs leading-relaxed text-ink-500">{caption}</figcaption>
      )}
    </figure>
  );
}

function H2({ children, id }: { children: string; id?: string }) {
  return (
    <h2 id={id} className="display mt-14 scroll-mt-24 text-[1.75rem] leading-tight md:text-[2.125rem]">
      {children}
    </h2>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="prose-research mt-4 text-pretty">{children}</p>;
}

export function BFPIMethodology() {
  return (
    <>
      <PageHeader
        label="Methodology"
        title="How BFPI is constructed"
        lede="Every choice behind the index, stated and defended: which indicators, which direction, why equal weights, why z-scores, why a 0–100 scale, and what the index cannot tell you."
        actions={
          <Link to="/models/bfpi" className="btn btn-primary">
            Open the model <ArrowRight size={12} />
          </Link>
        }
      />

      <article className="mx-auto max-w-[1400px] px-5 py-12 md:px-10 md:py-16">
        <div className="mx-auto max-w-reading">
          <Notice tone="caution" title="What BFPI is">
            BFPI is an original composite index constructed for analytical purposes. It is not an official RBI
            measure or banking-sector rating. Results depend on the selected sample, period, variables,
            standardisation method and weighting methodology.
          </Notice>

          <H2 id="indicators">Why these six indicators</H2>
          <P>
            A bank can fail in four broadly independent ways: it can stop earning, it can run out of capital, its
            loan book can deteriorate, or it can run out of cash. A composite that measures one of these
            dimensions well and ignores the others is not a summary of bank performance — it is a summary of one
            thing wearing the clothes of a summary of everything.
          </P>
          <P>
            The six indicators below are chosen so that each of the four dimensions is represented, and so that
            no dimension is represented by a measure that can be improved by worsening another.
          </P>

          <div className="mt-6 space-y-5">
            {INDICATOR_KEYS.map((k) => {
              const s = INDICATORS[k];
              return (
                <div key={k} className="border-l-2 border-white/[0.12] pl-4">
                  <div className="flex flex-wrap items-baseline gap-3">
                    <span className="font-mono text-2xs uppercase tracking-[0.14em] text-[#e8933a]">{s.short}</span>
                    <span className="text-[0.9375rem] text-ink-100">{s.label}</span>
                    <span
                      className="font-mono text-2xs"
                      style={{ color: s.direction > 0 ? '#4fae86' : '#d3675d' }}
                    >
                      d = {s.direction > 0 ? '+1' : '−1'} ({s.direction > 0 ? 'higher is better' : 'lower is better'})
                    </span>
                  </div>
                  <p className="mt-2 text-[0.875rem] leading-relaxed text-ink-300 text-pretty">{s.rationale}</p>
                </div>
              );
            })}
          </div>

          <H2 id="standardisation">Why z-scores</H2>
          <P>
            The six indicators are measured in incompatible units. NIM is a few percent, LCR is over a hundred
            percent, ROE can be negative. Combining them directly would weight them by the accident of their
            scale: LCR, being a large number, would dominate any unweighted sum.
          </P>
          <P>
            Standardisation removes the units. Each observation is expressed as the number of standard
            deviations it sits from the mean of the sample:
          </P>
          <Eq caption="Xᵢ is the bank's observation, μᵢ the sample mean, σᵢ the sample standard deviation, and dᵢ the direction coefficient.">
            zᵢ = dᵢ (Xᵢ − μᵢ) / σᵢ
          </Eq>
          <P>
            The direction coefficient is what makes the composite interpretable in one direction. For NPL and
            credit-loss provisions a higher raw value is worse, so dᵢ = −1 reverses the sign and a higher z
            always means better relative performance, whatever the indicator.
          </P>
          <P>
            The population standard deviation is used rather than the sample-corrected one, because the sample
            here <em>is</em> the reference set — we are not estimating a parameter of a wider population of
            banks, we are describing positions within a set we have fully observed. Where σ is zero, because
            every bank reported the same value, the z-score is 0: there is no relative information to extract,
            and reporting an infinite score would be an artefact rather than a finding.
          </P>

          <H2 id="pillars">Why four pillars and equal weights</H2>
          <P>
            Standardised indicators are averaged into four pillars, and the pillars are averaged into the
            composite with equal weights of 25% each.
          </P>

          <div className="mt-6 space-y-px border border-white/[0.09] bg-white/[0.09]">
            {PILLAR_KEYS.map((k) => {
              const p = PILLARS[k];
              return (
                <div key={k} className="bg-ink-950 p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-[0.9375rem] text-ink-100">{p.label}</span>
                    <span className="metric text-sm text-[#e8933a]">{(p.weight * 100).toFixed(0)}%</span>
                  </div>
                  <p className="mt-1.5 font-mono text-2xs text-ink-500">
                    {p.indicators.map((i) => INDICATORS[i].short).join(' + ')}
                    {p.indicators.length > 1 ? ' ÷ ' + p.indicators.length : ''}
                  </p>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-ink-400">{p.rationale}</p>
                </div>
              );
            })}
          </div>

          <Eq caption="P, C, A and L are the four pillar scores in z units.">
            Z_BFPI = 0.25·P + 0.25·C + 0.25·A + 0.25·L
          </Eq>

          <P>
            Equal weighting is a choice, and it should be defended rather than assumed. The defence is that any
            other weighting requires a theory of relative importance that the evidence does not supply. A
            regulator stress-testing solvency would weight capital more heavily; an equity analyst would weight
            profitability more heavily; a depositor would weight liquidity more heavily. Each of those is a
            legitimate index and none of them is <em>the</em> index. Equal weights make the absence of a
            privileged viewpoint explicit instead of smuggling one in.
          </P>
          <P>
            The cost is real: equal weighting implies that a standard deviation of capital adequacy and a
            standard deviation of net interest margin are equally consequential, which no supervisor believes.
            A reader who disagrees can read the pillar scores directly — they are published individually
            precisely so the composite is never the only thing on offer.
          </P>

          <H2 id="scale">Why the 0–100 transformation</H2>
          <P>
            A composite in z units is centred on zero and runs negative, which reads badly and invites the
            mistake of treating a negative number as a failing grade rather than a below-average position. The
            presentation scale is a linear transformation with no information content of its own:
          </P>
          <Eq caption="A bank at the sample mean on every indicator scores exactly 50. One standard deviation above scores 60.">
            BFPI = 50 + 10 · Z_BFPI
          </Eq>
          <P>
            The scale is clamped to [0, 100], which matters only at five standard deviations from the mean — far
            outside anything a real bank panel produces. Because the transformation is linear, nothing about the
            ordering or the relative distances changes; only the labels do.
          </P>

          <H2 id="bands">Interpretation bands</H2>
          <P>
            These bands describe position within the selected sample and period. They are not grades, not
            ratings and not statements about solvency.
          </P>
          <div className="mt-5 overflow-hidden border border-white/[0.09]">
            {BFPI_BANDS.map((b) => (
              <div
                key={b.label}
                className="flex items-baseline justify-between gap-4 border-b border-white/[0.04] px-4 py-2.5 last:border-0"
              >
                <span className="metric text-sm" style={{ color: b.tone }}>
                  {b.min}–{b.max >= 100 ? '100' : (b.max - 0.1).toFixed(1)}
                </span>
                <span className="text-[0.8125rem] text-ink-300">{b.label}</span>
              </div>
            ))}
          </div>

          <H2 id="missing">Missing data</H2>
          <P>
            Nothing is imputed. A missing indicator is not replaced with a zero, a sample mean, a previous
            period's value or an interpolation. The treatment is stated once and applied uniformly:
          </P>
          <ul className="mt-4 space-y-3">
            {[
              'A pillar is the mean of the standardised indicators available for that bank. Where a pillar is computed from fewer than all of its indicators, the result is marked partial and says which indicators it used.',
              'A pillar with no available indicator is not computed. The composite is then formed over the remaining pillars with their weights renormalised to sum to one, and the result is marked partial with the renormalisation stated.',
              'Where fewer than three of the four pillars are computable, the composite is withheld entirely rather than published on a thin base. The pillars that could be computed are still shown, because they are real measurements even when the composite is not.',
              'A z-score requires at least one other bank in the sample to have reported the same indicator. Where none has, the indicator cannot be standardised and is treated as unavailable.',
            ].map((t) => (
              <li key={t} className="flex gap-3 text-[0.9375rem] leading-relaxed text-ink-300">
                <span aria-hidden className="mt-[0.65em] h-px w-3 shrink-0 bg-[#e8933a]" />
                {t}
              </li>
            ))}
          </ul>
          <P>
            In the shipped FY2025 sample this is not hypothetical. Credit-loss provisions were not obtainable
            for any of the seven banks, so Asset Quality is computed from the NPL ratio alone throughout — a
            uniform narrowing that does not tilt the comparison but does narrow what the pillar measures. Two
            banks fall below the three-pillar threshold and their composites are withheld.
          </P>

          <H2 id="sample">The sample, and what it cannot support</H2>
          <ul className="mt-5 space-y-3">
            {PANEL_CAVEATS.map((c) => (
              <li key={c} className="flex gap-3 text-[0.9375rem] leading-relaxed text-ink-300">
                <span aria-hidden className="mt-[0.65em] h-px w-3 shrink-0 bg-ink-600" />
                {c}
              </li>
            ))}
          </ul>

          <H2 id="limits">Limitations</H2>
          <ul className="mt-5 space-y-3">
            {[
              'The index is relative by construction. A score of 58 means "above the centre of this sample in this year", not "strong". Add or remove a bank and every score moves.',
              'Seven banks is a small sample. Standard deviations estimated from seven observations are noisy, and a single outlier moves the reference point for everyone.',
              'One financial year is a cross-section, not a trend. Nothing here identifies whether a position is improving or deteriorating.',
              'Indicators are disclosed on different consolidation bases across the sample, which introduces variation that is an artefact of reporting rather than of performance.',
              'Accounting differences between public and private sector banks — provisioning policy, recognition timing, restructuring treatment — are not adjusted for.',
              'Equal weights and the chosen direction coefficients are both choices. Different defensible choices produce different scores, and the index cannot adjudicate between them.',
              'No causal claim is supported. The index describes positions; it does not explain them and does not predict what follows.',
            ].map((t) => (
              <li key={t} className="flex gap-3 text-[0.9375rem] leading-relaxed text-ink-300">
                <span aria-hidden className="mt-[0.65em] h-px w-3 shrink-0 bg-[#d3675d]" />
                {t}
              </li>
            ))}
          </ul>

          <div className="mt-12">
            <Notice title="Data retrieval">{RETRIEVAL_NOTE}</Notice>
          </div>

          <div className="mt-8 flex flex-wrap gap-2 border-t border-white/[0.07] pt-6">
            <Link to="/models/bfpi" className="btn btn-primary">
              Open the model <ArrowRight size={12} />
            </Link>
            <Link to="/research/the-great-indian-promise" className="btn">
              The companion research <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </article>
    </>
  );
}
