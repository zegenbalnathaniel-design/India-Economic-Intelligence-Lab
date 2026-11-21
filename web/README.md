# IEIL — India Economics Intelligence Lab

**Don't just read economics. Experiment with it.**

An interactive laboratory for understanding India's economy through data, research and
experimentation. Two research models run live in the browser; the research paper that
frames them embeds its own central figure as a working instrument rather than a picture.

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # 92 unit tests over the two model engines
npm run build
```

Requires Node 20+. No API keys, no backend, no analytics.

---

## What is here

| Route | What it is |
| --- | --- |
| `/` | Continuous narrative: pulse → globe → featured research → both models → experiments → states → library → timeline |
| `/research/the-great-indian-promise` | The paper, with Figure 2 embedded live in the reading column |
| `/models/figure-2` | Household wealth accumulation — the full model |
| `/models/bfpi` | Bank Financial Performance Index — model, stress test and bank explorer |
| `/models/bfpi/methodology` | Every construction choice behind BFPI, stated and defended |
| `/data` | Indicator explorer, source registry, data audit log |
| `/experiments` | Single-variable experiments on wealth and banking |
| `/india` | State economics map and the economic timeline |
| `/glossary` | Terms, formulas, and what each measure cannot tell you |

`⌘K` (or `/`) opens the command palette, which reaches every indicator, bank, glossary
term and paper section in the lab.

---

## Architecture

```
src/
  models/          Pure mathematics. No React, no formatting, no I/O.
    figure2/       Portfolio return, annuity future value, scenario comparison
    bfpi/          z-scores, pillars, composite, 0–100 transform, missing-data policy
  data/            Every datum with its source, period, status and provenance
  components/      UI, one directory per surface
  lib/             Formatting (Indian digit grouping), motion, smooth scroll
  pages/           Route components
```

The separation between `models/` and everything else is load-bearing. Both engines are
pure functions covered by unit tests; the UI cannot disagree with them because it has no
arithmetic of its own.

### Figure 2

```
R_p = Σ wᵢRᵢ                      weighted portfolio return
FV  = C · [ (1+r)ⁿ − 1 ] / r      annuity future value
```

The engine accumulates period by period rather than evaluating the closed form, because
that generalises to an opening balance, start-of-period contributions and sub-annual
frequencies. A test asserts the two agree to floating-point tolerance in the case the
closed form covers.

Allocations that do not sum to 100% are never renormalised. The unallocated share is
carried as non-earning residual cash so that every rupee contributed is accounted for,
and the baseline comparison is withheld, because a partly-uninvested scenario is not
comparable with the baseline on equal terms.

### BFPI

```
zᵢ   = dᵢ (Xᵢ − μᵢ) / σᵢ           dᵢ = −1 for NPL and provisions
P    = (z_NIM + z_ROE) / 2        C = z_CET1
A    = (z_NPL + z_PROV) / 2       L = z_LCR
Z    = 0.25P + 0.25C + 0.25A + 0.25L
BFPI = 50 + 10Z
```

BFPI is an original composite index constructed for analytical purposes. It is not an
RBI measure, not a rating and not a prediction. It describes position within a selected
sample and period, and nothing else.

Missing data is never imputed. A pillar is the mean of the indicators available for that
bank; a pillar with none is not computed and the remaining weights are renormalised;
below three computable pillars the composite is withheld entirely. Every one of those
treatments is reported on the result it touches.

---

## Data discipline

Every factual number travels inside a record carrying a source, a reporting period, a
publication date, a retrieval date and a status:

| Status | Meaning |
| --- | --- |
| `verified` | Traced to a specific primary release |
| `reported` | Transcribed from an issuer or industry disclosure this build could not open |
| `calculated` | Derived arithmetically from other records; the derivation is shown |
| `assumption` | An explicit modelling choice, not an observation |
| `scenario` | Produced by the reader moving a control |
| `unavailable` | Known to exist, not obtainable here, and never substituted |

Rules the codebase enforces rather than merely documents:

- Reporting periods are preserved verbatim. FY2025-26 is never written as 2026.
- Successive official vintages are all carried; the latest is used.
- Missing values are `null` and render as "Data unavailable" — never zero, never carried
  forward, never interpolated.
- Where authoritative sources conflict, both are shown with the conflict explained. The
  state GSDP discrepancy and the August 2026 CPI print are both live examples.

**Retrieval note.** This build was assembled in a sandbox whose egress proxy blocks
`rbi.org.in`, `mospi.gov.in`, `pib.gov.in` and the banks' investor-relations hosts, so no
figure here was fetched by machine. Values were transcribed from those publishers'
releases and each record links to the document that is the authority. Verify against the
linked source before citing.

---

## Accessibility and performance

- `prefers-reduced-motion` removes the boot sequence, disables smooth scroll and collapses
  every animation to its end state. Motion here carries meaning, so it degrades to instant
  state changes rather than being removed.
- Keyboard navigation throughout; the command palette is a listbox with `aria-activedescendant`.
- Charts carry text alternatives describing the series and its range.
- Three.js and both model labs are lazy-loaded; nothing WebGL ships on first paint.
- Animated numbers and morphing curves are written straight to the DOM from a motion
  value, so an animating chart never re-renders the panel around it.

---

## Stack

React 19 · TypeScript · Vite · Tailwind CSS · Framer Motion · Lenis · D3 (scale, shape) ·
Three.js via React Three Fiber · Lucide.

## Disclaimers

BFPI is an original composite index, not an official measure or rating, and does not
establish that any bank is best, safest or strongest. Figure 2 results are conditional on
the assumptions entered; historical returns do not guarantee future performance. Nothing
here is financial advice.
