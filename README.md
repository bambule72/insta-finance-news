# insta-finance-news

A Python microservice that scrapes financial news and EDGAR (SEC) filings using a modular parser architecture. It produces a compact JSON feed suitable for downstream content generators (e.g., short-form Instagram reels/stories).

This repo contains a conservative, RSS-first scraper with HTML fallback, optional Redis caching, modular SEC form parsers, and a Google Cloud Functions entrypoint for serverless deployment.

## What changed (high level)

- **Modular Parser Architecture**: Generic form fetcher with pluggable parsers for different SEC form types
- **RSS-first ingestion** for Bloomberg, MarketWatch, CNBC plus Atom feeds for SEC filings
- **SEC Form 144 Parser**: Extracts structured transaction data (buy/sell, shares, price/value) with date normalization (ISO 8601) and price rounding
- **Filing Timestamps**: Captures `accepted_date` from SEC feeds showing when filings were processed
- **Optional Redis caching** for HTTP responses to reduce load and speed up repeated runs
- **Per-host throttling** and site-specific headers (SEC feed uses contact email in User-Agent and From headers)
- **Docker support** with `docker-compose.yml` (app + redis) for reproducible runs

## Goals

- Scrape timely headlines and summaries relevant to major markets (DAX40, Nasdaq, Dow Jones, S&P 500)
- Ingest SEC filings with a modular parser architecture supporting multiple form types
- Surface structured transaction information with normalized dates (ISO 8601) and rounded prices
- Produce a clean JSON output consumable by other microservices

## Architecture

The scraper uses a modular parser architecture:

- **Generic Form Fetcher** (`src/news_scraper/form_fetcher.py`) - Handles fetching and deduplication for any SEC form type
- **Base Parser** (`src/news_scraper/parsers/base.py`) - Abstract base class with shared utilities (date normalization, number parsing, etc.)
- **Form-Specific Parsers** (`src/news_scraper/parsers/form144.py`, etc.) - Implement parsing logic for each form type
- **Parser Registry** (`src/news_scraper/parsers/__init__.py`) - Manages parser registration and lookup

See [docs/parser-architecture.md](docs/parser-architecture.md) for details on extending the architecture.

### Supported SEC Forms

- ✅ **Form 144** - Insider intent to sell filings
- 🔜 **Form 8-K** - Material events (planned)
- 🔜 **Form 4** - Insider transactions (planned)

### Output Format

Each Form 144 entry includes:

```json
{
  "form_type": "144",
  "transaction_type": "sell",
  "shares": 12493,
  "price": 135.37,
  "value": 1691200.10,
  "reporting_owner": "John Doe",
  "issuer_name": "Example Corp",
  "ticker": "EX",
  "accepted_date": "2025-01-15T14:30:00-05:00",
  "date_of_transaction": "2025-01-15",
  "index_url": "https://www.sec.gov/...",
  "document_url": "https://www.sec.gov/...",
  "source": "sec_form_144"
}
```

**Key Features:**
- Dates normalized to ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS±HH:MM`)
- Prices rounded to 2 decimal places
- `accepted_date` captures SEC filing timestamp from RSS feed
- Automatic deduplication by `document_url`

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
PYTHONPATH=/home/bambule/insta-finance/insta-finance-news pytest -xvs
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
docker compose run --rm app bash -c "PYTHONPATH=/app pytest -xvs"
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

- EDGAR filings vary in format. The scraper implements best-effort heuristics to extract transaction type (buy/sell), number of shares, price and transaction value
- Dates are automatically normalized to ISO 8601 format (`YYYY-MM-DD`)
- Prices are rounded to 2 decimal places for consistency
- The `accepted_date` field captures when the SEC processed the filing (from RSS feed metadata)
- The scraper attempts to match issuers to index constituents using a simple S&P 500 and DJIA fetcher (from Wikipedia) and string-matching heuristics
- Deduplication is performed based on `document_url` to avoid duplicate filings

## Environment variables

- `SCRAPER_CONTACT_EMAIL` — contact email used in SEC User-Agent and From headers (default set in code).
- `MIN_SECONDS_BETWEEN_REQUESTS` — per-host throttle delay in seconds (default 1.0).
- `IGNORE_ROBOTS` — when set to 1/true, ignore robots.txt disallow rules and attempt HTML scraping.
- `REDIS_URL` — when set, the scraper will use Redis for caching HTTP responses.

## Scripts

- `scripts/print_scrape.py` — run the scraper and optionally write JSON output (`--out file.json`)
- `scripts/debug_sec.py` — debug helper to fetch and print SEC Atom feed request/response details
- `scripts/debug_form144.py` — debug helper for testing Form 144 parser
- `scripts/debug_rss.py` — debug helper for testing RSS feed parsing

## Tests and CI

- Unit tests live in `tests/` and are executed during Docker image builds
- The project includes pytest-based tests for:
  - Form 144 parsing with 20 real-world fixtures
  - Price computation and normalization
  - Deduplication logic
  - RSS feed parsing
  - Network error handling
- Run tests with: `PYTHONPATH=/path/to/project pytest -xvs`
- Adding a GitHub Actions workflow to run tests and build the image is recommended (not added yet)

## Next steps and suggestions

- Add canonical CIK→ticker mapping to reliably filter EDGAR filings by index constituents
- Implement Form 8-K parser for material events (high market impact)
- Implement Form 4 parser for insider transactions
- Add a `--no-cache` CLI flag to `scripts/print_scrape.py` to bypass Redis when present
- Add GitHub Actions workflow for CI/CD
- Consider adding more form types (13D, 13F, etc.)

## Documentation

- [Parser Architecture](docs/parser-architecture.md) - Detailed guide on the modular parser system
- [SEC Forms Overview](docs/sec-forms-overview.md) - Market impact ranking of different SEC forms
- [Deployment Guide](docs/deploy.md) - Instructions for deploying to Google Cloud Functions
- [Security Logging](docs/security-logging.md) - Enhanced security event logging for audit trails and monitoring
