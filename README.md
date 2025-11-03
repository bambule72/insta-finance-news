# insta-finance-news

A Python microservice that scrapes financial news and EDGAR (SEC) Form 144 filings and produces a compact JSON feed suitable for downstream content generators (e.g., short-form Instagram reels/stories).

This repo contains a conservative, RSS-first scraper with HTML fallback, optional Redis caching, EDGAR (Form 144) parsing heuristics, and a Google Cloud Functions entrypoint for serverless deployment.

## What changed (high level)

- RSS-first ingestion for Bloomberg, MarketWatch, CNBC plus an Atom feed for recent SEC Form 144 filings.
- Best-effort EDGAR/SEC parsing: when Form 144 Atom entries are present the scraper will fetch the filing index page and attempt to extract transaction details (buy/sell, shares, price/value) into structured records.
- Optional Redis caching for HTTP responses to reduce load and speed up repeated runs.
- Per-host throttling and site-specific headers (the SEC feed uses a contact email in the User-Agent and From headers).
- Dockerfile and `docker-compose.yml` (app + redis) so tests and scraping can run reproducibly in a container.

## Goals

- Scrape timely headlines and summaries relevant to major markets (DAX40, Nasdaq, Dow Jones, S&P 500).
- Ingest SEC Form 144 filings and surface structured transaction information when available.
- Produce a clean JSON output consumable by other microservices.

## Quick start (local Python)

1. Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the test suite

```bash
pytest -q
```

4. Run locally with the Functions Framework

```bash
functions-framework --target=scrape_news --debug
curl http://localhost:8080/
```

## Docker (recommended for reproducible runs)

Build and run the app image (the image build runs pytest during the build so failures surface early):

```bash
docker compose build --no-cache
docker compose run --rm app pytest -q
```

Run the scraper and save JSON output to the host workspace:

```bash
docker compose run --rm --no-deps -v "$(pwd)":/app app python3 scripts/print_scrape.py --out /app/scrape_output.json
```

If you want the app to use Redis caching, start the full compose stack:

```bash
docker compose up -d
```

Then run the scraper (app will talk to the `redis` service defined in `docker-compose.yml`):

```bash
docker compose run --rm app python3 scripts/print_scrape.py --out /app/scrape_output.json
```

## Caching behaviour

- Redis caching is optional and enabled when `REDIS_URL` is set (for local compose we set `REDIS_URL=redis://redis:6379/0`).
- The scraper caches HTTP response bodies under keys such as `rss:{feed_url}` and `http:{url}`.
- TTLs used by the scraper (configurable by editing code):
  - RSS feeds: 300 seconds (5 minutes)
  - HTML pages: 600 seconds (10 minutes)
- On a cache hit the scraper logs `RSS cache hit` or `Cache hit` and returns cached content instead of making a network request.
- To force live fetching (bypass cache) you can:
  - Run the container without Redis (use `--no-deps` and do not pass `REDIS_URL`), or
  - Flush the Redis instance before a run: `docker compose exec redis redis-cli FLUSHALL`.

## EDGAR / SEC notes and compliance

- The SEC requires a descriptive `User-Agent` with contact information. The scraper sets `User-Agent` and `From` for the SEC feed using the `SCRAPER_CONTACT_EMAIL` environment variable (defaults to a placeholder).
- By default the scraper checks `robots.txt` for a site and will not perform HTML scraping if robots disallow it. If `robots.txt` is inaccessible (for example SEC returns 403) the scraper treats that as disallow unless you explicitly opt out.
- To override robots.txt checks (not recommended unless you understand the compliance implications) set:

```bash
IGNORE_ROBOTS=1
```

## EDGAR parsing caveats

- EDGAR filings vary in format. The scraper implements best-effort heuristics to extract transaction type (buy/sell), number of shares, price and transaction value. This is not guaranteed to be accurate for every filing.
- The scraper attempts to match issuers to index constituents using a simple S&P 500 and DJIA fetcher (from Wikipedia) and string-matching heuristics. This is best-effort and can be improved by adding a CIK↔ticker canonical mapping.

## Environment variables

- `SCRAPER_CONTACT_EMAIL` — contact email used in SEC User-Agent and From headers (default set in code).
- `MIN_SECONDS_BETWEEN_REQUESTS` — per-host throttle delay in seconds (default 1.0).
- `IGNORE_ROBOTS` — when set to 1/true, ignore robots.txt disallow rules and attempt HTML scraping.
- `REDIS_URL` — when set, the scraper will use Redis for caching HTTP responses.

## Scripts

- `scripts/print_scrape.py` — run the scraper and optionally write JSON output (`--out file.json`).
- `scripts/debug_sec.py` — debug helper to fetch and print SEC Atom feed request/response details.

## Tests and CI

- Unit tests live in `tests/` and are executed during Docker image builds. The project includes pytest-based tests for core scraper utilities.
- Adding a GitHub Actions workflow to run tests and build the image is recommended (not added yet).

## Next steps and suggestions

- Add a canonical CIK→ticker mapping to reliably filter EDGAR filings by index constituents.
- Improve EDGAR parsing by handling common HTML/XML table structures in filings rather than relying solely on regex over text.
- Add a small `--no-cache` CLI flag to `scripts/print_scrape.py` to make it easy to bypass Redis when present.

---

If you want, I can:

- Add the `--no-cache` CLI flag and wire it through the scraper, or
- Add a basic GitHub Actions workflow that builds the Docker image and runs tests on pushes.

Pick one and I'll implement it next.
