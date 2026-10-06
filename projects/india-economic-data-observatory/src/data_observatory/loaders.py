"""Category loaders: the public API of this package.

Every `load_<indicator>(start, end, allow_live=True)` function below follows
the same pipeline:

    1. If `allow_live`, attempt a real fetch against the indicator's
       official endpoint (`sources.py`).
    2. If that succeeds and returns usable data, use it; otherwise fall
       back to a deterministic synthetic series (`synthetic.py`).
    3. Validate and clean the series (`validation.py`) — dedupe periods,
       drop/flag impossible values, forward-fill gaps with an explicit
       `imputed` flag.
    4. Cache the cleaned result on disk, keyed by indicator + date range +
       live/synthetic status (`cache.py`).
    5. Return `(series_or_frame, Metadata)`, with `Metadata.status` set
       accurately to `OFFICIAL` or `SYNTHETIC` — never implied, always
       explicit, and never overridden by what the caller hoped for.

`INDICATORS`, the registry at the bottom of this module, is what the
Streamlit app and tests iterate over to discover every available series
without hard-coding a parallel list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import pandas as pd

from . import cache, sources, synthetic, validation
from .metadata import DataStatus, Metadata, with_date_coverage, with_status


@dataclass(frozen=True)
class IndicatorSpec:
    """Everything needed to load and describe one indicator series."""

    key: str                      # stable machine key, e.g. "gdp"
    name: str                     # human label, e.g. "GDP (current US$)"
    category: str                 # "Growth", "Prices", "Labour", "Government", "External sector", "Financial system"
    provider: str
    source_name: str
    url: str
    definition: str
    unit: str
    frequency: str
    transformations: Tuple[str, ...]
    limitations: str
    value_bounds: Optional[Tuple[float, float]]
    # live fetch
    wb_code: Optional[str]                         # World Bank indicator code, if applicable
    live_probe: Optional[Callable[[], Optional[bytes]]] = None  # best-effort probe for non-WB sources
    postprocess: Optional[Callable[[pd.Series], pd.Series]] = None  # e.g. pct_change for a "growth" derived series
    # synthetic fallback parameters
    synthetic_kind: str = "level"                  # "level" or "bounded"
    synthetic_base: float = 100.0
    synthetic_drift: float = 0.03
    synthetic_vol: float = 0.08
    synthetic_lower: float = 0.0
    synthetic_upper: float = float("inf")
    synthetic_mean_reversion: float = 0.3


def _build_metadata(spec: IndicatorSpec, status: DataStatus, start: str, end: str) -> Metadata:
    meta = Metadata(
        indicator=spec.name,
        source=spec.source_name,
        provider=spec.provider,
        url=spec.url,
        definition=spec.definition,
        unit=spec.unit,
        frequency=spec.frequency,
        date_coverage="",
        transformations=spec.transformations,
        limitations=spec.limitations,
        status=status,
    )
    meta = with_date_coverage(meta, start, end)
    return meta


def _try_live(spec: IndicatorSpec, start: str, end: str) -> Optional[pd.Series]:
    series: Optional[pd.Series] = None
    if spec.wb_code:
        series = sources.fetch_world_bank_indicator(spec.wb_code, start, end)
    elif spec.live_probe is not None:
        # Non-World-Bank sources (RBI DBIE, MoSPI) have no stable JSON API;
        # the probe is a genuine HTTP attempt but never yields a parsed
        # series today — see sources.py and docs/DATA_SOURCES.md.
        spec.live_probe()
        series = None
    if series is not None and spec.postprocess is not None:
        series = spec.postprocess(series)
    if series is not None:
        series = series.dropna()
        if series.empty:
            series = None
    return series


def _make_synthetic(spec: IndicatorSpec, start: str, end: str) -> pd.Series:
    if spec.synthetic_kind == "bounded":
        return synthetic.synthetic_bounded_series(
            key=spec.key,
            start=start,
            end=end,
            mean_value=spec.synthetic_base,
            mean_reversion_speed=spec.synthetic_mean_reversion,
            vol=spec.synthetic_vol,
            lower_bound=spec.synthetic_lower,
            upper_bound=spec.synthetic_upper,
        )
    return synthetic.synthetic_level_series(
        key=spec.key,
        start=start,
        end=end,
        base_value=spec.synthetic_base,
        annual_drift=spec.synthetic_drift,
        annual_vol=spec.synthetic_vol,
    )


def load_indicator(spec: IndicatorSpec, start: str, end: str, allow_live: bool = True) -> Tuple[pd.DataFrame, Metadata]:
    """Generic pipeline shared by every `load_<indicator>` wrapper below.

    Returns `(frame, metadata)` where `frame` has columns `value` and
    `imputed` (see `validation.py`).
    """
    status = DataStatus.SYNTHETIC
    series: Optional[pd.Series] = None

    if allow_live:
        series = _try_live(spec, start, end)
        if series is not None:
            status = DataStatus.OFFICIAL

    cached = cache.read_from_cache(spec.key, start, end, status.value)
    if cached is not None and series is None and status is DataStatus.SYNTHETIC:
        # Reuse a previously-generated (deterministic, so identical anyway)
        # synthetic series from cache rather than regenerating.
        frame = cached
        meta = _build_metadata(spec, status, start, end)
        if status is DataStatus.SYNTHETIC:
            meta = with_status(
                meta, status,
                extra_limitation="Live fetch unavailable or disabled; showing deterministic synthetic fallback.",
            )
        return frame, meta

    if series is None:
        series = _make_synthetic(spec, start, end)

    frame, report = validation.validate_and_clean_series(series, spec.name, spec.value_bounds)

    meta = _build_metadata(spec, status, start, end)
    if status is DataStatus.SYNTHETIC:
        meta = with_status(
            meta, status,
            extra_limitation="Live fetch unavailable, returned no data, or disabled (allow_live=False); "
                              "showing a deterministic synthetic fallback series instead of real data.",
        )
    if not report.is_clean:
        meta = with_status(meta, meta.status, extra_limitation=f"Validation notes: {report.summary()}.")

    cache.write_to_cache(spec.key, start, end, status.value, frame)
    return frame, meta


# ---------------------------------------------------------------------------
# Indicator registry
# ---------------------------------------------------------------------------

def _credit_growth_postprocess(series: pd.Series) -> pd.Series:
    """Domestic credit to private sector by banks, % of GDP -> YoY
    percentage-point change, used as a proxy for 'bank credit growth'
    (World Bank does not publish a direct YoY bank-credit-growth series for
    India under a plain indicator code)."""
    return series.diff().dropna()


INDICATORS: Dict[str, IndicatorSpec] = {
    "gdp": IndicatorSpec(
        key="gdp", name="GDP (current US$)", category="Growth",
        provider="World Bank", source_name="World Development Indicators — NY.GDP.MKTP.CD",
        url="https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD",
        definition="Gross Domestic Product at purchaser's prices, converted to current US dollars.",
        unit="current US$", frequency="annual",
        transformations=("none beyond World Bank's own current-US$ conversion",),
        limitations="Current-US$ GDP mixes real growth with exchange-rate and price-level effects; "
                     "not adjusted for inflation or PPP.",
        value_bounds=(0.0, float("inf")),
        wb_code="NY.GDP.MKTP.CD",
        synthetic_kind="level", synthetic_base=1.0e12, synthetic_drift=0.07, synthetic_vol=0.05,
    ),
    "gdp_per_capita": IndicatorSpec(
        key="gdp_per_capita", name="GDP per capita (current US$)", category="Growth",
        provider="World Bank", source_name="World Development Indicators — NY.GDP.PCAP.CD",
        url="https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.PCAP.CD",
        definition="GDP divided by midyear population, in current US dollars.",
        unit="current US$ per person", frequency="annual",
        transformations=("none beyond World Bank's own current-US$ conversion",),
        limitations="Current-US$ terms; does not adjust for cost-of-living (PPP) differences.",
        value_bounds=(0.0, float("inf")),
        wb_code="NY.GDP.PCAP.CD",
        synthetic_kind="level", synthetic_base=1600.0, synthetic_drift=0.055, synthetic_vol=0.04,
    ),
    "cpi": IndicatorSpec(
        key="cpi", name="CPI inflation (annual %)", category="Prices",
        provider="World Bank", source_name="World Development Indicators — FP.CPI.TOTL.ZG",
        url="https://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL.ZG",
        definition="Annual percentage change in the cost to the average consumer of acquiring a basket "
                     "of goods and services (consumer price index).",
        unit="%", frequency="annual",
        transformations=("none",),
        limitations="World Bank reports an annual series; India's official CPI (MoSPI) is published "
                     "monthly with a different base year and basket than this derived annual-change figure.",
        value_bounds=(-20.0, 60.0),
        wb_code="FP.CPI.TOTL.ZG",
        synthetic_kind="bounded", synthetic_base=5.5, synthetic_mean_reversion=0.4, synthetic_vol=2.2,
        synthetic_lower=-2.0, synthetic_upper=16.0,
    ),
    "wpi": IndicatorSpec(
        key="wpi", name="WPI inflation (annual %, illustrative subset)", category="Prices",
        provider="MoSPI", source_name="Wholesale Price Index bulletins",
        url="https://www.mospi.gov.in/",
        definition="Annual percentage change in the Wholesale Price Index, India's producer-price-level "
                     "measure, covering primary articles, fuel & power, and manufactured products.",
        unit="%", frequency="annual (official release is monthly)",
        transformations=("none",),
        limitations="WPI is published by MoSPI as monthly bulletins (PDF/Excel), not via a plain REST/JSON "
                     "API; this loader attempts a real HTTP GET against mospi.gov.in as a best-effort live "
                     "probe (see sources.probe_mospi), but cannot parse a true WPI series from that page. "
                     "Treat this series as illustrative-only until a scripted MoSPI bulletin parser is added.",
        value_bounds=(-20.0, 60.0),
        wb_code=None, live_probe=sources.probe_mospi,
        synthetic_kind="bounded", synthetic_base=4.0, synthetic_mean_reversion=0.35, synthetic_vol=3.0,
        synthetic_lower=-5.0, synthetic_upper=18.0,
    ),
    "unemployment_rate": IndicatorSpec(
        key="unemployment_rate", name="Unemployment rate", category="Labour",
        provider="World Bank", source_name="ILO modeled estimate via WDI — SL.UEM.TOTL.ZS",
        url="https://api.worldbank.org/v2/country/IND/indicator/SL.UEM.TOTL.ZS",
        definition="Share of the labour force that is without work but available for and seeking "
                     "employment (ILO modeled estimate).",
        unit="% of total labour force", frequency="annual",
        transformations=("none",),
        limitations="ILO modeled estimate, not India's own PLFS survey rate directly; smooths "
                     "methodology differences across countries for comparability.",
        value_bounds=(0.0, 100.0),
        wb_code="SL.UEM.TOTL.ZS",
        synthetic_kind="bounded", synthetic_base=7.0, synthetic_mean_reversion=0.3, synthetic_vol=1.2,
        synthetic_lower=2.0, synthetic_upper=20.0,
    ),
    "labour_force_participation": IndicatorSpec(
        key="labour_force_participation", name="Labour force participation rate", category="Labour",
        provider="World Bank", source_name="ILO modeled estimate via WDI — SL.TLF.ACTI.ZS",
        url="https://api.worldbank.org/v2/country/IND/indicator/SL.TLF.ACTI.ZS",
        definition="Share of the population ages 15+ that is economically active (working or "
                     "seeking work).",
        unit="% of population ages 15+", frequency="annual",
        transformations=("none",),
        limitations="ILO modeled estimate; India's measured LFPR is sensitive to survey design and has "
                     "shown large swings across NSSO/PLFS survey rounds.",
        value_bounds=(0.0, 100.0),
        wb_code="SL.TLF.ACTI.ZS",
        synthetic_kind="bounded", synthetic_base=50.0, synthetic_mean_reversion=0.25, synthetic_vol=1.5,
        synthetic_lower=30.0, synthetic_upper=70.0,
    ),
    "fiscal_balance": IndicatorSpec(
        key="fiscal_balance", name="Fiscal balance (cash surplus/deficit, % of GDP)", category="Government",
        provider="World Bank", source_name="World Development Indicators — GC.BAL.CASH.GD.ZS",
        url="https://api.worldbank.org/v2/country/IND/indicator/GC.BAL.CASH.GD.ZS",
        definition="Central government cash surplus (positive) or deficit (negative) as a share of GDP.",
        unit="% of GDP", frequency="annual",
        transformations=("none",),
        limitations="Central government only (excludes state governments and off-budget items); India's "
                     "own Budget-documents 'fiscal deficit' figure uses a different (gross borrowing) "
                     "definition and is typically larger in magnitude than this World Bank cash-basis series.",
        value_bounds=(-30.0, 30.0),
        wb_code="GC.BAL.CASH.GD.ZS",
        synthetic_kind="bounded", synthetic_base=-6.0, synthetic_mean_reversion=0.3, synthetic_vol=1.3,
        synthetic_lower=-15.0, synthetic_upper=2.0,
    ),
    "government_debt": IndicatorSpec(
        key="government_debt", name="Central government debt (% of GDP)", category="Government",
        provider="World Bank", source_name="World Development Indicators — GC.DOD.TOTL.GD.ZS",
        url="https://api.worldbank.org/v2/country/IND/indicator/GC.DOD.TOTL.GD.ZS",
        definition="Total outstanding debt of the central government as a share of GDP.",
        unit="% of GDP", frequency="annual",
        transformations=("none",),
        limitations="Central government only; India's combined general-government debt (adding states) "
                     "is materially higher than this series.",
        value_bounds=(0.0, 300.0),
        wb_code="GC.DOD.TOTL.GD.ZS",
        synthetic_kind="bounded", synthetic_base=70.0, synthetic_mean_reversion=0.2, synthetic_vol=2.5,
        synthetic_lower=40.0, synthetic_upper=100.0,
    ),
    "exports": IndicatorSpec(
        key="exports", name="Exports of goods and services (current US$)", category="External sector",
        provider="World Bank", source_name="World Development Indicators — NE.EXP.GNFS.CD",
        url="https://api.worldbank.org/v2/country/IND/indicator/NE.EXP.GNFS.CD",
        definition="Value of all goods and other market services provided to the rest of the world.",
        unit="current US$", frequency="annual",
        transformations=("none",),
        limitations="Balance-of-payments basis; current-US$ terms mix real volume and price/FX effects.",
        value_bounds=(0.0, float("inf")),
        wb_code="NE.EXP.GNFS.CD",
        synthetic_kind="level", synthetic_base=1.5e11, synthetic_drift=0.08, synthetic_vol=0.10,
    ),
    "imports": IndicatorSpec(
        key="imports", name="Imports of goods and services (current US$)", category="External sector",
        provider="World Bank", source_name="World Development Indicators — NE.IMP.GNFS.CD",
        url="https://api.worldbank.org/v2/country/IND/indicator/NE.IMP.GNFS.CD",
        definition="Value of all goods and other market services received from the rest of the world.",
        unit="current US$", frequency="annual",
        transformations=("none",),
        limitations="Balance-of-payments basis; current-US$ terms mix real volume and price/FX effects.",
        value_bounds=(0.0, float("inf")),
        wb_code="NE.IMP.GNFS.CD",
        synthetic_kind="level", synthetic_base=1.8e11, synthetic_drift=0.08, synthetic_vol=0.11,
    ),
    "current_account": IndicatorSpec(
        key="current_account", name="Current account balance (% of GDP)", category="External sector",
        provider="World Bank", source_name="World Development Indicators — BN.CAB.XOKA.GD.ZS",
        url="https://api.worldbank.org/v2/country/IND/indicator/BN.CAB.XOKA.GD.ZS",
        definition="Sum of net exports of goods/services, net income, and net current transfers, as a "
                     "share of GDP.",
        unit="% of GDP", frequency="annual",
        transformations=("none",),
        limitations="Annual, balance-of-payments basis; does not reveal within-year volatility (e.g. "
                     "quarterly swings around oil-price or capital-flow shocks).",
        value_bounds=(-20.0, 20.0),
        wb_code="BN.CAB.XOKA.GD.ZS",
        synthetic_kind="bounded", synthetic_base=-1.5, synthetic_mean_reversion=0.35, synthetic_vol=1.1,
        synthetic_lower=-6.0, synthetic_upper=4.0,
    ),
    "exchange_rate": IndicatorSpec(
        key="exchange_rate", name="Official exchange rate (INR per US$)", category="External sector",
        provider="World Bank", source_name="World Development Indicators — PA.NUS.FCRF",
        url="https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF",
        definition="Period-average official exchange rate, Indian rupees per US dollar.",
        unit="INR per US$", frequency="annual",
        transformations=("none",),
        limitations="Annual average, not a daily spot rate; RBI publishes daily reference rates with "
                     "finer granularity via DBIE.",
        value_bounds=(0.0, 500.0),
        wb_code="PA.NUS.FCRF",
        synthetic_kind="level", synthetic_base=65.0, synthetic_drift=0.025, synthetic_vol=0.05,
    ),
    "policy_rate": IndicatorSpec(
        key="policy_rate", name="Policy interest rate (illustrative; RBI repo rate proxy)", category="Financial system",
        provider="RBI (Database on Indian Economy)", source_name="Monetary policy repo rate",
        url="https://dbie.rbi.org.in/",
        definition="RBI's benchmark repo rate: the rate at which RBI lends short-term funds to "
                     "commercial banks, the primary monetary-policy-stance signal.",
        unit="%", frequency="event-driven (changes at RBI Monetary Policy Committee meetings)",
        transformations=("none",),
        limitations="RBI DBIE does not expose a stable unauthenticated JSON API; this loader performs a "
                     "real best-effort HTTP GET against the DBIE portal (sources.probe_rbi_dbie) but "
                     "cannot parse an actual repo-rate series from it today. Treat this series as "
                     "illustrative-only until a scripted DBIE export parser is added.",
        value_bounds=(0.0, 30.0),
        wb_code=None, live_probe=sources.probe_rbi_dbie,
        synthetic_kind="bounded", synthetic_base=6.0, synthetic_mean_reversion=0.25, synthetic_vol=0.6,
        synthetic_lower=3.0, synthetic_upper=9.0,
    ),
    "bank_credit_growth": IndicatorSpec(
        key="bank_credit_growth", name="Bank credit growth (p.p. change, domestic credit to private sector)",
        category="Financial system",
        provider="World Bank", source_name="World Development Indicators — FS.AST.PRVT.GD.ZS (derived)",
        url="https://api.worldbank.org/v2/country/IND/indicator/FS.AST.PRVT.GD.ZS",
        definition="Year-over-year change (in percentage points of GDP) in domestic credit to the "
                     "private sector by banks, used here as a proxy for bank-credit growth momentum.",
        unit="percentage points of GDP, YoY change", frequency="annual",
        transformations=("first difference (YoY) of domestic credit to private sector, % of GDP",),
        limitations="A level-ratio's YoY change is a proxy for credit *growth*, not a direct growth-rate "
                     "series; RBI DBIE publishes a direct non-food bank credit growth rate that is not "
                     "retrievable via a plain REST endpoint (see policy_rate limitations for the same "
                     "DBIE constraint).",
        value_bounds=(-50.0, 50.0),
        wb_code="FS.AST.PRVT.GD.ZS", postprocess=_credit_growth_postprocess,
        synthetic_kind="bounded", synthetic_base=2.0, synthetic_mean_reversion=0.4, synthetic_vol=3.0,
        synthetic_lower=-10.0, synthetic_upper=15.0,
    ),
}


def list_categories() -> Dict[str, list]:
    """Category -> list of indicator keys, in registry order."""
    out: Dict[str, list] = {}
    for key, spec in INDICATORS.items():
        out.setdefault(spec.category, []).append(key)
    return out


def load(indicator_key: str, start: str, end: str, allow_live: bool = True) -> Tuple[pd.DataFrame, Metadata]:
    """Load any registered indicator by its key. Raises `KeyError` for an
    unknown key."""
    if indicator_key not in INDICATORS:
        raise KeyError(f"Unknown indicator key: {indicator_key!r}. Known keys: {sorted(INDICATORS)}")
    return load_indicator(INDICATORS[indicator_key], start, end, allow_live=allow_live)


# Convenience named wrappers (`load_gdp(start, end, allow_live=True)`, etc.)
# so callers who prefer explicit function names over string keys have them.
def _make_wrapper(key: str) -> Callable[..., Tuple[pd.DataFrame, Metadata]]:
    def _wrapper(start: str, end: str, allow_live: bool = True) -> Tuple[pd.DataFrame, Metadata]:
        return load(key, start, end, allow_live=allow_live)

    _wrapper.__name__ = f"load_{key}"
    _wrapper.__doc__ = f"Load the '{INDICATORS[key].name}' indicator. See `load()` for details."
    return _wrapper


load_gdp = _make_wrapper("gdp")
load_gdp_per_capita = _make_wrapper("gdp_per_capita")
load_cpi = _make_wrapper("cpi")
load_wpi = _make_wrapper("wpi")
load_unemployment_rate = _make_wrapper("unemployment_rate")
load_labour_force_participation = _make_wrapper("labour_force_participation")
load_fiscal_balance = _make_wrapper("fiscal_balance")
load_government_debt = _make_wrapper("government_debt")
load_exports = _make_wrapper("exports")
load_imports = _make_wrapper("imports")
load_current_account = _make_wrapper("current_account")
load_exchange_rate = _make_wrapper("exchange_rate")
load_policy_rate = _make_wrapper("policy_rate")
load_bank_credit_growth = _make_wrapper("bank_credit_growth")
