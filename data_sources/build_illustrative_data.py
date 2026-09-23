"""Build the illustrative panel shipped in data/processed/.

Every value produced by this script is a plausible, seeded, synthetic figure
constructed to demonstrate the iBFPI methodology on a realistic-looking
panel. It is NOT a substitute for real bank disclosures. Real numbers should
replace this file when reproducing the analysis.

Reproducibility: `python -m data_sources.build_illustrative_data` regenerates
identical CSVs on any machine.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

BANKS = [
    "HDFC Bank",
    "ICICI Bank",
    "State Bank of India",
    "Axis Bank",
    "Kotak Mahindra Bank",
]

# Quarterly period ends, FY19Q1 through FY25Q2 (2018-Q2 .. 2024-Q3 cal.).
PERIODS = pd.date_range("2018-06-30", "2024-09-30", freq="QE")

# Baseline levels roughly reflecting published FY averages from bank
# annual reports; per-bank offsets to differentiate profiles.
BASE = {
    "ppnr_to_assets": 0.028,      # 2.8%
    "cet1_ratio": 0.155,          # 15.5%
    "nco_rate": 0.011,            # 1.1%
    "lcr": 1.30,                  # 130%
    "unrealised_loss_to_cet1": 0.020,  # 2.0%
}

BANK_OFFSET = {
    "HDFC Bank":           dict(ppnr_to_assets=+0.006, cet1_ratio=+0.010, nco_rate=-0.004, lcr=+0.05, unrealised_loss_to_cet1=-0.006),
    "ICICI Bank":          dict(ppnr_to_assets=+0.004, cet1_ratio=+0.005, nco_rate=-0.002, lcr=+0.02, unrealised_loss_to_cet1=-0.003),
    "State Bank of India": dict(ppnr_to_assets=-0.006, cet1_ratio=-0.020, nco_rate=+0.005, lcr=-0.05, unrealised_loss_to_cet1=+0.006),
    "Axis Bank":           dict(ppnr_to_assets=-0.002, cet1_ratio=+0.000, nco_rate=+0.001, lcr=-0.01, unrealised_loss_to_cet1=+0.000),
    "Kotak Mahindra Bank": dict(ppnr_to_assets=+0.005, cet1_ratio=+0.030, nco_rate=-0.003, lcr=+0.10, unrealised_loss_to_cet1=-0.006),
}


def _repo_path() -> np.ndarray:
    """Approximate RBI repo rate at quarter-end (%).

    Path chosen to match qualitative history: 6.25 -> 6.50 in FY19, cut to
    4.00 by mid-2020 (Covid), held near 4.00 through mid-2022, then 250bp of
    hikes to 6.50 by early 2023, held through 2024. Values are rounded and
    intended for illustration; replace with the RBI-published series when
    reproducing.
    """
    path = np.array([
        6.25, 6.50, 6.50, 6.25, 6.00, 5.75, 5.15, 4.40,
        4.00, 4.00, 4.00, 4.00, 4.00, 4.00, 4.40, 5.90,
        6.25, 6.50, 6.50, 6.50, 6.50, 6.50, 6.50, 6.50,
        6.50, 6.50,
    ])
    assert len(path) == len(PERIODS), (len(path), len(PERIODS))
    return path


def build() -> None:
    rng = np.random.default_rng(seed=42)
    repo = _repo_path()
    quarters = np.arange(len(PERIODS))

    # Cyclical common factor: positive in low-rate cushion years, negative
    # around covid stress and rate-hike quarters where MTM losses rise.
    covid_mask = (PERIODS >= pd.Timestamp("2020-03-31")) & (PERIODS <= pd.Timestamp("2021-03-31"))
    hike_mask = (PERIODS >= pd.Timestamp("2022-06-30")) & (PERIODS <= pd.Timestamp("2023-06-30"))

    rows = []
    for bank in BANKS:
        off = BANK_OFFSET[bank]
        for i, per in enumerate(PERIODS):
            noise = rng.normal(0, 0.001, size=5)
            # Common shocks
            covid = covid_mask[i]
            hike = hike_mask[i]

            ppnr = BASE["ppnr_to_assets"] + off["ppnr_to_assets"] + noise[0]
            ppnr += (-0.004 if covid else 0.0)
            ppnr += (0.002 if hike else 0.0)

            cet1 = BASE["cet1_ratio"] + off["cet1_ratio"] + noise[1] * 0.5
            cet1 += (-0.005 if covid else 0.0)
            cet1 += 0.0015 * (i / len(PERIODS))  # gradual build

            nco = BASE["nco_rate"] + off["nco_rate"] + abs(noise[2])
            nco += (0.008 if covid else 0.0)
            nco = max(nco, 0.001)

            lcr = BASE["lcr"] + off["lcr"] + noise[3] * 3
            lcr += (0.08 if covid else 0.0)  # rush to liquidity
            lcr = max(lcr, 1.05)

            ul = BASE["unrealised_loss_to_cet1"] + off["unrealised_loss_to_cet1"] + abs(noise[4]) * 0.5
            ul += (0.035 if hike else 0.0)   # AFS book MTM hit during hikes
            ul += (-0.010 if not (covid or hike) and repo[i] < 5.0 else 0.0)
            ul = max(ul, 0.0)

            rows.append(dict(
                bank=bank,
                period=per,
                ppnr_to_assets=round(ppnr, 5),
                cet1_ratio=round(cet1, 5),
                nco_rate=round(nco, 5),
                lcr=round(lcr, 4),
                unrealised_loss_to_cet1=round(ul, 5),
            ))
    panel = pd.DataFrame(rows)
    panel.to_csv(OUT / "bank_panel.csv", index=False)

    repo_df = pd.DataFrame({"period": PERIODS, "repo_rate": repo})
    repo_df.to_csv(OUT / "repo_rate.csv", index=False)

    print(f"wrote {OUT / 'bank_panel.csv'}: {len(panel)} rows, {len(BANKS)} banks, {len(PERIODS)} quarters.")
    print(f"wrote {OUT / 'repo_rate.csv'}: {len(repo_df)} quarters.")


if __name__ == "__main__":
    build()
