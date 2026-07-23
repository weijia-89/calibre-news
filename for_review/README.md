# Calibre News Aggregator — Operator Hand-off Convention

When the agent cannot fetch a site (timeout, paywall, JS-required, 403), the
operator downloads one article page (per article if possible) and drops a
single saved HTML file into this directory.

## File naming

    for_review/<slug>.html          # MUST match a slug below
    for_review/<slug>.json          # optional: any extra notes (DOM hooks, redirect targets)

## Site slug → URL mapping (required to discover what to download)

| slug | site | what to grab |
|---|---|---|
| `digitalapplied` | https://www.digitalapplied.com/blog/category/ai-development | one article page |
| `rtings`         | https://www.rtings.com/research/new                    | one `/research/<slug>/` page |
| `cats`           | https://cats.com/reviews                              | one `/reviews/<slug>/` page |
| `consumerlab`    | https://www.consumerlab.com/product-updates/          | one `?id=<n>` product-update page |
| `chipsandcheese` | https://chipsandcheese.com/ (or .substack.com)         | one article page |
| `essex`          | https://www.essex.ac.uk/blog/categories/voices-of-the-global-south | one blog post |
| `wabe`           | https://www.wabe.org                                  | one article |
| `newschool_headlines` | https://blogs.newschool.edu/news/in-the-headlines/ | one full HTML save (NOT the newschool feed) |

When you save the file, the agent re-reads the file with BeautifulSoup and
extracts `keep_only_tags` / `remove_tags` directly from the DOM.

Operator instruction is in `for_review/README.md`. Operator can also drop a
`.txt` or `.md` notes file alongside the HTML with any extra hints — agent
will read it as natural language context.

When there's nothing to fetch (the operator IS the source), you can also drop
a "stub" HTML here that is the article body in plain semantic HTML and the
agent will treat that as the canonical content for that site until you access
the live URL.
