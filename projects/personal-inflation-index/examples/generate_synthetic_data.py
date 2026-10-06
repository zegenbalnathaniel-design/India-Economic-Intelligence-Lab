"""Generate a deterministic, SEEDED, synthetic category price-index panel.

This script produces `data/synthetic_category_price_index.csv`: monthly
price-index values (base = 100 in the first month) for each of the
default spending categories, plus one `official_cpi_reference` column.

NONE OF THIS IS REAL DATA. Every series here is generated from a fixed
random seed using simple random-walk-with-drift dynamics so that
different categories plausibly grow at different average rates (e.g.
"healthcare" drifts up faster than "communication"), which is useful for
demonstrating the methodology (a basket skewed toward a fast-growing
category should produce a higher personal index) -- but the numbers are
not measurements of anything that happened in the real Indian economy.

Re-running this script with the same seed always reproduces byte-identical
output, which is the point: anyone can regenerate `data/*.csv` from this
script rather than treating the checked-in CSV as a primary source.

See docs/DATA_SOURCES.md for where to find real, official CPI data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20240601  # fixed seed -> deterministic, reproducible output
N_PERIODS = 60  # 5 years of monthly observations
START_PERIOD = "2019-01"

# Approximate monthly drift (mean log-growth) and monthly volatility per
# category. These are illustrative, hand-picked to produce a plausible
# spread of behavior (e.g. healthcare/education drifting up faster than
# communication) -- they are NOT estimated from real data.
CATEGORY_PARAMS: dict[str, dict[str, float]] = {
    "food": {"drift": 0.0048, "vol": 0.006},
    "housing": {"drift": 0.0040, "vol": 0.004},
    "transport": {"drift": 0.0045, "vol": 0.012},
    "education": {"drift": 0.0065, "vol": 0.003},
    "healthcare": {"drift": 0.0070, "vol": 0.005},
    "communication": {"drift": -0.0015, "vol": 0.004},
    "recreation": {"drift": 0.0038, "vol": 0.006},
    "clothing": {"drift": 0.0042, "vol": 0.005},
    "other": {"drift": 0.0045, "vol": 0.005},
}

# Illustrative example weights used ONLY to build the single-number
# "official_cpi_reference" column as a weighted blend of the synthetic
# category series below. NOT official MoSPI weights -- see
# docs/DATA_SOURCES.md and src/personal_inflation/example_data.py.
REFERENCE_WEIGHTS: dict[str, float] = {
    "food": 0.35,
    "housing": 0.20,
    "transport": 0.10,
    "education": 0.08,
    "healthcare": 0.07,
    "communication": 0.04,
    "recreation": 0.05,
    "clothing": 0.05,
    "other": 0.06,
}


def generate_panel(
    n_periods: int = N_PERIODS,
    start_period: str = START_PERIOD,
    seed: int = SEED,
) -> pd.DataFrame:
    """Build the deterministic synthetic monthly category price-index panel."""
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start=start_period, periods=n_periods, freq="M")

    data: dict[str, np.ndarray] = {}
    for category, params in CATEGORY_PARAMS.items():
        log_returns = rng.normal(loc=params["drift"], scale=params["vol"], size=n_periods)
        log_returns[0] = 0.0  # base period: level = 100 exactly
        log_level = np.cumsum(log_returns)
        price_index = 100.0 * np.exp(log_level)
        data[category] = price_index

    df = pd.DataFrame(data, index=periods.astype(str))
    df.index.name = "period"

    weights_sum = sum(REFERENCE_WEIGHTS.values())
    norm_weights = {k: v / weights_sum for k, v in REFERENCE_WEIGHTS.items()}
    df["official_cpi_reference"] = sum(
        df[cat] * w for cat, w in norm_weights.items()
    )

    return df


def main(out_path: str | None = None) -> Path:
    df = generate_panel()

    if out_path is None:
        project_root = Path(__file__).resolve().parent.parent
        out_path_p = project_root / "data" / "synthetic_category_price_index.csv"
    else:
        out_path_p = Path(out_path)

    out_path_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path_p)
    print(f"Wrote {len(df)} periods x {df.shape[1]} columns to {out_path_p}")
    return out_path_p


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
