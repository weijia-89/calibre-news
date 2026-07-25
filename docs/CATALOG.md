# Site Catalog — single source of truth, written BEFORE any recipe

Subject taxonomy (locked):

```
tech      : ieee_spectrum, chipsandcheese, hwcooling
consumer  : cats
security  : cyberscoop, darkreading, schneier
local     : 285south, saportareport, atlpresscollective
news      : npr, truthout, globaldev, newschool_headlines
```

`newschool_headlines` is special — its produced EPUB file lands under the
`news` group, even though it's its own recipe.

Each site has a corresponding recipe file: `calibre_news/recipes/<slug>.recipe`.

If a site is missing from this catalog, the recipe build will not start work
on it. That's the gate.
