import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from calibre_news.orchestrator.utils import load_catalog, CATALOG_PATH

def test_load_catalog_returns_data():
    subject_map, ordered = load_catalog()
    # Ensure we have at least the known subjects
    assert "tech" in subject_map
    assert isinstance(ordered, list)
    assert len(ordered) > 0
    # Verify that the catalog file path is correct
    assert CATALOG_PATH.is_file()


