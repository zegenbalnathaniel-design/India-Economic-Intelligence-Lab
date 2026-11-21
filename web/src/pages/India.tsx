import { useSearchParams } from 'react-router-dom';
import { EconomicTimeline } from '../components/EconomicTimeline/EconomicTimeline';
import { IndiaMap } from '../components/IndiaMap/IndiaMap';
import { PageHeader } from './PageHeader';

export function India() {
  const [params] = useSearchParams();
  const event = params.get('event') ?? undefined;

  return (
    <>
      <PageHeader
        label="India"
        title="The economic map, and how it got here"
        lede="State economies that differ by a factor of three and a half in income per person, and the six discontinuities that shaped the aggregate. Where the evidence is contested, this page says so instead of choosing."
      />

      <div className="mx-auto max-w-[1400px] space-y-20 px-5 py-12 md:px-10 md:py-16">
        <section id="map" className="scroll-mt-24">
          <span className="label-accent">Economic map</span>
          <h2 className="display mt-2 text-[1.75rem] md:text-[2.25rem]">State economics</h2>
          <div className="mt-7">
            <IndiaMap />
          </div>
        </section>

        <section id="timeline" className="scroll-mt-24">
          <span className="label-accent">Timeline</span>
          <h2 className="display mt-2 text-[1.75rem] md:text-[2.25rem]">1991 to now</h2>
          <p className="mt-4 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-400">
            Each entry separates what happened, which is a matter of record, from what the data can support,
            which usually is not. Demonetisation reports no growth impact here, because the credible estimates
            disagree and picking one would be a choice dressed as a finding.
          </p>
          <div className="mt-7">
            <EconomicTimeline initialId={event} />
          </div>
        </section>
      </div>
    </>
  );
}
