"""Calibre News Aggregator orchestrator.

This script reads the site catalog, generates a placeholder article URL for each
site, fetches the HTML (or uses a stub from ``for_review`` if present), applies
any site‑specific cleanup (not yet implemented), and converts the result to an
EPUB using Calibre.

A 7‑day rolling window is enforced by discarding any EPUB files older than 7
days.
"""

import sys
import datetime
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from .utils import load_catalog, fetch_article, convert_to_epub

# Directory where operator can drop manual HTML files
FOR_REVIEW_DIR = Path(__file__).resolve().parents[2] / "for_review"
# Output root – grouped by subject
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "output"

RECIPES_DIR = Path(__file__).resolve().parent.parent / "recipes"

def _load_recipe_config(slug: str) -> dict:
    """Return static default config for a site.

    Currently returns the same defaults regardless of whether a recipe file
    exists. In a future iteration this will parse ``<slug>.recipe`` for
    image‑scaling overrides.
    """
    return {
        "scale_images": (1264, 1680),
        "compress_images": True,
        "extra_args": ["--base-font-size=12", "--linearize-tables"],
    }


def _slug_to_url(slug: str) -> str:
    """PLACEHOLDER: generate a URL for direct HTML fetch.

    Uses ``nonexistent.invalid`` (RFC 2606 reserved, guaranteed to never
    resolve) so every live fetch will fail, forcing the operator to provide a
    ``for_review/<slug>.html`` stub. Real per‑site RSS/feed URLs belong in the
    recipe files under ``calibre_news/recipes/``.
    """
    return f"https://nonexistent.invalid/{slug}/article.html"

def _maybe_load_stub(slug: str) -> Path | None:
    """If the operator supplied a manual HTML file for *slug*, return its path.

    The filename must be ``for_review/<slug>.html``.
    """
    candidate = FOR_REVIEW_DIR / f"{slug}.html"
    return candidate if candidate.is_file() else None

def _process_slug(slug: str, subject: str) -> None:
    cfg = _load_recipe_config(slug)
    stub_path = _maybe_load_stub(slug)
    tmp_dir: Path | None = None
    if stub_path:
        html_path = stub_path
    else:
        url = _slug_to_url(slug)
        try:
            html_content = fetch_article(url)
        except Exception as e:
            print(f"[WARN] Unable to fetch {url}: {e}", file=sys.stderr)
            return
        tmp_dir = Path(tempfile.mkdtemp(prefix="calibre-news-"))
        html_path = tmp_dir / f"{slug}.html"
        html_path.write_text(html_content)
    dest_dir = OUTPUT_ROOT / subject
    dest_dir.mkdir(parents=True, exist_ok=True)
    epub_path = dest_dir / f"{slug}.epub"
    epub_existed_before = epub_path.exists()
    try:
        convert_to_epub(
            html_path,
            epub_path,
            scale_images=cfg.get("scale_images"),
            compress_images=cfg.get("compress_images", True),
            extra_args=cfg.get("extra_args"),
        )
    except Exception as e:
        if not epub_existed_before:
            epub_path.unlink(missing_ok=True)
        print(f"[ERROR] Conversion failed for {slug}: {e}", file=sys.stderr)
        return
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Generated EPUB for {slug} -> {epub_path}")

def _prune_old_epubs() -> None:
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for epub in OUTPUT_ROOT.rglob("*.epub"):
        mtime = datetime.datetime.fromtimestamp(epub.stat().st_mtime)
        if mtime < cutoff:
            epub.unlink(missing_ok=True)
            print(f"Pruned old EPUB: {epub}")

def run() -> None:
    subject_to_slugs, ordered_slugs = load_catalog()
    subject_map = {}
    for subject, slugs in subject_to_slugs.items():
        for s in slugs:
            subject_map[s] = subject
    for slug in ordered_slugs:
        subject = subject_map.get(slug, "misc")
        _process_slug(slug, subject)
    _prune_old_epubs()

if __name__ == "__main__":
    run()
