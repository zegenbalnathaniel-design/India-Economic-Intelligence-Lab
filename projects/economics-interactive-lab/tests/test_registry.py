import pytest

import econ_lab.modules  # noqa: F401  (import for registration side effect)
from econ_lab.registry import EconModule, all_modules, domains, get_module, modules_by_domain, register_module


EXPECTED_KEYS = {
    "micro_supply_demand",
    "micro_elasticity",
    "micro_tax_incidence",
    "micro_price_controls",
    "macro_ad_as",
    "macro_multiplier",
    "macro_growth",
    "finance_compound_interest",
    "finance_diversification",
}


def test_all_expected_modules_are_registered():
    registered = all_modules()
    assert EXPECTED_KEYS.issubset(registered.keys())


def test_every_module_has_required_fields_populated():
    for key, module in all_modules().items():
        assert isinstance(module, EconModule)
        assert module.key == key
        assert module.domain in {"Microeconomics", "Macroeconomics", "Finance"}
        assert module.title.strip()
        assert module.concept.strip()
        assert module.equation.strip()
        assert module.experiment.strip()
        assert module.explanation.strip()
        assert module.limitations.strip()
        assert callable(module.compute)
        assert callable(module.render_controls)
        assert callable(module.render_visualization)


def test_domain_counts_meet_the_minimum_bar():
    assert len(modules_by_domain("Microeconomics")) >= 4
    assert len(modules_by_domain("Macroeconomics")) >= 3
    assert len(modules_by_domain("Finance")) >= 2


def test_get_module_returns_the_right_module():
    module = get_module("micro_supply_demand")
    assert module.key == "micro_supply_demand"


def test_get_module_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        get_module("does_not_exist")


def test_registering_a_duplicate_key_raises():
    original = get_module("micro_supply_demand")
    with pytest.raises(ValueError):
        register_module(original)


def test_domains_lists_every_distinct_domain_present():
    found = set(domains())
    assert {"Microeconomics", "Macroeconomics", "Finance"}.issubset(found)


def test_run_convenience_method_delegates_to_compute():
    module = get_module("macro_multiplier")
    result = module.run(mpc=0.5, delta_g=10.0, rounds=3)
    assert result["multiplier"] == pytest.approx(2.0)
