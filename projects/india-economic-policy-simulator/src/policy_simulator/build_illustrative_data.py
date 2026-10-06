"""Build the illustrative bank panel shipped in data/processed/.

Every value produced by this script is a plausible, seeded, synthetic
figure constructed to demonstrate the iBFPI methodology on a realistic-
looking panel. It is NOT a substitute for real bank disclosures.

Reproducibility: `python -m policy_simulator.build_illustrative_data`
regenerates identical CSVs on any machine.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank"]
PERIODS = pd.date_range("2018-06-30", "2024-09-30", freq="QE")

BASE = {
    "ppnr_to_assets": 0.028,
    "cet1_ratio": 0.155,
    "nco_rate": 0.011,
    "lcr": 1.30,
    "unrealised_loss_to_cet1": 0.020,
}

BANK_OFFSET = {
    "HDFC Bank":           dict(ppnr_to_assets=+0.006, cet1_ratio=+0.010, nco_rate=-0.004, lcr=+0.05, unrealised_loss_to_cet1=-0.006),
    "ICICI Bank":          dict(ppnr_to_assets=+0.004, cet1_ratio=+0.005, nco_rate=-0.002, lcr=+0.02, unrealised_loss_to_cet1=-0.003),
    "State Bank of India": dict(ppnr_to_assets=-0.006, cet1_ratio=-0.020, nco_rate=+0.005, lcr=-0.05, unrealised_loss_to_cet1=+0.006),
    "Axis Bank":           dict(ppnr_to_assets=-0.002, cet1_ratio=+0.000, nco_rate=+0.001, lcr=-0.01, unrealised_loss_to_cet1=+0.000),
    "Kotak Mahindra Bank": dict(ppnr_to_assets=+0.005, cet1_ratio=+0.030, nco_rate=-0.003, lcr=+0.10, unrealised_loss_to_cet1=-0.006),
}


def _repo_path() -> np.ndarray:
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

    covid_mask = (PERIODS >= pd.Timestamp("2020-03-31")) & (PERIODS <= pd.Timestamp("2021-03-31"))
    hike_mask = (PERIODS >= pd.Timestamp("2022-06-30")) & (PERIODS <= pd.Timestamp("2023-06-30"))

    rows = []
    for bank in BANKS:
        off = BANK_OFFSET[bank]
        for i, per in enumerate(PERIODS):
            noise = rng.normal(0, 0.001, size=5)
            covid = covid_mask[i]
            hike = hike_mask[i]

            ppnr = BASE["ppnr_to_assets"] + off["ppnr_to_assets"] + noise[0]
            ppnr += (-0.004 if covid else 0.0) + (0.002 if hike else 0.0)

            cet1 = BASE["cet1_ratio"] + off["cet1_ratio"] + noise[1] * 0.5
            cet1 += (-0.005 if covid else 0.0) + 0.0015 * (i / len(PERIODS))

            nco = max(BASE["nco_rate"] + off["nco_rate"] + abs(noise[2]) + (0.008 if covid else 0.0), 0.001)

            lcr = max(BASE["lcr"] + off["lcr"] + noise[3] * 3 + (0.08 if covid else 0.0), 1.05)

            ul = BASE["unrealised_loss_to_cet1"] + off["unrealised_loss_to_cet1"] + abs(noise[4]) * 0.5
            ul += (0.035 if hike else 0.0)
            ul += (-0.010 if not (covid or hike) and repo[i] < 5.0 else 0.0)
            ul = max(ul, 0.0)

            rows.append(dict(
                bank=bank, period=per,
                ppnr_to_assets=round(ppnr, 5), cet1_ratio=round(cet1, 5),
                nco_rate=round(nco, 5), lcr=round(lcr, 4),
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
