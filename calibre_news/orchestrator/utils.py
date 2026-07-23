import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple

# Path to the catalog file (single source of truth)
CATALOG_PATH = Path(__file__).resolve().parents[2] / "docs" / "CATALOG.md"

def _extract_catalog_section() -> Tuple[Dict[str, List[str]], List[str]]:
    """Parse the CATALOG.md file.

    Returns a tuple of (subject_to_slugs, ordered_slugs).
    """
    subject_to_slugs: Dict[str, List[str]] = {}
    ordered_slugs: List[str] = []
    in_block = False
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        # Expected format: subject : slug1, slug2, ...
        if ":" not in line:
            continue
        subject, slugs = line.split(":", 1)
        subject = subject.strip()
        slugs_list = [s.strip() for s in slugs.split(",") if s.strip()]
        subject_to_slugs[subject] = slugs_list
        ordered_slugs.extend(slugs_list)
    return subject_to_slugs, ordered_slugs

def load_catalog() -> Tuple[Dict[str, List[str]], List[str]]:
    """Public helper to load catalog data."""
    return _extract_catalog_section()

def fetch_article(url: str) -> str:
    """Fetch HTML content for a given URL.

    For the purpose of this prototype we use ``curl`` with a short timeout.
    Returns the raw HTML string.
    """
    result = subprocess.run(
        ["curl", "-sL", "--max-time", "10",
         "-A", "Mozilla/5.0 (compatible; CalibreNews/0.1)",
         url],
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch {url}: {result.stderr}")
    return result.stdout

def _find_calibre_bin() -> Path:
    """Locate the Calibre ``ebook-convert`` binary.

    Checks ``PATH`` first (via ``shutil.which``), then falls back to the
    macOS default installation path. Raises ``FileNotFoundError`` if neither
    exists.
    """
    import shutil
    path = shutil.which("ebook-convert")
    if path:
        return Path(path)
    fallback = Path("/Applications/calibre.app/Contents/MacOS/ebook-convert")
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(
        "Calibre ebook-convert binary not found. "
        "Install Calibre from https://calibre-ebook.com or place it on your PATH."
    )


_CALIBRE_BIN: Path | None = None

def _get_calibre_bin() -> Path:
    global _CALIBRE_BIN
    if _CALIBRE_BIN is None:
        _CALIBRE_BIN = _find_calibre_bin()
    return _CALIBRE_BIN


def convert_to_epub(
    html_path: Path,
    epub_path: Path,
    profile: str = "kindle_oasis",
    scale_images: tuple[int, int] | None = (1264, 1680),
    compress_images: bool = True,
    extra_args: list[str] | None = None,
) -> None:
    """Convert a single HTML file to EPUB using Calibre's ``ebook-convert``.

    ``profile`` must be a valid Calibre output profile.

    When using recipe-based conversion (``calibre-ebook-convert`` with a Python
    recipe), image resizing and compression are set as class properties on the
    recipe itself (``scale_news_images``, ``compress_news_images``). For direct
    HTML-to-EPUB conversion those properties are not available; this wrapper
    instead passes ``extra_args`` to the CLI tool for equivalent behaviour.
    """
    calibre_bin = str(_get_calibre_bin())
    cmd = [
        calibre_bin,
        str(html_path),
        str(epub_path),
        f"--output-profile={profile}",
    ]
    if extra_args:
        cmd.extend(extra_args)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
