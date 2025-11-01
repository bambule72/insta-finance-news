"""Simple, conservative scraper for selected finance news sites.

Targets: Bloomberg, MarketWatch, CNBC

This module provides a function `get_latest_news()` which returns a list of
items with keys: source, title, summary, url.
"""
from __future__ import annotations

import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

from .logger import setup_logger

logger = setup_logger(__name__)


NEWS_SOURCES = {
    "bloomberg": "https://www.bloomberg.com",
    "marketwatch": "https://www.marketwatch.com",
    "cnbc": "https://www.cnbc.com",
}


def _request_with_retries(url: str, session: requests.Session | None = None, retries: int = 3, backoff: float = 1.0) -> str:
    session = session or requests.Session()
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.info("Fetching %s (attempt %d)", url, attempt)
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_exc = e
            wait = backoff * (2 ** (attempt - 1))
            logger.warning("Error fetching %s: %s. Retrying in %.1fs", url, e, wait)
            time.sleep(wait)
    raise last_exc


def _extract_from_html(html: str, base_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []

    # Conservative extraction: look for common headline tags and meta descriptions
    candidates = []
    # collect headline tags
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 30:  # avoid tiny labels
            # try find an URL
            a = tag.find("a") or tag.find_parent("a")
            href = a.get("href") if a else None
            candidates.append((text, href))

    # fallback: look for article links
    if not candidates:
        for a in soup.find_all("a"):
            txt = a.get_text(strip=True)
            if txt and len(txt) > 30:
                candidates.append((txt, a.get("href")))

    # build items, take first N
    seen_titles = set()
    for title, href in candidates[:8]:
        if title in seen_titles:
            continue
        seen_titles.add(title)
        summary = None
        # try meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            summary = meta.get("content")[:300]
        items.append({"title": title, "summary": summary, "url": href or base_url})

    return items


def fetch_site(source_key: str, session: requests.Session | None = None) -> List[Dict]:
    url = NEWS_SOURCES.get(source_key)
    if not url:
        raise ValueError(f"Unknown source: {source_key}")
    html = _request_with_retries(url, session=session)
    items = _extract_from_html(html, url)
    # annotate with source
    for it in items:
        it["source"] = source_key
    logger.info("Fetched %d items from %s", len(items), source_key)
    return items


def get_latest_news(sources: List[str] | None = None) -> List[Dict]:
    sources = sources or list(NEWS_SOURCES.keys())
    session = requests.Session()
    results: List[Dict] = []
    for s in sources:
        try:
            items = fetch_site(s, session=session)
            results.extend(items)
        except Exception as e:
            logger.exception("Failed to fetch %s: %s", s, e)
    # basic dedup by title
    seen = set()
    deduped = []
    for r in results:
        t = r.get("title")
        if t and t not in seen:
            seen.add(t)
            deduped.append(r)
    return deduped
