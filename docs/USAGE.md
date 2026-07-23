# Calibre News Aggregator — Usage Guide

## Prerequisites

- **Python 3.10+**
- **Calibre** (any version; the orchestrator discovers it via `$PATH` first,
  then falls back to `/Applications/calibre.app/Contents/MacOS/ebook-convert` on macOS)
- **curl** available on `$PATH`

Verify Calibre is accessible:

    ebook-convert --version

If that fails, install Calibre from https://calibre-ebook.com or ensure
`ebook-convert` is on your `$PATH`.

## Quick Start

Run the orchestrator from the project root:

    python -m calibre_news.orchestrator.main

This reads the site catalog, fetches or loads each site's article HTML, converts it to EPUB via Calibre's `ebook-convert`, and places output under `output/<subject>/<slug>.epub`. A post-pass prunes any EPUB older than 7 days.

## Site Catalog

20 sites in 5 subject groups, defined in `docs/CATALOG.md` (the single source of truth — no recipe is built for a slug absent from this file).

### Tech (6)

| Slug | Site | RSS Feed |
|------|------|----------|
| `digitalapplied` | Digital Applied | `https://digitalapplied.com/feed` |
| `ieee_spectrum` | IEEE Spectrum | `https://spectrum.ieee.org/feed` |
| `techspot` | TechSpot | `https://www.techspot.com/feed` |
| `rtings` | RTINGS | `https://www.rtings.com/reviews.rss` + `tv/reviews.rss` |
| `chipsandcheese` | Chips and Cheese | `https://chipsandcheese.com/feed` |
| `hwcooling` | HWCooling | `https://hwcooling.net/feed` |

### Consumer (2)

| Slug | Site | RSS Feed |
|------|------|----------|
| `cats` | Cats | `https://cats.com/feed/` |
| `consumerlab` | ConsumerLab | `https://www.consumerlab.com/feed/` |

### Security (3)

| Slug | Site | RSS Feed |
|------|------|----------|
| `cyberscoop` | CyberScoop | `https://cyberscoop.com/feed/` |
| `darkreading` | Dark Reading | `https://www.darkreading.com/rss.xml` |
| `schneier` | Schneier on Security | `https://www.schneier.com/feed/` |

### Local — Atlanta Metro (5)

| Slug | Site | RSS Feed |
|------|------|----------|
| `285south` | 285 South | `https://285south.com/feed/` |
| `saportareport` | SaportaReport | `https://saportareport.com/feed/` |
| `decaturish` | Decaturish | `http://www.decaturish.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc` |
| `atlpresscollective` | Atlanta Community Press Collective | `https://atlpresscollective.com/feed/` |
| `wabe` | WABE | `https://www.wabe.org/feed/` (may return 404 — try `/news/feed/`) |

### News (4)

| Slug | Site | RSS Feed |
|------|------|----------|
| `npr` | NPR | `https://feeds.npr.org/1001/rss.xml` |
| `truthout` | Truthout | `https://truthout.org/feed/` |
| `globaldev` | Guardian Global Dev | `https://www.theguardian.com/global-development/rss` |
| `newschool_headlines` | The New School — In the Headlines | No RSS — uses `parse_index()` to scrape link-roll page |

Note: `newschool_headlines` produces an EPUB under the `news` subject directory despite being its own recipe.

## Recipe System

Each site has a `.recipe` file at `calibre_news/recipes/<slug>.recipe`. These are standard Calibre `BasicNewsRecipe` subclasses with a shared convention:

```python
from calibre.web.feeds.news import BasicNewsRecipe

class ExampleSite(BasicNewsRecipe):
    title = 'Example Site'
    oldest_article = 7
    compress_news_images = True
    scale_news_images = (1264, 1680)
    language = 'en'
    requires_version = (9, 0, 0)
    auto_cleanup = True

    # keep_only_tags = [dict(name='article')]
    # remove_tags = [dict(name='nav'), dict(name='aside')]

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

### Content filtering

- **`keep_only_tags`** — when set, Calibre discards everything not matched by these selectors. Use this to isolate the article body.
- **`remove_tags`** — when set, Calibre removes matched elements from the page before conversion.
- **`auto_cleanup = True`** — fallback that heuristically strips navigation, ads, and chrome when no explicit tags are configured. Relies on Calibre's built-in heuristics; for problem sites, prefer explicit `keep_only_tags`.

Neither is populated in current stubs — they are filled per-site during the `for_review` workflow.

## Offline Fallback (`for_review`)

When live fetch fails (timeout, paywall, JS-required site, 403), the operator can drop a saved HTML file at:

    for_review/<slug>.html

The orchestrator checks this path before attempting a live `curl` fetch. If present, the file is used as the source HTML and no network request is made.

Optional companion file:

    for_review/<slug>.json     — extra notes (DOM hooks, redirect targets)

Site-specific grab instructions (from `for_review/README.md`):

| Slug | Source URL to save |
|------|--------------------|
| `digitalapplied` | `https://www.digitalapplied.com/blog/category/ai-development` — one article |
| `rtings` | `https://www.rtings.com/research/new` — one `/research/<slug>/` page |
| `cats` | `https://cats.com/reviews` — one `/reviews/<slug>/` page |
| `consumerlab` | `https://www.consumerlab.com/product-updates/` — one `?id=<n>` page |
| `chipsandcheese` | `https://chipsandcheese.com/` (or `.substack.com`) — one article |
| `wabe` | `https://www.wabe.org` — one article |
| `newschool_headlines` | `https://blogs.newschool.edu/news/in-the-headlines/` — full page save (not the feed) |

## Image Configuration

All recipes configure Calibre's built-in image resizing:

    scale_news_images = (1264, 1680)
    compress_news_images = True

The orchestrator's `convert_to_epub` wrapper in `utils.py` additionally passes:

    --output-profile=kindle_oasis

This sets the output profile to Kindle Oasis dimensions, producing EPUB files optimised for that device's screen.

When converting direct HTML (without a recipe), the same scale/compress parameters are forwarded as `extra_args` to `ebook-convert`.

## Rolling Window

Two mechanisms enforce a 7-day rolling window:

1. **Recipe-level**: `oldest_article = 7` on every `BasicNewsRecipe` subclass tells Calibre to skip articles older than 7 days at fetch time.
2. **Orchestrator-level**: `_prune_old_epubs()` in `main.py` scans `output/**/*.epub` and deletes any file whose `st_mtime` is older than 7 days. Runs at the end of every full `run()` cycle.

## Output Structure

    output/
    ├── tech/
    │   ├── digitalapplied.epub
    │   ├── ieee_spectrum.epub
    │   ├── techspot.epub
    │   ├── rtings.epub
    │   ├── chipsandcheese.epub
    │   └── hwcooling.epub
    ├── consumer/
    │   ├── cats.epub
    │   └── consumerlab.epub
    ├── security/
    │   ├── cyberscoop.epub
    │   ├── darkreading.epub
    │   └── schneier.epub
    ├── local/
    │   ├── 285south.epub
    │   ├── saportareport.epub
    │   ├── decaturish.epub
    │   ├── atlpresscollective.epub
    │   └── wabe.epub
    └── news/
        ├── npr.epub
        ├── truthout.epub
        ├── globaldev.epub
        └── newschool_headlines.epub

Subject directories are created on first run. The mapping from slug to subject is driven entirely by `CATALOG.md`.

## Adding a New Site

1. **Add to CATALOG.md** — insert the slug under the appropriate subject line in the fenced code block. The orchestrator will not build a site absent from this file.
2. **Create recipe stub** — copy an existing `.recipe` file to `calibre_news/recipes/<slug>.recipe`. Update `title` and the class name.
3. **Fill in the feed URL** — set the `feeds` list with the site's RSS endpoint. If the site has no RSS, implement `parse_index()` (see `newschool_headlines.recipe` for a template).
4. **Add cleanup rules** — use the `for_review` workflow: drop a saved HTML page at `for_review/<slug>.html`, run the orchestrator, inspect the output, then adjust `keep_only_tags` / `remove_tags` until the article body is clean.
5. **(Optional) Create meta file** — `recipes/<slug>.meta.yaml` for per-site overrides (e.g. custom `extra_args`, non-default image dimensions). The orchestrator's `_load_recipe_config()` reads this if present.

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `FileNotFoundError: Calibre ebook-convert binary not found` | Calibre not installed or path different | Install Calibre, or symlink `/Applications/calibre.app/Contents/MacOS/ebook-convert` |
| `curl: (28) Connection timed out` | Site slow or blocking curl | Save the article manually to `for_review/<slug>.html` and re-run |
| `[WARN] Unable to fetch ...` | Feed URL changed or site down | Check the site's RSS feed URL. Update `feeds` in the recipe. |
| EPUB has navigation/ads in article body | `keep_only_tags` / `remove_tags` not set | Use the `for_review` workflow to identify the correct selectors |
| `curl: (22) HTTP 404` | Feed URL is stale | Verify the feed URL in a browser. WABE is a known offender — try `/news/feed/` instead of `/feed/`. |
| `oldest_article` not filtering | Calibre's feed parser date extraction may fail | Set `max_articles_per_feed` as an additional constraint in the recipe |
| Recipe `feeds = []` but site has no RSS | Site uses JS-rendered content or link-roll | Implement `parse_index()` (see `newschool_headlines.recipe` stub) |
