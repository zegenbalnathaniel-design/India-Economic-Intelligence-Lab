"""Keep project modules outside app/ current after a redeploy.

Streamlit only watches files inside the main script's folder (app/) and on
PYTHONPATH. data_sources/ and analysis/ sit at the repo root, so after a
git pull on Streamlit Community Cloud the pages (inside app/) re-run with
new code while `data_sources.loaders` and `analysis.*` stay as the old
objects in sys.modules -- and a page calling a newly added function fails
with AttributeError / ImportError until the app is rebooted.

app/components/ is inside app/, but in practice its modules were not
reloaded either (verified: a changed home_theme.py kept serving the old
carousel script until restart), so it is covered too.

Every page calls `reload_stale_modules()` before importing those packages.
A module is reloaded (in place, so existing references see the new code)
when its file has changed since it was last loaded, or the first time this
helper sees it in a process. Packages are reloaded before their modules and
data_sources before analysis, which imports it.
"""
from __future__ import annotations

import importlib
import os
import sys
import threading

PACKAGES = ("data_sources", "analysis", "app.components")
# Never reload this module from inside its own function.
_SKIP = {__name__}
_MARK = "__ieil_loaded_mtime__"
_lock = threading.Lock()


def _mtime(module) -> float | None:
    path = getattr(module, "__file__", None)
    try:
        return os.path.getmtime(path) if path else None
    except OSError:
        return None


def reload_stale_modules() -> list[str]:
    """Reload stale project modules; return the names reloaded."""
    reloaded: list[str] = []
    with _lock:
        for pkg in PACKAGES:
            names = sorted(
                (n for n in list(sys.modules) if n == pkg or n.startswith(pkg + ".")),
                key=lambda n: (n.count("."), n),  # package __init__ first
            )
            for name in names:
                module = sys.modules.get(name)
                if module is None or name in _SKIP:
                    continue
                current = _mtime(module)
                if current is None or getattr(module, _MARK, None) == current:
                    continue
                try:
                    module = importlib.reload(module)
                except Exception:  # a broken module will surface on its own import
                    continue
                setattr(module, _MARK, current)
                reloaded.append(name)
    return reloaded
