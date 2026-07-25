# Calibre News Aggregator  -  Usage Guide

## Prerequisites

- **Python 3.10+**
- **Calibre** (any version; `ebook-convert` discovered via `$PATH` first,
  then falls back to `/Applications/calibre.app/Contents/MacOS/ebook-convert` on macOS)

Verify Calibre is accessible:

    ebook-convert --version

If that fails, install Calibre from https://calibre-ebook.com or ensure
`ebook-convert` is on your `$PATH`.

## Installation

Install the package in editable mode to get the `getnews` command:

    pip install -e .

Or with `uv`:

    uv pip install -e .

## Quick Start

Build all EPUBs:

    getnews

Build a specific subject group:

    getnews --subject tech

Build a single site:

    getnews --slug ieee_spectrum

Prune old EPUBs (older than 7 days):

    getnews --prune-only

Preview commands without executing:

    getnews --dry-run

Parallelism (default: CPU count):

    getnews --parallel 8

Alternative via Make:

    make              # build all
    make tech         # build tech subject
    make prune        # prune old EPUBs
    make dry-run      # preview

## Site Catalog

14 sites in 5 subject groups, defined in `docs/CATALOG.md` (the single source of truth - no recipe is built for a slug absent from this file).

### Tech (3)

| Slug | Site | RSS Feed |
|------|------|----------|
| `ieee_spectrum` | IEEE Spectrum | `https://spectrum.ieee.org/feeds/feed.rss` |
| `chipsandcheese` | Chips and Cheese | `https://chipsandcheese.com/feed` |
| `hwcooling` | HWCooling | `https://www.hwcooling.net/en/feed/` |

### Consumer (1)

| Slug | Site | RSS Feed |
|------|------|----------|
| `cats` | Cats | `https://cats.com/feed/` |

### Security (3)

| Slug | Site | RSS Feed |
|------|------|----------|
| `cyberscoop` | CyberScoop | `https://cyberscoop.com/feed/` |
| `darkreading` | Dark Reading | `https://www.darkreading.com/rss.xml` |
| `schneier` | Schneier on Security | `https://www.schneier.com/feed/` |

### Local - Atlanta Metro (3)

| Slug | Site | RSS Feed |
|------|------|----------|
| `285south` | 285 South | `https://285south.com/feed/` |
| `saportareport` | SaportaReport | `https://saportareport.com/feed/` |
| `atlpresscollective` | Atlanta Community Press Collective | `https://atlpresscollective.com/feed/` |

### News (4)

| Slug | Site | RSS Feed |
|------|------|----------|
| `npr` | NPR | `https://feeds.npr.org/1001/rss.xml` |
| `truthout` | Truthout | `https://truthout.org/feed/` |
| `globaldev` | Guardian Global Dev | `https://www.theguardian.com/global-development/rss` |
| `newschool_headlines` | The New School  -  In the Headlines | No RSS  -  uses `parse_index()` to scrape link-roll page |

## Recipe System

Each site has a `.recipe` file at `calibre_news/recipes/<slug>.recipe`. These are standard Calibre `BasicNewsRecipe` subclasses with a shared convention:

```python
from calibre.web.feeds.news import BasicNewsRecipe

class ExampleSite(BasicNewsRecipe):
    title = 'Example Site'
    author = 'Example Site'
    tags = ['news']
    oldest_article = 7
    compress_news_images = True
    scale_news_images = (1264, 1680)
    language = 'en'
    requires_version = (9, 0, 0)
    auto_cleanup = True

    feeds = [
        ('Example Site', 'https://example.com/feed'),
    ]
```

### Key properties

| Property | Value | Purpose |
|----------|-------|---------|
| `oldest_article` | `7` | Max article age in days |
| `compress_news_images` | `True` | Downscale images during conversion |
| `scale_news_images` | `(1264, 1680)` | Max image dimensions (width, height) |
| `auto_cleanup` | `True` | Automatic HTML sanitisation fallback |
| `requires_version` | `(9, 0, 0)` | Minimum Calibre version |
| `author` | `'Site Name'` | Publisher/author embedded in EPUB metadata |
| `tags` | `['subject']` | Subject category embedded in EPUB metadata |

### Content filtering

- **`keep_only_tags`**  -  when set, Calibre discards everything not matched by these selectors. Use this to isolate the article body.
- **`remove_tags`**  -  when set, Calibre removes matched elements from the page before conversion.
- **`auto_cleanup = True`**  -  fallback that heuristically strips navigation, ads, and chrome when no explicit tags are configured. Relies on Calibre's built-in heuristics; for problem sites, prefer explicit `keep_only_tags`.

Neither is populated in current stubs  -  they are filled per-site during the `for_review` workflow.

## Offline Fallback (`for_review`)

When live fetch fails (timeout, paywall, JS-required site, 403), the operator can drop a saved HTML file at:

    for_review/<slug>.html

Then run the review command to test the recipe's cleanup settings against real page content:

    python -m calibre_news.for_review <slug> [<html-file>]

If no HTML file is given, defaults to `for_review/<slug>.html`.

The review command:
1. Copies the site's recipe to a temp directory
2. Appends a `parse_index()` override that reads the saved HTML and returns it as a single article
3. Runs `ebook-convert` on the modified recipe
4. Outputs to `output/<slug>.epub`
5. Cleans up the temporary recipe

This lets you iterate on `keep_only_tags` / `remove_tags` against a real saved page before committing changes to the recipe.

Site-specific grab instructions:

| Slug | Source URL to save |
|------|--------------------|
| `cats` | `https://cats.com/reviews`  -  one `/reviews/<slug>/` page |
| `chipsandcheese` | `https://chipsandcheese.com/` (or `.substack.com`)  -  one article |
| `newschool_headlines` | `https://blogs.newschool.edu/news/in-the-headlines/`  -  full page save (not the feed) |

## Image Configuration

All recipes configure Calibre's built-in image resizing:

    scale_news_images = (1264, 1680)
    compress_news_images = True

The build script additionally passes:

    --output-profile=kindle_oasis

This sets the output profile to Kindle Oasis dimensions, producing EPUB files optimised for that device's screen.

## Rolling Window

Two mechanisms enforce a 7-day rolling window:

1. **Recipe-level**: `oldest_article = 7` on every `BasicNewsRecipe` subclass tells Calibre to skip articles older than 7 days at fetch time.
2. **Build-level**: `prune_old_epubs()` in `build.py` scans `output/*.epub` and deletes any file whose `st_mtime` is older than 7 days. Runs at the end of every full `getnews` cycle (unless `--no-prune` is passed).

## Output Structure

    output/
    ├── ieee_spectrum.epub
    ├── chipsandcheese.epub
    ├── hwcooling.epub
    ├── cats.epub
    ├── cyberscoop.epub
    ├── darkreading.epub
    ├── schneier.epub
    ├── 285south.epub
    ├── saportareport.epub
    ├── atlpresscollective.epub
    ├── npr.epub
    ├── truthout.epub
    ├── globaldev.epub
    └── newschool_headlines.epub

EPUBs are written to a flat `output/` directory. The mapping from slug to subject is driven entirely by `CATALOG.md` and embedded as `tags` metadata inside each EPUB.

## Adding a New Site

1. **Add to CATALOG.md**  -  insert the slug under the appropriate subject line in the fenced code block. The build will not build a site absent from this file.
2. **Create recipe stub**  -  copy an existing `.recipe` file to `calibre_news/recipes/<slug>.recipe`. Update `title`, `author`, `tags`, and the class name.
3. **Fill in the feed URL**  -  set the `feeds` list with the site's RSS endpoint. If the site has no RSS, implement `parse_index()` (see `newschool_headlines.recipe` for a template).
4. **Add cleanup rules**  -  use the `for_review` workflow: drop a saved HTML page at `for_review/<slug>.html`, run the review command, inspect the output, then adjust `keep_only_tags` / `remove_tags` until the article body is clean.
5. **(Optional) Create meta file**  -  `recipes/<slug>.meta.yaml` for per-site overrides (e.g. custom `extra_args`, non-default image dimensions). Not yet implemented.

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `FileNotFoundError: Calibre ebook-convert binary not found` | Calibre not installed or path different | Install Calibre, or symlink `/Applications/calibre.app/Contents/MacOS/ebook-convert` |
| `ebook-convert` hangs | Site slow or blocking | Save the article manually to `for_review/<slug>.html` and re-run |
| `[FAIL] Unable to fetch ...` | Feed URL changed or site down | Check the site's RSS feed URL. Update `feeds` in the recipe. |
| EPUB has navigation/ads in article body | `keep_only_tags` / `remove_tags` not set | Use the `for_review` workflow to identify the correct selectors |
| `curl: (22) HTTP 404` | Feed URL is stale | Verify the feed URL in a browser |
| `oldest_article` not filtering | Calibre's feed parser date extraction may fail | Set `max_articles_per_feed` as an additional constraint in the recipe |
| Recipe `feeds = []` but site has no RSS | Site uses JS-rendered content or link-roll | Implement `parse_index()` (see `newschool_headlines.recipe` stub) |
| No author or tags in EPUB metadata | Recipe missing `author` or `tags` | Add `author = 'Site Name'` and `tags = ['subject']` to the recipe class |
