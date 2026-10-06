import pandas as pd
import pytest

from data_observatory import cache, loaders
from data_observatory.metadata import DataStatus


@pytest.fixture(autouse=True)
def _isolated_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
    yield


ALL_KEYS = list(loaders.INDICATORS.keys())


def test_registry_covers_every_required_category():
    categories = loaders.list_categories()
    expected = {"Growth", "Prices", "Labour", "Government", "External sector", "Financial system"}
    assert expected.issubset(categories.keys())


@pytest.mark.parametrize("key", ALL_KEYS)
def test_every_indicator_loads_synthetic_without_network(key):
    frame, meta = loaders.load(key, "2000-01-01", "2020-01-01", allow_live=False)
    assert meta.status is DataStatus.SYNTHETIC
    assert "value" in frame.columns
    assert "imputed" in frame.columns
    assert len(frame) > 0
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert frame.index.is_monotonic_increasing


@pytest.mark.parametrize("key", ALL_KEYS)
def test_metadata_fields_are_populated(key):
    _, meta = loaders.load(key, "2000-01-01", "2020-01-01", allow_live=False)
    assert meta.indicator
    assert meta.provider
    assert meta.url.startswith("http")
    assert meta.unit
    assert meta.frequency
    assert meta.date_coverage == "2000-01-01 to 2020-01-01"
    assert meta.status is DataStatus.SYNTHETIC
    assert "synthetic" in meta.limitations.lower() or "live fetch" in meta.limitations.lower()


def test_unknown_indicator_key_raises():
    with pytest.raises(KeyError):
        loaders.load("not_a_real_indicator", "2000-01-01", "2020-01-01")


def test_named_wrapper_matches_registry_load():
    frame_a, meta_a = loaders.load_gdp("2000-01-01", "2010-01-01", allow_live=False)
    frame_b, meta_b = loaders.load("gdp", "2000-01-01", "2010-01-01", allow_live=False)
    assert meta_a.indicator == meta_b.indicator
    pd.testing.assert_series_equal(frame_a["value"], frame_b["value"], check_exact=False)


def test_value_bounds_enforced_end_to_end_for_unemployment():
    frame, _ = loaders.load("unemployment_rate", "1995-01-01", "2023-01-01", allow_live=False)
    assert (frame["value"] >= 0).all()
    assert (frame["value"] <= 100).all()


def test_allow_live_false_never_calls_network(monkeypatch):
    """Even if sources.fetch_world_bank_indicator were somehow reachable,
    allow_live=False must short-circuit before it is ever called."""
    called = {"flag": False}

    def _boom(*args, **kwargs):
        called["flag"] = True
        raise AssertionError("live fetch must not be attempted when allow_live=False")

    monkeypatch.setattr(loaders.sources, "fetch_world_bank_indicator", _boom)
    frame, meta = loaders.load("gdp", "2000-01-01", "2010-01-01", allow_live=False)
    assert called["flag"] is False
    assert meta.status is DataStatus.SYNTHETIC


def test_live_fetch_failure_falls_back_to_synthetic_and_labels_it(monkeypatch):
    """Simulate a live endpoint that is reachable but returns nothing
    usable (e.g. malformed response) — the loader must fall back cleanly
    and the resulting Metadata must say so, never claiming 'official'."""
    monkeypatch.setattr(loaders.sources, "fetch_world_bank_indicator", lambda *a, **k: None)
    frame, meta = loaders.load("gdp", "2000-01-01", "2010-01-01", allow_live=True)
    assert meta.status is DataStatus.SYNTHETIC
    assert "live fetch" in meta.limitations.lower()


def test_live_fetch_success_is_labeled_official(monkeypatch):
    """Simulate a successful live fetch and confirm it is labeled
    official and the real values are passed through (post validation)."""
    fake_series = pd.Series(
        [1.0e12, 1.05e12, 1.1e12],
        index=pd.to_datetime(["2000-01-01", "2001-01-01", "2002-01-01"]),
    )
    monkeypatch.setattr(loaders.sources, "fetch_world_bank_indicator", lambda *a, **k: fake_series)
    frame, meta = loaders.load("gdp", "2000-01-01", "2002-01-01", allow_live=True)
    assert meta.status is DataStatus.OFFICIAL
    assert list(frame["value"]) == [1.0e12, 1.05e12, 1.1e12]


def test_bank_credit_growth_postprocess_applies_first_difference(monkeypatch):
    fake_series = pd.Series(
        [40.0, 42.0, 45.0],
        index=pd.to_datetime(["2000-01-01", "2001-01-01", "2002-01-01"]),
    )
    monkeypatch.setattr(loaders.sources, "fetch_world_bank_indicator", lambda *a, **k: fake_series)
    frame, meta = loaders.load("bank_credit_growth", "2000-01-01", "2002-01-01", allow_live=True)
    assert meta.status is DataStatus.OFFICIAL
    # diff() of [40, 42, 45] -> [nan, 2, 3] -> dropna -> [2, 3]
    assert list(frame["value"]) == [2.0, 3.0]


def test_rbi_and_mospi_sources_have_no_wb_code_but_attempt_live_probe():
    assert loaders.INDICATORS["policy_rate"].wb_code is None
    assert loaders.INDICATORS["policy_rate"].live_probe is not None
    assert loaders.INDICATORS["wpi"].wb_code is None
    assert loaders.INDICATORS["wpi"].live_probe is not None


def test_caching_round_trip_for_synthetic_result():
    frame1, meta1 = loaders.load("cpi", "2000-01-01", "2010-01-01", allow_live=False)
    frame2, meta2 = loaders.load("cpi", "2000-01-01", "2010-01-01", allow_live=False)
    # frame2 round-trips through the on-disk CSV cache written by frame1's
    # load, so compare with float tolerance rather than bit-exactness.
    pd.testing.assert_series_equal(frame1["value"], frame2["value"], check_exact=False, atol=1e-6)
    assert meta1.status == meta2.status == DataStatus.SYNTHETIC
