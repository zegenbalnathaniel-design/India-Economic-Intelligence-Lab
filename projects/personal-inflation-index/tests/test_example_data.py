"""Tests for the illustrative example data and the synthetic data generator."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from personal_inflation.example_data import EXAMPLE_ILLUSTRATIVE_WEIGHTS
from personal_inflation.index import DEFAULT_CATEGORIES

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

import generate_synthetic_data as gen  # noqa: E402


def test_example_weights_sum_to_one():
    assert sum(EXAMPLE_ILLUSTRATIVE_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)


def test_example_weights_cover_default_categories():
    assert set(EXAMPLE_ILLUSTRATIVE_WEIGHTS) == set(DEFAULT_CATEGORIES)


def test_synthetic_generator_is_deterministic():
    df1 = gen.generate_panel()
    df2 = gen.generate_panel()
    pd.testing.assert_frame_equal(df1, df2)


def test_synthetic_generator_base_period_is_100():
    df = gen.generate_panel()
    first_row = df.iloc[0]
    for category in gen.CATEGORY_PARAMS:
        assert first_row[category] == pytest.approx(100.0, abs=1e-9)


def test_synthetic_generator_different_seed_gives_different_output():
    df_a = gen.generate_panel(seed=1)
    df_b = gen.generate_panel(seed=2)
    assert not df_a["food"].equals(df_b["food"])


def test_synthetic_csv_file_exists_and_matches_generator():
    csv_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_category_price_index.csv"
    assert csv_path.exists(), "run examples/generate_synthetic_data.py to produce this file"

    on_disk = pd.read_csv(csv_path, index_col="period")
    regenerated = gen.generate_panel()
    regenerated.index = regenerated.index.astype(str)

    pd.testing.assert_frame_equal(on_disk, regenerated, check_exact=False, rtol=1e-6)
