# Changelog

## [Unreleased]

### Added (v0.2.0 - `feat/recipe-feed-upgrades`)

- **`getnews` console script.** Single command builds all 20 site EPUBs grouped by subject. Installed via `pip install -e .` as `getnews`, backed by `calibre_news.cli:main` in `pyproject.toml`.
- **Calibre-native conversion.** The old Python orchestrator is gone. `build.py` calls `ebook-convert` directly on `.recipe` files. Calibre handles RSS fetching, image resizing (1264×1680, Kindle Oasis profile), article-age filtering, and HTML cleanup. No curl, no temp HTML, no manual fetch logic.
- **Parallel execution.** `build.py` dispatches `ebook-convert` processes through `concurrent.futures.ProcessPoolExecutor` with `as_completed()`. One hung site does not stall the whole run, it times out and the rest continue.
- **for_review workflow.** `python -m calibre_news.for_review <slug>` copies a recipe into a temp directory, appends a `parse_index()` override that reads saved HTML from `for_review/<slug>.html`, runs `ebook-convert`, then cleans up. The operator iterates cleanup settings against real page content without live RSS fetches.
- **CLI flags:** `--subject`, `--slug`, `--parallel`, `--timeout`, `--prune-only`, `--no-prune`, `--dry-run`. Exit codes: 0 (all OK), 1 (partial failure), 2 (configuration error, Calibre missing, catalog malformed).
- **Makefile.** `make`, `make tech`, `make consumer`, `make security`, `make local`, `make news`, `make prune`, `make dry-run`.
- **Catalog validation.** `load_catalog()` enforces locked subject taxonomy (tech, consumer, security, local, news). Rejects unknown subjects, empty slug lists, and empty catalogs. Malformed or missing `docs/CATALOG.md` exits with code 2.
- **20 site recipes** updated with real RSS feeds, `description` metadata, shared `remove_tags` blocks, `extra_css`, and `publication_type` annotations.
- **Recipe test generalization.** `test_feeds_or_parse_index_present` now accepts either a non-empty `feeds` list or a custom `parse_index()` method, replacing the old `newschool_headlines` carve-out.
- **ADR-001** accepted. Architecture Decision Record tracks the orchestrator removal and Calibre-native rationale.
- **README, USAGE.md, CHANGELOG.md, SECURITY.md.** User-facing docs match shipped CLI surface.

### Removed (v0.2.0)

- `calibre_news/orchestrator/` directory. All fetch logic replaced by Calibre's built-in RSS handling via `.recipe` files.
- `tests/test_orchestrator.py`, `tests/test_utils.py`. Replaced by `tests/test_build.py` with catalog, exit-code, prune, dry-run, and for_review tests.

### Fixed (v0.2.0)

- `find_ebook_convert()` is called once in `main()` before the executor starts. If Calibre is missing, exit 2 happens immediately, not per-worker inside the process pool.
- `for_review.py` recipe mutation now runs inside `tempfile.TemporaryDirectory`, never inside `output/review/`.

## [0.1.0] - 2026-07-23

### Added

- Initial commit: project scaffold, 20 Calibre `.recipe` stubs, orchestrator (`main.py` + `utils.py`), basic test suite, `CATALOG.md` subject taxonomy.
- Calibre image constants: `scale_news_images = (1264,1680)`, `compress_news_images = True`, `output_profile = 'kindle_oasis'`.
- Pruning: EPUBs older than 7 days (`PRUNE_DAYS`) deleted automatically.