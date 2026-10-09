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
        id="state_sectoral_gva",
        name="State-wise gross state value added (GSVA) by sector — not loaded",
        publisher="MoSPI (state DES estimates) as compiled in the RBI Handbook of Statistics on Indian States",
        url="https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States",
        status="DATA REQUIRED",
        period="Would need the 2011-12 base series, financial years 2011-12 onward",
        units="₹ crore at constant (2011-12) prices, by sector",
        coverage="States/UTs", frequency="Annual (financial year)",
        transformations="Not loaded — nothing is shown from this source.",
        missing="Not applicable: no file exists in this repository.",
        limitations="Required for state comparisons of industrialisation and productivity on the Structural "
                    "Transformation Lab; until supplied that section shows DATA REQUIRED.",
        used_on=("Structural Transformation Lab",),
    ),
    Dataset(
        id="plfs_state_industry",
        name="PLFS state-wise distribution of workers by broad industry — not loaded",
        publisher="Ministry of Statistics and Programme Implementation (NSO) — Periodic Labour Force Survey",
        url="https://www.mospi.gov.in/", status="DATA REQUIRED",
        period="Would need PLFS annual rounds (July–June survey years)",
        units="% of workers, usual status (principal + subsidiary)",
        coverage="States/UTs, rural + urban", frequency="Annual survey rounds",
        transformations="Not loaded — nothing is shown from this source.",
        missing="Not applicable: no file exists in this repository.",
        limitations="Required (with state GSVA by sector) for state relative labour productivity; survey years "
                    "(July–June) do not align with financial years (April–March).",
        used_on=("Structural Transformation Lab",),
    ),
]
