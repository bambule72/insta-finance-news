#!/usr/bin/env python3
"""Debug script to see what's in the SEC RSS feed."""

import feedparser
import requests

feed_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&output=atom"
headers = {
    "User-Agent": "insta-finance-news/0.1 (+max.schoenenberger@gmx.de)",
    "Accept": "application/atom+xml,application/xml,text/xml,*/*;q=0.1",
    "From": "max.schoenenberger@gmx.de",
}

print(f"Fetching {feed_url}...")
resp = requests.get(feed_url, headers=headers)
resp.raise_for_status()

print(f"\nParsing feed...")
parsed = feedparser.parse(resp.text)

if parsed.entries:
    entry = parsed.entries[0]
    print(f"\nFirst entry attributes:")
    for attr in dir(entry):
        if not attr.startswith('_'):
            val = getattr(entry, attr)
            if not callable(val):
                print(f"  {attr}: {val}")
else:
    print("No entries found")
