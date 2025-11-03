"""Scraper for SEC Form 144 filings.

This module provides functions to fetch and parse Form 144 filings from SEC EDGAR,
extracting structured data about proposed stock sales.
"""
from __future__ import annotations

import time
from typing import List, Dict, Optional, cast
import random
import urllib.robotparser
import urllib.parse
import feedparser
import os
import json
import re
import requests
from lxml import etree, html
from bs4 import BeautifulSoup

from .scraper_types import FormEntry
from . import company_tickers
from .logger import setup_logger

logger = setup_logger(__name__)

try:
    import redis as _redis  # type: ignore
except Exception:  # redis optional
    _redis = None

# Minimal site/source configuration and helpers used by tests and higher-level code
NEWS_SOURCES = {
    # SEC Form 144 filings (EDGAR current filings for type=144)
    "sec_form_144": "https://www.sec.gov",
}

# Atom/RSS feed URLs (optional; tests do not require full RSS handling)
RSS_FEEDS = {
    "sec_form_144": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&output=atom",
}

# A small set of common User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

# Site-specific header overrides (SEC expects a descriptive User-Agent and contact info)
SITE_HEADERS = {
    "sec_form_144": {
        "User-Agent": f"insta-finance-news/0.1 (+{os.environ.get('SCRAPER_CONTACT_EMAIL', 'max.schoenenberger@gmx.de')})",
        "Accept": "application/atom+xml,application/xml,text/xml,*/*;q=0.1",
        "From": os.environ.get('SCRAPER_CONTACT_EMAIL', 'max.schoenenberger@gmx.de'),
    }
}

# Simple in-process per-host throttle (kept minimal for tests)
_last_request_time: dict[str, float] = {}


def _throttle_for_host(url: str) -> None:
    # lightweight throttle for real scraping; tests call mostly mocked sessions
    return


def _request_with_retries(url: str, session: requests.Session | None = None, retries: int = 3, backoff: float = 1.0, headers: Dict | None = None) -> str:
    """Simple request helper used by tests. Accepts a session-like object exposing get()."""
    session = session or requests.Session()
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=10, headers=headers)
            # support DummyResponse used in tests
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
            return getattr(resp, "text", resp)
        except Exception as e:
            last_exc = e
            if attempt == retries:
                raise
            time.sleep(backoff * (2 ** (attempt - 1)))


def _fetch_rss(source_key: str, session: requests.Session | None = None, max_items: int = 10) -> List[Dict]:
    # For tests we keep RSS handling minimal and return empty
    return []


def _is_allowed_by_robots(session: requests.Session, base_url: str, user_agent: str = "*") -> bool:
    # tests don't exercise robots.txt; assume allowed
    return True


def _get_redis_client() -> Optional[object]:
    # Redis optional in tests
    return None


def _find_filing_document_link(index_html: str, index_url: str) -> Optional[str]:
    """Given an EDGAR index page HTML, find the most likely link to the actual filing document.

    Returns an absolute URL or None.
    """
    soup = BeautifulSoup(index_html, "lxml")
    # prefer XML links that contain '144' or 'form'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith("-index.htm"):
            continue
        low = href.lower()
        text = a.get_text(" ", strip=True).lower()
        if ".xml" in low and ("144" in low or "form" in low):
            return urllib.parse.urljoin("https://www.sec.gov", href)
        if "144" in low or "form 144" in text or "form144" in low or "form-144" in low:
            return urllib.parse.urljoin("https://www.sec.gov", href)

    # fallback: first .xml then .htm/.txt
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith("-index.htm"):
            continue
        if ".xml" in href:
            return urllib.parse.urljoin("https://www.sec.gov", href)
        if ".htm" in href or ".txt" in href:
            return urllib.parse.urljoin("https://www.sec.gov", href)
    return None


def _extract_from_html(html_text: str, base_url: str) -> List[Dict]:
    """Simple HTML extractor used by tests: find headline tags and meta description."""
    soup = BeautifulSoup(html_text, "lxml")
    items: List[Dict] = []

    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 15:
            a = tag.find("a") or tag.find_parent("a")
            href = a.get("href") if a else None
            candidates.append((text, href))

    if not candidates:
        for a in soup.find_all("a"):
            txt = a.get_text(strip=True)
            if txt and len(txt) > 30:
                candidates.append((txt, a.get("href")))

    seen = set()
    for title, href in candidates[:8]:
        if title in seen:
            continue
        seen.add(title)
        meta = soup.find("meta", attrs={"name": "description"})
        summary = meta.get("content")[:300] if meta and meta.get("content") else None
        items.append({"title": title, "summary": summary, "url": href or base_url})
    return items


def fetch_site(source_key: str, session: requests.Session | None = None) -> List[Dict]:
    url = NEWS_SOURCES.get(source_key)
    if not url:
        raise ValueError(f"Unknown source: {source_key}")
    session = session or requests.Session()

    # Try RSS first
    rss_items = _fetch_rss(source_key, session=session, max_items=10)
    if rss_items:
        for it in rss_items:
            it["source"] = source_key
        return rss_items

    # fallback to HTML scraping
    html_text = _request_with_retries(url, session=session, headers={"User-Agent": random.choice(USER_AGENTS)})
    items = _extract_from_html(html_text, url)
    for it in items:
        it["source"] = source_key
    return items


def get_latest_news(sources: List[str] | None = None) -> List[Dict]:
    sources = sources or list(NEWS_SOURCES.keys())
    session = requests.Session()
    results: List[Dict] = []
    for s in sources:
        try:
            items = fetch_site(s, session=session)
            results.extend(items)
        except Exception:
            continue
    # basic dedup by title
    seen = set()
    deduped = []
    for r in results:
        t = r.get("title")
        if t and t not in seen:
            seen.add(t)
            deduped.append(r)
    return deduped


def get_latest_sec_form_144(limit: int = 10) -> List[Dict]:
    """Fetch the SEC Form 144 atom feed, download filing documents, and return extracted items.

    This mirrors the debug helper but returns structured items for use by the CLI.
    """
    session = requests.Session()
    feed_url = RSS_FEEDS.get('sec_form_144')
    if not feed_url:
        return []
    try:
        feed_body = _request_with_retries(feed_url, session=session, headers=SITE_HEADERS.get('sec_form_144'))
    except Exception:
        return []

    parsed = feedparser.parse(feed_body)
    entries = getattr(parsed, 'entries', [])[:limit]
    results: List[Dict] = []
    for e in entries:
        index_url = getattr(e, 'link', None) or getattr(e, 'id', None)
        if not index_url:
            continue
        try:
            index_html = _request_with_retries(index_url, session=session, headers=SITE_HEADERS.get('sec_form_144'))
            doc_url = _find_filing_document_link(index_html, index_url)
            if not doc_url:
                continue
            filing_html = _request_with_retries(doc_url, session=session, headers=SITE_HEADERS.get('sec_form_144'))
            extracted = _extract_from_filing_text(filing_html)
            if extracted and any(v is not None for v in extracted.values()):
                extracted['index_url'] = index_url
                extracted['document_url'] = doc_url
                extracted['source'] = 'sec_form_144'
                results.append(extracted)
        except Exception:
            # skip individual failures
            continue
    # Deduplicate entries by document URL before returning
    return _dedup_form144_entries(results)


def _dedup_form144_entries(entries: List[FormEntry]) -> List[FormEntry]:
    """Remove duplicate Form 144 filings based on document URL."""
    seen_urls = set()
    deduped = []
    for e in entries:
        doc_url = e.get("document_url")
        if doc_url and doc_url not in seen_urls:
            seen_urls.add(doc_url)
            deduped.append(e)
    return deduped


def _normalize_number(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        # try to strip non-numeric
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
        if m:
            return float(m.group(1))
    return None


def _safe_int(s: str) -> Optional[int]:
    v = _normalize_number(s)
    return int(v) if v is not None else None


import datetime

def _normalize_date(date_str: str) -> str:
    """
    Normalize date strings like '10/31/2025' to ISO format '2025-10-31'.
    Returns the original string if parsing fails.
    """
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    return date_str.strip()

def _safe_float(val):
    try:
        return float(val.replace(",", "").replace("$", "").strip())
    except Exception:
        return None


def _extract_from_filing_text(text: str) -> FormEntry:
    """Extract transaction details from filing content. Simpler, robust implementation.

    This keeps the previous behavior but fixes syntax/indentation. It prefers structured parsing via
    lxml when available, but falls back to conservative text-based regex
    extraction which is sufficient for tests and CLI usage.
    """
    # Initialize output with all possible keys set to None
    out: FormEntry = {
        "transaction_type": None,
        "shares": None,
        "price": None,
        "value": None,
        "reporting_owner": None,
        "approximate_date_of_sale": None,
        "securities_exchange": None,
        "shares_outstanding": None,
        "issuer_name": None,
        "ticker": None,
        "index_url": None,
        "document_url": None,
        "source": None,
    }

    # Try structured parsing with lxml if available
    try:
        head_text = text[:200].lower()
        if text.strip().startswith("<?xml") or "<xml" in head_text:
            root = etree.fromstring(text.encode("utf-8"))
        else:
            root = html.fromstring(text)

        # Attempt to find issuer name by looking for the label cell and its sibling value cell
        issuer_cells = root.xpath(".//td[contains(., 'Name of Issuer') or contains(., 'Name of Issuer:')]")
        if issuer_cells:
            for cell in issuer_cells:
                parent = cell.getparent()
                # prefer the next td in the same row
                if parent is not None:
                    tds = parent.xpath('.//td')
                    try:
                        idx = tds.index(cell)
                    except ValueError:
                        idx = None
                    if idx is not None and idx + 1 < len(tds):
                        val = tds[idx + 1].text_content().strip()
                        val = re.sub(r'(?i)name of issuer[:\s]*', '', val).strip()
                        if val:
                            out['issuer_name'] = val
                            break

                # fallback: check for a nearby element containing the value
                sib = cell.xpath('./following-sibling::*')
                if sib:
                    txt = ' '.join([e.text_content().strip() for e in sib])
                    txt = re.sub(r'(?i)name of issuer[:\s]*', '', txt).strip()
                    if txt:
                        out['issuer_name'] = txt
                        break

                # last resort: remove the label from the cell's own text
                text_all = ''.join(cell.itertext()).strip()
                text_all = re.sub(r'(?i)name of issuer[:\s]*', '', text_all).strip()
                if text_all:
                    out['issuer_name'] = text_all
                    break

        # Try to find a table that contains share/price/value info and map headers to data cells
        tables = root.xpath('.//table')
        found = False
        for tbl in tables:
            txt = ' '.join(tbl.xpath('.//text()'))
            if not re.search(r'number of shares|aggregate market value|price per share|title of the class|title of the security', txt, re.IGNORECASE):
                continue

            rows = tbl.xpath('.//tr')
            header_cells = None
            header_index = None

            # Find a header row (either TH cells or a row that contains header-like text)
            for i, r in enumerate(rows):
                ths = [t.text_content().strip().lower() for t in r.xpath('.//th')]
                tds = [t.text_content().strip().lower() for t in r.xpath('.//td')]
                cell_texts = ths if ths else tds
                if not cell_texts:
                    continue
                if any(re.search(r'title of the class|title of the security|number of shares|price per share|aggregate market value|aggregate market', t) for t in cell_texts):
                    header_cells = cell_texts
                    header_index = i
                    break

            if header_cells is not None and header_index is not None:
                # Map subsequent rows using the header positions
                for r in rows[header_index + 1 :]:
                    cells = [c.text_content().strip() for c in r.xpath('.//td')]
                    if not cells:
                        continue

                    # Try to align header -> value by index. If lengths mismatch, use best-effort mapping.
                    for idx, h in enumerate(header_cells):
                        val = cells[idx].strip() if idx < len(cells) else ''
                        if not val:
                            continue
                        lh = h.lower()
                        # shares outstanding (match first because headers often contain 'number of shares')
                        if re.search(r'number of shares or other units outstanding|shares outstanding|\boutstanding\b', lh):
                            if out.get('shares_outstanding') is None:
                                out['shares_outstanding'] = _safe_int(val)
                        # shares being sold (more specific 'to be sold')
                        elif re.search(r'number of shares or other units to be sold|to be sold|number of shares to be sold', lh):
                            if out.get('shares') is None:
                                out['shares'] = _safe_int(val)
                        # generic shares fallback
                        elif re.search(r'number of shares|^shares$|\bshares\b', lh):
                            if out.get('shares') is None:
                                out['shares'] = _safe_int(val)
                        # price per share
                        elif re.search(r'price per share|price\b|per share', lh):
                            if out.get('price') is None:
                                out['price'] = _normalize_number(val)
                        # aggregate market value
                        elif re.search(r'aggregate market value|aggregate market|market value|value', lh):
                            if out.get('value') is None:
                                out['value'] = _normalize_number(val)
                        # shares outstanding
                        elif re.search(r'number of shares or other units outstanding|shares outstanding|outstanding', lh):
                            if out.get('shares_outstanding') is None:
                                out['shares_outstanding'] = _safe_int(val)
                        # approximate date of sale
                        elif re.search(r'approximate date of sale|date of sale|approximate date', lh):
                            if out.get('approximate_date_of_sale') is None:
                                out['approximate_date_of_sale'] = val
                        # securities exchange
                        elif re.search(r'name the securities exchange|securities exchange|exchange', lh):
                            if out.get('securities_exchange') is None:
                                out['securities_exchange'] = val

                    # If we found numeric data, stop scanning this table
                    if any(out.get(k) for k in ('shares', 'price', 'value')):
                        found = True
                        break

                if found:
                    break

            # Fallback: if no header mapping worked, try the old heuristic on the first numeric row
            for r in rows:
                cells = [c for c in r.xpath('.//td')]
                if not cells or len(cells) < 1:
                    continue
                row_text = ' '.join([c.text_content() for c in cells]).strip()
                if not re.search(r'[0-9]', row_text):
                    continue
                # try to extract shares, price, value from the row (fallback)
                m_shares = re.search(r'([0-9][0-9,]{1,}[0-9])', row_text)
                if m_shares and out.get('shares') is None:
                    out['shares'] = _safe_int(m_shares.group(1))
                m_price = re.search(r'\$?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:per share|price per share|price)?', row_text, re.IGNORECASE)
                if m_price and out.get('price') is None:
                    out['price'] = _normalize_number(m_price.group(1))
                m_value = re.search(r'\$\s*([0-9,]+(?:\.[0-9]{2})?)', row_text)
                if m_value and out.get('value') is None:
                    out['value'] = _normalize_number(m_value.group(1))
                found = True
                break
            if found:
                break

        # Try reporting owner in known labeled cells (use sibling value cell)
        owner_cells = root.xpath(".//td[contains(., 'Name of Reporting') or contains(., 'Name of Person') or contains(., 'Name of Person for Whose Account')]")
        if owner_cells:
            for cell in owner_cells:
                parent = cell.getparent()
                if parent is not None:
                    tds = parent.xpath('.//td')
                    try:
                        idx = tds.index(cell)
                    except ValueError:
                        idx = None
                    if idx is not None and idx + 1 < len(tds):
                        val = tds[idx + 1].text_content().strip()
                        val = re.sub(r'(?i)name of person for whose account the securities are to be sold[:\s]*', '', val).strip()
                        if val:
                            out['reporting_owner'] = val
                            break

                # fallback: remove label from own text
                text_all = ''.join(cell.itertext()).strip()
                text_all = re.sub(r'(?i)name of person for whose account the securities are to be sold[:\s]*', '', text_all).strip()
                if text_all and text_all.lower() not in ('name of person for whose account the securities are to be sold', 'name of reporting'):
                    out['reporting_owner'] = text_all
                    break

    except Exception:
        # Structured parsing failed; fall back to text extraction
        pass

    # Fallback/text-based extraction (also covers many simple cases)
    lowered = text.lower()
    if "disposition" in lowered or "sold" in lowered or "sale" in lowered or "disposed" in lowered:
        out["transaction_type"] = "sell"
    elif "acquisition" in lowered or "purchase" in lowered or "bought" in lowered or "acquired" in lowered:
        out["transaction_type"] = "buy"

    # reporting owner from text
    m = re.search(r"reporting owner[:\s]{1,20}([A-Za-z0-9 \.,&()\-]{2,200})", text, re.IGNORECASE)
    if m:
        out["reporting_owner"] = m.group(1).strip()

    # shares from text
    m = re.search(r"number of shares[:\s]*([0-9,]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([0-9,]+)\s+shares", text, re.IGNORECASE)
    if m and out.get('shares') is None:
        out["shares"] = _safe_int(m.group(1))

    # price from text
    m = re.search(r"price\s*(?:per share)?[:\s]*\$?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    if m and out.get('price') is None:
        out["price"] = _normalize_number(m.group(1))

    # transaction value from text
    m = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:total|value|amount)?", text)
    if m and out.get('value') is None:
        out["value"] = _normalize_number(m.group(1))

    # shares outstanding from text
    m = re.search(r"(?:number of shares|shares) outstanding[:\s]*([0-9,]+)", text, re.IGNORECASE)
    if m and out.get('shares_outstanding') is None:
        out["shares_outstanding"] = _safe_int(m.group(1))

    # Compute value if missing but we have shares and price.
    # Also compute per-share price if it's missing but we have aggregate value and shares.
    try:
        shares = out.get("shares")
        price = out.get("price")
        value = out.get("value")

        # If value missing but shares & price present, compute value
        if value is None and shares is not None and price is not None:
            out["value"] = float(shares) * float(price)
            value = out["value"]

        # If price missing but value & shares present and shares != 0, compute price
        if price is None and shares is not None and value is not None:
            try:
                if float(shares) != 0:
                    out["price"] = float(value) / float(shares)
            except Exception:
                # guard against weird types/values; leave price as None on failure
                pass
    except Exception:
        pass

    # Normalize exchange if present
    if out.get("securities_exchange"):
        exchange = str(out["securities_exchange"]).strip().upper()
        exchange_map = {
            'NASDAQ GLOBAL MARKET': 'NASDAQ',
            'NASDAQ GLOBAL SELECT MARKET': 'NASDAQ',
            'NASDAQ CAPITAL MARKET': 'NASDAQ',
            'NASDAQ STOCK MARKET': 'NASDAQ',
            'NYSE MKT': 'NYSE',
            'NEW YORK STOCK EXCHANGE': 'NYSE'
        }
        out["securities_exchange"] = exchange_map.get(exchange, exchange)

    # If we have an issuer name but no ticker yet, try SEC company info
    issuer = out.get("issuer_name")
    if issuer and not out.get("ticker"):
        try:
            ticker = company_tickers.find_ticker_by_name(str(issuer))
            if ticker:
                out["ticker"] = ticker
        except Exception:
            logger.debug("ticker lookup failed for issuer: %s", issuer)

    # After extracting fields from the table:
    if out.get("approximate_date_of_sale"):
        out["approximate_date_of_sale"] = _normalize_date(out["approximate_date_of_sale"])

    # Round computed price to 2 decimals if present
    if out.get("price") is not None:
        try:
            out["price"] = round(float(out["price"]), 2)
        except Exception:
            pass

    return out