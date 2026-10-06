"""Tests for housing_affordability.data_loader (the SYNTHETIC city dataset)."""
from __future__ import annotations

import pytest

from housing_affordability.data_loader import CITY_NAMES, city_baseline, load_synthetic_city_baseline


def test_load_synthetic_city_baseline_has_all_eight_cities():
    df = load_synthetic_city_baseline()
    assert len(df) == 8
    assert set(df["city"]) == set(CITY_NAMES)


def test_load_synthetic_city_baseline_is_labelled_synthetic():
    df = load_synthetic_city_baseline()
    assert (df["data_status"] == "SYNTHETIC").all()


def test_load_synthetic_city_baseline_has_positive_values():
    df = load_synthetic_city_baseline()
    assert (df["synthetic_annual_household_income_inr"] > 0).all()
    assert (df["synthetic_house_price_inr"] > 0).all()


def test_city_baseline_lookup():
    row = city_baseline("Mumbai")
    assert row["city"] == "Mumbai"
    assert row["data_status"] == "SYNTHETIC"
    assert row["synthetic_house_price_inr"] > 0


def test_city_baseline_rejects_unknown_city():
    with pytest.raises(ValueError):
        city_baseline("Atlantis")


def test_mumbai_and_delhi_have_higher_synthetic_pir_than_kolkata_and_ahmedabad():
    # Sanity check that the synthetic baseline's *relative shape* matches
    # the widely-reported qualitative ordering used to construct it
    # (Mumbai/Delhi NCR least affordable, Kolkata/Ahmedabad relatively more
    # affordable among these eight). This is a property of the synthetic
    # generator's anchors, not an empirical finding.
    df = load_synthetic_city_baseline().set_index("city")
    high = df.loc[["Mumbai", "Delhi NCR"], "synthetic_price_to_income_ratio"].min()
    low = df.loc[["Kolkata", "Ahmedabad"], "synthetic_price_to_income_ratio"].max()
    assert high > low
