"""The extensible module architecture for Economics Interactive Lab.

Every teaching module in this project is one ``EconModule`` instance. A
module bundles:

- ``concept``      -- short markdown explanation of the idea, in plain English.
- ``equation``      -- the governing equation(s), as a markdown/LaTeX string.
                        This is the general THEORY: true by construction,
                        regardless of what numbers a user plugs in.
- ``compute``       -- a pure-Python function implementing that equation.
                        It takes only plain Python/NumPy types and returns a
                        plain ``dict`` of results. It has no Streamlit (or
                        any UI) dependency, so it is directly unit-testable
                        and directly reusable from a notebook or script.
- ``render_controls``     -- a Streamlit function that draws the input
                              widgets for *this* module's parameters and
                              returns a kwargs ``dict`` suitable for
                              ``compute(**kwargs)``. These are the specific,
                              user-chosen, illustrative numbers.
- ``render_visualization`` -- a Streamlit function that takes the inputs
                               dict and the ``compute(...)`` output dict and
                               draws the chart(s)/table(s).
- ``experiment``    -- a concrete "try this and see what happens" prompt.
- ``explanation``   -- a longer walk-through of what the results mean.
- ``limitations``   -- an explicit statement distinguishing the always-true
                        equation from the illustrative, user-chosen inputs,
                        plus any other modeling caveats.

New modules are added by creating a new file under ``econ_lab.modules``
that builds an ``EconModule`` and calls ``register_module(...)`` on it --
no existing file needs to change. ``econ_lab.modules.__init__`` imports
every module file (for its registration side effect); the Streamlit app
and the test suite both discover modules purely through the registry
below, never by importing a specific module file by name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

ComputeFn = Callable[..., Dict[str, Any]]
ControlsFn = Callable[[], Dict[str, Any]]
VizFn = Callable[[Dict[str, Any], Dict[str, Any]], None]


@dataclass(frozen=True)
class EconModule:
    """A single, self-contained interactive economics teaching module."""

    key: str
    domain: str  # "Microeconomics" | "Macroeconomics" | "Finance"
    title: str
    concept: str
    equation: str
    compute: ComputeFn
    render_controls: ControlsFn
    render_visualization: VizFn
    experiment: str
    explanation: str
    limitations: str

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Convenience wrapper so callers (tests, notebooks) can skip the
        Streamlit controls entirely and just call the math."""
        return self.compute(**kwargs)


_REGISTRY: Dict[str, EconModule] = {}


def register_module(module: EconModule) -> EconModule:
    """Register an ``EconModule`` in the global registry and return it
    unchanged, so module files can write ``MODULE = register_module(EconModule(...))``.

    Raises ``ValueError`` if ``module.key`` is already registered, so two
    modules can never silently collide.
    """
    if module.key in _REGISTRY:
        raise ValueError(f"A module with key {module.key!r} is already registered.")
    _REGISTRY[module.key] = module
    return module


def get_module(key: str) -> EconModule:
    """Look up a single module by its registry key."""
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"No module registered under key {key!r}.") from exc


def all_modules() -> Dict[str, EconModule]:
    """Return a shallow copy of the full registry, keyed by module key."""
    return dict(_REGISTRY)


def modules_by_domain(domain: str) -> Dict[str, EconModule]:
    """Return only the modules belonging to the given domain
    (e.g. "Microeconomics", "Macroeconomics", "Finance")."""
    return {k: m for k, m in _REGISTRY.items() if m.domain == domain}


def domains() -> List[str]:
    """Return the distinct domains currently registered, in first-seen order."""
    seen: List[str] = []
    for module in _REGISTRY.values():
        if module.domain not in seen:
            seen.append(module.domain)
    return seen
