import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

from calibre_news.orchestrator.main import run, OUTPUT_ROOT, _load_recipe_config, _prune_old_epubs


def setup_module(module):
    if OUTPUT_ROOT.exists() and "calibre-news" in str(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)


def teardown_module(module):
    if OUTPUT_ROOT.exists() and "calibre-news" in str(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)


@patch("calibre_news.orchestrator.main.convert_to_epub")
@patch("calibre_news.orchestrator.main.fetch_article")
def test_run_creates_subject_dirs(mock_fetch, mock_convert):
    """Verify the orchestrator creates subject directories and calls
    convert_to_epub for each slug."""
    mock_fetch.return_value = "<html><body>stub</body></html>"
    run()
    subject_dirs = [p for p in OUTPUT_ROOT.iterdir() if p.is_dir()]
    assert subject_dirs, "No subject directories were created"
    assert len(subject_dirs) == 5, f"Expected 5 subject dirs, got {len(subject_dirs)}"
    assert {d.name for d in subject_dirs} == {
        "tech", "consumer", "security", "local", "news"
    }
    # Config function returns correct keys
    config = _load_recipe_config("digitalapplied")
    assert "scale_images" in config
    assert "compress_images" in config
    assert "extra_args" in config
    # convert_to_epub was called at least once
    assert mock_convert.call_count > 0


def test_load_recipe_config_defaults():
    config = _load_recipe_config("nonexistent")
    assert config["scale_images"] == (1264, 1680)
    assert config["compress_images"] is True
    assert config["extra_args"] == ["--base-font-size=12", "--linearize-tables"]


def test_load_recipe_config_known_slug():
    config = _load_recipe_config("digitalapplied")
    assert "scale_images" in config
    assert "compress_images" in config
    assert "extra_args" in config


@patch("calibre_news.orchestrator.main.OUTPUT_ROOT")
def test_prune_old_epubs(mock_root):
    """_prune_old_epubs should not crash when called on a non-existent dir."""
    mock_root.rglob.return_value = []
    _prune_old_epubs()
    mock_root.rglob.assert_called_once_with("*.epub")
