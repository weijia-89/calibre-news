# calibre-news

Calibre-based news aggregator — 20 site recipes, one build command, EPUBs grouped by subject for Kindle Oasis.

## Quick start

```bash
pip install -e .
getnews                  # build all 20 EPUBs
getnews --subject tech   # build just the tech subject
getnews --prune-only     # clean EPUBs older than 7 days
```

## How it works

Each site has a `.recipe` file in `calibre_news/recipes/`. These are standard Calibre `BasicNewsRecipe` subclasses with real RSS feeds, image scaling, and HTML cleanup rules. `getnews` reads the catalog (`docs/CATALOG.md`), maps each slug to its subject, and runs `ebook-convert` directly on each recipe file — no curl, no temp HTML, no manual fetch logic.

Calibre handles everything downstream: RSS feed retrieval, article extraction, image resizing (1264×1680, Kindle Oasis profile), and HTML cleanup. Output lands in `output/<subject>/<slug>.epub`. EPUBs older than 7 days are pruned automatically.

## Subjects

| Subject | Slugs | Sites |
|---------|-------|-------|
| tech | 6 | Digital Applied, IEEE Spectrum, TechSpot, RTINGS, Chips and Cheese, HWCooling |
| consumer | 2 | Cats, ConsumerLab |
| security | 3 | CyberScoop, Dark Reading, Schneier on Security |
| local | 5 | 285 South, SaportaReport, Decaturish, Atlanta Press Collective, WABE |
| news | 4 | NPR, Truthout, Guardian Global Dev, New School Headlines |

Subject taxonomy and slug list live in `docs/CATALOG.md`. That file is the gate — no recipe is built for a slug not listed there.

## Adding a site

1. Add the slug to `docs/CATALOG.md` under the right subject line.
2. Create `calibre_news/recipes/<slug>.recipe` — copy an existing recipe, update `title` and `feeds`.
3. Run `getnews --slug <slug>` to verify.

To add cleanup rules (`remove_tags`, `keep_only_tags`): drop a saved HTML page at `for_review/<slug>.html`, then run `python -m calibre_news.for_review <slug>`. This tests recipe settings against real page content without live RSS fetching.

## for_review workflow

```bash
# Save a page from the site
curl -o for_review/wabe.html https://www.wabe.org/some-article

# Test cleanup settings
python -m calibre_news.for_review wabe

# Output at output/review/wabe.epub
# Iterate remove_tags / keep_only_tags in the recipe until the article body is clean
```

## Commands

| Command | What it does |
|---------|-------------|
| `getnews` | Build all sites |
| `getnews --subject tech` | Build one subject group |
| `getnews --slug rtings` | Build one site |
| `getnews --prune-only` | Clean EPUBs older than 7 days |
| `getnews --dry-run` | Print commands without executing |
| `getnews --parallel 4` | Concurrency limit |
| `getnews --no-prune` | Skip automatic cleanup |
| `python -m calibre_news.for_review <slug>` | Test recipe cleanup against saved HTML |

## Requirements

- Python 3.10+
- Calibre (`ebook-convert` on PATH, or `/Applications/calibre.app/` on macOS)
- No other dependencies

## Testing

```bash
python -m pytest tests/ -v
# 14 tests: catalog parsing, recipe importability, pruning, exit codes, for_review
```

## Project layout

```
calibre_news/
  _calibre.py     — find_ebook_convert() + constants
  build.py        — daily build driver with parallel execution
  for_review.py   — stub-based review workflow
  cli.py          — getnews entry point
  recipes/        — 20 Calibre BasicNewsRecipe files
docs/
  CATALOG.md      — subject/slug mapping (source of truth)
  USAGE.md        — full usage guide
  adr/            — architecture decision records
  reviews/        — adversarial review records
tests/
  test_build.py   — catalog, prune, exit codes, for_review
  test_recipes.py — recipe importability and attribute checks
Makefile          — convenience targets (make, make tech, make prune)
output/           — generated EPUBs, grouped by subject
for_review/       — saved HTML stubs for cleanup testing
```