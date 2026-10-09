"""app/components/freshness.py: stale project modules are reloaded in place."""
from __future__ import annotations

import os
import sys
import time

from app.components import freshness
from data_sources import loaders


def test_missing_function_restored_after_redeploy_like_state():
    freshness.reload_stale_modules()          # mark everything as current
    del loaders.load_macro_monthly            # simulate the old in-memory module
    os.utime(loaders.__file__)                # ...and a newer file on disk
    time.sleep(0.01)
    reloaded = freshness.reload_stale_modules()
    assert "data_sources.loaders" in reloaded
    assert hasattr(sys.modules["data_sources.loaders"], "load_macro_monthly")
    assert loaders.load_macro_monthly is sys.modules["data_sources.loaders"].load_macro_monthly  # in place


def test_unchanged_modules_are_not_reloaded_again():
    freshness.reload_stale_modules()
    assert "data_sources.loaders" not in freshness.reload_stale_modules()
