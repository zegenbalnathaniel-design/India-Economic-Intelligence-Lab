"""World Bank World Development Indicators (WDI) provider -- API v2, stdlib only.

Live provider for India's annual macro series and a small set of peer
economies. Nothing in this module ships, caches or substitutes data: every
value comes from a live call to the World Bank API, and any failure
(timeout, network error, HTTP error, an API error message, or a payload
that does not match the documented schema) raises a typed
`WorldBankError` subclass. Callers must show *no data* on failure -- never
stale or placeholder numbers (see DATA_REGISTRY.md).

Design notes
------------
* **Stdlib only** (`urllib`, `json`): no new dependency in requirements.txt.
* **Streamlit-free**: caching (`st.cache_data`) lives in the page layer, so
  this module stays unit-testable without a Streamlit runtime.
* **Strict parsing** against the documented v2 JSON schema::

      GET https://api.worldbank.org/v2/country/{ISO3;ISO3...}/indicator/{CODE}
          ?format=json&per_page=20000&date=YYYY:YYYY

  returns ``[ {page, pages, per_page, total, sourceid, lastupdated},
  [ {indicator:{id,value}, country:{id,value}, countryiso3code, date,
  value, unit, obs_status, decimal}, ... ] ]``; an error returns
  ``[ {"message": [ {id, key, value} ]} ]``.
* **Missing is not zero**: a JSON ``null`` value stays ``NaN``.
* WDI series used here are **annual**; `date` must be a four-digit year.
"""
from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

BASE_URL = "https://api.worldbank.org/v2"
DEFAULT_TIMEOUT_S = 20.0
PER_PAGE = 20000
MAX_PAGES = 50  # hard stop against a malformed `pages` field looping forever
USER_AGENT = "India-Economic-Intelligence-Lab/1.0 (+https://streamlit.io; WDI API v2 client)"

SOURCE_NAME = "World Bank WDI"

# Change semantics used by `latest_vs_previous`:
#   "pp"     -- series is already a percent/rate: report a percentage-point
#               change only (a % change of a % is misleading).
#   "points" -- an index with its own scale (e.g. Gini 0-100): report a
#               point change only.
#   "level"  -- a strictly positive level/stock/price: absolute change plus
#               a % change (only when the previous value is > 0).
CHANGE_KINDS = ("pp", "points", "level")

TIDY_COLUMNS = [
    "country", "iso3", "indicator", "indicator_name", "year", "value",
    "lastupdated", "retrieved_at",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class WorldBankError(RuntimeError):
    """Base class for every failure fetching or parsing WDI data."""


class WorldBankTimeoutError(WorldBankError):
    """The request timed out (connect or read)."""


class WorldBankConnectionError(WorldBankError):
    """The host could not be reached (DNS, refused, proxy, TLS...)."""


class WorldBankHTTPError(WorldBankError):
    """The API answered with a non-2xx HTTP status."""

    def __init__(self, status: int, reason: str, url: str):
        super().__init__(f"HTTP {status} {reason} from {url}")
        self.status = status
        self.reason = reason
        self.url = url


class WorldBankAPIError(WorldBankError):
    """The API answered 200 but with its documented error-message payload."""

    def __init__(self, messages: list[dict[str, Any]], url: str | None = None):
        parts = [
            f"[{m.get('id', '?')}] {m.get('key', '')}: {m.get('value', '')}".strip()
            for m in messages
        ]
        where = f" ({url})" if url else ""
        super().__init__("World Bank API error: " + "; ".join(parts) + where)
        self.messages = messages
        self.url = url


class WorldBankSchemaError(WorldBankError):
    """The payload does not match the documented v2 JSON schema."""


# Errors that mean "the service is unreachable from here" (as opposed to a
# problem with one particular request); callers can back off on these.
NETWORK_ERRORS: tuple[type[WorldBankError], ...] = (
    WorldBankTimeoutError, WorldBankConnectionError,
)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Indicator:
    code: str
    label: str
    unit: str
    change_kind: str          # one of CHANGE_KINDS
    definition: str           # plain-language, paraphrased from WDI metadata
    source_note: str          # provenance / comparability caveat

    @property
    def url(self) -> str:
        return f"https://data.worldbank.org/indicator/{self.code}"


INDICATORS: dict[str, Indicator] = {i.code: i for i in [
    Indicator(
        "NY.GDP.MKTP.KD.ZG", "Real GDP growth", "% per year", "pp",
        "Annual percentage growth of gross domestic product at market prices, "
        "based on constant local currency (i.e. after removing price changes).",
        "WDI national accounts (World Bank and OECD national accounts files). "
        "India's national accounts are compiled on an April-March fiscal-year "
        "basis; check the WDI country metadata for how each fiscal year maps "
        "to the year label shown.",
    ),
    Indicator(
        "NY.GDP.PCAP.PP.KD", "GDP per capita, PPP", "constant international $", "level",
        "GDP divided by mid-year population, converted to international dollars "
        "with purchasing-power-parity (PPP) rates, in constant prices. An "
        "international dollar buys roughly what a US dollar buys in the US.",
        "WDI / International Comparison Program (ICP). The PPP base year "
        "follows the ICP round used by the current WDI release -- the API's "
        "indicator name (shown with the data) states it. PPP levels are "
        "revised when a new ICP round is adopted.",
    ),
    Indicator(
        "FP.CPI.TOTL.ZG", "CPI inflation", "% per year", "pp",
        "Annual percentage change in the cost to the average consumer of a "
        "basket of goods and services, as measured by the consumer price index.",
        "WDI (IMF International Financial Statistics). The national CPI series "
        "WDI uses for India may not be MOSPI's headline CPI (Combined) that the "
        "RBI targets, and annual averages differ from monthly year-on-year "
        "prints -- compare with MOSPI before quoting.",
    ),
    Indicator(
        "SL.UEM.TOTL.ZS", "Unemployment (ILO modelled)", "% of labour force", "pp",
        "Share of the labour force that is without work but available for and "
        "seeking employment -- an ILO modelled estimate, harmonised across "
        "countries.",
        "ILO modelled estimates via WDI. This is NOT the PLFS rate published by "
        "MOSPI (shown on the State Economy Lab); modelled estimates are "
        "revised and can differ materially from national survey figures.",
    ),
    Indicator(
        "BN.CAB.XOKA.GD.ZS", "Current account balance", "% of GDP", "pp",
        "Net exports of goods and services plus net primary income plus net "
        "secondary income, as a share of GDP. Negative = current-account deficit.",
        "WDI (IMF Balance of Payments statistics and World Bank GDP). Calendar- "
        "vs fiscal-year treatment can differ from RBI's own BoP releases.",
    ),
    Indicator(
        "FI.RES.TOTL.CD", "Total reserves (incl. gold)", "current US$", "level",
        "Holdings of monetary gold, special drawing rights, reserve position in "
        "the IMF and foreign exchange under the control of monetary "
        "authorities -- an end-of-period stock, in current US dollars.",
        "WDI (IMF International Financial Statistics). An annual end-of-period "
        "figure; it will not match RBI's latest weekly reserves release, and "
        "dollar values move with gold prices and cross-currency valuation.",
    ),
    Indicator(
        "PA.NUS.FCRF", "Official exchange rate", "local currency per US$ (period average)", "level",
        "Exchange rate determined by national authorities or the legally "
        "sanctioned market, as an annual average of monthly rates, in local "
        "currency units per US dollar. For India a higher number means a weaker "
        "rupee.",
        "WDI (IMF International Financial Statistics). Levels are in each "
        "country's own currency, so they are not comparable across countries -- "
        "only the direction and pace of change are.",
    ),
    Indicator(
        "NE.TRD.GNFS.ZS", "Trade openness", "% of GDP", "pp",
        "Sum of exports and imports of goods and services, as a share of GDP.",
        "WDI national accounts. A ratio of flows to GDP: large economies "
        "structurally trade less relative to GDP than small ones.",
    ),
    Indicator(
        "NE.EXP.GNFS.ZS", "Exports of goods & services", "% of GDP", "pp",
        "Value of all goods and market services provided to the rest of the "
        "world, as a share of GDP.",
        "WDI national accounts.",
    ),
    Indicator(
        "NE.IMP.GNFS.ZS", "Imports of goods & services", "% of GDP", "pp",
        "Value of all goods and market services received from the rest of the "
        "world, as a share of GDP.",
        "WDI national accounts.",
    ),
    Indicator(
        "GC.DOD.TOTL.GD.ZS", "Central government debt", "% of GDP", "pp",
        "Gross stock of the central government's outstanding direct, fixed-term "
        "contractual obligations, as a share of GDP.",
        "WDI (IMF Government Finance Statistics). Central government only -- "
        "for India this excludes state-government debt, so it is well below "
        "general-government debt. WDI coverage for some countries, possibly "
        "including India, is sparse or absent; gaps are shown as gaps.",
    ),
    Indicator(
        "SI.POV.GINI", "Gini index", "index, 0-100", "points",
        "Extent to which the distribution of income or consumption across "
        "individuals deviates from perfect equality: 0 = perfect equality, "
        "100 = one person has everything.",
        "World Bank Poverty and Inequality Platform via WDI. Available only "
        "for survey years. Some countries' estimates are based on consumption "
        "surveys (India's are) and others on income surveys; income-based "
        "Ginis tend to be higher, so cross-country comparisons mix definitions.",
    ),
]}

# Short, fixed list of comparators offered in the UI (ISO3 -> display name).
# Names shown in charts come from the API response, not from this table.
PEER_COUNTRIES: dict[str, str] = {
    "CHN": "China",
    "IDN": "Indonesia",
    "BRA": "Brazil",
    "BGD": "Bangladesh",
    "VNM": "Viet Nam",
    "PHL": "Philippines",
    "THA": "Thailand",
    "MYS": "Malaysia",
    "MEX": "Mexico",
    "ZAF": "South Africa",
    "TUR": "Türkiye",
    "KOR": "Korea, Rep.",
    "USA": "United States",
}
DEFAULT_PEERS: tuple[str, ...] = ("CHN", "IDN", "BRA")
INDIA = "IND"


def source_label(code: str) -> str:
    return f"{SOURCE_NAME} ({code})"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def build_url(code: str, countries: Sequence[str], start: int, end: int, page: int = 1) -> str:
    if not countries:
        raise ValueError("at least one country code is required")
    if int(start) > int(end):
        raise ValueError(f"start year {start} is after end year {end}")
    country_part = ";".join(urllib.parse.quote(c.strip().upper(), safe="") for c in countries)
    query = urllib.parse.urlencode({
        "format": "json",
        "per_page": PER_PAGE,
        "date": f"{int(start)}:{int(end)}",
        "page": int(page),
    })
    return f"{BASE_URL}/country/{country_part}/indicator/{urllib.parse.quote(code, safe='.')}?{query}"


def _is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, socket.timeout))


def _http_get_json(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> Any:
    """GET `url` and decode JSON, mapping every failure to a typed error."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status is not None and not (200 <= int(status) < 300):
                raise WorldBankHTTPError(int(status), str(getattr(resp, "reason", "")), url)
            raw = resp.read()
    except WorldBankError:
        raise
    except urllib.error.HTTPError as exc:
        raise WorldBankHTTPError(exc.code, str(exc.reason), url) from exc
    except urllib.error.URLError as exc:
        if _is_timeout(exc.reason):
            raise WorldBankTimeoutError(f"Timed out after {timeout:g}s reaching {url}") from exc
        raise WorldBankConnectionError(f"Could not reach {url}: {exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise WorldBankTimeoutError(f"Timed out after {timeout:g}s reaching {url}") from exc
    except OSError as exc:
        raise WorldBankConnectionError(f"Could not reach {url}: {exc}") from exc

    try:
        text = raw.decode("utf-8-sig")  # the API has been seen to prepend a BOM
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        snippet = raw[:160].decode("utf-8", errors="replace")
        raise WorldBankSchemaError(f"Response from {url} is not JSON: {snippet!r}") from exc


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise WorldBankSchemaError(f"metadata field {field!r} is not an integer: {value!r}") from exc


def _parse_value(raw: Any) -> float:
    if raw is None:
        return math.nan  # missing stays missing -- never zero
    if isinstance(raw, bool):
        raise WorldBankSchemaError(f"observation value is a boolean: {raw!r}")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        if raw.strip() == "":
            return math.nan
        try:
            return float(raw)
        except ValueError as exc:
            raise WorldBankSchemaError(f"observation value is not numeric: {raw!r}") from exc
    raise WorldBankSchemaError(f"observation value has unexpected type: {type(raw).__name__}")


def parse_response(payload: Any, url: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate one v2 JSON page; return (metadata, observation rows).

    Raises `WorldBankAPIError` for the documented error payload and
    `WorldBankSchemaError` for anything else that does not match the schema.
    Each returned row has keys country, iso3, indicator, indicator_name,
    year (int), value (float, NaN when the API sent null).
    """
    if not isinstance(payload, list) or not payload:
        raise WorldBankSchemaError(f"expected a non-empty JSON array, got {type(payload).__name__}")

    head = payload[0]
    if isinstance(head, dict) and "message" in head:
        msgs = head["message"]
        if not isinstance(msgs, list):
            msgs = [{"id": "?", "key": "message", "value": str(msgs)}]
        raise WorldBankAPIError([m if isinstance(m, dict) else {"value": str(m)} for m in msgs], url)

    if len(payload) != 2:
        raise WorldBankSchemaError(f"expected a 2-element array [metadata, data], got {len(payload)} elements")
    if not isinstance(head, dict):
        raise WorldBankSchemaError("first element (metadata) is not an object")
    for key in ("page", "pages", "total"):
        if key not in head:
            raise WorldBankSchemaError(f"metadata is missing {key!r}")
    meta = {
        "page": _as_int(head["page"], "page"),
        "pages": _as_int(head["pages"], "pages"),
        "total": _as_int(head["total"], "total"),
        "lastupdated": head.get("lastupdated"),
        "sourceid": head.get("sourceid"),
    }

    data = payload[1]
    if data is None:  # the API sends null when a query matches no rows
        if meta["total"] != 0:
            raise WorldBankSchemaError(f"data is null but metadata reports total={meta['total']}")
        return meta, []
    if not isinstance(data, list):
        raise WorldBankSchemaError("second element (data) is not an array")

    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(data):
        if not isinstance(rec, dict):
            raise WorldBankSchemaError(f"observation {i} is not an object")
        for key in ("indicator", "country", "date", "value"):
            if key not in rec:
                raise WorldBankSchemaError(f"observation {i} is missing {key!r}")
        ind, ctry = rec["indicator"], rec["country"]
        if not isinstance(ind, dict) or "id" not in ind:
            raise WorldBankSchemaError(f"observation {i}: 'indicator' must be an object with 'id'")
        if not isinstance(ctry, dict) or "value" not in ctry:
            raise WorldBankSchemaError(f"observation {i}: 'country' must be an object with 'value'")
        date = str(rec["date"]).strip()
        if not (len(date) == 4 and date.isdigit()):
            raise WorldBankSchemaError(f"observation {i}: expected an annual 'date' (YYYY), got {rec['date']!r}")
        iso3 = (rec.get("countryiso3code") or ctry.get("id") or "").strip().upper()
        rows.append({
            "country": str(ctry["value"]),
            "iso3": iso3,
            "indicator": str(ind["id"]),
            "indicator_name": str(ind.get("value", "")),
            "year": int(date),
            "value": _parse_value(rec["value"]),
        })
    return meta, rows


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_one(code: str, countries: Sequence[str], start: int, end: int, timeout: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page, pages = 1, 1
    lastupdated = None
    while page <= pages:
        url = build_url(code, countries, start, end, page=page)
        meta, page_rows = parse_response(_http_get_json(url, timeout=timeout), url=url)
        retrieved = _utc_now_iso()
        pages = min(max(meta["pages"], 1), MAX_PAGES)
        lastupdated = meta["lastupdated"] if meta["lastupdated"] is not None else lastupdated
        for r in page_rows:
            r["lastupdated"] = lastupdated
            r["retrieved_at"] = retrieved
        rows.extend(page_rows)
        page += 1
    return rows


def fetch(
    codes: str | Iterable[str],
    countries: str | Iterable[str],
    start: int,
    end: int,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    max_workers: int = 4,
) -> pd.DataFrame:
    """Fetch annual WDI observations as a tidy DataFrame.

    One request per indicator (paged if needed), run with modest
    concurrency. **All-or-nothing**: the first failure raises its
    `WorldBankError` subclass and no partial frame is returned.

    Columns: country, iso3, indicator, indicator_name, year (int), value
    (float; NaN where the API reported null), lastupdated (the API's
    ``lastupdated`` metadata, str or None), retrieved_at (UTC ISO-8601 time
    the page was received). Sorted by indicator, iso3, year.
    """
    code_list = [codes] if isinstance(codes, str) else list(codes)
    country_list = [countries] if isinstance(countries, str) else list(countries)
    code_list = list(dict.fromkeys(c.strip() for c in code_list if c and c.strip()))
    country_list = list(dict.fromkeys(c.strip().upper() for c in country_list if c and c.strip()))
    if not code_list:
        raise ValueError("at least one indicator code is required")
    if not country_list:
        raise ValueError("at least one country code is required")

    all_rows: list[dict[str, Any]] = []
    if len(code_list) == 1 or max_workers <= 1:
        for code in code_list:
            all_rows.extend(_fetch_one(code, country_list, start, end, timeout))
    else:
        pool = ThreadPoolExecutor(max_workers=min(max_workers, len(code_list)))
        try:
            futures = [pool.submit(_fetch_one, c, country_list, start, end, timeout) for c in code_list]
            for fut in futures:  # in catalogue order; first error wins
                all_rows.extend(fut.result())
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    df = pd.DataFrame(all_rows, columns=TIDY_COLUMNS)
    df["year"] = df["year"].astype("int64")
    df["value"] = pd.to_numeric(df["value"], errors="raise").astype("float64")
    return df.sort_values(["indicator", "iso3", "year"], kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def change_kind_for(code: str, overrides: Mapping[str, str] | None = None) -> str:
    """Change semantics for an indicator; unknown codes get the conservative
    "points" (absolute change only, never a % change)."""
    if overrides and code in overrides:
        kind = overrides[code]
    elif code in INDICATORS:
        kind = INDICATORS[code].change_kind
    else:
        kind = "points"
    if kind not in CHANGE_KINDS:
        raise ValueError(f"unknown change kind {kind!r} for {code}")
    return kind


LVP_COLUMNS = [
    "iso3", "country", "indicator", "change_kind",
    "latest_year", "latest_value", "previous_year", "previous_value",
    "abs_change", "pp_change", "pct_change",
]


def latest_vs_previous(df: pd.DataFrame, change_kinds: Mapping[str, str] | None = None) -> pd.DataFrame:
    """Latest vs previous *non-null* observation per (iso3, indicator).

    * Null (NaN) observations are skipped, so "previous" may be several
      years before "latest" (survey-year series such as Gini).
    * `abs_change` = latest - previous, in the series' own unit.
    * `pp_change`  = abs_change for percent/rate series ("pp"), else NaN.
    * `pct_change` = 100 * (latest / previous - 1) only for "level" series
      with previous > 0; NaN otherwise (a % change of a rate, of an index
      in points, or from a zero/negative base is not meaningful).
    * Groups with no non-null observation are omitted; groups with exactly
      one keep NaN previous/changes.
    """
    if df.empty:
        return pd.DataFrame(columns=LVP_COLUMNS)
    obs = df.dropna(subset=["value"]).sort_values(["iso3", "indicator", "year"], kind="stable")
    out: list[dict[str, Any]] = []
    for (iso3, code), g in obs.groupby(["iso3", "indicator"], sort=True):
        kind = change_kind_for(str(code), change_kinds)
        last = g.iloc[-1]
        prev = g.iloc[-2] if len(g) >= 2 else None
        latest_value = float(last["value"])
        prev_value = float(prev["value"]) if prev is not None else math.nan
        abs_change = latest_value - prev_value if prev is not None else math.nan
        pp_change = abs_change if kind == "pp" else math.nan
        pct_change = math.nan
        if kind == "level" and prev is not None and prev_value > 0:
            pct_change = (latest_value / prev_value - 1.0) * 100.0
        out.append({
            "iso3": iso3,
            "country": last["country"],
            "indicator": code,
            "change_kind": kind,
            "latest_year": int(last["year"]),
            "latest_value": latest_value,
            "previous_year": int(prev["year"]) if prev is not None else pd.NA,
            "previous_value": prev_value,
            "abs_change": abs_change,
            "pp_change": pp_change,
            "pct_change": pct_change,
        })
    res = pd.DataFrame(out, columns=LVP_COLUMNS)
    res["previous_year"] = res["previous_year"].astype("Int64")
    return res
