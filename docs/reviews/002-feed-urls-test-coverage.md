# Review Record — PR #2: Feed URLs, Test Coverage, Docs Sync

## Loop 1 (initial commit — 14 findings)

All resolved before PR #1 merge. See commit history.

## Loop 2 (current batch — 2 critical, 0 major, 1 minor)

| Severity | Finding | File | Fix |
|----------|---------|------|-----|
| CRITICAL | RTINGS feed URL is HTML page, not RSS | `recipes/rtings.recipe` | Changed to `/reviews.rss` + `/tv/reviews.rss` |
| CRITICAL | Decaturish feed URL returns 404 | `recipes/decaturish.recipe` | Changed to TownNews search RSS |
| MINOR | `newschool_headlines` stale comment said "scrapes link-roll" but has `parse_index()` stub returning `[]` | `recipes/newschool_headlines.recipe` | Stale docstring removed |

## Loop 3 — Adversarial Checklist (0 findings)

SENIOR-ENGINEER CHECKLIST run against total diff:

1. Dead references — recipe/catalog 1:1 enforced by test ✓
2. Config/env drift — all 20 recipes consistent: `oldest_article=7`, `scale=(1264,1680)`, `compress=True`, `output_profile='kindle_oasis'` ✓
3. Silent no-ops — `newschool_headlines.parse_index()` returns `[]` (known stub, documented in USAGE.md) ✓
4. Platform assumptions — Calibre PATH discovery handles macOS `/Applications/...` ✓
5. Enforcement backstop — tests enforce catalog cross-ref, attribute presence, feeds non-empty, URL format ✓
6. Unbounded loops — none ✓
7. Off-by-one — prune: `oldest_article=7`, `_prune_old_epubs()` checks `>7 days` ✓
8. Error paths — `shutil.which()` + try/except for missing Calibre ✓
9. Idempotency — safe to run twice ✓
10. Cache/state invalidation — `_prune_old_epubs()` runs every cycle ✓
11. Injection surface — static strings only ✓
12. Secrets hygiene — no secrets in recipe/config files ✓
13. Least privilege — read-only web fetches ✓
14. Human-in-the-loop — not required for recipe/config changes ✓
15. Evidence over claims — 9/9 tests pass ✓

## Loop 4 — Final Verification (0 findings)

- `pytest -v`: 9/9 passing
- All 20 `.recipe` files compile with `py_compile`
- Catalog cross-reference: 1:1 match

## Sign-off

All critical and major findings resolved. Branch ready for merge.
