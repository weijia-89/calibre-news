import shutil
from pathlib import Path

PRUNE_DAYS = 7
OUTPUT_PROFILE = "kindle_oasis"


def find_ebook_convert() -> Path:
    """Locate the Calibre ``ebook-convert`` binary.

    Checks ``PATH`` first (via ``shutil.which``), then falls back to the
    macOS default installation path. Raises ``FileNotFoundError`` if neither
    exists.
    """
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