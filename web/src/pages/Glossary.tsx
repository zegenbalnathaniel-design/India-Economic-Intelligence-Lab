import { useSearchParams } from 'react-router-dom';
import { Glossary as GlossaryList } from '../components/Glossary/Glossary';
import { PageHeader } from './PageHeader';

export function GlossaryPage() {
  const [params] = useSearchParams();
  const term = params.get('term') ?? undefined;

  return (
    <>
      <PageHeader
        label="Glossary"
        title="The terms, and what they will not tell you"
        lede="Every entry carries the definition, the formula where one exists, and the caution — the thing the measure is routinely asked to do that it cannot. The cautions are the useful part."
      />
      <div className="mx-auto max-w-[1400px] px-5 pb-24 md:px-10">
        <GlossaryList initialTerm={term} />
      </div>
    </>
  );
}
