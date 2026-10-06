"""Unit tests for portfolio_lab.network3d (classical MDS layout)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from portfolio_lab import network3d as net


def test_correlation_to_distance_zero_for_perfect_correlation():
    corr = np.array([[1.0, 1.0], [1.0, 1.0]])
    d = net.correlation_to_distance(corr)
    assert np.allclose(d, 0.0)


def test_correlation_to_distance_maximal_for_perfect_anticorrelation():
    corr = np.array([[1.0, -1.0], [-1.0, 1.0]])
    d = net.correlation_to_distance(corr)
    assert math.isclose(d[0, 1], 2.0, rel_tol=1e-9)


def test_classical_mds_recovers_relative_distances_for_simple_case():
    # Three assets: A & B highly correlated, C uncorrelated with both.
    corr = np.array([
        [1.0, 0.9, 0.0],
        [0.9, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    coords = net.classical_mds_3d(net.correlation_to_distance(corr))
    assert coords.shape == (3, 3)
    dist_ab = np.linalg.norm(coords[0] - coords[1])
    dist_ac = np.linalg.norm(coords[0] - coords[2])
    # A-B should end up much closer in the embedding than A-C, matching
    # their correlation-implied distances.
    assert dist_ab < dist_ac


def test_classical_mds_rejects_non_square():
    with pytest.raises(ValueError):
        net.classical_mds_3d(np.zeros((3, 4)))


def test_layout_from_correlation_preserves_index():
    tickers = ["A", "B", "C"]
    corr_df = pd.DataFrame(np.eye(3), index=tickers, columns=tickers)
    layout = net.layout_from_correlation(corr_df)
    assert list(layout.index) == tickers
    assert list(layout.columns) == ["x", "y", "z"]


def test_edge_list_respects_threshold():
    tickers = ["A", "B", "C"]
    corr_df = pd.DataFrame(
        [[1.0, 0.8, 0.1], [0.8, 1.0, 0.05], [0.1, 0.05, 1.0]], index=tickers, columns=tickers,
    )
    edges = net.edge_list(corr_df, threshold=0.3)
    assert len(edges) == 1
    assert set(edges.iloc[0][["source", "target"]]) == {"A", "B"}
