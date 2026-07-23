import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import importlib.util
import importlib.machinery
import inspect
import types
from pathlib import Path

import pytest

from calibre_news.orchestrator.utils import load_catalog
from calibre_news.orchestrator.main import RECIPES_DIR

# ---------------------------------------------------------------------------
# Mock the calibre module hierarchy so recipe files can be imported without
# a real Calibre installation.
# ---------------------------------------------------------------------------
_calibre_mod = types.ModuleType("calibre")
_calibre_web_mod = types.ModuleType("calibre.web")
_calibre_feeds_mod = types.ModuleType("calibre.web.feeds")
_calibre_news_mod = types.ModuleType("calibre.web.feeds.news")

_calibre_mod.web = _calibre_web_mod
_calibre_web_mod.feeds = _calibre_feeds_mod
_calibre_feeds_mod.news = _calibre_news_mod


class BasicNewsRecipe:
    pass


_calibre_news_mod.BasicNewsRecipe = BasicNewsRecipe

sys.modules["calibre"] = _calibre_mod
sys.modules["calibre.web"] = _calibre_web_mod
sys.modules["calibre.web.feeds"] = _calibre_feeds_mod
sys.modules["calibre.web.feeds.news"] = _calibre_news_mod


def _recipe_files():
    return sorted(RECIPES_DIR.glob("*.recipe"))


def _import_recipe(slug: str) -> types.ModuleType:
    recipe_path = str(RECIPES_DIR / f"{slug}.recipe")
    loader = importlib.machinery.SourceFileLoader(slug, recipe_path)
    spec = importlib.util.spec_from_loader(slug, loader, origin=recipe_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_recipe_class(module):
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if obj is BasicNewsRecipe:
            continue
        if issubclass(obj, BasicNewsRecipe):
            return obj
    return None


def _catalog_slugs():
    _subject_map, ordered = load_catalog()
    return ordered


def _slug_from_path(recipe_path: Path) -> str:
    return recipe_path.stem


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_recipes_importable():
    for rp in _recipe_files():
        slug = _slug_from_path(rp)
        mod = _import_recipe(slug)
        cls = _find_recipe_class(mod)
        assert cls is not None, f"{slug}.recipe has no BasicNewsRecipe subclass"


def test_recipe_attributes():
    for rp in _recipe_files():
        slug = _slug_from_path(rp)
        mod = _import_recipe(slug)
        cls = _find_recipe_class(mod)
        instance = cls()
        assert instance.oldest_article == 7, f"{slug}: oldest_article mismatch"
        assert instance.compress_news_images is True, f"{slug}: compress_news_images mismatch"
        assert instance.scale_news_images == (1264, 1680), f"{slug}: scale_news_images mismatch"
        assert instance.language == "en", f"{slug}: language mismatch"
        assert hasattr(instance, "description"), f"{slug}: missing description"
        assert hasattr(instance, "publication_type"), f"{slug}: missing publication_type"
        assert hasattr(instance, "extra_css"), f"{slug}: missing extra_css"
        assert instance.auto_cleanup is True, f"{slug}: auto_cleanup should be True"
        assert instance.requires_version is not None, f"{slug}: missing requires_version"


def test_feeds_non_empty_except_parse_index():
    for rp in _recipe_files():
        slug = _slug_from_path(rp)
        if slug == "newschool_headlines":
            continue  # uses parse_index()
        mod = _import_recipe(slug)
        cls = _find_recipe_class(mod)
        instance = cls()
        assert instance.feeds is not None, f"{slug}: feeds should not be None"
        if isinstance(instance.feeds, list):
            assert len(instance.feeds) > 0, f"{slug}: feeds list is empty"


def test_catalog_matches_recipes():
    catalog = _catalog_slugs()
    recipe_slugs = {_slug_from_path(rp) for rp in _recipe_files()}
    for slug in catalog:
        assert slug in recipe_slugs, f"{slug} in CATALOG.md but no .recipe file found"
    for slug in recipe_slugs:
        assert slug in catalog, f"{slug}.recipe exists but no entry in CATALOG.md"
