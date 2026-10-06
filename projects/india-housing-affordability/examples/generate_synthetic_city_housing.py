"""Generate a clearly-labelled SYNTHETIC per-city housing baseline dataset.

THIS IS NOT REAL DATA. There is no live housing-price or household-income
feed in this environment, and real Indian city-level price and income data
is not accessible here either. Every number this script writes is
illustrative and manufactured for demonstration purposes only.

To keep the *relative* shape of the synthetic baseline plausible, the
anchors below use widely-reported, qualitative relative orderings only
(e.g. "Mumbai and Delhi NCR have the highest price-to-income ratios among
major Indian cities; Kolkata and Ahmedabad are relatively more
affordable") — not specific real statistics. The actual numbers (income
multipliers, price-to-income anchors, noise) are hand-picked for
illustration and should never be read as empirical measurements. See
`docs/DATA_SOURCES.md` for where real data could be sourced for a future
version of this tool.

The script is fully deterministic given `SEED`: re-running it reproduces a
byte-identical CSV.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2024

# Baseline order-of-magnitude illustrative annual household income (INR),
# representative of a dual-income, formal-sector urban household that might
# realistically be shopping for a home loan. NOT a survey statistic.
BASE_ANNUAL_INCOME_INR = 1_200_000.0

# Illustrative relative income multiplier per city (cost-of-living / typical
# salary-level proxy). Purely for shaping the synthetic baseline; not a
# claim about actual relative incomes.
INCOME_MULTIPLIER: dict[str, float] = {
    "Mumbai": 1.35,
    "Delhi NCR": 1.25,
    "Bengaluru": 1.30,
    "Pune": 1.05,
    "Hyderabad": 1.10,
    "Chennai": 1.00,
    "Kolkata": 0.85,
    "Ahmedabad": 0.90,
}

# Illustrative price-to-income anchor per city, set only to reflect the
# commonly-reported *relative ordering* across major Indian cities (Mumbai
# and Delhi NCR are widely reported as having the highest price-to-income
# ratios; Kolkata and Ahmedabad are widely reported as relatively more
# affordable). The specific numbers are illustrative scaffolding, not
# sourced statistics.
PRICE_TO_INCOME_ANCHOR: dict[str, float] = {
    "Mumbai": 11.0,
    "Delhi NCR": 9.0,
    "Bengaluru": 8.0,
    "Pune": 7.0,
    "Hyderabad": 6.5,
    "Chennai": 6.0,
    "Ahmedabad": 5.0,
    "Kolkata": 5.0,
}

CITIES = sorted(INCOME_MULTIPLIER.keys())


def generate(seed: int = SEED) -> pd.DataFrame:
    """Build the synthetic per-city baseline DataFrame.

    For each city: annual_income = BASE_ANNUAL_INCOME_INR * income_multiplier
    * (1 + income_noise), and house_price = annual_income * pir_anchor *
    (1 + price_noise), with small independent Gaussian noise terms so the
    dataset doesn't look suspiciously exact while staying anchored to the
    illustrative multipliers above. Deterministic given `seed`.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for city in CITIES:
        income_noise = rng.normal(loc=0.0, scale=0.03)
        price_noise = rng.normal(loc=0.0, scale=0.04)

        annual_income = BASE_ANNUAL_INCOME_INR * INCOME_MULTIPLIER[city] * (1.0 + income_noise)
        pir_anchor = PRICE_TO_INCOME_ANCHOR[city]
        house_price = annual_income * pir_anchor * (1.0 + price_noise)

        rows.append(
            {
                "city": city,
                "synthetic_annual_household_income_inr": round(annual_income, -3),
                "synthetic_house_price_inr": round(house_price, -3),
                "illustrative_price_to_income_anchor": pir_anchor,
                "data_status": "SYNTHETIC",
            }
        )

    df = pd.DataFrame(rows)
    df["synthetic_price_to_income_ratio"] = (
        df["synthetic_house_price_inr"] / df["synthetic_annual_household_income_inr"]
    ).round(2)
    return df


if __name__ == "__main__":
    df = generate()
    out_path = Path(__file__).resolve().parents[1] / "data" / "synthetic_city_housing_baseline.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} SYNTHETIC city rows to {out_path}")
    print(df.to_string(index=False))
