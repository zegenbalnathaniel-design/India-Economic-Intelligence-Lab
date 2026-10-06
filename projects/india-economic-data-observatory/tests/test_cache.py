import pandas as pd
import pytest

from data_observatory import cache


@pytest.fixture(autouse=True)
def _isolated_cache_dir(tmp_path, monkeypatch):
    """Point the cache at a throwaway directory so tests never touch the
    real data/cache/ folder and never interfere with each other."""
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
    yield
    cache.clear_cache()


def _sample_frame():
    idx = pd.date_range("2000-01-01", periods=5, freq="YS")
    return pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0], "imputed": [False] * 5}, index=idx)


def test_read_from_cache_returns_none_when_absent():
    assert cache.read_from_cache("gdp", "2000", "2020", "official") is None


def test_write_then_read_round_trip():
    frame = _sample_frame()
    cache.write_to_cache("gdp", "2000", "2020", "official", frame)
    loaded = cache.read_from_cache("gdp", "2000", "2020", "official")
    assert loaded is not None
    assert list(loaded["value"]) == list(frame["value"])


def test_different_status_keys_do_not_collide():
    frame_live = _sample_frame()
    frame_synth = _sample_frame()
    frame_synth["value"] = frame_synth["value"] * -1
    cache.write_to_cache("gdp", "2000", "2020", "official", frame_live)
    cache.write_to_cache("gdp", "2000", "2020", "illustrative_synthetic", frame_synth)

    loaded_live = cache.read_from_cache("gdp", "2000", "2020", "official")
    loaded_synth = cache.read_from_cache("gdp", "2000", "2020", "illustrative_synthetic")
    assert list(loaded_live["value"]) != list(loaded_synth["value"])


def test_different_date_ranges_do_not_collide():
    cache.write_to_cache("gdp", "2000", "2010", "official", _sample_frame())
    assert cache.read_from_cache("gdp", "2000", "2020", "official") is None


def test_clear_cache_removes_files_and_reports_count():
    cache.write_to_cache("gdp", "2000", "2020", "official", _sample_frame())
    cache.write_to_cache("cpi", "2000", "2020", "official", _sample_frame())
    removed = cache.clear_cache()
    assert removed == 2
    assert cache.read_from_cache("gdp", "2000", "2020", "official") is None


def test_safe_key_sanitizes_special_characters():
    key = cache._safe_key("gdp per capita!", "2000-01-01", "2020-01-01", "official")
    assert all(c.isalnum() or c in "_.-" for c in key)
