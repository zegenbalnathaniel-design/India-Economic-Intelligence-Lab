import { Navigate, useParams } from 'react-router-dom';
import { ResearchReader } from '../components/ResearchReader/ResearchReader';
import { GREAT_INDIAN_PROMISE } from '../data/research/greatIndianPromise';

const PAPERS = { [GREAT_INDIAN_PROMISE.slug]: GREAT_INDIAN_PROMISE };

export function ResearchPaper() {
  const { slug } = useParams();
  const paper = slug ? PAPERS[slug] : undefined;
  if (!paper) return <Navigate to="/research" replace />;
  return <ResearchReader paper={paper} />;
}
