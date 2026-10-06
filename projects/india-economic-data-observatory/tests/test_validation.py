import numpy as np
import pandas as pd
import pytest

from data_observatory.validation import (
    check_monotonic_increasing,
    check_no_duplicate_periods,
    validate_and_clean_series,
)


def _series(dates, values):
    return pd.Series(values, index=pd.DatetimeIndex(dates))


def test_check_monotonic_increasing_true_and_false():
    assert check_monotonic_increasing(pd.date_range("2000", periods=5, freq="YS"))
    unsorted = pd.DatetimeIndex(["2001-01-01", "2000-01-01", "2002-01-01"])
    assert not check_monotonic_increasing(unsorted)


def test_check_no_duplicate_periods():
    assert check_no_duplicate_periods(pd.date_range("2000", periods=5, freq="YS"))
    dupes = pd.DatetimeIndex(["2000-01-01", "2000-01-01", "2001-01-01"])
    assert not check_no_duplicate_periods(dupes)


def test_validate_sorts_unsorted_index():
    s = _series(["2002-01-01", "2000-01-01", "2001-01-01"], [3.0, 1.0, 2.0])
    frame, report = validate_and_clean_series(s, "test indicator")
    assert frame.index.is_monotonic_increasing
    assert not report.was_monotonic_on_input
    assert list(frame["value"]) == [1.0, 2.0, 3.0]


def test_validate_deduplicates_keeping_last():
    s = _series(
        ["2000-01-01", "2000-01-01", "2001-01-01"],
        [1.0, 1.5, 2.0],  # second 2000 observation is a "revision"
    )
    frame, report = validate_and_clean_series(s, "test indicator")
    assert len(frame) == 2
    assert report.n_duplicates_removed == 1
    assert frame.loc["2000-01-01", "value"] == 1.5


def test_validate_flags_out_of_domain_as_imputed_after_ffill():
    # Negative unemployment rate is impossible; should become NaN, then be
    # forward-filled from the prior valid value, and flagged as imputed.
    s = _series(
        ["2000-01-01", "2001-01-01", "2002-01-01"],
        [5.0, -3.0, 6.0],
    )
    frame, report = validate_and_clean_series(s, "unemployment rate", value_bounds=(0.0, 100.0))
    assert report.n_out_of_domain == 1
    assert frame.loc["2001-01-01", "value"] == 5.0  # forward-filled from 2000
    assert bool(frame.loc["2001-01-01", "imputed"]) is True
    assert bool(frame.loc["2000-01-01", "imputed"]) is False
    assert bool(frame.loc["2002-01-01", "imputed"]) is False


def test_validate_handles_missing_values_with_explicit_flag():
    s = _series(
        ["2000-01-01", "2001-01-01", "2002-01-01"],
        [10.0, np.nan, 12.0],
    )
    frame, report = validate_and_clean_series(s, "test indicator")
    assert report.n_imputed == 1
    assert frame.loc["2001-01-01", "value"] == 10.0
    assert frame["imputed"].sum() == 1


def test_validate_leading_missing_value_cannot_be_ffilled():
    s = _series(
        ["2000-01-01", "2001-01-01"],
        [np.nan, 5.0],
    )
    frame, report = validate_and_clean_series(s, "test indicator")
    assert pd.isna(frame.loc["2000-01-01", "value"])
    assert any("leading" in issue for issue in report.issues)


def test_clean_series_reports_is_clean_true_when_nothing_to_fix():
    s = _series(["2000-01-01", "2001-01-01"], [1.0, 2.0])
    frame, report = validate_and_clean_series(s, "test indicator", value_bounds=(0.0, 10.0))
    assert report.is_clean
    assert "no issues found" in report.summary()


def test_validate_rejects_non_datetime_index():
    s = pd.Series([1, 2, 3], index=[0, 1, 2])
    with pytest.raises(TypeError):
        validate_and_clean_series(s, "bad indicator")
