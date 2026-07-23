# ADR-001: Calibre-native conversion replaces Python orchestrator

**Date:** 2026-07-23
**Status:** Accepted

## Context

The v0.1 orchestrator (`calibre_news/orchestrator/`) fetched article HTML with `curl`, wrote it to a temp file, and passed flat HTML to `ebook-convert`. The 20 `.recipe` files — each a `BasicNewsRecipe` subclass with real RSS feed URLs, image-dimension settings, and HTML cleanup selectors — sat unused by the orchestrator.

This created an architectural gap: recipe settings drifted from actual conversion output. Calibre's built-in RSS fetching, image processing, article-age filtering, and HTML sanitization were all bypassed.

The choice was between fixing the orchestrator's wiring to reference the recipes, or removing the Python layer entirely and letting Calibre do the work it was built for.

## Decision

Remove the orchestrator. Call `ebook-convert` directly on the `.recipe` files. Keep a thin build driver (`build.py`) for catalog reading, subject grouping, parallel dispatch, and EPUB pruning — small enough to stay correct.

Replace `python -m calibre_news.orchestrator.main` with `getnews`, an installable console script (via `pyproject.toml` `[project.scripts]` entry point).

## Rationale

- **No double-config.** Every recipe currently duplicated image parameters inside the orchestrator's `_load_recipe_config()`. In the new system, the recipe file IS the configuration source. No drift possible.
- **Smaller surface area.** The orchestrator was ~200 lines across two modules. The replacement is ~100 lines. Bug probability drops.
- **Calibre handles edge cases we weren't.** RSS feed parsing, image resizing, article date extraction, output-profile optimization — all free, all battle-tested inside `ebook-convert`.
- **Maintenance profile.** Adding a new site = create a `.recipe` file + edit one catalog line. Changing image dimensions or cleanup rules = edit one recipe. No other files touched.
- **Parallel execution.** `ProcessPoolExecutor` allows concurrent `ebook-convert` processes, gated by a per-process timeout. The orchestrator was single-threaded.
- **for_review workflow preserved.** Instead of live `curl` fetch, the operator drops a saved HTML page and runs `python -m calibre_news.for_review <slug>`. This copies the recipe, appends a `parse_index()` override with the local HTML content, and runs `ebook-convert` on the modified recipe — testing cleanup rules against real pages without RSS fetches.

## Consequences

- `calibre_news/orchestrator/` is removed. Any scripts or documentation calling `python -m calibre_news.orchestrator.main` must switch to `getnews` or `python -m calibre_news.build`.
- `tests/test_orchestrator.py` and `tests/test_utils.py` are removed. Replaced by `tests/test_build.py` with catalog parsing, exit-code, pruning, and for_review tests.
- The `for_review/` directory stays but its workflow is now `python -m calibre_news.for_review <slug>` instead of the old orchestrator's automatic stub detection.
- `load_catalog()` moves from `utils.py` into `build.py`. No functional change; same parser, same CATALOG.md.