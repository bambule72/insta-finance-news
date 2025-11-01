"""Debug helper to examine SEC Form 144 filings and parsing diagnostics.

Usage:
    python3 scripts/debug_form144.py --limit 5 --save-dir /tmp/form144

This script will:
 - fetch the SEC atom feed for type=144
 - for each entry, find the filing document URL (index -> document)
 - download the filing document HTML/XML
 - save it to disk (optional)
 - run the scraper's extractor on the raw HTML and print diagnostics

Designed to run inside the project's docker container (same env as normal runner).
"""
from __future__ import annotations

import os
import argparse
import json
import textwrap
import requests
from bs4 import BeautifulSoup

# import helpers from the package
from src.news_scraper import scraper


def find_doc_url(index_url: str, session: requests.Session) -> str | None:
    try:
        html = scraper._request_with_retries(index_url, session=session, headers=scraper.SITE_HEADERS.get('sec_form_144'))
        return scraper._find_filing_document_link(html, index_url)
    except Exception as e:
        print(f"Error fetching index page {index_url}: {e}")
        return None


def download_doc(doc_url: str, session: requests.Session) -> str | None:
    try:
        return scraper._request_with_retries(doc_url, session=session, headers=scraper.SITE_HEADERS.get('sec_form_144'))
    except Exception as e:
        print(f"Error fetching document {doc_url}: {e}")
        return None


def main(limit: int = 10, save_dir: str | None = None):
    session = requests.Session()
    feed_url = scraper.RSS_FEEDS['sec_form_144']
    print(f"Fetching feed {feed_url}")
    try:
        feed_body = scraper._request_with_retries(feed_url, session=session, headers=scraper.SITE_HEADERS.get('sec_form_144'))
    except Exception as e:
        print(f"Failed to fetch feed: {e}")
        return

    # parse feed entries via feedparser for consistency with scraper
    import feedparser

    parsed = feedparser.parse(feed_body)
    entries = parsed.entries[:limit]
    print(f"Found {len(entries)} entries (showing up to {limit})")

    os.makedirs(save_dir, exist_ok=True) if save_dir else None

    for i, e in enumerate(entries, start=1):
        title = getattr(e, 'title', '')
        index_url = getattr(e, 'link', None) or getattr(e, 'id', None)
        print('\n' + '=' * 80)
        print(f"[{i}] Title: {title}")
        print(f"Index URL: {index_url}")
        if not index_url:
            print('  no index URL found, skipping')
            continue

        doc_url = find_doc_url(index_url, session)
        print(f"Document URL: {doc_url}")
        if not doc_url:
            continue

        filing_html = download_doc(doc_url, session)
        if not filing_html:
            continue

        # save raw HTML if requested
        if save_dir:
            fn = os.path.join(save_dir, f"entry_{i}.html")
            with open(fn, 'w', encoding='utf-8') as fh:
                fh.write(filing_html)
            print(f"  saved filing to {fn}")

        # run the extractor (gives structured output)
        extracted = scraper._extract_from_filing_text(filing_html)
        print('Extractor output:')
        print(json.dumps(extracted, indent=2, ensure_ascii=False))

        # additional diagnostics: parse as BeautifulSoup and show first table captions and headers
        soup = BeautifulSoup(filing_html, 'lxml')
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables in document")
        for ti, t in enumerate(tables[:5], start=1):
            cap = t.find('caption')
            cap_text = cap.get_text(strip=True) if cap else ''
            headers = []
            # try to get first header row
            hdr = t.find('tr')
            if hdr:
                for th in hdr.find_all(['th','td']):
                    text = th.get_text(strip=True)
                    if len(text) > 0:
                        headers.append(text)
            print(f"  Table {ti}: caption='{cap_text}' headers={headers}")

        # show text snippet around likely '144' labels
        txt = soup.get_text('\n')
        low = txt.lower()
        idx = low.find('144:')
        if idx >= 0:
            start = max(0, idx-200)
            end = idx+400
            snippet = txt[start:end]
            print('\nSnippet around "144:":\n')
            print(textwrap.indent(snippet, '    '))
        else:
            print('\nNo explicit "144:" label found in the plaintext of this document')

    print('\nDone')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=5, help='How many feed entries to process')
    p.add_argument('--save-dir', type=str, default=None, help='Optional directory to save raw filings')
    args = p.parse_args()
    main(limit=args.limit, save_dir=args.save_dir)
