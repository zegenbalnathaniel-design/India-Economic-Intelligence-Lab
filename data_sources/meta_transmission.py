"""Evidence-ledger record for the Macro Transmission Simulator's parameters."""
from __future__ import annotations

from data_sources.registry import Dataset

DATASETS = [
    Dataset(
        id="transmission_parameters",
        name="Transmission coefficients for India, with citations (simulator parameters)",
        publisher=("Compiled in this project from RBI (Monetary Policy Reports, Bulletin articles, working papers, "
                   "Mint Street Memo) and NIPFP / Margin (Bose & Bhanumurthy) publications — one citation per row"),
        url="", status="PARTIAL",
        period="Sources dated 2011–2025; each row states the period or episode its number comes from",
        units="Per row (pp per pp, bps per 10% shock, pp of GDP per US$10/bbl, ₹ per ₹)",
        coverage="India (national)", frequency="Point estimates",
        files=("data/raw/transmission/parameters.csv",),
        publication="Compiled 2026-10-09", added="2026-10-09",
        transformations=("Numbers recorded as the sources state them; three pass-through ratios are computed here "
                         "from the source's own figures (187/250, 111/250, -160/250) and say so in the row."),
        missing=("Coefficients that could not be verified are blank with status DATA REQUIRED; the simulator then "
                 "shows 'needs parameter' for every link that uses them — never a number."),
        methodology=("Each value was accepted only if a web search result attributed that specific number to an "
                     "identifiable publication; the wording is stored in quote_or_context and how it was checked in "
                     "verified_via. Set B rows are alternative cited estimates for side-by-side comparison."),
        limitations=("Verified through search-engine summaries, not by opening the primary PDFs (direct fetch was "
                     "blocked from the build environment) — re-check each figure against its source before relying on "
                     "it. Coefficients come from different models, samples and episodes and are not mutually "
                     "consistent; MPR sensitivities are scenario outputs of the RBI's model, not structural elasticities."),
        used_on=("Macro Transmission Simulator",),
    ),
]
