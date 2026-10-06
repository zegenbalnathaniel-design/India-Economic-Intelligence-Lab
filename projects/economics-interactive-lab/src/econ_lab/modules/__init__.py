"""Importing this package registers every built-in module in
``econ_lab.registry``. To add a new module, create a new file in this
package that builds an ``EconModule`` and calls ``register_module(...)``
on it, then add one import line below -- no existing module file needs
to change.
"""

from econ_lab.modules import (
    finance_compound_interest,
    finance_diversification,
    macro_ad_as,
    macro_growth,
    macro_multiplier,
    micro_elasticity,
    micro_price_controls,
    micro_supply_demand,
    micro_tax_incidence,
)

__all__ = [
    "micro_supply_demand",
    "micro_elasticity",
    "micro_tax_incidence",
    "micro_price_controls",
    "macro_ad_as",
    "macro_multiplier",
    "macro_growth",
    "finance_compound_interest",
    "finance_diversification",
]
