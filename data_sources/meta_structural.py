"""Evidence-ledger records for the Structural Transformation Lab.

Collected automatically by `data_sources.registry.all_datasets()`.
The WDI structural series are fetched live (no file in the repository);
the two state-level records are DATA REQUIRED -- they describe files
that would enable the state comparison and do not exist yet.
"""
from __future__ import annotations

from data_sources.registry import Dataset

DATASETS: list[Dataset] = [
    Dataset(
        id="wdi_structural",
        name="WDI structural-transformation series: sector value-added and employment shares, "
             "labour force participation, GDP per person employed, vulnerable employment (live API)",
        publisher="World Bank — World Development Indicators (national accounts; ILO modelled estimates via ILOSTAT)",
        url="https://data.worldbank.org/", status="LIVE",
        period="As returned by the API at run time (years chosen on the page)",
        units="% of GDP (value added); % of total employment; % of population 15+ (participation); "
              "constant PPP $ per person employed",
        coverage="India and selected peer economies", frequency="Annual",
        transformations="Fetched with data_sources/worldbank.fetch (codes NV.AGR.TOTL.ZS, NV.IND.TOTL.ZS, "
                        "NV.IND.MANF.ZS, NV.SRV.TOTL.ZS, SL.AGR.EMPL.ZS, SL.IND.EMPL.ZS, SL.SRV.EMPL.ZS, "
                        "SL.TLF.CACT.FE.ZS, SL.TLF.CACT.MA.ZS, SL.GDP.PCAP.EM.KD, SL.EMP.VULN.ZS). Derived on the "
                        "page (analysis/structural.py): output-minus-employment share gaps, sector sums, "
                        "relative labour productivity = VA share / employment share, and an optional, "
                        "labelled rescaling of VA shares to their three-sector total.",
        missing="API nulls stay missing; a derived value needs every input for the same country and year — "
                "nothing is interpolated. Any failed request shows DATA UNAVAILABLE, never stale values.",
        methodology="Relative labour productivity compares a sector's value added per worker with GDP per "
                    "worker; it is not an absolute productivity level.",
        limitations="Value-added shares are of GDP at market prices, so the three sectors sum to less than 100 "
                    "(net taxes on products); shares are nominal, so they move with relative prices. Employment, "
                    "participation and vulnerable-employment series are ILO modelled estimates, not India's PLFS. "
                    "Value added (national accounts) and employment (ILO) come from different sources. "
                    "Not reachable from the build sandbox — verified only on the deployed app.",
        used_on=("Structural Transformation Lab",),
    ),
    Dataset(
        id="state_gsva_plfs_shares",
        name="State sector shares of GSVA and of workers (PLFS), 19 states",
        publisher="Compiled and supplied by the project author from state GSVA (RBI Handbook / MoSPI) and PLFS",
        url="https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States",
        status="PARTIAL",
        period="Not stated in the supplied table (GSVA year and PLFS round unknown)",
        units="% of GSVA; % of workers", coverage="19 states", frequency="Single cross-section",
        files=("data/raw/state_structural/state_gsva_plfs_sector_shares.csv",), added="2026-10-10",
        transformations="Entered as supplied (the author's latest version). Relative labour productivity = GSVA "
                        "share ÷ worker share within each state (analysis/structural.state_rlp).",
        missing="Other states and union territories are not in the table and are not shown.",
        methodology="The author states the figures are verified. Earlier versions supplied on 2026-10-10 gave "
                    "different values for several states (e.g. Andhra Pradesh agriculture 26.4% / 31.2% of GSVA); "
                    "this file uses the latest version.",
        limitations="The GSVA year, price basis (current or constant) and PLFS round are not stated, so states "
                    "may not be measured at the same date and the two sides may be different years. Sector "
                    "groupings (industry = mining, manufacturing, construction, utilities) are assumed to match "
                    "between GSVA and PLFS. Not a time series: shows levels, not change.",
        used_on=("Structural Transformation Lab",),
    ),
]
