# Calibre-Native News Aggregation

Date: 2026-07-23

## Motivation

The current orchestrator (`calibre_news/orchestrator/`) fetches article HTML via `curl`, writes it to a temp file, then passes flat HTML to `ebook-convert`. The 20 `.recipe` files — which define RSS feeds, image settings, and HTML cleanup rules — are never used by the orchestrator. This creates an architectural gap: recipe settings drift from actual conversion output, and Calibre's built-in RSS fetching, image processing, and HTML sanitization are bypassed.

## Goals

1. **Calibre-native conversion** — `ebook-convert` is called directly with recipe files, letting Calibre handle RSS fetching, image resizing, article age filtering, and HTML cleanup.
2. **Maintainability** — no Python code to maintain for the daily build path. Recipe files are the single source of truth for per-site configuration.
3. **Extensibility** — adding a new feed = create a `.recipe` file + edit one catalog line. Article sanitization = edit `remove_tags` / `keep_only_tags` in a recipe — no cascading code changes.
4. **Cross-platform** — works on macOS, Linux, Windows without platform-specific code (no `curl`, no hardcoded macOS paths).
5. **Parallel execution** — multiple `ebook-convert` processes run concurrently when building all sites.
6. **for_review workflow preserved** — operator can drop a saved HTML file and run a command to test recipe cleanup settings against real page content.

## Non-goals

- Cross-run deduplication (each run fetches fresh from RSS)
- Article-level caching
- GUI or content server integration
- Per-site `extra_args` overrides (Calibre recipe properties suffice)

## Architecture

### Components

```
Makefile              — convenience targets
calibre_news/
  __init__.py
  cli.py              — entry point exposing `getnews` console script
  build.py            — daily build driver
  for_review.py       — stub-based review workflow
  _calibre.py         — shared `find_ebook_convert()` and `PRUNE_DAYS` constants
  recipes/            — 20 .recipe files (unchanged)
docs/
  CATALOG.md          — subject/slug mapping (unchanged)
  USAGE.md            — updated
```

### build.py

Reads `CATALOG.md`, iterates over all (subject, slug) pairs, and for each calls:

```
ebook-convert calibre_news/recipes/<slug>.recipe output/<subject>/<slug>.epub \
    --output-profile=kindle_oasis
```

Key behaviour:
- **Parallelism:** uses `concurrent.futures.ProcessPoolExecutor` wrapped in a `with` block to run N `ebook-convert` processes concurrently (default: CPU count).
- **Subject grouping:** output directory mirrors CATALOG.md hierarchy (`output/tech/`, `output/security/`, etc.). `newschool_headlines` produces `output/news/newschool_headlines.epub` per CATALOG.md.
- **Pruning:** automatic post-build pass (unless `--no-prune` is set) deletes EPUBs with `mtime` older than `PRUNE_DAYS = 7` (defined in `_calibre.py`). `--prune-only` skips the build entirely and just cleans. If both `--no-prune` and `--prune-only` are passed, `--prune-only` wins.
- **Error handling:** per-slug failures are logged to stderr; other builds continue. Exit codes are: 0 = all OK, 1 = some builds failed, 2 = configuration error (Calibre missing, CATALOG.md malformed, invalid CLI args).
- **Subprocess timeout:** each `ebook-convert` invocation has a hard timeout of 120 seconds (configurable via `--timeout`). On timeout, the worker is marked failed but the executor continues. This prevents one hanging site from stalling the whole run.
- **CLI flags:**
  - `--subject SUBJECT` — build only one subject group
  - `--slug SLUG` — build only one site
  - `--parallel N` — concurrency limit (default: `os.cpu_count()`)
  - `--timeout SECONDS` — per-process timeout (default: 120)
  - `--prune-only` — skip build, just prune old EPUBs
  - `--no-prune` — skip the automatic prune pass
  - `--dry-run` — print commands without executing

**Implementation contracts:**
- The Calibre binary check at startup is skipped if `--prune-only` is the only build action. Pruning operates on filesystem state alone.
- CLI parsing uses Python stdlib `argparse` only. No third-party CLI libraries.
- `OUTPUT_PROFILE` ("kindle_oasis") and `PRUNE_DAYS` (7) live as constants in `_calibre.py`. Single source of truth.
- Use `subprocess.run([...list, ...], check=True, capture_output=True, text=True, timeout=N)`. Never use `os.system`, `shell=True`, or string-shell concatenation.
- Use `pathlib.Path` for all path operations. No string concatenation for paths.
- Catch `subprocess.CalledProcessError`, `subprocess.TimeoutExpired`, `FileNotFoundError` specifically. Never use bare `except:`.
- Wrap `ProcessPoolExecutor` in a `with` block.
- Use `as_completed()` to iterate over futures so one failure doesn't block the others. Collect failed `(slug, exception)` tuples and continue. After all futures complete, exit with code based on whether any `failed` tuples exist.
- Pattern (skeleton):
  ```python
  with ProcessPoolExecutor(max_workers=parallel) as ex:
      futures = {ex.submit(_build_one, slug, subject): slug for slug in slugs}
      failed = []
      for fut in as_completed(futures):
          slug = futures[fut]
          try:
              fut.result()
              print(f"[OK] {slug}")
          except Exception as e:
              failed.append(slug)
              print(f"[FAIL] {slug}: {e}", file=sys.stderr)
  sys.exit(1 if failed else 0)
  ```

### for_review.py

Usage: `python -m calibre_news.for_review <slug> [<html-file>]`

Workflow:
1. Reads the real recipe at `calibre_news/recipes/<slug>.recipe` and copies it to `output/review/<slug>.recipe` (creating the directory if missing).
2. Appends override code to the copied recipe file:
   ```python
   # for_review overrides — appended programmatically
   feeds = []
   def parse_index(self):
       # reads HTML from for_review/<slug>.html, returns a single article
       import re
       from calibre.ebooks.BeautifulSoup import BeautifulSoup
       with open('for_review/<slug>.html', 'r', encoding='utf-8') as f:
           html = f.read()
       soup = BeautifulSoup(html)
       title = soup.title.string if soup.title else '<slug>'
       return [('Articles', [{
           'title': title,
           'url': f'file://for_review/<slug>.html',
           'content': str(soup),
       }])]
   ```
   By overriding `feeds = []` and adding `parse_index()`, we bypass the RSS fetch entirely. The original class properties (`remove_tags`, `keep_only_tags`, `scale_news_images`, `compress_news_images`, etc.) are inherited naturally because we appended to the same class body.
3. Calls `ebook-convert output/review/<slug>.recipe output/review/<slug>.epub --output-profile=kindle_oasis --timeout=120`. The `--timeout` flag here is a Calibre-side timeout for any internal network calls; in addition, for_review.py wraps the call in Python `subprocess.run(timeout=120)` for belt-and-suspenders.
4. Cleans up the appended copy in a `try/finally` block — via either `os.unlink()` (single file) or reverting to the original (track and snapshot the source). Simplest: copy to a temp location, write a brand-new file, run ebook-convert on that file, then delete.
5. Defaults to `for_review/<slug>.html` if no HTML file argument is given.

**Why copy + append (not import-and-subclass):** Calibre's `ebook-convert` runs as Calibre's own Python where `calibre.*` is importable. If we tried `from rtings_recipe import RTINGS`, the temp file's import path wouldn't resolve cleanly without sys.path manipulation. Copying the file preserves its original `from calibre...` imports which Calibre's Python resolves naturally.

**Output location:** `output/review/<slug>.epub` — flat directory, not subject-grouped, since the for_review output is for the operator only and not part of the daily distribution.

### `getnews` CLI entry point

Defined in `pyproject.toml`:

```toml
[project.scripts]
getnews = "calibre_news.cli:main"
```

`calibre_news/cli.py` is a thin module that imports and runs `calibre_news.build`'s main function. After `pip install -e .` or `uv pip install -e .`, the user can run:

```bash
getnews                  # build all
getnews --subject tech   # build just tech
getnews --prune-only     # clean old EPUBs
getnews --dry-run        # preview
```

### Makefile

Convenience wrapper for users who prefer `make`:

```makefile
all:           ; python3 -m calibre_news.build
tech:          ; python3 -m calibre_news.build --subject tech
consumer:      ; python3 -m calibre_news.build --subject consumer
security:      ; python3 -m calibre_news.build --subject security
local:         ; python3 -m calibre_news.build --subject local
news:          ; python3 -m calibre_news.build --subject news
prune:         ; python3 -m calibre_news.build --prune-only
```

### Files removed

| File | Replacement |
|------|-------------|
| `calibre_news/orchestrator/main.py` | `calibre_news/build.py` |
| `calibre_news/orchestrator/utils.py` | removed (`load_catalog` moves inline into `calibre_news/build.py`) |

### Files unchanged

- `calibre_news/recipes/*.recipe` (20 files — same as today)
- `docs/CATALOG.md`
- `tests/test_recipes.py`

### Files removed

- `calibre_news/orchestrator/` (entire directory)
- `tests/test_orchestrator.py`
- `tests/test_utils.py`

## Data flow

```
── daily ──────────────────────────────────────────────────────
CATALOG.md ──→ build.py ──→ for each (subject, slug):
                              ebook-convert <slug>.recipe
                              → output/<subject>/<slug>.epub
                          → prune EPUBs older than 7 days

── for_review ────────────────────────────────────────────────
python -m calibre_news.for_review <slug> [<html-file>]
    → reads <slug>.recipe
    → generates temp recipe with parse_index() + stub HTML
    → ebook-convert <temp.recipe> → output/review/<slug>.epub
    → deletes temp recipe
```

## Error handling

| Scenario | Exit code | Behaviour |
|----------|-----------|-----------|
| `ebook-convert` not found (and not `--prune-only`) | 2 | `build.py` exits with "Calibre ebook-convert not found. Install from https://calibre-ebook.com" |
| Single recipe fails (network, bad feed, timeout) | 1 (at end) | Logged to stderr as `[FAIL] <slug>: <reason>`. Other builds continue. |
| All recipes succeed | 0 | After prune passes. |
| CATALOG.md missing or malformed | 2 | Parse error raised, exit before any build. |
| Output directory unwritable | 1 (per site) | `ebook-convert` fails per-site; error logged, other sites continue. |
| `for_review.py` — slug not found in recipes | 2 | Exit with "No recipe found for <slug>". |
| `for_review.py` — HTML file missing | 2 | Exit with "Stub file not found at <path>". |

## Testing

### Existing tests
- `tests/test_recipes.py` stays, with one update: `test_feeds_non_empty_except_parse_index` is generalized to verify each recipe has EITHER a non-empty `feeds` list OR a defined `parse_index()` method (at least one is required).

### New tests in `tests/test_build.py`
- `test_load_catalog_returns_expected_shape` — parses CATALOG.md, asserts all 5 subjects present, asserts total slug count is 20.
- `test_find_ebook_convert_returns_path_or_raises` — verifies `_calibre.find_ebook_convert()` returns a Path when Calibre is on PATH or under the macOS default install; raises `FileNotFoundError` otherwise. Skipped if Calibre is not installed in the test environment.
- `test_build_dry_run_prints_expected_command` — uses a fixture CALIBRE stub and asserts `--dry-run` writes the expected `ebook-convert` invocation per (subject, slug) to stdout.
- `test_prune_old_epubs_removes_old_files` — creates `output/<x>/test.epub`, patches `st_mtime` to 8 days ago, runs prune, asserts the file is gone. Newer files survive.
- `test_subject_filter_only_builds_one_subject` — given `--subject tech`, asserts ebook-convert is called exactly once per tech subject slug (6 calls), not for slugs in other subjects.
- `test_slug_filter_only_builds_one_site` — given `--slug rtings`, asserts ebook-convert is called exactly once with rtings.
- `test_exit_code_on_partial_failure` — patches ebook-convert to fail for one slug; asserts exit code = 1.
- `test_exit_code_on_config_error` — given a missing CATALOG.md, asserts exit code = 2.
- `test_for_review_generates_valid_overlay_recipe` — feeds a stub HTML file, asserts the temp recipe file is created in `output/review/`, is a copy of the real recipe with a `parse_index()` method appended, and contains the override block. Asserts temp file is deleted even when ebook-convert fails (via `try/finally`).
- `test_for_review_inherits_cleanup_settings` — verifies the override copy preserves `remove_tags`, `keep_only_tags`, `scale_news_images`, `compress_news_images` from the parent class (introspect the class defined in the copied recipe file).

### Removed tests
- `tests/test_orchestrator.py` — references deleted `calibre_news.orchestrator.main` module.
- `tests/test_utils.py` — references deleted `calibre_news.orchestrator.utils` module.

## Migration path

1. Write `calibre_news/_calibre.py` (shared find_ebook_convert + constants).
2. Write `calibre_news/build.py` (new file).
3. Write `calibre_news/for_review.py` (new file).
4. Write `calibre_news/cli.py` (new file).
5. Update `pyproject.toml` with the `getnews` entry point.
6. Write `Makefile` (new file).
7. Delete `calibre_news/orchestrator/` directory.
8. Update `tests/` — add `test_build.py`, remove `test_orchestrator.py` and `test_utils.py`, update `test_recipes.py` per above.
9. Update `docs/USAGE.md` — replace orchestrator instructions with `getnews` / `python -m calibre_news.build`.
10. Update `docs/CATALOG.md` if needed.
11. Verify: `pip install -e . && getnews --dry-run` prints expected commands.
