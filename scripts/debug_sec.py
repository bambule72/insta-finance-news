#!/usr/bin/env python3
"""Debug helper: perform a single request to the SEC Form 144 Atom feed with the
same headers the scraper uses and print request/response details for diagnosis.

Usage:
  python scripts/debug_sec.py
"""
from __future__ import annotations

import random
import requests
import os
from src.news_scraper.scraper import RSS_FEEDS, USER_AGENTS, SITE_HEADERS


def main() -> int:
    feed_url = RSS_FEEDS.get("sec_form_144")
    if not feed_url:
        print("No SEC feed configured")
        return 2

    headers = dict(SITE_HEADERS.get("sec_form_144", {}))
    if "User-Agent" not in headers:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    print("Requesting:", feed_url)
    print("Request headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    try:
        resp = requests.get(feed_url, timeout=15, headers=headers)
    except Exception as e:
        print("Request failed:", e)
        return 1

    print("\nResponse status:", resp.status_code)
    print("Response headers:")
    for k, v in resp.headers.items():
        print(f"  {k}: {v}")

    body = resp.text
    print("\nBody snippet (first 2000 chars):\n")
    print(body[:2000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
