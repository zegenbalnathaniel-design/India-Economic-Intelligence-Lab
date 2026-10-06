"""Static metadata registry for every indicator the package exposes.

This module holds no logic that touches the network. It is a plain data
table describing, for each indicator, where live data *would* come from
(World Bank indicator codes), what each resulting column means, and the
parameters used to generate the synthetic fallback series when a live
fetch isn't possible or isn't requested.

Keeping this as one declarative table makes it easy to answer "what does
india_econ actually cover?" by reading a single file, and is what
``get_metadata()`` and ``docs/DATA_SOURCES.md`` are both built from.
"""

from __future__ import annotations

from typing import Any, Dict, NamedTuple, Tuple

WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2/country/IND/indicator"


class SyntheticSpec(NamedTuple):
    """Parameters for a deterministic synthetic random-walk column.

    Attributes
    ----------
    base:
        Value of the series in the first synthetic year.
    drift:
        Average per-year additive change.
    vol:
        Standard deviation of year-to-year noise.
    mean_revert_to:
        If given, the walk is pulled gently back toward this level each
        step (used for rate-like series that shouldn't wander forever).
    round_to:
        Decimal places to round the generated values to.
    """

    base: float
    drift: float
    vol: float
    mean_revert_to: float | None = None
    round_to: int = 2


class WorldBankColumn(NamedTuple):
    """One World Bank indicator code mapped to an output column."""

    code: str
    column: str
    synthetic: SyntheticSpec


class IndicatorSpec(NamedTuple):
    """Everything india_econ knows about one public indicator."""

    name: str
    provider: str
    url: str
    definition: str
    unit: str
    frequency: str
    columns: Tuple[WorldBankColumn, ...]
    notes: str = ""


# Default synthetic/display window used when a caller passes start=None,
# end=None and no live data is available (or live fetching is disabled).
DEFAULT_SYNTHETIC_START = 2000
DEFAULT_SYNTHETIC_END = 2023

REGISTRY: Dict[str, IndicatorSpec] = {
    "gdp": IndicatorSpec(
        name="gdp",
        provider="World Bank Open Data (World Development Indicators)",
        url=f"{WORLD_BANK_BASE_URL}/NY.GDP.MKTP.CD",
        definition=(
            "GDP at current market prices (US$), plus a derived year-over-year "
            "growth rate computed from the level series."
        ),
        unit="current US$ (level); % year-over-year (growth)",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="NY.GDP.MKTP.CD",
                column="gdp_current_usd",
                synthetic=SyntheticSpec(base=1.2e12, drift=9.5e10, vol=6e10, round_to=0),
            ),
        ),
        notes=(
            "gdp_growth_pct is derived locally (percent change of "
            "gdp_current_usd) rather than fetched as a second series, to "
            "keep this to one live request per call."
        ),
    ),
    "inflation": IndicatorSpec(
        name="inflation",
        provider="World Bank Open Data (World Development Indicators)",
        url=f"{WORLD_BANK_BASE_URL}/FP.CPI.TOTL.ZG",
        definition="Consumer price inflation, annual % change in the CPI basket.",
        unit="% per year",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="FP.CPI.TOTL.ZG",
                column="cpi_inflation_pct",
                synthetic=SyntheticSpec(base=6.5, drift=0.0, vol=1.8, mean_revert_to=5.5),
            ),
        ),
    ),
    "unemployment": IndicatorSpec(
        name="unemployment",
        provider="World Bank Open Data (ILO modeled estimate)",
        url=f"{WORLD_BANK_BASE_URL}/SL.UEM.TOTL.ZS",
        definition=(
            "Share of the labor force that is unemployed, ILO modeled "
            "estimate (national surveys differ and may disagree with this)."
        ),
        unit="% of total labor force",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="SL.UEM.TOTL.ZS",
                column="unemployment_rate_pct",
                synthetic=SyntheticSpec(base=7.0, drift=0.0, vol=0.35, mean_revert_to=7.0),
            ),
        ),
    ),
    "trade": IndicatorSpec(
        name="trade",
        provider="World Bank Open Data (World Development Indicators)",
        url=f"{WORLD_BANK_BASE_URL}/NE.EXP.GNFS.CD,{WORLD_BANK_BASE_URL}/NE.IMP.GNFS.CD",
        definition="Exports and imports of goods and services (balance of payments basis).",
        unit="current US$",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="NE.EXP.GNFS.CD",
                column="exports_usd",
                synthetic=SyntheticSpec(base=1.0e11, drift=1.1e10, vol=8e9, round_to=0),
            ),
            WorldBankColumn(
                code="NE.IMP.GNFS.CD",
                column="imports_usd",
                synthetic=SyntheticSpec(base=1.15e11, drift=1.2e10, vol=9e9, round_to=0),
            ),
        ),
    ),
    "exchange_rate": IndicatorSpec(
        name="exchange_rate",
        provider="World Bank Open Data (IMF International Financial Statistics)",
        url=f"{WORLD_BANK_BASE_URL}/PA.NUS.FCRF",
        definition="Official exchange rate, period average, INR per USD.",
        unit="INR per USD",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="PA.NUS.FCRF",
                column="inr_per_usd",
                synthetic=SyntheticSpec(base=45.0, drift=1.65, vol=1.5, round_to=2),
            ),
        ),
    ),
    "interest_rates": IndicatorSpec(
        name="interest_rates",
        provider="World Bank Open Data (World Development Indicators)",
        url=f"{WORLD_BANK_BASE_URL}/FR.INR.LEND",
        definition=(
            "Commercial bank lending interest rate. The World Bank's open, "
            "unauthenticated API does not publish the RBI's policy repo "
            "rate directly, so this lending rate is used as the closest "
            "available policy-adjacent proxy -- see docs/DATA_SOURCES.md."
        ),
        unit="% per year",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="FR.INR.LEND",
                column="lending_rate_pct",
                synthetic=SyntheticSpec(base=11.0, drift=0.0, vol=0.6, mean_revert_to=10.0),
            ),
        ),
        notes="Proxy for a policy rate; not the RBI repo rate itself.",
    ),
    "government_finance": IndicatorSpec(
        name="government_finance",
        provider="World Bank Open Data (World Development Indicators / IMF GFS)",
        url=f"{WORLD_BANK_BASE_URL}/GC.BAL.CASH.GD.ZS,{WORLD_BANK_BASE_URL}/GC.DOD.TOTL.GD.ZS",
        definition=(
            "Central government cash surplus/deficit (negative = deficit) "
            "and central government debt, both as a % of GDP."
        ),
        unit="% of GDP",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="GC.BAL.CASH.GD.ZS",
                column="fiscal_balance_pct_gdp",
                synthetic=SyntheticSpec(base=-5.5, drift=0.0, vol=0.9, mean_revert_to=-6.0),
            ),
            WorldBankColumn(
                code="GC.DOD.TOTL.GD.ZS",
                column="government_debt_pct_gdp",
                synthetic=SyntheticSpec(base=72.0, drift=0.3, vol=1.5, mean_revert_to=78.0),
            ),
        ),
    ),
    "household_finance": IndicatorSpec(
        name="household_finance",
        provider="World Bank Open Data (World Development Indicators)",
        url=f"{WORLD_BANK_BASE_URL}/NY.GNS.ICTR.ZS,{WORLD_BANK_BASE_URL}/FS.AST.PRVT.GD.ZS",
        definition=(
            "Gross domestic savings (% of GDP, a national-not-strictly-"
            "household proxy) and domestic credit to the private sector "
            "by banks (% of GDP, a credit-availability proxy)."
        ),
        unit="% of GDP",
        frequency="annual",
        columns=(
            WorldBankColumn(
                code="NY.GNS.ICTR.ZS",
                column="gross_savings_pct_gdp",
                synthetic=SyntheticSpec(base=30.0, drift=0.0, vol=1.2, mean_revert_to=30.0),
            ),
            WorldBankColumn(
                code="FS.AST.PRVT.GD.ZS",
                column="domestic_credit_private_pct_gdp",
                synthetic=SyntheticSpec(base=46.0, drift=0.6, vol=1.5, mean_revert_to=52.0),
            ),
        ),
        notes=(
            "The World Bank's open API has no household-level savings or "
            "credit series for India, so these are economy-wide proxies, "
            "not household survey data."
        ),
    ),
}


def get_spec(indicator_name: str) -> IndicatorSpec:
    """Look up an :class:`IndicatorSpec` by name, raising on an unknown name."""
    from .exceptions import UnknownIndicatorError  # local import avoids a cycle

    try:
        return REGISTRY[indicator_name]
    except KeyError as exc:
        known = ", ".join(sorted(REGISTRY))
        raise UnknownIndicatorError(
            f"Unknown indicator '{indicator_name}'. Known indicators: {known}."
        ) from exc


def metadata_dict(indicator_name: str) -> Dict[str, Any]:
    """Return the static (pre-fetch) metadata dict for one indicator."""
    spec = get_spec(indicator_name)
    return {
        "name": spec.name,
        "provider": spec.provider,
        "url": spec.url,
        "definition": spec.definition,
        "unit": spec.unit,
        "frequency": spec.frequency,
        "columns": [c.column for c in spec.columns],
        "notes": spec.notes,
    }
