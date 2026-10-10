"""Grouped navigation: every page is registered once with a stable URL,
and every in-app link target resolves to a registered page."""
from __future__ import annotations

import re
from pathlib import Path

from app.components import navigation, terrain_hero, turntable_home

APP = Path(__file__).resolve().parents[1] / "app"

# URLs Streamlit derived from the page file names before navigation was
# grouped; they must not change (bookmarks, shared links).
LEGACY_URLS = {
    "pages/1_Wealth_Inequality_Lab.py": "Wealth_Inequality_Lab",
    "pages/2_Banking_Monetary_Policy_Lab.py": "Banking_Monetary_Policy_Lab",
    "pages/3_State_Economy_Lab.py": "State_Economy_Lab",
    "pages/4_Housing_Intelligence_Lab.py": "Housing_Intelligence_Lab",
    "pages/5_Research.py": "Research",
    "pages/6_Methodology.py": "Methodology",
    "pages/7_Data.py": "Data",
    "pages/8_About.py": "About",
    "pages/9_Limitations.py": "Limitations",
    "pages/10_Economic_Relationships_Lab.py": "Economic_Relationships_Lab",
    "pages/12_Macro_and_World.py": "Macro_and_World",
}


def test_every_page_file_registered_once():
    registered = [p.path for p in navigation.all_pages()]
    assert len(registered) == len(set(registered))
    on_disk = {f"pages/{f.name}" for f in (APP / "pages").glob("*.py")}
    assert on_disk | {"home_page.py"} == set(registered)
    for p in registered:
        assert (APP / p).is_file(), p


def test_url_paths_unique_and_legacy_preserved():
    urls = [p.url_path for p in navigation.all_pages()]
    assert len(urls) == len(set(urls))
    by_path = {p.path: p.url_path for p in navigation.all_pages()}
    for path, url in LEGACY_URLS.items():
        assert by_path[path] == url
    assert by_path["home_page.py"] == ""


def test_all_link_targets_registered():
    registered = {p.path for p in navigation.all_pages()}
    targets = set(terrain_hero.PAGE_FOR_SLUG.values()) | set(turntable_home.PAGE_FOR_SLUG.values())
    for f in list(APP.glob("*.py")) + list((APP / "pages").glob("*.py")) + list((APP / "components").glob("*.py")):
        text = f.read_text()
        targets |= set(re.findall(r"(?:page_link|switch_page)\(\s*\"([^\"]+\.py)\"", text))
        targets |= set(re.findall(r"\"(pages/[^\"]+\.py)\"", text))  # targets kept in tables, e.g. home cards
    missing = targets - registered
    assert not missing, missing
