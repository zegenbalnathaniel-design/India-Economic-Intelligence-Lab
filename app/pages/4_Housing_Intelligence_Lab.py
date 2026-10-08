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
from app.components.theme import setup, kicker, callout, source_badge, stat_card, footnote
from data_sources import loaders

setup("Housing Intelligence Lab")

with st.sidebar:
    st.markdown("## Housing Intelligence Lab")
    st.caption("Sections")
    st.markdown(
        "- A · Price trend (real)\n"
        "- B · City affordability\n"
        "- C · EMI calculator\n"
        "- D · Data required"
    )
    st.markdown("---")
    st.caption("Prices: VERIFIED (NHB RESIDEX) · Income: PARTIAL (state proxy)")

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

st.markdown("---")

# ---------- B. City affordability ranking ---------------------------------
st.header("B · Price-to-income, all cities (state-proxy income)")
unit_size = st.slider("Reference dwelling size (sq.m.)", 40, 150, int(housing.DEFAULT_UNIT_SIZE_SQM), step=5)
down_payment_pct = st.slider("Down payment (%)", 0, 50, 20) / 100
rate = st.slider("Mortgage rate (%)", 5.0, 14.0, 8.5) / 100
tenure = st.slider("Loan tenure (years)", 5, 30, 20)

aff = housing.affordability_across_cities(
    price_levels, nsdp_current, unit_size_sqm=unit_size,
    down_payment_pct=down_payment_pct, annual_interest_rate=rate, loan_years=tenure,
)

fig2 = go.Figure(go.Bar(x=aff["city"], y=aff["price_to_income"]))
fig2.add_hline(y=5, line_dash="dash", annotation_text="P/I = 5 (commonly cited stress threshold)", annotation_position="top left")
fig2.update_layout(title=f"Price-to-income ratio by city ({unit_size:.0f} sq.m. reference unit)", xaxis_title="",
                    yaxis_title="Price / annual income (proxy)", height=500)
st.plotly_chart(fig2, use_container_width=True)

st.dataframe(
    aff[["city", "state", "quarter", "price_per_sqm", "unit_price", "annual_income_proxy", "price_to_income", "emi_monthly", "emi_to_income_pct"]]
    .rename(columns={"annual_income_proxy": "annual_income (STATE PROXY)"})
    .style.format({
        "price_per_sqm": "₹{:,.0f}", "unit_price": "₹{:,.0f}", "annual_income (STATE PROXY)": "₹{:,.0f}",
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
        "Annual household income (₹) — override the state proxy", min_value=0, value=0, step=50_000,
        help="Leave at 0 to use the state per-capita NSDP proxy.",
    )

try:
    result = housing.city_affordability(
        price_levels, nsdp_current, city, unit_size_sqm=unit_size,
        down_payment_pct=down_payment_pct, annual_interest_rate=rate, loan_years=tenure,
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
        stat_card("Price-to-income", f"{pi:.2f}×", "state proxy" if custom_income == 0 else "your input")
    with c4:
        stat_card("EMI / income", f"{emi_pct:.1f}%", "state proxy" if custom_income == 0 else "your input")

    if custom_income == 0:
        st.caption(f"Using {result.state}'s per-capita NSDP (₹{result.annual_income_proxy:,.0f}) as the income proxy for {city}. Enter your own household income above to override.")
except (KeyError, ValueError) as exc:
    st.error(str(exc))

st.markdown("---")

# ---------- D. Data required ----------------------------------------------
st.header("D · Data required to go further")
st.markdown(
    """
**DATA REQUIRED**

- **City-level household income** (any city, any year) — would replace the state-proxy assumption everywhere on this page.
- **RESIDEX's documented base-quarter confirmation** — inferred here as Mar-2018=100 from the data itself (35/50 cities read exactly 100 that quarter); a direct NHB confirmation would upgrade this from inferred to confirmed.
- **Mortgage rate history** (actual bank-average home-loan rates by year) — the calculator above uses a single user-set rate, not a historical series.

Status: **AWAITING DATA**. See `DATA_REGISTRY.md` in the repository for the full, current list.
"""
)

with st.expander("Methodology & limitations"):
    st.markdown(
        """
**EMI formula**: `EMI = P·r·(1+r)^n / ((1+r)^n − 1)`, monthly rate `r`, `n` monthly instalments. At `r=0`, reduces to `P/n`.

**Price-to-income**: `unit_price / annual_income`. **EMI-to-income**: `monthly_EMI / monthly_income`.

**Unit price**: `price_per_sq.m. × reference_dwelling_size`. The reference size (default 70 sq.m., adjustable) is a modelling choice, not a measured average dwelling size for any specific city.

**Limitations**:
- State-proxy income (see the warning above) is the single biggest limitation on this page — it is explicit everywhere a number depends on it.
- RESIDEX price levels are transaction/registration-based indices for *existing* housing stock in each city's RESIDEX coverage area, which may not match new-construction asking prices.
- A single reference unit size cannot represent the full range of dwelling types in any city.
- No adjustment for differences in mortgage-market access, down-payment norms, or informal financing across cities or income groups.
"""
    )

footnote(
    "NHB RESIDEX price data is real. Income is a documented state-level proxy, not measured city income — "
    "see the warning banner above before drawing conclusions from any single city's numbers."
)
