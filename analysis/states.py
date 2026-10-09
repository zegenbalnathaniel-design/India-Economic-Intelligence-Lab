"""State Economy Explorer -- one long-format panel of every real
state-level indicator in `data/raw/`.

Nothing here estimates, interpolates or fills a value. The module does
four things, all of them mechanical:

1. **Name normalisation.** The raw files spell some states/UTs differently
   ("Andaman & Nicobar Islands" vs "Andaman and Nicobar Islands",
   "Jammu & Kashmir" vs "Jammu and Kashmir" vs "Jammu & Kashmir*" vs
   "Jammu & Kashmir-U.T."). `normalise_state()` maps every variant that
   actually occurs in the files onto one canonical list
   (`CANONICAL_STATES`), maps the national rows ("India", "All-India") onto
   `NATIONAL`, and returns ``None`` for anything else (e.g. table footnotes
   that were ingested as rows) so nothing is silently guessed.
2. **One long panel** (`build_panel()`): ``state, indicator, period, value,
   unit, source, status, note``. Blank cells in a source stay as NaN rows
   with a note -- a blank is "no data", never 0.
3. **National benchmarks** (`national_benchmarks()`), taken only from rows
   the source itself supplies ("India" / "All-India"). No population-
   weighted average is computed here: none of these files ships the
   weights, so indicators without a national row in their source say
   "no national benchmark in source".
4. **Descriptive calculations**: latest value, cross-state rank, side-by-
   side comparison and first-vs-latest change with CAGR where that is
   mathematically defined (both endpoints positive, at least one year
   apart).

Known data issues (see DATA_REGISTRY.md) are carried through, not hidden:
Delhi and Puducherry are missing from the current-price NSDP table (their
rows were transcribed with 13 of 14 values and kept unmerged); the older
`state_gsdp_nsdp_percapita.csv` is a different release vintage of the
current-price series; the constant-price series is a splice of two base
years; MPCE is consumption, not income.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from data_sources import loaders

# ---------------------------------------------------------------------------
# 1. State names
# ---------------------------------------------------------------------------

# The union of every state/UT that appears in any state-level file in
# data/raw/, written in the spelling most of those files use ("&").
CANONICAL_STATES: tuple[str, ...] = (
    "Andaman & Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra & Nagar Haveli and Daman & Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu & Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)

NATIONAL = "India (national)"

# Variants that occur in the raw files and are not resolved by the generic
# "&" <-> "and" / punctuation-insensitive key below. Every entry here was
# observed in a file; none is guessed.
_EXPLICIT_ALIASES: dict[str, str] = {
    # percapita_nsdp_constant_prices_2004_05_to_2022_23.csv, 2011-12 base.
    # The asterisk is the table's own footnote: "Relates to Jammu & Kashmir
    # and Ladakh" (the pre-2019 state). "-U.T." is the post-2019 UT.
    # Different territories -- mapped to one canonical name for lookup,
    # but see JK_TERRITORY_NOTE wherever both are shown together.
    "Jammu & Kashmir*": "Jammu & Kashmir",
    "Jammu & Kashmir-U.T.": "Jammu & Kashmir",
    # National rows.
    "India": NATIONAL,
    "All-India": NATIONAL,
}

JK_TERRITORY_NOTE = (
    "Jammu & Kashmir's territory changed in 2019: RBI Table 26 marks values "
    "to 2018-19 as relating to Jammu & Kashmir *and Ladakh*, and reports the "
    "Jammu & Kashmir UT separately from 2019-20. 2023-24 files list Ladakh "
    "as its own UT."
)

# Rows ingested from table footnotes, not states. Recognised explicitly so
# the name test can tell "known non-state row" apart from "unknown name".
NON_STATE_ROWS: frozenset[str] = frozenset({
    "-: Not Available. * : Relates to Jammu & Kashmir and Ladakh.",
    "Source: National Statistics Office, Ministry of Statistics and Programme Implementation, Government of India.",
})


def _key(name: str) -> str:
    """Spelling-insensitive key: lower-case, '&' == 'and', punctuation and
    whitespace removed. "Andaman and Nicobar Islands" and "Andaman &
    Nicobar Islands" share a key; "Jammu & Kashmir*" does not (handled by
    the explicit alias table instead, so the territorial note is kept)."""
    s = name.strip().lower().replace("&", " and ")
    return re.sub(r"[^a-z]", "", s)


_CANONICAL_BY_KEY = {_key(s): s for s in CANONICAL_STATES}


def normalise_state(name: object) -> Optional[str]:
    """Map a raw state/UT label onto `CANONICAL_STATES`, `NATIONAL`, or
    ``None`` (footnote row, blank, or an unrecognised name -- never a
    guess)."""
    if not isinstance(name, str) or not name.strip():
        return None
    raw = name.strip()
    if raw in NON_STATE_ROWS:
        return None
    if raw in _EXPLICIT_ALIASES:
        return _EXPLICIT_ALIASES[raw]
    return _CANONICAL_BY_KEY.get(_key(raw))


def unmatched_names(names: Iterable[object]) -> list[str]:
    """Names that are neither a canonical state, the national row, nor a
    known footnote row. An empty list means every name was resolved."""
    out = []
    for n in names:
        if isinstance(n, str) and n.strip() in NON_STATE_ROWS:
            continue
        if normalise_state(n) is None:
            out.append(n)
    return sorted(set(map(str, out)))


def name_variants(names: Iterable[object]) -> dict[str, str]:
    """{raw spelling: canonical} for every raw label that differs from its
    canonical form -- the actual variants found in a file."""
    out = {}
    for n in names:
        c = normalise_state(n)
        if c is not None and c != n:
            out[str(n)] = c
    return out


# ---------------------------------------------------------------------------
# 2. Indicator metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Indicator:
    key: str
    label: str
    unit: str
    source: str
    source_file: str
    status: str
    price_basis: str  # "constant", "current", or "n/a"
    explainer: str


_GSDP_FILE = "data/raw/state_gsdp_nsdp_percapita.csv"
_GSDP_SOURCE = (
    "state_gsdp_nsdp_percapita.csv (earlier upload; likely MoSPI / RBI state "
    "accounts -- source not confirmed)"
)
_GSDP_CAVEAT = (
    "**Caveat.** This file's source has not been confirmed (status PARTIAL) "
    "and it is an *older release vintage* than the RBI current-price table "
    "used elsewhere on this page: for ~20 states its 2023-24 and 2024-25 "
    "values differ from the newer table by a small, consistent ~1-2% "
    "(the pattern of provisional vs. revised estimates). Delhi's row is "
    "blank (it was malformed in the original upload) and Ladakh's row has "
    "one value fewer than the header, so it is excluded rather than "
    "realigned by guesswork. Only two years -- a change between them is "
    "one year's growth, not a trend."
)

INDICATORS: dict[str, Indicator] = {
    "nsdp_pc_constant_spliced": Indicator(
        key="nsdp_pc_constant_spliced",
        label="Per-capita NSDP, constant prices (spliced)",
        unit="₹",
        source="RBI Handbook of Statistics on Indian States, Table 26 -- 2004-05 and 2011-12 base years linked by overlap-year factors",
        source_file="data/raw/rbi_handbook/percapita_nsdp_constant_prices_SPLICED_2004_05_to_2022_23.csv",
        status="SPLICED",
        price_basis="constant",
        explainer=(
            "**What it measures.** Net State Domestic Product per person at "
            "*constant* prices -- output per resident with inflation removed, "
            "so a rise is real growth, not just higher prices.\n\n"
            "**Period.** Annual, 2004-05 to 2022-23 (19 financial years), 32 "
            "states/UTs.\n\n"
            "**How it was built.** RBI publishes this in two base years (2004-05 "
            "and 2011-12). Values from 2011-12 onward are the 2011-12-base "
            "figures as published; earlier values are the 2004-05-base figures "
            "multiplied by a per-state link factor (mean ratio of new to old base "
            "over 2011-12 to 2014-15). Each row's method is shown in the tables.\n\n"
            "**Caveat.** Output produced in a state is not income received by its "
            "residents, and an average says nothing about distribution. Growth "
            "across the 2010-11/2011-12 boundary depends on the link factor. "
            "Jammu & Kashmir is not in the spliced file (its territory changed "
            "in 2019). The source has no all-India row, so there is no national "
            "benchmark for this series."
        ),
    ),
    "nsdp_pc_current_rbi": Indicator(
        key="nsdp_pc_current_rbi",
        label="Per-capita NSDP, current prices (RBI, newer vintage)",
        unit="₹",
        source="RBI DBIE Handbook -- per-capita NSDP at current prices (screenshot transcription)",
        source_file="data/raw/rbi_handbook/nsdp_current_prices_by_state_2011_12_to_2024_25.csv",
        status="PARTIAL",
        price_basis="current",
        explainer=(
            "**What it measures.** Net State Domestic Product per person at "
            "*current* (nominal) prices -- not adjusted for inflation, so growth "
            "in this series mixes real growth with price increases.\n\n"
            "**Period.** Annual, 2011-12 to 2024-25, 31 states/UTs. 2024-25 is "
            "blank in the source for 14 of them (estimates not yet released).\n\n"
            "**Caveat.** Transcribed by AI vision from a screenshot of the RBI "
            "table (status PARTIAL). **Delhi and Puducherry are missing**: their "
            "rows showed 13 values for 14 years, so the transcription kept them "
            "unmerged rather than guessing which year was absent. Bihar's rows "
            "carry a CHECK flag (conflict with the older-vintage file). Do not "
            "compare levels directly with the constant-price series. The source "
            "has no all-India row, so there is no national benchmark here."
        ),
    ),
    "gsdp_pc_current_old": Indicator(
        key="gsdp_pc_current_old",
        label="Per-capita GSDP, current prices (older-vintage file)",
        unit="₹",
        source=_GSDP_SOURCE,
        source_file=_GSDP_FILE,
        status="PARTIAL",
        price_basis="current",
        explainer=(
            "**What it measures.** *Gross* State Domestic Product per person at "
            "current prices -- like NSDP but before subtracting depreciation "
            "(consumption of fixed capital), so it is always somewhat higher.\n\n"
            "**Period.** 2023-24 and 2024-25. The file includes an 'India' row, "
            "used here as the national benchmark exactly as given.\n\n" + _GSDP_CAVEAT
        ),
    ),
    "gsdp_pc_constant_old": Indicator(
        key="gsdp_pc_constant_old",
        label="Per-capita GSDP, constant prices (older-vintage file)",
        unit="₹",
        source=_GSDP_SOURCE,
        source_file=_GSDP_FILE,
        status="PARTIAL",
        price_basis="constant",
        explainer=(
            "**What it measures.** Gross State Domestic Product per person at "
            "constant prices (inflation removed).\n\n"
            "**Period.** 2023-24 and 2024-25, with an 'India' row used as the "
            "national benchmark exactly as given.\n\n" + _GSDP_CAVEAT
        ),
    ),
    "nsdp_pc_current_old": Indicator(
        key="nsdp_pc_current_old",
        label="Per-capita NSDP, current prices (older-vintage file)",
        unit="₹",
        source=_GSDP_SOURCE,
        source_file=_GSDP_FILE,
        status="PARTIAL",
        price_basis="current",
        explainer=(
            "**What it measures.** The same concept as the RBI current-price "
            "NSDP series above, from a different (older) release.\n\n"
            "**Period.** 2023-24 and 2024-25, with an 'India' row used as the "
            "national benchmark exactly as given.\n\n"
            "**Why it is shown separately.** The two vintages disagree slightly; "
            "DATA_REGISTRY.md treats the newer RBI table as the current record "
            "but keeps this one, and neither is marked superseded. They are kept "
            "as two indicators so the disagreement is visible, not averaged "
            "away.\n\n" + _GSDP_CAVEAT
        ),
    ),
    "nsdp_pc_constant_old": Indicator(
        key="nsdp_pc_constant_old",
        label="Per-capita NSDP, constant prices (older-vintage file)",
        unit="₹",
        source=_GSDP_SOURCE,
        source_file=_GSDP_FILE,
        status="PARTIAL",
        price_basis="constant",
        explainer=(
            "**What it measures.** Net State Domestic Product per person at "
            "constant prices.\n\n"
            "**Period.** 2023-24 and 2024-25, with an 'India' row used as the "
            "national benchmark exactly as given.\n\n"
            "**Not joined to the spliced series.** These later years are not "
            "appended to the spliced 2004-05 to 2022-23 series: they come from "
            "a different file and release, and chaining them would create a "
            "series that no source publishes.\n\n" + _GSDP_CAVEAT
        ),
    ),
    "plfs_unemployment": Indicator(
        key="plfs_unemployment",
        label="Unemployment rate, usual status, 15+ (PLFS)",
        unit="%",
        source="Periodic Labour Force Survey 2023-24 (MoSPI) -- exact report table not confirmed",
        source_file="data/raw/plfs_unemployment_rate_by_state_2023_24.csv",
        status="PARTIAL",
        price_basis="n/a",
        explainer=(
            "**What it measures.** Share of the labour force aged 15+ that is "
            "available for and seeking work but has none, under the 'usual "
            "status' definition (365-day reference period).\n\n"
            "**Period.** One survey year, 2023-24, 28 states plus Delhi -- a "
            "snapshot, not a trend. The file's 'India' row is the national "
            "benchmark.\n\n"
            "**Caveat.** Higher is not 'better' or 'worse' on its own: a low rate "
            "can coexist with widespread informal or under-employment, because "
            "few people can afford to be formally jobless. People not seeking "
            "work are outside the labour force, not unemployed. The exact PLFS "
            "table is not confirmed (status PARTIAL)."
        ),
    ),
    "hces_urban_mpce": Indicator(
        key="hces_urban_mpce",
        label="Urban MPCE -- monthly per-capita consumption spending (HCES)",
        unit="₹/month",
        source="MoSPI HCES 2023-24 Statement 7",
        source_file="data/raw/hces/state_ut_urban_mpce_2023_24.csv",
        status="VERIFIED",
        price_basis="current",
        explainer=(
            "**What it measures.** Average monthly per-capita *consumption "
            "expenditure* of urban households -- what people spend, not what "
            "they earn.\n\n"
            "**Period.** One survey year, 2023-24, all 36 states/UTs, urban "
            "sector only. The file's 'All-India' row is the national "
            "benchmark.\n\n"
            "**Caveat.** This is **consumption, not income**, and **urban only**. "
            "The source file says so on every row: \"Use only as an urban "
            "state/UT consumption proxy; do not label as city household "
            "income.\" Rural households, often the majority of a state's "
            "population, are not in this number."
        ),
    ),
}

PANEL_COLUMNS = ["state", "indicator", "period", "value", "unit", "source", "status", "note"]

# Why a state that exists elsewhere is absent from a particular source,
# taken from DATA_REGISTRY.md. Used to explain "no data" precisely.
SOURCE_ABSENCE_REASONS: dict[str, dict[str, str]] = {
    "nsdp_pc_current_rbi": {
        "Delhi": "row transcribed with 13 of 14 values -- kept unmerged in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv, not guessed",
        "Puducherry": "row transcribed with 13 of 14 values -- kept unmerged in nsdp_current_prices_delhi_puducherry_UNALIGNED.csv, not guessed",
    },
    "nsdp_pc_constant_spliced": {
        "Jammu & Kashmir": "not in the spliced file -- RBI Table 26 reports J&K under two territorial definitions (incl. Ladakh to 2018-19; UT from 2019-20)",
    },
}

_GSDP_COLUMNS = {
    "gsdp_pc_current": "gsdp_pc_current_old",
    "gsdp_pc_constant": "gsdp_pc_constant_old",
    "nsdp_pc_current": "nsdp_pc_current_old",
    "nsdp_pc_constant": "nsdp_pc_constant_old",
}

_DELHI_GSDP_NOTE = "row blanked in this file (malformed in the original upload) -- see DATA_REGISTRY.md"


# ---------------------------------------------------------------------------
# 3. Building the panel
# ---------------------------------------------------------------------------

def fiscal_year_start(period: str) -> int:
    """'2011-12' -> 2011. Raises ValueError for anything else."""
    m = re.fullmatch(r"\s*(\d{4})-(\d{2})\s*", str(period))
    if not m:
        raise ValueError(f"not a financial year: {period!r}")
    return int(m.group(1))


def _to_number(cell: object) -> float:
    """Blank (incl. a lone space, as in the GSDP file) -> NaN. Anything
    else must parse as a number -- an unparseable cell raises rather than
    silently becoming NaN."""
    if cell is None or (isinstance(cell, float) and np.isnan(cell)):
        return float("nan")
    s = str(cell).strip().replace(",", "")
    if s in ("", "-"):
        return float("nan")
    return float(s)


def malformed_rows(path) -> dict[str, int]:
    """{first field: field count} for every row whose field count differs
    from the header's, read with the csv module (pandas would silently pad
    a short row with NaN)."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for row in reader:
            if row and len(row) != len(header):
                out[row[0]] = len(row)
    return out


def _rows(state, indicator, period, value, note="") -> dict:
    meta = INDICATORS[indicator]
    return {
        "state": state, "indicator": indicator, "period": period, "value": value,
        "unit": meta.unit, "source": meta.source, "status": meta.status, "note": note,
    }


def _blank_note(value: float, note: str) -> str:
    if np.isnan(value) and not note:
        return "blank in source"
    return note


def _raw_rows() -> list[dict]:
    """Every observation (states and national rows) from every source,
    canonical names, NaN for blank cells. National rows carry
    state == NATIONAL."""
    rows: list[dict] = []

    # Spliced constant-price NSDP.
    sp = loaders.load_nsdp_spliced()
    for r in sp.itertuples(index=False):
        v = _to_number(r.percapita_nsdp_constant_prices_inr_SPLICED)
        rows.append(_rows(normalise_state(r.state), "nsdp_pc_constant_spliced", r.financial_year, v,
                          _blank_note(v, str(r.method))))

    # Current-price NSDP, RBI screenshot.
    cur = loaders.load_nsdp_current()
    for r in cur.itertuples(index=False):
        v = _to_number(r.percapita_nsdp_current_prices_inr)
        flag = r.transcription_flag if isinstance(r.transcription_flag, str) else ""
        rows.append(_rows(normalise_state(r.state), "nsdp_pc_current_rbi", r.financial_year, v,
                          _blank_note(v, flag)))

    # Older-vintage GSDP/NSDP file.
    gs = loaders.load_state_gsdp_nsdp_percapita()
    bad = malformed_rows(loaders.RAW_DIR / "state_gsdp_nsdp_percapita.csv")
    n_header = gs.shape[1]
    for _, r in gs.iterrows():
        raw_name = r["state"]
        state = normalise_state(raw_name)
        for col in gs.columns:
            if col == "state":
                continue
            m = re.fullmatch(r"(.+)_(\d{4})_(\d{2})", col)
            prefix, period = m.group(1), f"{m.group(2)}-{m.group(3)}"
            ind = _GSDP_COLUMNS[prefix]
            if raw_name in bad:
                v = float("nan")
                note = (f"row has {bad[raw_name]} fields vs {n_header} in the header -- values cannot be "
                        "placed in columns with certainty, so excluded rather than realigned")
            else:
                v = _to_number(r[col])
                note = _DELHI_GSDP_NOTE if (state == "Delhi" and np.isnan(v)) else _blank_note(v, "")
            rows.append(_rows(state, ind, period, v, note))

    # PLFS.
    pl = loaders.load_unemployment_by_state()
    for r in pl.itertuples(index=False):
        v = _to_number(r.unemployment_rate_usual_status_15plus_2023_24)
        rows.append(_rows(normalise_state(r.state), "plfs_unemployment", "2023-24", v, _blank_note(v, "")))

    # HCES urban MPCE.
    hc = loaders.load_hces_urban_mpce()
    for r in hc.itertuples(index=False):
        v = _to_number(r.average_monthly_per_capita_consumption_expenditure_inr)
        rows.append(_rows(normalise_state(r.state_ut), "hces_urban_mpce", str(r.survey_year), v,
                          _blank_note(v, "")))
    return rows


def build_panel() -> pd.DataFrame:
    """Long panel of every state-level observation: one row per (state,
    indicator, period). Columns: state, indicator, period, value, unit,
    source, status, note. National rows are excluded (see
    `national_benchmarks()`); blank source cells are kept as NaN rows with
    a note -- never as 0. Raises if any state name fails to normalise."""
    df = pd.DataFrame(_raw_rows(), columns=PANEL_COLUMNS)
    if df["state"].isna().any():
        raise ValueError("unrecognised state names in source files -- see analysis.states.unmatched_names")
    df = df[df["state"] != NATIONAL]
    return df.sort_values(["indicator", "state", "period"]).reset_index(drop=True)


def national_benchmarks() -> pd.DataFrame:
    """National values exactly as the sources give them ("India" /
    "All-India" rows). Columns: indicator, period, value, source_label.
    Indicators with no national row in their source are simply absent."""
    df = pd.DataFrame(_raw_rows(), columns=PANEL_COLUMNS)
    nat = df[(df["state"] == NATIONAL) & df["value"].notna()].copy()
    labels = {
        "plfs_unemployment": "India (PLFS file)",
        "hces_urban_mpce": "All-India (HCES file)",
    }
    nat["source_label"] = nat["indicator"].map(labels).fillna("India (state_gsdp_nsdp_percapita.csv)")
    return nat[["indicator", "period", "value", "source_label"]].reset_index(drop=True)


NO_BENCHMARK = "no national benchmark in source"


def benchmark_for(benchmarks: pd.DataFrame, indicator: str, period: str) -> Optional[float]:
    hit = benchmarks[(benchmarks["indicator"] == indicator) & (benchmarks["period"] == period)]
    return None if hit.empty else float(hit["value"].iloc[0])


# ---------------------------------------------------------------------------
# 4. Lookups and descriptive calculations
# ---------------------------------------------------------------------------

def states_in_panel(panel: pd.DataFrame) -> list[str]:
    """Every canonical state with at least one non-blank value."""
    return sorted(panel.loc[panel["value"].notna(), "state"].unique().tolist())


def periods_for(panel: pd.DataFrame, indicator: str) -> list[str]:
    p = panel.loc[(panel["indicator"] == indicator) & panel["value"].notna(), "period"].unique()
    return sorted(p, key=fiscal_year_start)


def missing_reason(panel: pd.DataFrame, state: str, indicator: str, period: Optional[str] = None) -> str:
    """Plain-language reason a (state, indicator[, period]) has no value."""
    sub = panel[(panel["state"] == state) & (panel["indicator"] == indicator)]
    if sub.empty:
        special = SOURCE_ABSENCE_REASONS.get(indicator, {}).get(state)
        return special or "state not in source table"
    if period is not None:
        cell = sub[sub["period"] == period]
        if cell.empty:
            return f"no {period} row in source"
        if cell["value"].isna().all():
            return cell["note"].iloc[0] or "blank in source"
        return ""
    if sub["value"].isna().all():
        return sub["note"].iloc[0] or "blank in source"
    return ""


def rank_states(panel: pd.DataFrame, indicator: str, period: str, ascending: bool = False,
                states: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Rank states by value for one indicator and period. Rank 1 = highest
    value (or lowest when ``ascending``); ties share the lower rank.
    States with no value are kept at the bottom with rank NaN and a
    reason -- never dropped. ``states`` defaults to every state in the
    panel. Columns: rank, state, value, status, note, n_reporting."""
    universe = list(states) if states is not None else states_in_panel(panel)
    sub = panel[(panel["indicator"] == indicator) & (panel["period"] == period)]
    sub = sub.drop_duplicates("state").set_index("state")
    rows = []
    for s in universe:
        if s in sub.index and pd.notna(sub.at[s, "value"]):
            rows.append({"state": s, "value": float(sub.at[s, "value"]), "status": sub.at[s, "status"],
                         "note": sub.at[s, "note"]})
        else:
            rows.append({"state": s, "value": np.nan, "status": INDICATORS[indicator].status,
                         "note": missing_reason(panel, s, indicator, period)})
    out = pd.DataFrame(rows, columns=["state", "value", "status", "note"])
    reporting = out["value"].notna()
    out["rank"] = out["value"].rank(ascending=ascending, method="min")
    out["n_reporting"] = int(reporting.sum())
    out = pd.concat([
        out[reporting].sort_values(["rank", "state"]),
        out[~reporting].sort_values("state"),
    ])
    return out[["rank", "state", "value", "status", "note", "n_reporting"]].reset_index(drop=True)


def latest_for_state(panel: pd.DataFrame, state: str, indicator: str) -> Optional[dict]:
    """The state's most recent non-blank observation, or None."""
    sub = panel[(panel["state"] == state) & (panel["indicator"] == indicator) & panel["value"].notna()]
    if sub.empty:
        return None
    sub = sub.assign(_y=sub["period"].map(fiscal_year_start)).sort_values("_y")
    r = sub.iloc[-1]
    return {"period": r["period"], "value": float(r["value"]), "status": r["status"], "note": r["note"]}


def state_profile(panel: pd.DataFrame, state: str, benchmarks: pd.DataFrame) -> pd.DataFrame:
    """One row per indicator for a state: latest value and period, rank
    among states reporting that period (1 = highest), the national
    benchmark for the same period if the source has one, and a reason when
    there is no data. Every indicator is present -- missing ones have
    value NaN."""
    rows = []
    for key, meta in INDICATORS.items():
        latest = latest_for_state(panel, state, key)
        base = {"indicator": key, "label": meta.label, "unit": meta.unit, "source": meta.source,
                "status": meta.status}
        if latest is None:
            rows.append({**base, "period": None, "value": np.nan, "rank": np.nan, "n_reporting": np.nan,
                         "benchmark": np.nan, "benchmark_note": "", "note": "",
                         "missing_reason": missing_reason(panel, state, key)})
            continue
        ranked = rank_states(panel, key, latest["period"])
        rank = ranked.loc[ranked["state"] == state, "rank"].iloc[0]
        bm = benchmark_for(benchmarks, key, latest["period"])
        rows.append({**base, "period": latest["period"], "value": latest["value"], "rank": rank,
                     "n_reporting": int(ranked["n_reporting"].iloc[0]),
                     "benchmark": np.nan if bm is None else bm,
                     "benchmark_note": "" if bm is not None else NO_BENCHMARK,
                     "note": latest["note"], "missing_reason": ""})
    return pd.DataFrame(rows)


def compare_states(panel: pd.DataFrame, states: list[str], indicators: list[str],
                   basis: str = "common") -> pd.DataFrame:
    """Side-by-side values for every (state, indicator) pair requested --
    missing pairs are rows with value NaN and a reason, never dropped.

    basis="common": for each indicator, the latest period in which at least
    one of the chosen states reports, used for all of them (like-for-like).
    basis="own_latest": each state's own most recent observation (periods
    may differ between states; the period column says which)."""
    if basis not in ("common", "own_latest"):
        raise ValueError("basis must be 'common' or 'own_latest'")
    rows = []
    for ind in indicators:
        meta = INDICATORS[ind]
        sub = panel[(panel["indicator"] == ind) & panel["state"].isin(states) & panel["value"].notna()]
        common = max(sub["period"], key=fiscal_year_start) if not sub.empty else None
        for s in states:
            base = {"state": s, "indicator": ind, "label": meta.label, "unit": meta.unit,
                    "source": meta.source, "status": meta.status}
            if basis == "own_latest":
                latest = latest_for_state(panel, s, ind)
                if latest is None:
                    rows.append({**base, "period": None, "value": np.nan,
                                 "note": "no data: " + missing_reason(panel, s, ind)})
                else:
                    rows.append({**base, "period": latest["period"], "value": latest["value"],
                                 "note": latest["note"]})
            else:
                if common is None:
                    rows.append({**base, "period": None, "value": np.nan,
                                 "note": "no data: " + missing_reason(panel, s, ind)})
                    continue
                cell = sub[(sub["state"] == s) & (sub["period"] == common)]
                if cell.empty:
                    rows.append({**base, "period": common, "value": np.nan,
                                 "note": "no data: " + missing_reason(panel, s, ind, common)})
                else:
                    rows.append({**base, "period": common, "value": float(cell["value"].iloc[0]),
                                 "note": cell["note"].iloc[0]})
    return pd.DataFrame(rows, columns=["state", "indicator", "label", "period", "value", "unit",
                                       "status", "source", "note"])


def cagr(first: float, last: float, years: float) -> tuple[float, str]:
    """Compound annual growth rate in % and an empty reason, or (NaN,
    reason) when CAGR is not mathematically defined."""
    if first is None or last is None or pd.isna(first) or pd.isna(last):
        return float("nan"), "missing endpoint"
    if years <= 0:
        return float("nan"), "endpoints in the same year"
    if first <= 0 or last <= 0:
        return float("nan"), "non-positive endpoint (CAGR undefined)"
    return ((last / first) ** (1.0 / years) - 1.0) * 100.0, ""


def historical_change(panel: pd.DataFrame, indicator: str, states: list[str], start: str, end: str,
                      strict: bool = False) -> pd.DataFrame:
    """First vs latest observation inside [start, end] for each state.

    strict=False: each state's own first and last non-blank observation in
    the window (they may be inside the window bounds -- the period columns
    say which). strict=True: only the exact ``start`` and ``end`` periods;
    a state missing either gets no change figures and a reason.

    Every requested state is returned. Columns: state, first_period,
    first_value, last_period, last_value, change, pct_change, years,
    cagr_pct, note."""
    y0, y1 = fiscal_year_start(start), fiscal_year_start(end)
    if y1 < y0:
        y0, y1 = y1, y0
    sub = panel[(panel["indicator"] == indicator) & panel["value"].notna()].copy()
    sub["_y"] = sub["period"].map(fiscal_year_start)
    sub = sub[(sub["_y"] >= y0) & (sub["_y"] <= y1)]
    rows = []
    for s in states:
        ss = sub[sub["state"] == s].sort_values("_y")
        if strict:
            ss = ss[ss["_y"].isin([y0, y1])]
        row = {"state": s, "first_period": None, "first_value": np.nan, "last_period": None,
               "last_value": np.nan, "change": np.nan, "pct_change": np.nan, "years": np.nan,
               "cagr_pct": np.nan, "note": ""}
        if ss.empty:
            row["note"] = "no data in window: " + missing_reason(panel, s, indicator)
            rows.append(row)
            continue
        f, l = ss.iloc[0], ss.iloc[-1]
        if strict and not (f["_y"] == y0 and l["_y"] == y1):
            missing = start if f["_y"] != y0 else end
            row["note"] = f"no value at {missing}: " + missing_reason(panel, s, indicator, missing)
            rows.append(row)
            continue
        row.update(first_period=f["period"], first_value=float(f["value"]),
                   last_period=l["period"], last_value=float(l["value"]))
        years = int(l["_y"] - f["_y"])
        row["years"] = years
        if years == 0:
            row["note"] = "only one observation in window"
            rows.append(row)
            continue
        row["change"] = row["last_value"] - row["first_value"]
        if row["first_value"] != 0:
            row["pct_change"] = row["change"] / row["first_value"] * 100.0
        row["cagr_pct"], reason = cagr(row["first_value"], row["last_value"], years)
        row["note"] = reason
        rows.append(row)
    return pd.DataFrame(rows)


def inventory(panel: pd.DataFrame, benchmarks: pd.DataFrame) -> pd.DataFrame:
    """One row per indicator: label, period range, number of periods,
    number of states/UTs with at least one value, status, source, file,
    benchmark availability -- all computed from the panel, not typed."""
    rows = []
    for key, meta in INDICATORS.items():
        p = periods_for(panel, key)
        sub = panel[(panel["indicator"] == key) & panel["value"].notna()]
        has_bm = not benchmarks[benchmarks["indicator"] == key].empty
        rows.append({
            "indicator": key, "label": meta.label, "unit": meta.unit,
            "first_period": p[0] if p else None, "last_period": p[-1] if p else None,
            "n_periods": len(p), "n_states": sub["state"].nunique(), "status": meta.status,
            "source": meta.source, "source_file": meta.source_file,
            "national_benchmark": "yes (from source)" if has_bm else NO_BENCHMARK,
        })
    return pd.DataFrame(rows)


def format_value(value: float, unit: str) -> str:
    """'no data' for NaN (never 0); Indian digit grouping for rupees."""
    if value is None or pd.isna(value):
        return "no data"
    if unit == "%":
        return f"{value:.1f}%"
    neg = value < 0
    n = int(round(abs(value)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1]
        s = f"{head},{tail}"
    s = ("-" if neg else "") + "₹" + s
    return s + ("/month" if unit == "₹/month" else "")
