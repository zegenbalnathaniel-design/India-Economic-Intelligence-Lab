# Portfolio Build Order

A recommended order for building (or reading) these nine projects, based on intellectual value, technical difficulty, relationships to the others, practical usefulness, and potential as source material for written pieces (e.g. a "Financial Frontier"-style article series).

## Tier 1 — build/read first

1. **`portfolio-optimization-lab`** — the highest intellectual-to-effort ratio in the portfolio: real Lagrangian derivations, a real (if simplified) global multi-exchange dataset problem, and a genuinely novel visual (3D correlation network via classical MDS). Self-contained; doesn't depend on anything else. Strongest candidate for a written piece on "what the efficient frontier actually is" or "why mean-variance optimization is harder than it looks" (estimation error, Michaud resampling).
2. **`india-wealth-inequality-toolkit`** — directly tied to the author's own research paper; the Gini/Lorenz/Palma toolkit is broadly reusable (useful beyond this portfolio) and the composition-effect simulator is a clean, teachable mechanism. Good source material for a piece on "why income growth isn't the whole wealth story."

## Tier 2 — build next

3. **`india-economic-policy-simulator`** — the most technically demanding model in the portfolio (seven coupled equations, Taylor-rule feedback, debt dynamics) and the best "systems thinking" demonstration. Pairs naturally with the Data Observatory once real series are wired in. Strong source material for an explainer on fiscal multipliers and crowding out.
4. **`sip-monte-carlo`** — high practical usefulness (the question "how much will my SIP be worth" is one almost every reader has asked) and a clean vehicle for teaching sequence-of-returns risk, a genuinely underappreciated concept. Natural companion piece to the Portfolio Lab.
5. **`india-housing-affordability`** — high public interest (housing affordability is a live policy debate in India), moderate technical difficulty (EMI/amortization math is exact and well-defined even though the city-level data is synthetic here).

## Tier 3 — build after the above have real data wiring

6. **`india-economic-data-observatory`** — most valuable *after* the modeling projects exist, since it's the thing that would feed them real series instead of synthetic fallbacks. Its main technical content (standardized metadata, validation, live/synthetic fallback architecture) is a real contribution on its own, independent of which specific indicators it carries.
7. **`india-econ`** — the packaging exercise. Most useful once the Data Observatory's loader patterns are proven out; a lot of its value is in doing packaging *correctly* (src-layout, CI, type hints, caching) rather than in novel economics.

## Tier 4 — broadest scope, build last

8. **`personal-inflation-index`** — conceptually simple (one formula, the Laspeyres index) but requires the most care in avoiding fabrication (CPI category weights are easy to get specific-sounding and wrong without a verified source) — safest to build once the portfolio's data-sourcing conventions are well established elsewhere.
9. **`economics-interactive-lab`** — the broadest scope (micro + macro + finance, many modules) and the one most tempting to pad superficially. Best built last, once the portfolio's "concept → equation → controls → visualization → experiment → limitations" pattern has already been proven out in the more focused projects above — at that point, this project is mostly an exercise in applying a known-good pattern repeatedly and extensibly, which is a much better position to build 10+ modules from than starting cold.

## Why this order, in one line each

- **Intellectual value**: Tier 1 projects have the richest underlying mathematics (Lagrangian optimization, inequality measurement theory) relative to their scope.
- **Technical difficulty**: the policy simulator and portfolio lab are the hardest; the inflation index and housing affordability are the most mechanically simple (closed-form formulas).
- **Relationships to the others**: the Data Observatory is positioned in Tier 3, not first, because it's more valuable once there are modeling projects downstream that actually want its output — building a data pipeline with no consumer invites scope creep.
- **Practical usefulness**: SIP Monte Carlo and Housing Affordability answer questions real people actually ask themselves; they're prioritized accordingly.
- **Article-series potential**: Tier 1 and 2 projects each map cleanly onto a single strong written piece (mean-variance optimization; composition effect and wealth inequality; fiscal multipliers and crowding out; sequence-of-returns risk) — the kind of content that reads well as a standalone explainer, not just a code demo.
