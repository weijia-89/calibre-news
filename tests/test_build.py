"""Tests for the Calibre-native build system."""

import io
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))


def _patch_catalog(text):
    """Helper: patch Path.read_text on the CATALOG_PATH to return ``text``.

    Python ≥3.14 makes ``PosixPath.read_text`` read-only; ``patch.object``
    on an instance attribute fails.  We mock the *class* method.
    """
    from calibre_news.build import CATALOG_PATH
    from pathlib import Path as PathCls

    def _fake_read_text(self, encoding=None):
        _ = self  # unused — return the fixture text regardless of which Path
        return text

    return patch.object(PathCls, "read_text", _fake_read_text), CATALOG_PATH


@pytest.fixture
def reset_sys_modules():
    """Ensure calibre_news modules are clean between tests."""
    yield


# ---------------------------------------------------------------------------
# load_catalog tests
# ---------------------------------------------------------------------------

class TestCatalogParsing:

    def test_load_catalog_expected_shape(self):
        """Parse real CATALOG.md, assert 5 subjects and 16 slugs."""
        from calibre_news.build import load_catalog

        subject_map, ordered = load_catalog()
        assert "tech" in subject_map
        assert "consumer" in subject_map
        assert "security" in subject_map
        assert "local" in subject_map
        assert "news" in subject_map
        assert len(subject_map["tech"]) == 5
        assert len(subject_map["consumer"]) == 1
        assert len(subject_map["security"]) == 3
        assert len(subject_map["local"]) == 3
        assert len(subject_map["news"]) == 4
        assert len(ordered) == 16

    def test_load_catalog_ordered_consistent(self):
        """Ordered list matches concatenation of subject lists."""
        from calibre_news.build import load_catalog

        subject_map, ordered = load_catalog()
        reconstructed = []
        for slugs in subject_map.values():
            reconstructed.extend(slugs)
        assert ordered == reconstructed

    def test_load_catalog_rejects_unknown_subject(self):
        """Malformed catalog with unknown subject raises ValueError."""
        from calibre_news.build import load_catalog

        mock, _ = _patch_catalog("```\nunknown_subj : slug1\n```")
        with mock:
            with pytest.raises(ValueError, match="unknown subject"):
                load_catalog()

    def test_load_catalog_rejects_empty_slugs(self):
        """Subject line with no slugs raises ValueError."""
        from calibre_news.build import load_catalog

        mock, _ = _patch_catalog("```\ntech :\n```")
        with mock:
            with pytest.raises(ValueError, match="has no slugs"):
                load_catalog()

    def test_load_catalog_rejects_empty(self):
        """Catalog with zero subjects raises ValueError."""
        from calibre_news.build import load_catalog

        mock, _ = _patch_catalog("```\n```")
        with mock:
            with pytest.raises(ValueError, match="parsed empty"):
                load_catalog()


# ---------------------------------------------------------------------------
# find_ebook_convert tests
# ---------------------------------------------------------------------------

class TestFindEbookConvert:

    def test_find_ebook_convert_raises_when_not_found(self):
        """When Calibre is not on PATH and macOS fallback absent, raises."""
        from calibre_news._calibre import find_ebook_convert
        import shutil

        # Patch PATH to not find it
        with patch.object(shutil, "which", return_value=None):
            # Patch the macOS fallback file check to fail
            with patch.object(Path, "is_file", return_value=False):
                with pytest.raises(FileNotFoundError, match="Calibre ebook-convert"):
                    find_ebook_convert()

    @pytest.fixture
    def mock_calibre_path(self):
        import shutil
        _orig_which = shutil.which
        return _orig_which

    def test_find_on_path(self, mock_calibre_path):
        """When ebook-convert is on PATH, return it."""
        from calibre_news._calibre import find_ebook_convert
        import shutil

        with patch.object(shutil, "which", return_value="/usr/local/bin/ebook-convert"):
            result = find_ebook_convert()
            assert result == Path("/usr/local/bin/ebook-convert")


# ---------------------------------------------------------------------------
# dry-run tests
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_dry_run_prints_expected_commands(self):
        """Given --dry-run --slug rtings, prints ebook-convert command."""
        from calibre_news.build import main
        import subprocess

        # Simulate CPython finding function importable (ProcessPoolExecutor
        # needs picklable top-levels — not relevant for dry-run, but we mock
        # to avoid real calibre binary check.
        with patch("sys.argv", ["getnews", "--dry-run", "--slug", "rtings"]):
            with patch("calibre_news.build.find_ebook_convert",
                       return_value=Path("/fake/ebook-convert")):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    main()
                output = captured.getvalue()
                assert "ebook-convert" in output
                assert "rtings" in output.lower()


# ---------------------------------------------------------------------------
# prune tests
# ---------------------------------------------------------------------------

class TestPruning:

    def test_prune_old_epubs_cleans(self, tmp_path):
        """Prune removes EPUBs with old mtime, keeps new ones."""
        from calibre_news.build import prune_old_epubs
        from calibre_news._calibre import PRUNE_DAYS

        epub_old = tmp_path / "old_file.epub"
        epub_new = tmp_path / "new_file.epub"
        epub_old.write_text("old content")
        epub_new.write_text("new content")

        old_time = time.time() - (PRUNE_DAYS + 1) * 86400
        os.utime(str(epub_old), (old_time, old_time))

        with patch("calibre_news.build.OUTPUT_ROOT", tmp_path):
            with patch("sys.stdout", io.StringIO()):
                prune_old_epubs()

        assert not epub_old.exists()
        assert epub_new.exists()


# ---------------------------------------------------------------------------
# exit-code tests
# ---------------------------------------------------------------------------

class TestExitCodes:

    def test_invalid_subject_exits_2(self):
        """Unknown --subject gives exit code 2."""
        from calibre_news.build import main

        with patch("sys.argv", ["getnews", "--subject", "nonexistent"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_missing_slug_exits_2(self):
        """Unknown --slug exits with code 2."""
        from calibre_news.build import main

        with patch("sys.argv", ["getnews", "--slug", "nonexistent"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_partial_failure_exits_1(self):
        """When one slug's ebook-convert fails, exit code is 1."""
        import subprocess
        from calibre_news.build import main

        with patch("sys.argv", ["getnews", "--slug", "rtings"]):
            with patch("calibre_news.build.find_ebook_convert",
                       return_value=Path("/fake/ebook-convert")):
                with patch.object(subprocess, "run",
                                  side_effect=subprocess.CalledProcessError(1, [], stderr="fake fail")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

    def test_prune_only_wins_over_no_prune(self):
        """When both --prune-only and --no-prune, --prune-only wins (no build)."""
        from calibre_news.build import main

        # Patch prune_old_epubs to be a no-op so we don't touch real files
        with patch("sys.argv", ["getnews", "--prune-only", "--no-prune"]):
            with patch("calibre_news.build.prune_old_epubs"):
                # Should NOT call load_catalog or find_ebook_convert — returns early
                main()  # no SystemExit = prune_only short-circuited correctly


# ---------------------------------------------------------------------------
# for_review tests
# ---------------------------------------------------------------------------

class TestForReview:

    def setup_method(self):
        """Ensure output/review dir is clean."""
        from calibre_news.for_review import OUTPUT_ROOT
        review_dir = OUTPUT_ROOT / "review"
        if review_dir.exists():
            for f in review_dir.glob("*.recipe"):
                f.unlink()

    def test_missing_recipe_exits_2(self):
        """When slug has no recipe, exit code 2."""
        from calibre_news.for_review import main

        with patch("sys.argv", ["for_review", "nonexistent"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_missing_html_exits_2(self):
        """When default HTML (for_review/<slug>.html) not present, exit 2."""
        from calibre_news.for_review import main

        with patch("sys.argv", ["for_review", "rtings"]):
            # rtings.recipe exists but for_review/rtings.html likely doesn't
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2