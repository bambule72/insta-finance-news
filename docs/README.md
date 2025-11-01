# docs

Developer notes and quick references for the insta-finance-news service.

- Service entry point: `main.scrape_news`
- Scraper package: `src/news_scraper/`
- Tests: `pytest` in `tests/`

Running with Redis cache (development)
------------------------------------

You can run the service together with a Redis cache using Docker Compose:

```bash
docker compose up --build
```

This will start a Redis container and the app. The app will connect to Redis using the
`REDIS_URL` environment variable (set in `docker-compose.yml`). Caching is optional and
the scraper will work without Redis as well.

EDGAR / SEC compliance notes
---------------------------

- The scraper sets a descriptive User-Agent for EDGAR and includes a contact email.
- The scraper enforces per-host throttling (configurable via `MIN_SECONDS_BETWEEN_REQUESTS`).
- By default, if `robots.txt` for a site is inaccessible (403/401) we treat that as a disallow
	for safety; set `IGNORE_ROBOTS=1` to override (not recommended for EDGAR).
- Configure the contact email with `SCRAPER_CONTACT_EMAIL` environment variable.

When scraping SEC EDGAR, prefer using the official feeds and respect rate limits. If you need
to run at scale, consider using EDGAR bulk data or contact the SEC for permission.
