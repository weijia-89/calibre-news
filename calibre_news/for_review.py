"""Calibre News Aggregator for_review workflow.

Copies a site's recipe, appends a parse_index() override that reads a saved
HTML file, and runs ebook-convert on the modified recipe. Useful for testing
cleanup settings against real page content.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ._calibre import find_ebook_convert, OUTPUT_PROFILE

RECIPES_DIR = Path(__file__).resolve().parent / "recipes"
FOR_REVIEW_DIR = Path(__file__).resolve().parents[1] / "for_review"
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "output"


def main():
    parser = argparse.ArgumentParser(
        description="Test recipe cleanup settings against a saved HTML file"
    )
    parser.add_argument("slug", help="Site slug (must match a .recipe file)")
    parser.add_argument("html_file", nargs="?", help="Path to saved HTML (default: for_review/<slug>.html)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-process timeout in seconds (default: 120)")
    args = parser.parse_args()

    slug = args.slug
    recipe_src = RECIPES_DIR / f"{slug}.recipe"
    if not recipe_src.is_file():
        print(f"No recipe found for {slug}: {recipe_src}", file=sys.stderr)
        sys.exit(2)

    html_file = args.html_file or FOR_REVIEW_DIR / f"{slug}.html"
    if not html_file.is_file():
        print(f"Stub file not found: {html_file}", file=sys.stderr)
        sys.exit(2)

    review_dir = OUTPUT_ROOT
    review_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        recipe_dst = Path(tmpdir) / f"{slug}.recipe"
        shutil.copy2(recipe_src, recipe_dst)

        override = '''

# for_review overrides — appended programmatically
feeds = []
def parse_index(self):
    # reads HTML from for_review/{slug}.html, returns a single article
    import re
    from calibre.ebooks.BeautifulSoup import BeautifulSoup
    with open('for_review/{slug}.html', 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html)
    title = soup.title.string if soup.title else '{slug}'
    return [('Articles', [{{
        'title': title,
        'url': f'file://for_review/{slug}.html',
        'content': str(soup),
    }}])]
'''.format(slug=slug)
        with open(recipe_dst, "a", encoding="utf-8") as f:
            f.write(override)

        calibre_bin = str(find_ebook_convert())
        epub_path = review_dir / f"{slug}.epub"
        cmd = [
            calibre_bin,
            str(recipe_dst),
            str(epub_path),
            f"--output-profile={OUTPUT_PROFILE}",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=args.timeout)
            print(f"[OK] Review EPUB written to {epub_path}")
        except subprocess.TimeoutExpired:
            print(f"[FAIL] Timeout after {args.timeout}s", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] {e.stderr.strip() or e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()