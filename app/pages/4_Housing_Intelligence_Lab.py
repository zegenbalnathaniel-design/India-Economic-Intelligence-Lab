"""Housing Intelligence Lab.

Research question: is Indian housing becoming less affordable relative to
income, and how does that affordability vary across cities?
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from analysis import housing
from app.components.theme import setup, kicker, callout, source_badge, stat_card, footnote, GOLD
from data_sources import loaders

setup("Housing Intelligence Lab", accent=GOLD)

with st.sidebar:
    st.markdown("## Housing Intelligence Lab")
    st.caption("Sections")
    st.markdown(
        "- A · Price trend (real)\n"
        "- B · City affordability\n"
        "- C · EMI calculator\n"
        "- D · RPIPI (price vs. income over time)\n"
        "- E · ICHASI stress cross-section\n"
        "- F · Data required"
    )
    st.markdown("---")
    st.caption("Prices: VERIFIED (NHB RESIDEX) · Income: PARTIAL (state proxy) or VERIFIED-but-consumption (HCES MPCE)")

kicker("HOUSING INTELLIGENCE · INDIA")
st.title("Is housing outpacing income across Indian cities?")
st.markdown(
    "Real NHB RESIDEX price data for 50 cities (2013-2024), paired with state per-capita "
    "NSDP as an **explicit, documented income proxy** — there is no city-level household "
    "income in any source available to this project yet. Every number derived from the "
    "proxy is labelled as such below; none of it should be read as true city-level income."
)
source_badge("NHB RESIDEX (city prices)", "RBI Handbook (state income, proxy)")

callout(
    "⚠️ **No city-level household income exists in this dataset.** Price-to-income and "
    "EMI-to-income figures below use **state-average per-capita NSDP** as a stand-in for "
    "city income. This systematically **overstates** housing stress in cities whose actual "
    "incomes run well above their state average — most visibly Delhi-NCR satellite cities "
    "(Noida, Ghaziabad, Greater Noida), which are priced on Delhi-adjacent demand but "
    "proxied with Uttar Pradesh's state-average income. Read the ranking below as "
    "*price pressure relative to a state benchmark*, not as a literal affordability verdict "
    "on any one city.",
    kind="warn",
)

st.markdown("---")

price_levels = loaders.load_residex_price_levels()
nsdp_current = loaders.load_nsdp_current()
mpce_urban = loaders.load_hces_urban_mpce()
usable_records = loaders.load_residex_usable_records()

# ---------- A. Real price trend ------------------------------------------
st.header("A · Real housing price trend")
cities = sorted(price_levels["city"].unique())
default_cities = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad"]
selected = st.multiselect("Cities", cities, default=[c for c in default_cities if c in cities])

if selected:
    fig = go.Figure()
    for city in selected:
        sub = housing.sort_quarters(price_levels[price_levels["city"] == city])
        fig.add_trace(go.Scatter(x=sub["quarter"], y=sub["composite_price_inr_per_sqm"], name=city, mode="lines"))
    fig.update_layout(title="Composite price, ₹ per sq.m.", xaxis_title="Quarter", yaxis_title="₹/sq.m.", height=450)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Source: NHB RESIDEX, actual price levels (not an index) — Jun-2013 to Sep-2024.")
else:
    st.info("Select at least one city to see its price trend.")

latest_usable = housing.sort_quarters(usable_records, quarter_col="quarter_label").iloc[-1]
with st.expander(f"Data quality — how much of the underlying RESIDEX series was usable? (latest: {latest_usable['quarter_label']})"):
    source_badge("VERIFIED — NHB RESIDEX Usable Records")
    st.markdown(
        f"At **{latest_usable['quarter_label']}**, NHB's Assessment-Prices HPI methodology found "
        f"**{latest_usable['usable_records_percent']:.0f}%** of phase-1 city residential-apartment "
        f"records usable ({latest_usable['usable_records']:,} of {latest_usable['phase_1_city_residential_apartment_records']:,}). "
        "Across Jun-2017 to Jun-2026, the usable share has ranged "
        f"{usable_records['usable_records_percent'].min():.0f}%–{usable_records['usable_records_percent'].max():.0f}%."
    )
    callout(
        "**This is data-quality coverage of the underlying RESIDEX series, not a new price metric "
        "or a city HPI index value** — the source file states this verbatim on every row. It is a "
        "caveat about how much of the raw administrative data behind the chart above was usable, "
        "not a measure of housing prices or affordability itself.",
        kind="note",
    )
    usable_chart = go.Figure(go.Scatter(
        x=housing.sort_quarters(usable_records, quarter_col="quarter_label")["quarter_label"],
        y=housing.sort_quarters(usable_records, quarter_col="quarter_label")["usable_records_percent"],
        mode="lines+markers", name="Usable records (%)",
    ))
    usable_chart.update_layout(title="Usable-records share, phase-1 city residential apartments (%)",
                                xaxis_title="Quarter", yaxis_title="% usable", height=320)
    st.plotly_chart(usable_chart, use_container_width=True)

st.markdown("---")

# ---------- B. City affordability ranking ---------------------------------
st.header("B · Price-to-income, all cities")
income_source_label = st.radio(
    "Income proxy",
    ["State per-capita NSDP (current prices)", "State/UT urban per-capita MPCE (HCES 2023-24)"],
    index=0,
    help="Neither is true city-level household income — see the caveat below whichever you pick.",
)
income_source = "nsdp" if income_source_label.startswith("State per-capita NSDP") else "mpce"

if income_source == "nsdp":
    callout(housing.INCOME_PROXY_CAVEATS["nsdp"], kind="warn")
else:
    callout(housing.INCOME_PROXY_CAVEATS["mpce"], kind="warn")

unit_size = st.slider("Reference dwelling size (sq.m.)", 40, 150, int(housing.DEFAULT_UNIT_SIZE_SQM), step=5)
down_payment_pct = st.slider("Down payment (%)", 0, 50, 20) / 100
rate = st.slider("Mortgage rate (%)", 5.0, 14.0, 8.5) / 100
tenure = st.slider("Loan tenure (years)", 5, 30, 20)

aff = housing.affordability_across_cities(
    price_levels, nsdp_current, mpce_urban=mpce_urban, unit_size_sqm=unit_size,
    down_payment_pct=down_payment_pct, annual_interest_rate=rate, loan_years=tenure,
    income_source=income_source,
)

income_col_label = "annual_income (STATE PROXY, NSDP)" if income_source == "nsdp" else "annual_income (STATE/UT PROXY, MPCE x12 — consumption, not income)"

fig2 = go.Figure(go.Bar(x=aff["city"], y=aff["price_to_income"]))
fig2.add_hline(y=5, line_dash="dash", annotation_text="P/I = 5 (commonly cited stress threshold)", annotation_position="top left")
fig2.update_layout(title=f"Price-to-income ratio by city ({unit_size:.0f} sq.m. reference unit, {income_source.upper()} income proxy)", xaxis_title="",
                    yaxis_title="Price / annual income (proxy)", height=500)
st.plotly_chart(fig2, use_container_width=True)

st.dataframe(
    aff[["city", "state", "quarter", "price_per_sqm", "unit_price", "annual_income_proxy", "price_to_income", "emi_monthly", "emi_to_income_pct"]]
    .rename(columns={"annual_income_proxy": income_col_label})
    .style.format({
        "price_per_sqm": "₹{:,.0f}", "unit_price": "₹{:,.0f}", income_col_label: "₹{:,.0f}",
        "price_to_income": "{:.2f}", "emi_monthly": "₹{:,.0f}", "emi_to_income_pct": "{:.1f}%",
    }),
    use_container_width=True, hide_index=True,
)

st.markdown("---")

# ---------- C. EMI calculator ---------------------------------------------
st.header("C · EMI calculator — single city")
col1, col2 = st.columns(2)
with col1:
    city = st.selectbox("City", cities, index=cities.index("Mumbai") if "Mumbai" in cities else 0)
with col2:
    custom_income = st.number_input(
        "Annual household income (₹) — override the income proxy", min_value=0, value=0, step=50_000,
        help="Leave at 0 to use the income proxy selected in section B.",
    )

try:
    result = housing.city_affordability(
        price_levels, nsdp_current, city, unit_size_sqm=unit_size,
        down_payment_pct=down_payment_pct, annual_interest_rate=rate, loan_years=tenure,
        income_source=income_source, mpce_urban=mpce_urban,
    )
    income_used = custom_income if custom_income > 0 else result.annual_income_proxy
    emi_monthly = housing.emi(result.unit_price * (1 - down_payment_pct), rate, tenure)
    pi = housing.price_to_income_ratio(result.unit_price, income_used)
    emi_pct = housing.mortgage_payment_to_income_ratio(emi_monthly, income_used / 12) * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Unit price", f"₹{result.unit_price:,.0f}", f"{unit_size:.0f} sq.m. @ ₹{result.price_per_sqm:,.0f}/sq.m.")
    with c2:
        stat_card("Monthly EMI", f"₹{emi_monthly:,.0f}", f"{rate*100:.1f}% · {tenure}y")
    with c3:
        stat_card("Price-to-income", f"{pi:.2f}×", income_source.upper() + " proxy" if custom_income == 0 else "your input")
    with c4:
        stat_card("EMI / income", f"{emi_pct:.1f}%", income_source.upper() + " proxy" if custom_income == 0 else "your input")

    if custom_income == 0:
        if income_source == "nsdp":
            st.caption(f"Using {result.state}'s per-capita NSDP (₹{result.annual_income_proxy:,.0f}/yr) as the income proxy for {city}. Enter your own household income above to override.")
        else:
            st.caption(f"Using {result.state}'s urban per-capita MPCE annualised (₹{result.annual_income_proxy:,.0f}/yr — consumption, not income) as the proxy for {city}. Enter your own household income above to override.")
except (KeyError, ValueError) as exc:
    st.error(str(exc))

st.markdown("---")

# ---------- D. RPIPI — relative price-to-income pressure over time --------
st.header("D · RPIPI — relative price-to-income pressure, over time")
source_badge("DERIVED — real RESIDEX composite index × real state NSDP")
st.markdown(
    "The **Relative Price-to-Income Pressure Index (RPIPI)** tracks whether housing price has "
    "outpaced income, or the reverse, *since a base period* — using the real NHB RESIDEX "
    "**composite index** (2013-2024) and the real state NSDP time series, with no invented "
    "benchmark price level or rate history. 100 = price and income grew equally since the base "
    "period; **>100 = price outpaced income; <100 = income outpaced price**."
)
rpipi_city = st.selectbox("City", cities, index=cities.index("Mumbai") if "Mumbai" in cities else 0, key="rpipi_city")
try:
    residex_index = loaders.load_residex_index()
    rpipi_result = housing.relative_price_income_pressure(residex_index, nsdp_current, rpipi_city)

    c1, c2, c3 = st.columns(3)
    with c1:
        stat_card("Base financial year", rpipi_result.base_financial_year, "RPIPI = 100 here, by construction")
    with c2:
        stat_card("Latest financial year", rpipi_result.latest_financial_year, rpipi_result.status)
    with c3:
        stat_card("Latest RPIPI", f"{rpipi_result.latest_rpipi:.1f}",
                   "price outpaced income" if rpipi_result.latest_rpipi > 100 else "income outpaced price")

    fig_rpipi = go.Figure(go.Scatter(x=rpipi_result.series["financial_year"], y=rpipi_result.series["rpipi"], mode="lines+markers", name="RPIPI"))
    fig_rpipi.add_hline(y=100, line_dash="dash", annotation_text="100 = price & income grew equally since base year", annotation_position="top left")
    fig_rpipi.update_layout(title=f"{rpipi_city}: RPIPI, base {rpipi_result.base_financial_year}=100", xaxis_title="Financial year", yaxis_title="RPIPI", height=420)
    st.plotly_chart(fig_rpipi, use_container_width=True)

    if rpipi_result.status != "ok":
        st.warning(f"Insufficient overlap for a meaningful trend: {rpipi_result.status}.")

    with st.expander("RPIPI methodology"):
        st.markdown(
            """
`RPIPI_c,t = 100 × (HPI_c,t / HPI_c,0) / (Y_c,t / Y_c,0)` — `HPI` is the city's real RESIDEX
composite index (averaged across the quarters observed within each Indian financial year, to
align it with the annual income series), `Y` is the city's state per-capita NSDP (current
prices), and `0` is the earliest financial year both series cover for this city (its base
period — not a single fixed calendar year for every city).

This is fully computable from real data already in this project — unlike the full ICHASI
methodology, no benchmark price level or mortgage-rate history needs to be assumed or
reconstructed. The income-proxy caveat above (state NSDP, not true city income) still applies.
"""
        )
except (KeyError, ValueError) as exc:
    st.error(str(exc))

st.markdown("---")

# ---------- E. ICHASI — percentile-clipped cross-sectional stress score ---
st.header("E · ICHASI cross-section — affordability stress score, 0–100")
source_badge("DERIVED — real RESIDEX prices × income proxy × one representative rate")
st.markdown(
    "A percentile-clipped, 0–100 stress score across cities **at the quarter selected above** "
    "(reuses the price-to-income ratios from section B). Each city's price-to-income ratio is "
    "clipped to the 5th–95th percentile of the comparison set, then rescaled linearly to 0–100 — "
    "so one extreme-outlier city cannot compress every other city's score toward zero."
)
callout(housing.RATE_DISCLOSURE, kind="warn")

try:
    stress_result = housing.stress_index_cross_section(
        price_levels, nsdp_current, unit_size_sqm=unit_size, down_payment_pct=down_payment_pct,
        annual_interest_rate=rate, loan_years=tenure, income_source=income_source, mpce_urban=mpce_urban,
    )
    fig_stress = go.Figure(go.Bar(x=stress_result.scores["city"], y=stress_result.scores["stress_score_0_100"]))
    fig_stress.update_layout(
        title=f"ICHASI cross-section stress score, {stress_result.quarter} ({stress_result.annual_interest_rate*100:.1f}% rate, {stress_result.loan_years:.0f}y, {stress_result.down_payment_pct*100:.0f}% down)",
        xaxis_title="", yaxis_title="Stress score (0–100)", height=500,
    )
    st.plotly_chart(fig_stress, use_container_width=True)
    st.caption(
        f"Clipped to the {stress_result.clip_low_pctile:.0f}th–{stress_result.clip_high_pctile:.0f}th percentile of "
        f"price-to-income ratios at {stress_result.quarter} before rescaling to 0–100."
    )
    st.dataframe(
        stress_result.scores.style.format({"price_to_income": "{:.2f}", "pti_clipped": "{:.2f}", "stress_score_0_100": "{:.1f}"}),
        use_container_width=True, hide_index=True,
    )
except ValueError as exc:
    st.error(str(exc))

st.markdown("---")

# ---------- F. Data required ----------------------------------------------
st.header("F · Data required to go further")
st.markdown(
    """
**DATA REQUIRED**

- **City-level household income** (any city, any year) — would replace the state-proxy (or state/UT consumption-proxy) assumption everywhere on this page.
- **RESIDEX's documented base-quarter confirmation** — inferred here as Mar-2018=100 from the data itself (35/50 cities read exactly 100 that quarter); a direct NHB confirmation would upgrade this from inferred to confirmed.
- **Mortgage rate history** (a real, fixed lender panel observed over time) — the EMI calculator, section B and the ICHASI cross-section above all use a single user-set rate, not an observed historical series. See `DATA_REGISTRY.md` → "Still specifically needed" for the exact schema this project needs before it can build a real rate-history series; no such series has been fabricated here.

Status: **AWAITING DATA**. See `DATA_REGISTRY.md` in the repository for the full, current list.
"""
)

with st.expander("Methodology & limitations"):
    st.markdown(
        """
**EMI formula**: `EMI = P·r·(1+r)^n / ((1+r)^n − 1)`, monthly rate `r`, `n` monthly instalments. At `r=0`, reduces to `P/n`.

**Price-to-income**: `unit_price / annual_income`. **EMI-to-income**: `monthly_EMI / monthly_income`.

**Unit price**: `price_per_sq.m. × reference_dwelling_size`. The reference size (default 70 sq.m., adjustable) is a modelling choice, not a measured average dwelling size for any specific city.

**RPIPI** (section D): `100 × (HPI_t/HPI_0) / (Y_t/Y_0)`, base period = earliest financial year both the RESIDEX composite index and the NSDP series cover for that city.

**ICHASI cross-section** (section E): price-to-income, clipped to the 5th–95th percentile across cities at one quarter, rescaled linearly to 0–100. Uses one representative, currently-selected mortgage rate — not an observed rate history (none exists yet; see section F).

**Limitations**:
- State-proxy income, or the HCES urban-MPCE consumption proxy (see the warning above) is the single biggest limitation on this page — it is explicit everywhere a number depends on it. The MPCE proxy is a single 2023-24 cross-section, not a time series, so it cannot be used for RPIPI.
- RESIDEX price levels are transaction/registration-based indices for *existing* housing stock in each city's RESIDEX coverage area, which may not match new-construction asking prices.
- A single reference unit size cannot represent the full range of dwelling types in any city.
- No adjustment for differences in mortgage-market access, down-payment norms, or informal financing across cities or income groups.
- The ICHASI cross-section and EMI calculator use ONE representative current rate for every city and every year — see the rate disclosure above section E.
"""
    )

footnote(
    "NHB RESIDEX price data is real. Income is a documented state-level proxy, not measured city income — "
    "see the warning banner above before drawing conclusions from any single city's numbers."
)
