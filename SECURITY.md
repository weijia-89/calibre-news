# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes |
| 0.1.x   | No  -  upgrade recommended |

Security fixes are backported to the current minor version only. Upgrade via `git pull origin main` and `pip install -e .`.

## Reporting a Vulnerability

Email `wei@jia.mozmail.com` with the subject `calibre-news security`. Expect acknowledgement within 48 hours and a resolution timeline within 7 days. Do not open public issues for undisclosed vulnerabilities.

## Threat Model

### What calibre-news does not do (and therefore cannot leak)

- No network requests. RSS fetching, image downloading, and HTML retrieval are handled entirely by Calibre's `ebook-convert` binary, not by this codebase.
- No authentication, API tokens, secrets, or credentials. The project has no `.env`, no `config.yaml`, and no secrets file.
- No database. All state is filesystem-based (`output/`, `for_review/`).
- No server, no open port, no web interface.

### What calibre-news does that could carry risk

1. **Subprocess execution.** `build.py` and `for_review.py` call `ebook-convert` via `subprocess.run([...], shell=False)`. Arguments are passed as a Python list, never as a shell string. No user input reaches the subprocess argument list except the slug name, which is validated against the locked catalog (`docs/CATALOG.md`) before any subprocess call.
2. **File system writes.** Output lands in `output/<subject>/<slug>.epub`. Pruning deletes EPUBs with `mtime` older than 7 days. Both operations use `pathlib.Path`; paths are constructed from validated slugs and locked subject names, never from user input.
3. **Recipe file execution.** `.recipe` files are Python subclasses of Calibre's `BasicNewsRecipe`. They run inside Calibre's own Python interpreter, not the host Python. Do not paste untrusted recipe code into `calibre_news/recipes/` without review.

## Best Practices for Operators

- Keep Calibre updated. `ebook-convert` is the actual network-facing surface; patch it through your OS package manager.
- Do not commit `.epub` files to version control. The `output/` directory is gitignored.
- Review RSS feed URLs in `.recipe` files before adding a new site. A malicious feed could serve unexpected content to Calibre's parser. calibre-news does not sanitize feed content itself.
- The `for_review/` directory accepts arbitrary HTML. Review saved HTML before running `python -m calibre_news.for_review <slug>`; the HTML is passed to Calibre's `BeautifulSoup` parser inside `ebook-convert`.

## Disclosure History

| Date | CVE / Issue | Severity | Fixed In |
|------|-------------|----------|----------|
| None |  -  |  -  |  -  |

No security issues disclosed to date.
