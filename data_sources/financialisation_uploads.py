"""Loader contracts for financialisation data the project does NOT yet have.

Status of every dataset below: DATA REQUIRED. No file ships with the
project and nothing here generates, estimates or back-fills values. Each
contract says which publisher file would fill it, where to put the CSV
and which columns it must have; `load()` returns ``None`` while the file
is absent, so the page shows a DATA REQUIRED panel instead of numbers.

When a file is added it must also be registered in
`data_sources/meta_financialisation.py` (``files=(...)`` and a status other
than DATA REQUIRED) -- `registry.registry_problems()` flags any CSV under
data/ that is not in the ledger.

Contracts
---------
``amfi_folios`` -- data/raw/financialisation/amfi_folios_monthly.csv
    Source: Association of Mutual Funds in India (AMFI),
    https://www.amfiindia.com/ -- the monthly industry data (scheme-category
    table with the number of folios), one row per month x category as
    published. Columns:

    ============== ======= ==================================================
    month          str     ``YYYY-MM`` (month the figure refers to)
    scheme_category str    category exactly as printed (e.g. the equity /
                           debt / hybrid sub-categories, or ``Grand Total``)
    folios         int     number of folios (accounts), as published
    source_file    str     name of the AMFI file the row was copied from
    ============== ======= ==================================================

    SAFEGUARD: a folio is an account in one scheme; one investor can hold
    many folios. Folio counts are NOT unique investors.

``amfi_sip`` -- data/raw/financialisation/amfi_sip_monthly.csv
    Source: AMFI, https://www.amfiindia.com/ -- monthly SIP data
    (contribution amount and SIP accounts). Columns:

    ======================== ===== ==========================================
    month                    str   ``YYYY-MM``
    sip_contribution_inr_cr  float SIP inflows in the month, ₹ crore
    sip_accounts             int   SIP accounts outstanding / contributing,
                                   as published (blank if not published)
    source_file              str   AMFI file name
    ======================== ===== ==========================================

    SAFEGUARD: aggregate SIP inflows measure a flow of saving into funds;
    they say nothing about how that saving -- or the wealth it builds -- is
    distributed across households.

``demat_accounts`` -- data/raw/financialisation/demat_accounts_monthly.csv
    Source: National Securities Depository Ltd (NSDL),
    https://nsdl.co.in/ and Central Depository Services (India) Ltd (CDSL),
    https://www.cdslindia.com/ -- each depository's published count of
    demat (beneficial-owner) accounts. One row per month x depository.
    Columns:

    =============== ===== ===================================================
    month           str   ``YYYY-MM`` (month-end the count refers to)
    depository      str   ``NSDL`` or ``CDSL`` (exactly)
    demat_accounts  int   accounts as published by that depository
    source_file     str   publisher file / page the figure came from
    =============== ===== ===================================================

    SAFEGUARD: demat accounts are not unique investors. One person can hold
    several accounts, at one depository or across both; adding NSDL and
    CDSL counts gives accounts, not people.

``aidis_composition`` -- data/raw/financialisation/aidis77_asset_composition.csv
    Source: NSS 77th round (January-December 2019), All India Debt and
    Investment Survey (AIDIS) -- the MoSPI report tables on asset
    composition by asset-holding class, or estimates computed from the
    unit-level microdata (microdata.gov.in, registered access). Columns:

    ================= ===== =================================================
    sector            str   ``rural``, ``urban`` or ``all``
    asset_class_group str   household group as defined in the source (e.g.
                            decile class of asset holding: ``D1`` ... ``D10``)
    asset_type        str   asset category as defined in the source (land,
                            buildings, livestock, transport equipment,
                            financial assets, gold/jewellery, ...)
    share_pct         float that asset type's share of the group's total
                            assets, %
    source_table      str   report table number or microdata computation note
    ================= ===== =================================================
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "data" / "raw" / "financialisation"
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass(frozen=True)
class Contract:
    name: str
    path: Path
    columns: dict[str, str]       # column -> "str" | "int" | "float"
    publisher: str
    url: str
    series: str                   # what to download, in words
    safeguard: str
    optional: tuple[str, ...] = ()

    @property
    def relpath(self) -> str:
        return str(self.path.relative_to(ROOT))


CONTRACTS: dict[str, Contract] = {c.name: c for c in [
    Contract(
        "amfi_folios", UPLOAD_DIR / "amfi_folios_monthly.csv",
        {"month": "str", "scheme_category": "str", "folios": "int", "source_file": "str"},
        "Association of Mutual Funds in India (AMFI)", "https://www.amfiindia.com/",
        "Monthly mutual-fund industry data: number of folios by scheme category",
        "Folios are accounts, not people: one investor can hold many folios across schemes "
        "and fund houses, so folio counts overstate the number of unique investors.",
    ),
    Contract(
        "amfi_sip", UPLOAD_DIR / "amfi_sip_monthly.csv",
        {"month": "str", "sip_contribution_inr_cr": "float", "sip_accounts": "int", "source_file": "str"},
        "Association of Mutual Funds in India (AMFI)", "https://www.amfiindia.com/",
        "Monthly SIP data: SIP contribution (₹ crore) and number of SIP accounts",
        "Aggregate SIP inflows are a flow of saving into funds. They are not a measure of how "
        "financial wealth is distributed across households.",
        optional=("sip_accounts",),
    ),
    Contract(
        "demat_accounts", UPLOAD_DIR / "demat_accounts_monthly.csv",
        {"month": "str", "depository": "str", "demat_accounts": "int", "source_file": "str"},
        "NSDL (https://nsdl.co.in/) and CDSL (https://www.cdslindia.com/)", "https://nsdl.co.in/",
        "Each depository's published count of demat (beneficial-owner) accounts, month-end",
        "Demat accounts are not unique investors: one person can hold several accounts, at one "
        "depository or across NSDL and CDSL. NSDL + CDSL = accounts, not people.",
    ),
    Contract(
        "aidis_composition", UPLOAD_DIR / "aidis77_asset_composition.csv",
        {"sector": "str", "asset_class_group": "str", "asset_type": "str", "share_pct": "float",
         "source_table": "str"},
        "MoSPI — NSS 77th round, All India Debt and Investment Survey (AIDIS) 2019",
        "https://www.mospi.gov.in/",
        "Composition of household assets by asset-holding class (e.g. deciles), rural/urban",
        "Survey-based: AIDIS is known to under-capture the wealthiest households and financial "
        "assets, so the top of the distribution would still be under-represented.",
    ),
]}


def validate(df: pd.DataFrame, contract: Contract) -> list[str]:
    """Problems with `df` against `contract`; an empty list means it passes.
    Checks presence of columns, numeric types, month format, negative
    counts/amounts, shares outside 0-100 and duplicate keys. Nothing is
    repaired."""
    problems: list[str] = []
    missing = [c for c in contract.columns if c not in df.columns]
    if missing:
        return [f"missing column(s): {', '.join(missing)}"]
    if df.empty:
        return ["file has no rows"]
    for col, kind in contract.columns.items():
        if kind in ("int", "float"):
            vals = pd.to_numeric(df[col], errors="coerce")
            bad = df[col].notna() & vals.isna()
            if bad.any():
                problems.append(f"{col}: {int(bad.sum())} non-numeric value(s)")
            if col not in contract.optional and df[col].isna().any():
                problems.append(f"{col}: {int(df[col].isna().sum())} blank value(s)")
            if (vals < 0).any():
                problems.append(f"{col}: negative value(s)")
            if col == "share_pct" and (vals > 100).any():
                problems.append("share_pct: value(s) above 100")
    if "month" in df.columns:
        bad_m = ~df["month"].astype(str).str.strip().str.match(MONTH)
        if bad_m.any():
            problems.append(f"month: {int(bad_m.sum())} value(s) not in YYYY-MM form")
    if "depository" in df.columns:
        bad_d = ~df["depository"].isin(["NSDL", "CDSL"])
        if bad_d.any():
            problems.append("depository: values must be exactly NSDL or CDSL")
    keys = [c for c in ("month", "scheme_category", "depository", "sector", "asset_class_group", "asset_type")
            if c in df.columns]
    if keys and df.duplicated(keys).any():
        problems.append(f"duplicate rows for key ({', '.join(keys)})")
    return problems


def load(name: str) -> tuple[pd.DataFrame | None, list[str]]:
    """(frame, problems) for contract `name`; (None, []) when the file is
    absent -- the DATA REQUIRED state."""
    contract = CONTRACTS[name]
    if not contract.path.exists():
        return None, []
    df = pd.read_csv(contract.path)
    return df, validate(df, contract)


def template(name: str) -> pd.DataFrame:
    """An EMPTY frame with the contract's columns (header only) -- offered
    as a download so a user can fill it from the publisher's file."""
    return pd.DataFrame(columns=list(CONTRACTS[name].columns))
