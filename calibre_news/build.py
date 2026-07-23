"""Calibre News Aggregator build driver.

Reads the site catalog, converts each recipe to EPUB via Calibre's
``ebook-convert``, groups output by subject, and prunes EPUBs older than
``PRUNE_DAYS``.
"""

import argparse
import concurrent.futures
import os
import subprocess
import sys
import time
from pathlib import Path

from ._calibre import find_ebook_convert, OUTPUT_PROFILE, PRUNE_DAYS

CATALOG_PATH = Path(__file__).resolve().parents[1] / "docs" / "CATALOG.md"
RECIPES_DIR = Path(__file__).resolve().parent / "recipes"
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "output"
VALID_SUBJECTS = frozenset({"tech", "consumer", "security", "local", "news"})


def _extension_from_line(line: str) -> tuple[str, list[str]]:
    """Parse a CATALOG.md data line: ``subject : slug, slug, ...``.

    Raises ``ValueError`` if the subject is not in the locked taxonomy.
    """
    if ":" not in line:
        raise ValueError("catalog line missing colon")
    subject, slugs = line.split(":", 1)
    subject = subject.strip()
    if subject not in VALID_SUBJECTS:
        raise ValueError(f"unknown subject in catalog: {subject!r}")
    slugs_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slugs_list:
        raise ValueError(f"subject {subject!r} has no slugs")
    return subject, slugs_list


def load_catalog():
    """Parse the CATALOG.md file.

    Returns a tuple of (subject_to_slugs, ordered_slugs).
    Raises ``ValueError`` on malformed input.
    """
    subject_to_slugs: dict[str, list[str]] = {}
    ordered_slugs: list[str] = []
    in_block = False
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        subject, slugs_list = _extension_from_line(line)
        if subject in subject_to_slugs:
            raise ValueError(f"duplicate subject in catalog: {subject!r}")
        subject_to_slugs[subject] = slugs_list
        ordered_slugs.extend(slugs_list)
    if not subject_to_slugs:
        raise ValueError("catalog parsed empty — no subject entries found")
    return subject_to_slugs, ordered_slugs


def _build_one(slug: str, subject: str, calibre_bin: str, timeout: int) -> tuple[str, str | None]:
    recipe_path = RECIPES_DIR / f"{slug}.recipe"
    if not recipe_path.is_file():
        return slug, f"Recipe not found: {recipe_path}"

    dest_dir = OUTPUT_ROOT / subject
    dest_dir.mkdir(parents=True, exist_ok=True)
    epub_path = dest_dir / f"{slug}.epub"

    cmd = [
        calibre_bin,
        str(recipe_path),
        str(epub_path),
        f"--output-profile={OUTPUT_PROFILE}",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return slug, None
    except subprocess.TimeoutExpired:
        return slug, f"Timeout after {timeout}s"
    except subprocess.CalledProcessError as e:
        return slug, e.stderr.strip() or str(e)
    except FileNotFoundError as e:
        return slug, str(e)


def prune_old_epubs():
    """Delete EPUBs older than PRUNE_DAYS (seconds)."""
    cutoff = PRUNE_DAYS * 86400
    now = time.time()
    for epub in OUTPUT_ROOT.rglob("*.epub"):
        if now - epub.stat().st_mtime > cutoff:
            epub.unlink(missing_ok=True)
            print(f"Pruned old EPUB: {epub}")


def main():
    parser = argparse.ArgumentParser(description="Build news EPUBs from Calibre recipes")
    parser.add_argument("--subject", help="Build only one subject group")
    parser.add_argument("--slug", help="Build only one site")
    parser.add_argument("--parallel", type=int, default=None,
                        help="Concurrency limit (default: CPU count)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-process timeout in seconds (default: 120)")
    parser.add_argument("--prune-only", action="store_true",
                        help="Skip build, just prune old EPUBs")
    parser.add_argument("--no-prune", action="store_true",
                        help="Skip the automatic prune pass")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing")
    args = parser.parse_args()

    if args.prune_only:
        prune_old_epubs()
        return

    try:
        subject_to_slugs, ordered_slugs = load_catalog()
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Catalog error: {e}", file=sys.stderr)
        sys.exit(2)    

    # Filter by subject
    if args.subject:
        if args.subject not in subject_to_slugs:
            print(f"Unknown subject: {args.subject}", file=sys.stderr)
            sys.exit(2)
        slugs = subject_to_slugs[args.subject]
    else:
        slugs = ordered_slugs

    # Filter by slug
    if args.slug:
        if args.slug not in slugs:
            print(f"Slug {args.slug} not in selected subject", file=sys.stderr)
            sys.exit(2)
        slugs = [args.slug]

    try:
        calibre_bin = str(find_ebook_convert())
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        for slug in slugs:
            subject = next(s for s, lst in subject_to_slugs.items() if slug in lst)
            print(f"{calibre_bin} {RECIPES_DIR}/{slug}.recipe {OUTPUT_ROOT}/{subject}/{slug}.epub --output-profile={OUTPUT_PROFILE}")
        return

    parallel = args.parallel or os.cpu_count() or 4
    failed = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=parallel) as ex:
        futures = {
            ex.submit(_build_one, slug,
                      next(s for s, lst in subject_to_slugs.items() if slug in lst),
                      calibre_bin, args.timeout): slug
            for slug in slugs
        }
        for fut in concurrent.futures.as_completed(futures):
            slug = futures[fut]
            try:
                _, err = fut.result()
                if err:
                    failed.append((slug, err))
                    print(f"[FAIL] {slug}: {err}", file=sys.stderr)
                else:
                    print(f"[OK] {slug}")
            except Exception as e:
                failed.append((slug, str(e)))
                print(f"[FAIL] {slug}: {e}", file=sys.stderr)

    if not args.no_prune:
        prune_old_epubs()

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

