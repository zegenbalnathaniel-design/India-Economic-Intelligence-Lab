"""Structural transformation and productivity: pure calculations.

Inputs are tidy World Bank WDI frames as returned by
`data_sources.worldbank.fetch` (columns country, iso3, indicator,
indicator_name, year, value, lastupdated, retrieved_at). Nothing here
fetches, stores or invents data, and nothing is interpolated: a value is
computed only from observations that exist for the *same* country and
*same* year, and anything else stays missing (NaN).

Definitions
-----------
* **Value-added share** of sector s: WDI "value added (% of GDP)". GDP is
  at market prices, i.e. gross value added (GVA) at basic prices *plus net
  taxes on products*, so the three sector shares do not sum to 100. The
  shortfall is reported, never silently rescaled away::

      va_sum      = VA_agr + VA_ind + VA_srv          (all three present)
      va_residual = 100 - va_sum                      (net taxes on products
                                                       and other adjustments)

* **Employment share** of sector s: ILO modelled estimate, % of total
  employment. The three shares should sum to ~100; the sum is reported.
* **Relative labour productivity** (RLP) of sector s::

      RLP_s = VA share_s / employment share_s

  = (sector value added per worker) / (GDP per worker). It is *relative to
  the economy average*, not an absolute productivity level. Because GDP
  includes net taxes, the employment-weighted average of the published
  ratios is va_sum / 100 (below 1), not exactly 1.
* **Rescaled** (labelled, optional): VA shares divided by va_sum and
  multiplied by 100, i.e. shares of the three-sector total. RLP on that
  basis is sector value added per worker relative to *total GVA per
  worker*. Ratios *between* sectors are identical on both bases.

Manufacturing (NV.IND.MANF.ZS) is a subset of industry and is never added
into the three-sector sum. WDI has no matching manufacturing-employment
series in this set (industry employment includes mining, construction and
utilities), so no manufacturing productivity ratio is computed.
"""
from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

import pandas as pd

from data_sources.worldbank import Indicator

# ---------------------------------------------------------------------------
# Indicator catalogue (WDI codes; definitions paraphrased from WDI metadata)
# ---------------------------------------------------------------------------
_NA_NOTE = (
    "WDI national accounts (World Bank and OECD national accounts files). Shares of GDP at "
    "market prices in current prices, so they move with relative prices as well as volumes. "
    "India's national accounts are compiled on an April-March fiscal year; check the WDI country "
    "metadata for how each fiscal year maps to the year label shown."
)
_ILO_NOTE = (
    "ILO modelled estimate (ILOSTAT, via WDI). Modelled to be comparable across countries and "
    "revised between releases; for India it is NOT the PLFS figure published by MoSPI and can "
    "differ materially from it, in level and in recent trend."
)

INDICATORS: dict[str, Indicator] = {i.code: i for i in [
    Indicator("NV.AGR.TOTL.ZS", "Agriculture, forestry & fishing value added", "% of GDP", "pp",
              "Net output of agriculture, forestry and fishing (ISIC divisions 1-3) after subtracting "
              "intermediate inputs, as a share of GDP.", _NA_NOTE),
    Indicator("NV.IND.TOTL.ZS", "Industry value added (incl. construction)", "% of GDP", "pp",
              "Net output of mining, manufacturing, construction, electricity, water and gas "
              "(ISIC divisions 5-43), as a share of GDP.", _NA_NOTE),
    Indicator("NV.IND.MANF.ZS", "Manufacturing value added", "% of GDP", "pp",
              "Net output of manufacturing (ISIC divisions 10-33), as a share of GDP. A subset of "
              "industry -- never added to the three-sector total.", _NA_NOTE),
    Indicator("NV.SRV.TOTL.ZS", "Services value added", "% of GDP", "pp",
              "Net output of services (trade, transport, finance, real estate, public administration "
              "and other services), as a share of GDP. See the WDI metadata page for exactly what "
              "each country's services aggregate includes.", _NA_NOTE),
    Indicator("SL.AGR.EMPL.ZS", "Employment in agriculture (ILO modelled)", "% of total employment", "pp",
              "Persons employed in agriculture, hunting, forestry and fishing, as a share of all "
              "employed persons.", _ILO_NOTE),
    Indicator("SL.IND.EMPL.ZS", "Employment in industry (ILO modelled)", "% of total employment", "pp",
              "Persons employed in mining, manufacturing, construction and utilities, as a share of "
              "all employed persons.", _ILO_NOTE),
    Indicator("SL.SRV.EMPL.ZS", "Employment in services (ILO modelled)", "% of total employment", "pp",
              "Persons employed in services (trade, transport, finance, public administration and "
              "other services), as a share of all employed persons.", _ILO_NOTE),
    Indicator("SL.TLF.CACT.FE.ZS", "Female labour force participation (ILO modelled)",
              "% of female population 15+", "pp",
              "Share of women aged 15 and over who are economically active: employed, or "
              "unemployed and seeking work.", _ILO_NOTE),
    Indicator("SL.TLF.CACT.MA.ZS", "Male labour force participation (ILO modelled)",
              "% of male population 15+", "pp",
              "Share of men aged 15 and over who are economically active: employed, or "
              "unemployed and seeking work.", _ILO_NOTE),
    Indicator("SL.GDP.PCAP.EM.KD", "GDP per person employed", "constant PPP $ (base year in API name)", "level",
              "GDP divided by total employment, converted with purchasing-power-parity rates to "
              "constant international dollars. An average output per worker -- not a wage.",
              "WDI (ILO employment and World Bank PPP GDP). Employment is the ILO modelled series, so "
              "the PPP base year and the employment estimates both change between releases; the "
              "API's indicator name, shown with the data, states the base year."),
    Indicator("SL.EMP.VULN.ZS", "Vulnerable employment (ILO modelled)", "% of total employment", "pp",
              "Own-account workers plus contributing family workers, as a share of all employed "
              "persons -- people less likely to have formal work arrangements or social protection.",
              _ILO_NOTE),
]}

CODES: tuple[str, ...] = tuple(INDICATORS)

SECTORS: dict[str, tuple[str, str]] = {
    # sector -> (value-added share code, employment share code)
    "Agriculture": ("NV.AGR.TOTL.ZS", "SL.AGR.EMPL.ZS"),
    "Industry": ("NV.IND.TOTL.ZS", "SL.IND.EMPL.ZS"),
    "Services": ("NV.SRV.TOTL.ZS", "SL.SRV.EMPL.ZS"),
}
MANUF = "NV.IND.MANF.ZS"
LFP_FEMALE = "SL.TLF.CACT.FE.ZS"
LFP_MALE = "SL.TLF.CACT.MA.ZS"
GDP_PER_WORKER = "SL.GDP.PCAP.EM.KD"
VULNERABLE = "SL.EMP.VULN.ZS"

SHARE_COLUMNS = [
    "iso3", "country", "year", "sector", "va_share", "emp_share", "gap_pp",
    "va_sum", "va_residual", "emp_sum", "va_share_rescaled", "rlp", "rlp_rescaled",
]


# ---------------------------------------------------------------------------
# Reshaping
# ---------------------------------------------------------------------------
def country_names(df: pd.DataFrame) -> dict[str, str]:
    """iso3 -> country name as returned by the API."""
    if df.empty:
        return {}
    d = df.dropna(subset=["country"]).drop_duplicates("iso3")
    return dict(zip(d["iso3"], d["country"]))


def panel(df: pd.DataFrame, codes: Iterable[str] | None = None) -> pd.DataFrame:
    """Wide frame indexed by (iso3, year) with one column per indicator.

    Only observations that exist are used; missing combinations are NaN.
    Duplicate (iso3, indicator, year) rows are an error -- they would make
    "which value?" ambiguous.
    """
    codes = list(codes) if codes is not None else list(CODES)
    sub = df[df["indicator"].isin(codes)]
    if sub.duplicated(["iso3", "indicator", "year"]).any():
        raise ValueError("duplicate (iso3, indicator, year) observations")
    if sub.empty:
        return pd.DataFrame(columns=codes, index=pd.MultiIndex.from_tuples([], names=["iso3", "year"]))
    wide = sub.pivot(index=["iso3", "year"], columns="indicator", values="value")
    for c in codes:
        if c not in wide.columns:
            wide[c] = math.nan
    return wide[codes].sort_index()


def _safe_ratio(num: float, den: float) -> float:
    if pd.isna(num) or pd.isna(den) or den <= 0:
        return math.nan
    return float(num) / float(den)


def sector_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (iso3, year, sector) with shares, gaps, sums and RLP.

    * gap_pp = va_share - emp_share (percentage points; NaN unless both exist)
    * va_sum / emp_sum: sum of the three sectors, only when all three exist
      for that country-year (a partial sum is never reported)
    * va_residual = 100 - va_sum
    * va_share_rescaled = 100 * va_share / va_sum (labelled derived)
    * rlp = va_share / emp_share; rlp_rescaled = va_share_rescaled / emp_share
      (NaN when either input is missing or emp_share <= 0)

    Country-years with no sector observation at all are dropped.
    """
    va_codes = [v for v, _ in SECTORS.values()]
    emp_codes = [e for _, e in SECTORS.values()]
    wide = panel(df, va_codes + emp_codes)
    names = country_names(df)
    rows: list[dict[str, Any]] = []
    for (iso3, year), r in wide.iterrows():
        if r.isna().all():
            continue
        va_vals = [r[c] for c in va_codes]
        emp_vals = [r[c] for c in emp_codes]
        va_sum = float(sum(va_vals)) if all(pd.notna(v) for v in va_vals) else math.nan
        emp_sum = float(sum(emp_vals)) if all(pd.notna(v) for v in emp_vals) else math.nan
        va_resid = 100.0 - va_sum if pd.notna(va_sum) else math.nan
        for sector, (vc, ec) in SECTORS.items():
            va, emp = r[vc], r[ec]
            resc = 100.0 * va / va_sum if pd.notna(va) and pd.notna(va_sum) and va_sum > 0 else math.nan
            rows.append({
                "iso3": iso3, "country": names.get(iso3, iso3), "year": int(year), "sector": sector,
                "va_share": float(va) if pd.notna(va) else math.nan,
                "emp_share": float(emp) if pd.notna(emp) else math.nan,
                "gap_pp": float(va - emp) if pd.notna(va) and pd.notna(emp) else math.nan,
                "va_sum": va_sum, "va_residual": va_resid, "emp_sum": emp_sum,
                "va_share_rescaled": resc,
                "rlp": _safe_ratio(va, emp),
                "rlp_rescaled": _safe_ratio(resc, emp),
            })
    out = pd.DataFrame(rows, columns=SHARE_COLUMNS)
    if not out.empty:
        out["year"] = out["year"].astype("int64")
    return out


def complete_years(table: pd.DataFrame, iso3: str) -> list[int]:
    """Years in which `iso3` has all three VA shares *and* all three
    employment shares (so every RLP and both sums exist), ascending."""
    t = table[table["iso3"] == iso3]
    if t.empty:
        return []
    ok = (t.assign(_ok=t["rlp"].notna() & t["va_sum"].notna())
           .groupby("year")["_ok"].agg(lambda s: len(s) == len(SECTORS) and bool(s.all())))
    return sorted(int(y) for y, v in ok.items() if v)


def snapshot(table: pd.DataFrame, iso3: str, year: int) -> pd.DataFrame:
    """The three sector rows for one country-year (empty if absent)."""
    t = table[(table["iso3"] == iso3) & (table["year"] == int(year))]
    return t.set_index("sector").reindex(list(SECTORS)).reset_index() if not t.empty else t


def weighted_rlp(snap: pd.DataFrame, rescaled: bool = False) -> float:
    """Employment-weighted mean of RLP across sectors (a consistency check):
    equals va_sum/100 on the published basis and emp_sum/100 (~1) rescaled."""
    col = "rlp_rescaled" if rescaled else "rlp"
    if snap.empty or snap[col].isna().any() or snap["emp_share"].isna().any():
        return math.nan
    return float((snap[col] * snap["emp_share"]).sum() / 100.0)


def composition_change(table: pd.DataFrame, iso3: str, y0: int, y1: int) -> pd.DataFrame:
    """VA and employment shares in y0 and y1 and their pp changes, per sector.
    Changes are NaN where either endpoint is missing -- nothing is filled."""
    a = snapshot(table, iso3, y0)
    b = snapshot(table, iso3, y1)
    rows = []
    for sector in SECTORS:
        ra = a[a["sector"] == sector] if not a.empty else a
        rb = b[b["sector"] == sector] if not b.empty else b
        def g(frame, col):
            return float(frame[col].iloc[0]) if not frame.empty and pd.notna(frame[col].iloc[0]) else math.nan
        va0, va1, e0, e1 = g(ra, "va_share"), g(rb, "va_share"), g(ra, "emp_share"), g(rb, "emp_share")
        rows.append({"sector": sector, f"va_{y0}": va0, f"va_{y1}": va1, "va_change_pp": va1 - va0,
                     f"emp_{y0}": e0, f"emp_{y1}": e1, "emp_change_pp": e1 - e0})
    return pd.DataFrame(rows)


def series(df: pd.DataFrame, code: str, iso3: str | None = None) -> pd.DataFrame:
    """Non-null observations of one indicator, sorted (iso3, year)."""
    s = df[(df["indicator"] == code) & df["value"].notna()]
    if iso3 is not None:
        s = s[s["iso3"] == iso3]
    return s.sort_values(["iso3", "year"])[["iso3", "country", "year", "value"]].reset_index(drop=True)


def peak_and_latest(df: pd.DataFrame, code: str, iso3: str) -> dict[str, Any] | None:
    """Peak (first year of the maximum) and latest observation of a series
    within the fetched window, or None if there are no observations."""
    s = series(df, code, iso3)
    if s.empty:
        return None
    pk = s.loc[s["value"].idxmax()]
    last = s.iloc[-1]
    first = s.iloc[0]
    return {
        "first_year": int(first["year"]), "first_value": float(first["value"]),
        "peak_year": int(pk["year"]), "peak_value": float(pk["value"]),
        "latest_year": int(last["year"]), "latest_value": float(last["value"]),
        "change_from_peak_pp": float(last["value"] - pk["value"]),
        "n_obs": int(len(s)),
    }


def lfp_table(df: pd.DataFrame) -> pd.DataFrame:
    """Female and male participation per (iso3, year) and the male-minus-
    female gap in pp (NaN unless both exist in that year)."""
    w = panel(df, [LFP_FEMALE, LFP_MALE]).dropna(how="all")
    names = country_names(df)
    out = w.rename(columns={LFP_FEMALE: "female", LFP_MALE: "male"}).reset_index()
    out["gap_pp"] = out["male"] - out["female"]
    out["country"] = out["iso3"].map(lambda i: names.get(i, i))
    return out[["iso3", "country", "year", "female", "male", "gap_pp"]]


def latest_pair(df: pd.DataFrame, x_code: str, y_code: str) -> pd.DataFrame:
    """Per country, the latest year in which *both* indicators exist (same
    year -- never mixing years within a country)."""
    w = panel(df, [x_code, y_code]).dropna()
    names = country_names(df)
    rows = []
    for iso3, g in w.groupby(level="iso3"):
        y = int(g.index.get_level_values("year").max())
        r = g.xs((iso3, y))
        rows.append({"iso3": iso3, "country": names.get(iso3, iso3), "year": y,
                     "x": float(r[x_code]), "y": float(r[y_code])})
    return pd.DataFrame(rows, columns=["iso3", "country", "year", "x", "y"])


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
def _f1(x: float) -> str:
    return f"{x:.1f}"


def findings(df: pd.DataFrame, iso3: str = "IND") -> list[str]:
    """Deterministic sentences built only from values in `df`.

    Each sentence is emitted only if every number it needs exists; nothing
    is estimated or interpolated. Returns [] for an empty frame.
    """
    if df.empty:
        return []
    names = country_names(df)
    name = names.get(iso3, iso3)
    out: list[str] = []
    table = sector_table(df)
    years = complete_years(table, iso3)

    if years:
        y = years[-1]
        snap = snapshot(table, iso3, y).set_index("sector")
        ag = snap.loc["Agriculture"]
        out.append(
            f"In {y}, agriculture employed {_f1(ag['emp_share'])}% of workers in {name} but produced "
            f"{_f1(ag['va_share'])}% of GDP as value added — a gap of {ag['gap_pp']:+.1f} percentage points."
        )
        srv, ind = snap.loc["Services"], snap.loc["Industry"]
        if ag["rlp"] > 0:
            out.append(
                f"In {y}, value added per worker in services was {srv['rlp'] / ag['rlp']:.1f}× that in "
                f"agriculture, and in industry {ind['rlp'] / ag['rlp']:.1f}× (ratios of relative labour "
                f"productivity: services {srv['rlp']:.2f}, industry {ind['rlp']:.2f}, agriculture {ag['rlp']:.2f})."
            )
        out.append(
            f"In {y}, the three sector value-added shares sum to {_f1(ag['va_sum'])}% of GDP; the remaining "
            f"{_f1(ag['va_residual'])}% is net taxes on products and other adjustments, not a sector."
        )
        if len(years) >= 2:
            y0 = years[0]
            a0 = snapshot(table, iso3, y0).set_index("sector").loc["Agriculture"]
            out.append(
                f"Agriculture's share of employment went from {_f1(a0['emp_share'])}% in {y0} to "
                f"{_f1(ag['emp_share'])}% in {y} ({ag['emp_share'] - a0['emp_share']:+.1f} pp), while its "
                f"value-added share went from {_f1(a0['va_share'])}% to {_f1(ag['va_share'])}% "
                f"({ag['va_share'] - a0['va_share']:+.1f} pp)."
            )

    m = peak_and_latest(df, MANUF, iso3)
    if m is not None:
        if m["n_obs"] >= 2 and m["peak_year"] != m["latest_year"]:
            out.append(
                f"Manufacturing value added was {_f1(m['latest_value'])}% of GDP in {m['latest_year']}, "
                f"{m['change_from_peak_pp']:+.1f} pp from its highest level in the selected years "
                f"({_f1(m['peak_value'])}% in {m['peak_year']})."
            )
        elif m["n_obs"] >= 2:
            out.append(
                f"Manufacturing value added was {_f1(m['latest_value'])}% of GDP in {m['latest_year']}, "
                f"the highest level in the selected years (from {_f1(m['first_value'])}% in {m['first_year']})."
            )
        else:
            out.append(f"Manufacturing value added was {_f1(m['latest_value'])}% of GDP in {m['latest_year']}.")

    lfp = lfp_table(df)
    lfp = lfp[(lfp["iso3"] == iso3)].dropna(subset=["female", "male"])
    if not lfp.empty:
        r = lfp.sort_values("year").iloc[-1]
        out.append(
            f"In {int(r['year'])}, {_f1(r['female'])}% of women aged 15+ in {name} were in the labour force "
            f"against {_f1(r['male'])}% of men — a gap of {_f1(r['gap_pp'])} pp (ILO modelled estimates)."
        )

    v = series(df, VULNERABLE, iso3)
    if not v.empty:
        last = v.iloc[-1]
        out.append(
            f"In {int(last['year'])}, {_f1(last['value'])}% of {name}'s workers were in vulnerable employment "
            f"(own-account or contributing family work; ILO modelled estimate)."
        )
    return out


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
def settings_record(settings: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-safe copy of the page settings plus the indicator codes used."""
    rec = {k: (list(v) if isinstance(v, (tuple, set)) else v) for k, v in settings.items()}
    rec.setdefault("indicators", list(CODES))
    return rec


def csv_with_header(df: pd.DataFrame, settings: Mapping[str, Any], title: str) -> str:
    """CSV text preceded by '# key: value' comment lines recording the
    settings (read back with pandas.read_csv(..., comment='#'))."""
    rec = settings_record(settings)
    lines = [f"# {title}"]
    for k, v in rec.items():
        lines.append(f"# {k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines) + "\n" + df.to_csv(index=False)
