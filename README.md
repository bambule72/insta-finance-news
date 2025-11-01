# insta-finance-news

A microservice to scrape financial news and prepare short summaries for Instagram reels/stories.

This is the first microservice in a larger system. It scrapes headlines and short summaries about major market indexes and prepares structured output for downstream services that will generate media and publish it.

Goals
- Scrape financial news relevant to major indexes (DAX40, Nasdaq, Dow Jones 30, S&P 500).
- Produce daily and weekly summaries of market trends.
- Provide a clean JSON output consumable by content-generation microservices.

This service is implemented in Python and designed to be deployed to Google Cloud Functions.

Quick start

1. Create and activate a virtual environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run tests
```bash
pytest -q
```

4. Run locally with Functions Framework
```bash
functions-framework --target=scrape_news --debug
curl http://localhost:8080/
```

Roadmap
- Add rate limiting, user-agent rotation and robots.txt respect.
- Integrate `news-please` or another news extraction library as an optional back-end.
- Add Instagram content generation microservice and publishing automation.
