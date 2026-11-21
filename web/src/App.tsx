import { Suspense, lazy, useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import { CommandPalette } from './components/CommandPalette/CommandPalette';
import { useCommandPalette } from './components/CommandPalette/useCommandPalette';
import { Footer } from './components/Footer/Footer';
import { Navigation } from './components/Navigation/Navigation';
import { useLenis } from './lib/useLenis';
import { About } from './pages/About';
import { BFPIMethodology } from './pages/BFPIMethodology';
import { BFPIPage } from './pages/BFPIPage';
import { Data } from './pages/Data';
import { Experiments } from './pages/Experiments';
import { Figure2Page } from './pages/Figure2Page';
import { GlossaryPage } from './pages/Glossary';
import { Home } from './pages/Home';
import { India } from './pages/India';
import { Models } from './pages/Models';
import { NotFound } from './pages/NotFound';
import { Research } from './pages/Research';

// Each lab is its own chunk: its data bundle loads only when the lab is opened.
const LabsIndex = lazy(() => import('./pages/labs/LabsIndex'));
const StatesLab = lazy(() => import('./pages/labs/StatesLab'));
const HousingLab = lazy(() => import('./pages/labs/HousingLab'));
const InequalityLab = lazy(() => import('./pages/labs/InequalityLab'));
const StructuralLab = lazy(() => import('./pages/labs/StructuralLab'));
const RelationshipsLab = lazy(() => import('./pages/labs/RelationshipsLab'));
const TransmissionLab = lazy(() => import('./pages/labs/TransmissionLab'));
const MacroLab = lazy(() => import('./pages/labs/MacroLab'));

function LabFallback() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <span className="label animate-pulse">Loading the lab…</span>
    </div>
  );
}
import { ResearchPaper } from './pages/ResearchPaper';

/**
 * Route changes reset scroll, except when the URL carries a hash — a link
 * into a paper section or a page anchor should land where it points.
 */
function ScrollBehaviour() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) {
        requestAnimationFrame(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }));
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [pathname, hash]);

  return null;
}

export default function App() {
  const { open, setOpen } = useCommandPalette();
  useLenis();

  return (
    <>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:border focus:border-[#f3c542] focus:bg-ink-950 focus:px-4 focus:py-2 focus:font-mono focus:text-2xs focus:uppercase focus:tracking-[0.14em] focus:text-ink-50"
      >
        Skip to content
      </a>

      <Navigation onOpenPalette={() => setOpen(true)} />
      <CommandPalette open={open} onClose={() => setOpen(false)} />
      <ScrollBehaviour />

      <main id="main">
        <Suspense fallback={<LabFallback />}>
        <Routes>
          <Route path="/labs" element={<LabsIndex />} />
          <Route path="/labs/states" element={<StatesLab />} />
          <Route path="/labs/housing" element={<HousingLab />} />
          <Route path="/labs/inequality" element={<InequalityLab />} />
          <Route path="/labs/structural" element={<StructuralLab />} />
          <Route path="/labs/relationships" element={<RelationshipsLab />} />
          <Route path="/labs/transmission" element={<TransmissionLab />} />
          <Route path="/labs/macro" element={<MacroLab />} />
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<Research />} />
          <Route path="/research/:slug" element={<ResearchPaper />} />
          <Route path="/models" element={<Models />} />
          <Route path="/models/figure-2" element={<Figure2Page />} />
          <Route path="/models/bfpi" element={<BFPIPage />} />
          <Route path="/models/bfpi/methodology" element={<BFPIMethodology />} />
          <Route path="/data" element={<Data />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/india" element={<India />} />
          <Route path="/glossary" element={<GlossaryPage />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
      </main>

      <Footer />
    </>
  );
}
