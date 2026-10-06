"""Economics Interactive Lab.

A small, extensible library of self-contained economics teaching modules.
Each module pairs a pure-Python ``compute`` function (the real math) with
Streamlit rendering hooks (the UI), a plain-English explanation of the
theory, and an explicit statement of what the module's numbers do and do
not claim to show.

See ``econ_lab.registry`` for the ``EconModule`` abstraction and the
module registry, and ``econ_lab.modules`` for the concrete modules.
"""

from econ_lab.registry import EconModule, all_modules, get_module, modules_by_domain, register_module

__all__ = [
    "EconModule",
    "register_module",
    "get_module",
    "all_modules",
    "modules_by_domain",
]

__version__ = "0.1.0"
