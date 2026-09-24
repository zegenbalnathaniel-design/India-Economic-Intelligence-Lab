import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Figure2Lab } from '../components/Figure2Lab/Figure2Lab';
import { FIGURE2_CLASSIFICATION } from '../data/wealth/assumptions';
import { StatusBadge } from '../components/ui';
import { PageHeader } from './PageHeader';

export function Figure2Page() {
  return (
    <>
      <PageHeader
        label="Model 01 · Figure 02"
        title="Household Wealth Accumulation"
        lede="What happens when ₹1 lakh is saved every year for 30 years? The defaults are the household portfolio the RBI measured and a set of return assumptions stated in full. Change any of them and everything recomputes — the curve, the headline numbers and the working."
        actions={
          <>
            <Link to="/research/the-great-indian-promise" className="btn btn-primary">
              Read the methodology <ArrowRight size={12} />
            </Link>
            <Link to="/experiments#wealth" className="btn">
              Run the experiment <ArrowRight size={12} />
            </Link>
          </>
        }
      />

      <div className="mx-auto max-w-[1400px] px-5 py-10 md:px-10 md:py-14">
        <Figure2Lab />

        <section className="mt-16">
          <h2 className="display text-[1.75rem]">Every variable, classified</h2>
          <p className="mt-3 max-w-[64ch] text-[0.9375rem] leading-relaxed text-ink-400">
            The distinction between what was measured and what was assumed is the most important thing on this
            page. An allocation is an observation about how Indian households actually hold wealth. A
            thirty-year return is not an observation about anything — it is a choice, and the result is
            conditional on it.
          </p>

          <div className="mt-7 overflow-x-auto border border-white/[0.09]">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.09] bg-ink-900/60">
                  {['Variable', 'Value', 'Class', 'Status', 'Basis'].map((h) => (
                    <th key={h} className="label px-4 py-3 font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FIGURE2_CLASSIFICATION.map((c) => (
                  <tr key={c.variable} className="border-b border-white/[0.04] last:border-0">
                    <td className="px-4 py-3 text-[0.8125rem] text-ink-100">{c.variable}</td>
                    <td className="metric px-4 py-3 text-sm" data-numeric>
                      {c.value}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="border px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-[0.14em]"
                        style={{
                          color:
                            c.classification === 'OBSERVED'
                              ? '#4fae86'
                              : c.classification === 'DERIVED'
                                ? '#4aa5a8'
                                : c.classification === 'ASSUMPTION'
                                  ? '#e8933a'
                                  : '#8b7fd4',
                          borderColor: 'rgba(255,255,255,0.14)',
                        }}
                      >
                        {c.classification}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} size="xs" />
                    </td>
                    <td className="max-w-[420px] px-4 py-3 text-2xs leading-relaxed text-ink-400">
                      {c.basis}
                      {c.sourceUrl && (
                        <a
                          href={c.sourceUrl}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="mt-1 block text-ink-500 underline decoration-ink-700 underline-offset-2 hover:text-[#e8933a]"
                        >
                          {c.source}
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}
