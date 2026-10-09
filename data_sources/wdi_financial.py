"""World Bank WDI financial-inclusion and financial-depth series, fetched
one indicator at a time so that one failing code does not blank the page.

Reuses the stdlib provider in `data_sources.worldbank` (unchanged): every
value comes from a live API call; nothing is stored, cached on disk or
substituted. Unlike `worldbank.fetch`, which is all-or-nothing across
indicators, `fetch_each` returns a per-series status:

    OK                 -- at least one non-missing observation came back
    NO DATA RETURNED   -- the API answered, but every value was null or no
                          rows matched (e.g. a survey-only series outside
                          its survey years, or a code with no India data)
    API ERROR          -- the API answered with an error message, an HTTP
                          error or a payload that failed schema checks
                          (e.g. an unknown indicator code)
    UNREACHABLE        -- timeout / connection failure
    NOT ATTEMPTED      -- skipped because an earlier request found the host
                          unreachable (saves N x timeout when offline)

The caller decides how to cache (the page caches successful fetches only).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import pandas as pd

from data_sources import worldbank as WB

OK, NO_DATA, API_ERROR, UNREACHABLE, NOT_ATTEMPTED = (
    "OK", "NO DATA RETURNED", "API ERROR", "UNREACHABLE", "NOT ATTEMPTED")

_FINDEX_NOTE = (
    "Global Findex Database (World Bank), via WDI. A household survey run in "
    "survey years only (the API returns null in other years; those stay "
    "missing and are never filled). Account ownership counts whether an adult "
    "has an account, not how much is held in it or whether it is used."
)

INDICATORS: dict[str, WB.Indicator] = {i.code: i for i in [
    WB.Indicator(
        "FX.OWN.TOTL.ZS", "Account ownership, all adults", "% of population ages 15+", "pp",
        "Share of adults (15+) who report having an account, alone or with "
        "someone else, at a bank or another type of financial institution, or "
        "personally using a mobile-money service in the past 12 months.",
        _FINDEX_NOTE,
    ),
    WB.Indicator(
        "FX.OWN.TOTL.FE.ZS", "Account ownership, women", "% of female population ages 15+", "pp",
        "As for all adults, restricted to women aged 15+.",
        _FINDEX_NOTE,
    ),
    WB.Indicator(
        "FX.OWN.TOTL.40.ZS", "Account ownership, poorest 40%", "% of population ages 15+, poorest 40%", "pp",
        "Account ownership among adults in the poorest 40% of households, "
        "ranked by household income within the country (as defined by Findex).",
        _FINDEX_NOTE + " The income ranking is Findex's own, not WIL's.",
    ),
    WB.Indicator(
        "FX.OWN.TOTL.60.ZS", "Account ownership, richest 60%", "% of population ages 15+, richest 60%", "pp",
        "Account ownership among adults in the richest 60% of households, "
        "ranked by household income within the country (as defined by Findex).",
        _FINDEX_NOTE + " 'Richest 60%' is a broad group, not the top of the distribution.",
    ),
    WB.Indicator(
        "FS.AST.PRVT.GD.ZS", "Domestic credit to private sector", "% of GDP", "pp",
        "Financial resources provided to the private sector by financial "
        "corporations -- loans, purchases of non-equity securities, trade "
        "credit and other claims for repayment -- as a share of GDP.",
        "WDI (IMF International Financial Statistics and World Bank GDP). An "
        "aggregate stock-to-flow ratio: it measures financial depth, not who "
        "borrows.",
    ),
    WB.Indicator(
        "FD.AST.PRVT.GD.ZS", "Domestic credit to private sector by banks", "% of GDP", "pp",
        "Credit to the private sector from deposit-taking corporations other "
        "than the central bank, as a share of GDP.",
        "WDI (IMF International Financial Statistics). A subset of the series "
        "above; the difference is credit from non-bank financial corporations.",
    ),
    WB.Indicator(
        "CM.MKT.LCAP.GD.ZS", "Market capitalisation of listed domestic companies", "% of GDP", "pp",
        "Share price times shares outstanding for listed domestic companies, "
        "year-end, as a share of GDP (investment funds and pure holding "
        "companies excluded).",
        "WDI (World Federation of Exchanges database). Moves with share prices "
        "as much as with new listings; it says nothing about who owns the shares. "
        "WDI coverage for recent years may be incomplete -- gaps are shown as gaps.",
    ),
]}

ACCOUNT_CODES = ("FX.OWN.TOTL.ZS", "FX.OWN.TOTL.FE.ZS", "FX.OWN.TOTL.40.ZS", "FX.OWN.TOTL.60.ZS")
DEPTH_CODES = ("FS.AST.PRVT.GD.ZS", "FD.AST.PRVT.GD.ZS", "CM.MKT.LCAP.GD.ZS")
POOREST_40, RICHEST_60, MARKET_CAP = "FX.OWN.TOTL.40.ZS", "FX.OWN.TOTL.60.ZS", "CM.MKT.LCAP.GD.ZS"


@dataclass
class SeriesResult:
    code: str
    status: str
    frame: pd.DataFrame | None = None   # tidy WDI frame (worldbank.TIDY_COLUMNS) when OK
    error: str = ""

    @property
    def n_obs(self) -> int:
        if self.frame is None or self.frame.empty:
            return 0
        return int(self.frame["value"].notna().sum())


Fetcher = Callable[[str, tuple[str, ...], int, int], pd.DataFrame]


def _default_fetch(code: str, countries: tuple[str, ...], start: int, end: int) -> pd.DataFrame:
    return WB.fetch(code, countries, start, end)


def fetch_each(
    codes: Iterable[str],
    countries: Iterable[str] = (WB.INDIA,),
    start: int = 1990,
    end: int = 2030,
    *,
    fetch: Fetcher = _default_fetch,
    stop_on_unreachable: bool = True,
) -> dict[str, SeriesResult]:
    """Fetch each code separately; never raises a `WorldBankError`.

    Returns {code: SeriesResult} in input order. After the first
    UNREACHABLE result the remaining codes are NOT ATTEMPTED (when
    `stop_on_unreachable`), because the host -- not the code -- is the
    problem.
    """
    ctry = tuple(countries)
    out: dict[str, SeriesResult] = {}
    host_down = False
    for code in dict.fromkeys(codes):
        if host_down:
            out[code] = SeriesResult(code, NOT_ATTEMPTED, error="host unreachable on an earlier request")
            continue
        try:
            df = fetch(code, ctry, int(start), int(end))
        except WB.NETWORK_ERRORS as exc:
            out[code] = SeriesResult(code, UNREACHABLE, error=f"{type(exc).__name__}: {exc}")
            host_down = stop_on_unreachable
            continue
        except WB.WorldBankError as exc:
            out[code] = SeriesResult(code, API_ERROR, error=f"{type(exc).__name__}: {exc}")
            continue
        if df is None or df.empty or df["value"].notna().sum() == 0:
            out[code] = SeriesResult(code, NO_DATA, frame=df)
        else:
            out[code] = SeriesResult(code, OK, frame=df)
    return out


def status_table(results: dict[str, SeriesResult], iso3: str = WB.INDIA) -> pd.DataFrame:
    """One row per requested code: label, status, observations and the
    first/latest non-missing year for `iso3` -- no values are invented."""
    rows = []
    for code, r in results.items():
        meta = INDICATORS.get(code)
        first = latest = None
        if r.status == OK:
            s = r.frame[(r.frame["iso3"] == iso3)].dropna(subset=["value"])
            if not s.empty:
                first, latest = int(s["year"].min()), int(s["year"].max())
        rows.append({
            "code": code,
            "indicator": meta.label if meta else code,
            "status": r.status,
            "observations": r.n_obs,
            "first_year": first,
            "latest_year": latest,
            "detail": r.error,
        })
    out = pd.DataFrame(rows, columns=["code", "indicator", "status", "observations", "first_year",
                                      "latest_year", "detail"])
    for c in ("first_year", "latest_year"):
        out[c] = out[c].astype("Int64")
    return out


def all_unreachable(results: dict[str, SeriesResult]) -> bool:
    """True when no request reached the API (so nothing can be shown)."""
    return bool(results) and all(r.status in (UNREACHABLE, NOT_ATTEMPTED) for r in results.values())


def combined_frame(results: dict[str, SeriesResult]) -> pd.DataFrame:
    """All OK frames stacked (tidy), for display and CSV download."""
    frames = [r.frame for r in results.values() if r.status == OK and r.frame is not None]
    if not frames:
        return pd.DataFrame(columns=WB.TIDY_COLUMNS)
    return pd.concat(frames, ignore_index=True)
