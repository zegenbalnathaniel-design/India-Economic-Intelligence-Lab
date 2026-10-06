"""3D layout for the asset-correlation network view.

Turns an n-asset correlation matrix into 3D coordinates via **classical
multidimensional scaling (MDS)** — a real, standard dimensionality-
reduction technique (Torgerson, 1952), not an arbitrary decorative layout.
Highly correlated assets end up close together in the resulting space;
weakly/negatively correlated assets end up far apart.

Steps
-----
1. Convert correlation to a distance: `d_ij = sqrt(2 * (1 - rho_ij))`, which
   is a proper metric (zero iff rho=1, maximal at rho=-1) commonly used to
   turn a correlation matrix into a distance matrix.
2. Classical MDS: double-center the squared-distance matrix,
   `B = -1/2 * J @ D2 @ J` with `J = I - (1/n) * ones(n,n)`, then take the
   top-3 eigenvectors of `B` (scaled by the square root of their
   eigenvalues) as 3D coordinates. Negative eigenvalues (possible for a
   non-Euclidean distance) are clipped to zero rather than producing
   complex coordinates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def correlation_to_distance(corr: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.clip(2.0 * (1.0 - corr), 0.0, None))
    np.fill_diagonal(d, 0.0)
    return d


def classical_mds_3d(distance: np.ndarray) -> np.ndarray:
    n = distance.shape[0]
    if distance.shape != (n, n):
        raise ValueError("distance must be a square matrix.")
    d2 = distance ** 2
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ d2 @ J
    eigvals, eigvecs = np.linalg.eigh(B)
    order = np.argsort(eigvals)[::-1][:3]
    top_vals = np.clip(eigvals[order], 0.0, None)
    coords = eigvecs[:, order] * np.sqrt(top_vals)
    if coords.shape[1] < 3:
        coords = np.hstack([coords, np.zeros((n, 3 - coords.shape[1]))])
    return coords


def layout_from_correlation(corr_df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper: correlation DataFrame -> DataFrame of x,y,z per
    ticker, ready to hand to the Three.js (or Plotly 3D) renderer."""
    distance = correlation_to_distance(corr_df.values)
    coords = classical_mds_3d(distance)
    return pd.DataFrame(coords, index=corr_df.index, columns=["x", "y", "z"])


def edge_list(corr_df: pd.DataFrame, threshold: float = 0.3) -> pd.DataFrame:
    """Pairs of tickers whose |correlation| exceeds `threshold`, for
    drawing edges in the network view. Self-pairs excluded."""
    tickers = corr_df.columns.tolist()
    rows = []
    for i, a in enumerate(tickers):
        for j, b in enumerate(tickers):
            if j <= i:
                continue
            rho = corr_df.iloc[i, j]
            if abs(rho) >= threshold:
                rows.append({"source": a, "target": b, "correlation": float(rho)})
    return pd.DataFrame(rows)
