"""Generate a clearly-labelled SYNTHETIC household net-worth dataset.

This is NOT real survey data. It exists only so the toolkit's functions and
the Streamlit demo have something to run against out of the box. The
generator mixes a lognormal body with a Pareto tail (a standard way to get a
heavy-tailed, wealth-like shape) and is fully deterministic given the seed —
re-running this script reproduces byte-identical output.

To analyse real data instead: point `india_inequality.inequality` functions
at a CSV of your own (one numeric column of wealth/income values) — nothing
in the toolkit itself knows or cares that this file is synthetic.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate(n_households: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Body: lognormal, loosely shaped to resemble a right-skewed net-worth
    # distribution in INR lakhs. Parameters are illustrative, not fitted to
    # any specific survey.
    body = rng.lognormal(mean=1.6, sigma=1.1, size=n_households)

    # Tail: top 2% redrawn from a Pareto distribution to create the
    # heavy upper tail characteristic of wealth (rather than income)
    # distributions.
    tail_mask = rng.random(n_households) < 0.02
    n_tail = int(tail_mask.sum())
    if n_tail > 0:
        body[tail_mask] = 50.0 * (1.0 + rng.pareto(a=1.5, size=n_tail))

    wealth_lakhs = np.round(body, 2)
    household_id = np.arange(1, n_households + 1)
    return pd.DataFrame({"household_id": household_id, "net_worth_inr_lakhs": wealth_lakhs})


if __name__ == "__main__":
    df = generate()
    out_path = Path(__file__).resolve().parents[1] / "data" / "synthetic_household_wealth.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} SYNTHETIC rows to {out_path}")
