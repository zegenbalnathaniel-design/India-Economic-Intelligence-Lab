"""Evidence-ledger records for the Inequality & Financialisation Lab.

Collected automatically by `data_sources.registry.all_datasets()`. Live
WDI series are LIVE (fetched at run time, nothing stored); the rest are
DATA REQUIRED -- named sources the project does not hold, with no files
and no numbers. See data_sources/financialisation_uploads.py for the CSV
contract each DATA REQUIRED record would be loaded through.
"""
from __future__ import annotations

from data_sources.registry import Dataset

_PAGE = ("Inequality & Financialisation Lab",)

DATASETS: list[Dataset] = [
    Dataset(
        id="wdi_financial_inclusion",
        name="Account ownership, Global Findex (WDI: FX.OWN.TOTL.ZS, .FE.ZS, .40.ZS, .60.ZS)",
        publisher="World Bank — Global Findex Database, via World Development Indicators",
        url="https://data.worldbank.org/indicator/FX.OWN.TOTL.ZS", status="LIVE",
        period="Findex survey years only, as returned by the API at run time",
        units="% of population ages 15+ (total, women, poorest 40%, richest 60%)",
        coverage="India", frequency="Survey years (not annual)",
        transformations="None. Gap = richest 60% minus poorest 40%, computed only for years where both are reported.",
        missing="API nulls (non-survey years) stay missing and are never interpolated; a failed request shows "
                "DATA UNAVAILABLE for that series only.",
        methodology="Household survey of adults; 'poorest 40% / richest 60%' are Findex's within-country income groups.",
        limitations="Measures having an account, not balances, use or asset holdings; survey sampling error "
                    "not reported here; not reachable from the build sandbox, so verified only on the deployed app.",
        used_on=_PAGE,
    ),
    Dataset(
        id="wdi_financial_depth",
        name="Financial depth (WDI: FS.AST.PRVT.GD.ZS, FD.AST.PRVT.GD.ZS, CM.MKT.LCAP.GD.ZS)",
        publisher="World Bank WDI (IMF International Financial Statistics; World Federation of Exchanges)",
        url="https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS", status="LIVE",
        period="As returned by the API at run time", units="% of GDP",
        coverage="India", frequency="Annual",
        transformations="None; changes and correlations with WIL shares are computed on the page over overlapping years only.",
        missing="API nulls stay missing; each code is fetched separately and a failure is reported per series.",
        limitations="Aggregate ratios: they measure the size of credit and equity markets, not who owns the "
                    "assets. Market capitalisation moves with share prices. Not reachable from the build sandbox.",
        used_on=_PAGE,
    ),
    Dataset(
        id="amfi_mf_folios_sip",
        name="Mutual-fund folios and SIP inflows (monthly)",
        publisher="Association of Mutual Funds in India (AMFI)",
        url="https://www.amfiindia.com/", status="DATA REQUIRED",
        period="Not loaded", units="Folios (count); SIP contribution (₹ crore); SIP accounts (count)",
        coverage="All-India mutual-fund industry", frequency="Monthly",
        transformations="None yet. Loader contract: data_sources/financialisation_uploads.py (amfi_folios, amfi_sip).",
        missing="No file in the project — every figure is shown as DATA REQUIRED.",
        limitations="Folios are not unique investors (one person can hold many); aggregate SIP inflows are "
                    "not a measure of how wealth is distributed.",
        used_on=_PAGE,
    ),
    Dataset(
        id="nsdl_demat_accounts",
        name="Demat accounts held at NSDL (monthly)",
        publisher="National Securities Depository Ltd (NSDL)",
        url="https://nsdl.co.in/", status="DATA REQUIRED",
        period="Not loaded", units="Accounts (count)", coverage="NSDL depository participants' clients",
        frequency="Monthly",
        transformations="None yet. Loader contract: data_sources/financialisation_uploads.py (demat_accounts).",
        missing="No file in the project — shown as DATA REQUIRED.",
        limitations="Accounts are not unique investors: one person can hold several accounts, including at "
                    "both depositories, so NSDL + CDSL counts cannot be added to count people.",
        used_on=_PAGE,
    ),
    Dataset(
        id="cdsl_demat_accounts",
        name="Demat (BO) accounts held at CDSL (monthly)",
        publisher="Central Depository Services (India) Ltd (CDSL)",
        url="https://www.cdslindia.com/", status="DATA REQUIRED",
        period="Not loaded", units="Accounts (count)", coverage="CDSL depository participants' clients",
        frequency="Monthly",
        transformations="None yet. Loader contract: data_sources/financialisation_uploads.py (demat_accounts).",
        missing="No file in the project — shown as DATA REQUIRED.",
        limitations="Accounts are not unique investors; see the NSDL record.",
        used_on=_PAGE,
    ),
    Dataset(
        id="aidis77_asset_composition",
        name="Household asset composition by asset-holding class (NSS 77th round AIDIS, 2019)",
        publisher="Ministry of Statistics and Programme Implementation (NSO) — All India Debt and Investment Survey",
        url="https://www.mospi.gov.in/", status="DATA REQUIRED",
        period="Not loaded (survey reference year 2019)", units="% of each group's total assets",
        coverage="Rural and urban households, by asset-holding class", frequency="Survey round",
        transformations="None yet. Loader contract: data_sources/financialisation_uploads.py (aidis_composition).",
        missing="No file in the project — composition by household group is shown as DATA REQUIRED.",
        limitations="Survey under-captures the wealthiest households and financial assets; unit-level data "
                    "needs registered access at microdata.gov.in.",
        used_on=_PAGE,
    ),
    Dataset(
        id="consumption_gini_series",
        name="Consumption inequality (Gini) series comparable over time",
        publisher="Ministry of Statistics and Programme Implementation — Household Consumption Expenditure Survey",
        url="https://www.mospi.gov.in/", status="DATA REQUIRED",
        period="Not loaded", units="Gini coefficient of per-capita consumption",
        coverage="All-India", frequency="Survey rounds",
        transformations="None.",
        missing="No consumption-Gini series is in the project — shown as DATA REQUIRED.",
        limitations="Consumption surveys changed design between rounds (recall periods, questionnaires), so a "
                    "comparable series needs careful harmonisation; consumption inequality is not income or "
                    "wealth inequality.",
        used_on=_PAGE,
    ),
]
