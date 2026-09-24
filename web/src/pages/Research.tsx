import { ResearchLibrary } from '../components/ResearchLibrary/ResearchLibrary';
import { PageHeader } from './PageHeader';

export function Research() {
  return (
    <>
      <PageHeader
        label="Research"
        title="Papers, methodology notes and the programme behind them"
        lede="Research and models are the same object here. Every paper's figures are live, every figure links back to the methodology that produced it, and every claim that rests on an external number carries a citation to the primary source."
      />
      <div className="mx-auto max-w-[1400px] px-5 pb-24 md:px-10">
        <ResearchLibrary />
      </div>
    </>
  );
}
