"""India Economic Data Observatory — a data ingestion, cleaning and
validation platform for Indian economic indicators.

Every series this package returns is bundled with a `Metadata` record
(`metadata.py`) that states, among other things, whether it is `official`
(fetched live from a cited real source) or `illustrative_synthetic` (a
deterministic fallback used when the live fetch failed or was disabled).
See `loaders.py` for the public loading API and `docs/DATA_SOURCES.md` for
the full source table and this environment's actual network-probe result.
"""
from .metadata import DataStatus, Metadata
from .loaders import INDICATORS, IndicatorSpec, list_categories, load

__all__ = [
    "DataStatus",
    "Metadata",
    "INDICATORS",
    "IndicatorSpec",
    "list_categories",
    "load",
]

__version__ = "0.1.0"
