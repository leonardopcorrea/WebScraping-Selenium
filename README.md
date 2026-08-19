# Web Scraping — Hockey Teams Table

![Tests](https://github.com/leonardopcorrea/WebScraping-Selenium/actions/workflows/test.yml/badge.svg)

HTTP scraper for the paginated hockey teams table at [scrapethissite.com/pages/forms](https://www.scrapethissite.com/pages/forms/). It fetches static HTML with **httpx**, parses rows with **selectolax**, validates each record with **Pydantic**, and writes results to **Excel**, **CSV**, or **JSON**.

The default path is **httpx only** — no browser is required for the public table. Optional **Playwright** is available solely for JavaScript-heavy login when `AUTH_MODE=browser` (see [Optional authentication](#optional-authentication)).

## Quick start

**Requirements:** Python 3.11+

```bash
cp .env.example .env
py -3 -m pip install -r requirements.txt
py -3 -m scraper
```

On Windows, if `python` is not on your PATH, use `py -3` instead of `python`.

For a short smoke test, set `MAX_PAGES=2` in `.env` before running.

## Configuration (`.env`)

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `BASE_URL` | `https://www.scrapethissite.com/pages/forms/` | Listing URL (no query string) |
| `PAGE_SIZE` | `25` | Rows per page (`per_page` query param) |
| `MAX_PAGES` | `0` | Page cap; `0` = scrape until pagination ends |
| `OUTPUT_PATH` | `output/hockey_teams.xlsx` | Output file path |
| `REQUEST_TIMEOUT_S` | `20` | HTTP timeout per request |
| `MAX_RETRIES` | `4` | Retries on timeout, transport errors, 408/425/429/5xx |
| `MIN_DELAY_S` / `MAX_DELAY_S` | `0.4` / `1.2` | Random pause before each page |
| `USER_AGENT` | *(Chrome-like default)* | Optional custom User-Agent |
| `PROXY_URL` | *(empty)* | Optional HTTP proxy |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Optional authentication

Public scrape is the default (`AUTH_MODE=off`). Enable login only when needed; keep credentials in `.env` (never in code or git).

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `AUTH_MODE` | `off` | `off`, `cookie`, `form`, or `browser` |
| `LOGIN_URL` | *(empty)* | Required for `form` / `browser` |
| `USERNAME` / `PASSWORD` | *(empty)* | Required for `form` / `browser` |
| `COOKIE_HEADER` | *(empty)* | Raw `Cookie` header for `cookie` mode |
| `AUTH_BEARER` | *(empty)* | Bearer token for `cookie` mode |
| `LOGIN_*_SELECTOR` | `#username`, `#password`, `button[type="submit"]` | CSS selectors for `browser` (and form field lookup) |
| `LOGIN_SUCCESS_URL` | *(empty)* | Optional URL substring to confirm login |

- **cookie** — injects `Cookie` / `Authorization` on the shared `httpx.Client`.
- **form** — GET login page, extract hidden/CSRF fields, POST credentials; cookies stay in the client jar.
- **browser** — Playwright fills the form and exports cookies to httpx. Install with `pip install -r requirements-browser.txt`, then run `playwright install chromium`.

Failed login (401/403, or login form still visible on the session probe) aborts **before** pagination starts.

## CLI

Command-line flags override `.env` values for a single run:

```bash
py -3 -m scraper --max-pages 2
py -3 -m scraper --output output/teams.csv --format csv
py -3 -m scraper --output output/teams.json --format json
```

| Flag | Description |
| ---- | ----------- |
| `--max-pages N` | Stop after N pages (overrides `MAX_PAGES`) |
| `--output PATH` | Output file path (overrides `OUTPUT_PATH`) |
| `--format {xlsx,csv,json}` | Output format; inferred from `--output` extension when omitted |

## How it works

```
.env / Settings → run() → authenticate (if AUTH_MODE != off) → polite delay → HttpFetcher GET
  → parse_listing (CSS) → HockeyTeamRecord → output file
```

1. `python -m scraper` calls `run()` in `scraper/__main__.py`.
2. `Settings` loads configuration from `.env`.
3. When `AUTH_MODE` is not `off`, `authenticate()` establishes a session on the shared `httpx.Client` (cookie injection, form POST, or Playwright login).
4. `HttpFetcher` opens a reusable `httpx.Client` with browser-like headers, builds URLs `?page_num=N&per_page=25`, and retries transient failures with exponential backoff. HTTP 429 respects `Retry-After`.
5. Before each page, a random delay runs between `MIN_DELAY_S` and `MAX_DELAY_S`.
6. `parse_listing` selects `table.table tr.team` and reads cell classes (`td.name`, `td.year`, etc.). Missing table → error; no team rows → empty page (end of pagination).
7. Each row becomes a `HockeyTeamRecord`. Invalid rows are logged and skipped; they do not abort the page.
8. Fetch/parse failures **skip the page**; exhausted 429 **stops the job**. Two consecutive empty pages (or the first empty page when `MAX_PAGES=0`) stop pagination.
9. Results are written to the configured output file with source URL and page number columns (Excel/CSV) or full record fields (JSON).

Logs go to stderr with `url=` and `page=` context.

## Output columns

Excel and CSV include:

`Team Name`, `Year`, `Wins`, `Losses`, `OT Losses`, `Win %`, `Goals For (GF)`, `Goals Against (GA)`, `+ / -`, `Source URL`, `Page`

JSON exports a list of validated record objects (field names in snake_case).

## What this project does **not** do

By design, the scraper is scoped to one static table on one site:

- No CAPTCHA handling or aggressive anti-bot evasion
- No proxy rotation
- No multi-site or plug-in spider architecture
- No database sink or resume/checkpoint support

Use it for learning and for sites that expose data as plain HTML. Do not point it at production sites with restrictive terms of service or heavy bot protection.

## Development

Install test dependencies and run offline tests (parser, auth, HTTP retry logic — no live network):

```bash
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest
```

Fixtures live under `tests/fixtures/` (sample HTML) and use `httpx.MockTransport` for retry and auth behavior.

## Project layout

```
scraper/
  __main__.py      # CLI entry point and orchestration
  auth.py          # Optional login (cookie / form / Playwright)
  config.py        # Settings from environment
  exceptions.py    # Domain-specific errors
  fetcher.py       # HTTP client, retries, pagination URLs
  logging_setup.py # Structured stderr logging
  parser.py        # selectolax CSS extraction
  models.py        # Pydantic record schema
  storage.py       # Excel / CSV / JSON writers
  stealth.py       # Headers and jitter delay
tests/
  conftest.py
  fixtures/        # Offline HTML samples
  test_auth.py
  test_cli.py
  test_fetcher.py
  test_parser.py
  test_storage.py
requirements.txt           # Runtime dependencies (httpx path)
requirements-dev.txt       # pytest and dev tools
requirements-browser.txt   # Optional Playwright for AUTH_MODE=browser
pyproject.toml             # Project metadata and pytest config
```
