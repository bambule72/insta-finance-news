"""Simple, conservative scraper for selected finance news sites.

Targets: Bloomberg, MarketWatch, CNBC

This module provides a function `get_latest_news()` which returns a list of
items with keys: source, title, summary, url.
"""
from __future__ import annotations

import time
from typing import List, Dict
import random
import urllib.robotparser
import urllib.parse
import feedparser
import os
import json
from typing import Optional

try:
    import redis as _redis  # type: ignore
except Exception:  # redis optional
    _redis = None

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import re


from .logger import setup_logger

logger = setup_logger(__name__)


NEWS_SOURCES = {
    "bloomberg": "https://www.bloomberg.com",
    "marketwatch": "https://www.marketwatch.com",
    "cnbc": "https://www.cnbc.com",
    # SEC Form 144 filings (EDGAR current filings for type=144)
    "sec_form_144": "https://www.sec.gov",
}

# Optional RSS feeds (prefer RSS where available). These are conservative common feeds;
# site-specific feeds can be added or configured later.
RSS_FEEDS = {
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    # Atom feed for recent Form 144 filings
    "sec_form_144": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&output=atom",
}

# A small set of common User-Agent strings to reduce trivial blocking.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

# Runtime-configurable defaults for polite crawling
SCRAPER_CONTACT_EMAIL = os.environ.get("SCRAPER_CONTACT_EMAIL", "max.schoenenberger@gmx.de")
MIN_SECONDS_BETWEEN_REQUESTS = float(os.environ.get("MIN_SECONDS_BETWEEN_REQUESTS", "1.0"))
IGNORE_ROBOTS = os.environ.get("IGNORE_ROBOTS", "0") in ("1", "true", "True", "yes", "on")

# Site-specific header overrides (SEC requires a descriptive User-Agent with contact info)
SITE_HEADERS = {
    "sec_form_144": {
        # User-Agent will be combined with contact email below if needed
        "User-Agent": f"insta-finance-news/0.1 (+{SCRAPER_CONTACT_EMAIL})",
        "Accept": "application/atom+xml,application/xml,text/xml,*/*;q=0.1",
        "From": SCRAPER_CONTACT_EMAIL,
    }
}

# Simple in-process per-host throttle
_last_request_time: dict[str, float] = {}


def _throttle_for_host(url: str) -> None:
    """Sleep to enforce MIN_SECONDS_BETWEEN_REQUESTS between requests to the same host."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc
    now = time.time()
    last = _last_request_time.get(host)
    if last is not None:
        elapsed = now - last
        if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
            wait = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
            logger.info("Throttling %s for %.2fs to respect rate limit", host, wait)
            time.sleep(wait)
    _last_request_time[host] = time.time()


def _request_with_retries(
    url: str,
    session: requests.Session | None = None,
    retries: int = 3,
    backoff: float = 1.0,
    headers: Dict | None = None,
) -> str:
    session = session or requests.Session()
    last_exc = None
    # optionally try cache first
    cache_client = _get_redis_client()
    cache_key = f"http:{url}"
    if cache_client:
        try:
            cached = cache_client.get(cache_key)
            if cached:
                logger.info("Cache hit for %s", url)
                return json.loads(cached)
        except Exception:
            # ignore cache errors
            logger.debug("Cache read failed for %s", url)
    for attempt in range(1, retries + 1):
        try:
            # rotate/set a User-Agent if none supplied
            req_headers = dict(headers or {})
            if "User-Agent" not in req_headers:
                req_headers.setdefault("User-Agent", random.choice(USER_AGENTS))

            # throttle per-host to be polite
            _throttle_for_host(url)

            logger.info("Fetching %s (attempt %d)", url, attempt)
            resp = session.get(url, timeout=10, headers=req_headers)
            resp.raise_for_status()
            body = resp.text
            # write to cache if available
            if cache_client:
                try:
                    cache_client.set(cache_key, json.dumps(body), ex=600)
                except Exception:
                    logger.debug("Cache write failed for %s", url)
            return body
        except Exception as e:
            last_exc = e
            wait = backoff * (2 ** (attempt - 1))
            logger.warning("Error fetching %s: %s. Retrying in %.1fs", url, e, wait)
            time.sleep(wait)
    raise last_exc


def _is_allowed_by_robots(session: requests.Session, base_url: str, user_agent: str = "*") -> bool:
    """Check robots.txt for the given base URL. If robots.txt cannot be fetched, assume allowed.

    We fetch robots.txt using the provided session so proxies/headers are used consistently.
    """
    robots_url = base_url.rstrip("/") + "/robots.txt"
    try:
        resp = session.get(robots_url, timeout=5, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            # If robots.txt exists but is inaccessible (403/401) treat as disallow by default
            if not IGNORE_ROBOTS:
                logger.info("robots.txt not accessible at %s (status %s); treating as disallow", robots_url, resp.status_code)
                return False
            logger.info("robots.txt not accessible at %s (status %s); IGNORE_ROBOTS set - assuming allowed", robots_url, resp.status_code)
            return True
        rp = urllib.robotparser.RobotFileParser()
        # RobotFileParser.parse expects an iterable of lines
        rp.parse(resp.text.splitlines())
        allowed = rp.can_fetch(user_agent, "/")
        logger.info("robots.txt allows fetch for %s: %s", base_url, allowed)
        return allowed
    except Exception:
        logger.warning("Failed to fetch/parse robots.txt for %s; assuming allowed", base_url)
        return True


def _fetch_rss(source_key: str, session: requests.Session | None = None, max_items: int = 10) -> List[Dict]:
    """Try to fetch RSS for a source and return parsed items.

    Returns an empty list if RSS is not available or contains no entries.
    """
    session = session or requests.Session()
    feed_url = RSS_FEEDS.get(source_key)
    if not feed_url:
        return []
    try:
        logger.info("Trying RSS feed for %s: %s", source_key, feed_url)
        cache_client = _get_redis_client()
        cache_key = f"rss:{feed_url}"
        body = None
        if cache_client:
            try:
                cached = cache_client.get(cache_key)
                if cached:
                    logger.info("RSS cache hit for %s", source_key)
                    body = json.loads(cached)
            except Exception:
                logger.debug("RSS cache read failed for %s", source_key)

        if body is None:
            # allow site-specific header overrides (SEC requires contact info in UA)
            headers = dict(SITE_HEADERS.get(source_key, {}))
            if "User-Agent" not in headers:
                headers["User-Agent"] = random.choice(USER_AGENTS)
            resp = session.get(feed_url, timeout=10, headers=headers)
            resp.raise_for_status()
            body = resp.text
            if cache_client:
                try:
                    cache_client.set(cache_key, json.dumps(body), ex=300)
                except Exception:
                    logger.debug("RSS cache write failed for %s", source_key)

        parsed = feedparser.parse(body)
        entries = []
        for e in parsed.entries[:max_items]:
            title = getattr(e, "title", None) or getattr(e, "summary", "")
            summary = getattr(e, "summary", None) or getattr(e, "description", None)
            link = getattr(e, "link", None)
            entries.append({"title": title, "summary": (summary[:300] if summary else None), "url": link, "source": source_key, "raw": e})
        logger.info("RSS returned %d entries for %s", len(entries), source_key)

        # If this is the SEC Form 144 feed, attempt to parse filings into structured records
        if source_key == "sec_form_144":
            try:
                structured = _process_sec_form144_entries(entries, session=session)
                logger.info("Parsed %d structured SEC Form 144 entries", len(structured))
                return structured
            except Exception as e:
                logger.warning("Failed to parse SEC Form 144 entries: %s", e)
                # fall back to raw entries
        return entries
    except Exception as e:
        logger.warning("RSS fetch/parse failed for %s: %s", source_key, e)
        return []


def _get_redis_client() -> Optional[object]:
    """Lazily create and return a redis client if REDIS_URL is set and redis package available.

    Returns None if redis is not configured or import failed.
    """
    url = os.environ.get("REDIS_URL")
    if not url or _redis is None:
        return None
    try:
        # use a simple redis.Redis client
        client = _redis.from_url(url, decode_responses=True)
        # quick ping to validate connection (non-fatal)
        client.ping()
        return client
    except Exception:
        logger.warning("Could not connect to Redis at %s; continuing without cache", url)
        return None


def _extract_from_html(html: str, base_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []

    # Conservative extraction: look for common headline tags and meta descriptions
    candidates = []
    # collect headline tags
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        # accept shorter titles too (financial headlines can be concise)
        if text and len(text) > 15:  # avoid tiny labels
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
    session = session or requests.Session()

    # Try RSS first (use site-specific headers where appropriate).
    # We allow RSS to be fetched even when robots.txt is inaccessible because RSS
    # is an official published feed; treat HTML scraping more conservatively.
    rss_items = _fetch_rss(source_key, session=session, max_items=10)
    if rss_items and len(rss_items) >= 1:
        logger.info("Using RSS items for %s (%d)", source_key, len(rss_items))
        return rss_items

    # Respect robots.txt for the base site before attempting HTML scraping
    if not _is_allowed_by_robots(session, url, user_agent="*"):
        logger.info("robots.txt disallows scraping %s; skipping HTML fetch", source_key)
        return []

    # Fallback to HTML scraping when RSS not available or insufficient
    # pass site-specific headers for HTML fetch as well
    headers = SITE_HEADERS.get(source_key)
    html = _request_with_retries(url, session=session, headers=headers)
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


# ---- SEC / EDGAR parsing helpers ----

# simple cache for index constituents to avoid repeated web calls
_index_cache: dict = {"ts": 0.0, "data": {}}


def _fetch_sp500_members(session: requests.Session) -> set:
    """Fetch S&P 500 tickers from Wikipedia (best-effort).

    Returns a set of uppercase tickers. If fetching fails, returns an empty set.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        body = _request_with_retries(url, session=session, retries=2)
        soup = BeautifulSoup(body, "lxml")
        table = soup.find("table", attrs={"id": "constituents"}) or soup.find("table", class_="wikitable")
        members = set()
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if not cols:
                    continue
                ticker = cols[0].get_text(strip=True).upper()
                members.add(ticker)
        return members
    except Exception:
        logger.warning("Could not fetch S&P 500 members from Wikipedia")
        return set()


def _fetch_djia_members(session: requests.Session) -> set:
    """Fetch DJIA members from Wikipedia (best-effort).

    Returns a set of uppercase tickers. If fetching fails, returns an empty set.
    """
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    try:
        body = _request_with_retries(url, session=session, retries=2)
        soup = BeautifulSoup(body, "lxml")
        # DJIA page includes a table of components; find a table with 'Components' caption
        tables = soup.find_all("table", class_="wikitable")
        members = set()
        for table in tables:
            if table.find("caption") and "components" in table.find("caption").get_text(strip=True).lower():
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if cols:
                        ticker = cols[2].get_text(strip=True).upper() if len(cols) > 2 else cols[0].get_text(strip=True).upper()
                        members.add(ticker)
                break
        # fallback: try first wikitable and take ticker-like strings
        if not members and tables:
            for row in tables[0].find_all("tr")[1:]:
                cols = row.find_all("td")
                if cols:
                    ticker = cols[2].get_text(strip=True).upper() if len(cols) > 2 else cols[0].get_text(strip=True).upper()
                    members.add(ticker)
        return members
    except Exception:
        logger.warning("Could not fetch DJIA members from Wikipedia")
        return set()


def _get_index_lists(session: requests.Session) -> dict:
    """Return a dict of index_name -> set(tickers). Caches results during process lifetime."""
    # cache for 12 hours
    now = time.time()
    if now - _index_cache.get("ts", 0) < 60 * 60 * 12 and _index_cache.get("data"):
        return _index_cache["data"]
    data = {}
    data["sp500"] = _fetch_sp500_members(session)
    data["djia"] = _fetch_djia_members(session)
    # nasdaq/nyse composite lists are large and not fetched here; leave empty
    data["nasdaq"] = set()
    data["nyse"] = set()
    _index_cache["ts"] = now
    _index_cache["data"] = data
    return data


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


def _find_filing_document_link(index_html: str, index_url: str) -> Optional[str]:
    """Given an EDGAR index page HTML, find the most likely link to the actual Form 144 filing document.

    Returns an absolute URL or None.
    """
    soup = BeautifulSoup(index_html, "lxml")
    # EDGAR index pages often contain a table with class 'tableFile' or links under 'Documents'
    # Search for <a> whose href contains '.htm' or '.txt' but not '-index.htm'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith("-index.htm"):
            continue
        if ".htm" in href or ".txt" in href or ".xml" in href:
            # prefer XML files (more structured) and links containing 'form' or '144'
            text = a.get_text(" ", strip=True).lower()
            if (".xml" in href.lower() and ("144" in href.lower() or "form" in href.lower())) or \
               "144" in href.lower() or "form 144" in text or "form144" in href.lower() or "form-144" in href.lower():
                return urllib.parse.urljoin("https://www.sec.gov", href)
    # fallback: take first .htm/.txt/xml link that's not the index itself
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith("-index.htm"):
            continue
        if ".xml" in href:  # prefer XML if available
            return urllib.parse.urljoin("https://www.sec.gov", href)
        if ".htm" in href or ".txt" in href:
            return urllib.parse.urljoin("https://www.sec.gov", href)
    return None


def _extract_from_filing_text(text: str) -> dict:
    """Extract transaction details from filing content. Handles both XML and text content.
    Returns a dict with transaction_type, shares, price, value, reporting_owner.
    """
    out = {"transaction_type": None, "shares": None, "price": None, "value": None, "reporting_owner": None}
    
    # If this looks like XML/HTML with tables, try to parse with lxml first
    head_text = text[:2000].lower()
    if text.strip().startswith("<?xml") or "<xml" in head_text or "<html" in head_text or "<table" in head_text:
        try:
            # Use lxml for better XPath support; use the HTML parser when appropriate
            from lxml import etree, html
            root = None
            try:
                # If it's XML-like, try strict XML parse
                if text.strip().startswith("<?xml") or "<xml" in head_text:
                    root = etree.fromstring(text.encode("utf-8"))
                else:
                    # HTML parse (more forgiving)
                    root = html.fromstring(text)
            except Exception:
                # fallback to HTML parser
                root = html.fromstring(text)
            
            # Form 144 is always in HTML table format with multiple tables and headers
            
            # First try to get reporting owner name (in a div with class "fakeBox" or labeled cell)
            owner_cells = root.xpath("""//td[
                contains(text(), 'Name of Person') or 
                contains(text(), 'Account the Securities') or 
                contains(text(), 'Name of Reporting')
            ]/following-sibling::td[1]/div[@class='fakeBox']""")
            if owner_cells:
                owner = owner_cells[0].text_content().strip()
                if owner:
                    out["reporting_owner"] = owner
            
            # Primary table: Form 144 always has a summary table at top with:
            # - Title of Securities (usually first column)
            # - Number of Shares 
            # - Aggregate Market Value
            # This table comes before the transaction history table

            # First try to find tables with Form 144 transaction details
            main_table = root.xpath("""//table[
                .//tr[
                    contains(normalize-space(.), 'Title of Securities') or
                    contains(normalize-space(.), 'Number of Shares') or
                    contains(normalize-space(.), 'Aggregate Market Value') or
                    contains(normalize-space(.), 'Securities to be Sold')
                ]
            ]""") 

            # If no table matched, try more generic tables with Common Stock references
            if not main_table:
                main_table = root.xpath("""//table[.//tr[
                    contains(normalize-space(.), 'Common Stock') or
                    contains(normalize-space(.), 'Class A') or
                    contains(normalize-space(.), 'Class B')
                ]]""")

            # If still not found, look for explicit section labels such as
            # "144: Securities Information" or "144: Issuer Information" and
            # take the first following table.
            if not main_table:
                label_nodes = root.xpath("""//*[contains(translate(string(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '144: securities information') or contains(translate(string(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '144: issuer information') or contains(translate(string(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'securities information') or contains(translate(string(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'issuer information')]""")
                for label in label_nodes:
                    following_tables = label.xpath('following::table')
                    if following_tables:
                        main_table = [following_tables[0]]
                        break
            
            if main_table:
                tbl = main_table[0]

                # Try to detect a caption or nearby label indicating the Form 144 "Securities Information" table
                caption = " ".join(tbl.xpath('.//caption//text()') or [])

                # Find a header row (first row containing th elements or obvious header-like td's)
                header_row = None
                for tr in tbl.xpath('.//tr'):
                    if tr.xpath('.//th'):
                        header_row = tr
                        break
                    # some tables use bold/strong in td for headers
                    if tr.xpath('.//td//strong') or tr.xpath('.//td//b'):
                        header_row = tr
                        break

                # fallback to first row
                if header_row is None:
                    rows = tbl.xpath('.//tr')
                    header_row = rows[0] if rows else None

                # Map header text -> column index for known fields
                share_col = value_col = price_col = date_col = exchange_col = issuer_col = None
                header_texts = []
                if header_row is not None:
                    cells = header_row.xpath('.//th|.//td')
                    for i, cell in enumerate(cells):
                        txt = cell.text_content().lower().strip()
                        header_texts.append(txt)
                        # common header variants for number of shares
                        if re.search(r'number of shares|number of shares or other units to be sold|shares to be sold|amount of securities|number of units|units to be sold', txt):
                            share_col = i
                        # aggregate market value
                        elif re.search(r'aggregate market value|aggregate value|market value|total value|aggregate amount', txt):
                            value_col = i
                        # price per share
                        elif re.search(r'price per share|price\s*per\s*share|market price|price', txt):
                            price_col = i
                        # approximate date of sale
                        elif re.search(r'approximate date|approximate date of sale|date of sale', txt):
                            date_col = i
                        # securities exchange
                        elif re.search(r'name of securities exchange|securities exchange|exchange', txt):
                            exchange_col = i
                        # issuer name column
                        elif re.search(r'name of issuer|issuer', txt):
                            issuer_col = i

                # Now find the most likely data row: prefer rows mentioning 'common' or numeric content
                data_rows = tbl.xpath('.//tr[td]')
                chosen_row = None
                for row in data_rows:
                    txt = row.xpath('string()').lower()
                    if any(x in txt for x in ('common', 'class a', 'class b', 'ordinary shares')):
                        chosen_row = row
                        break

                if chosen_row is None:
                    # pick first row that has at least one numeric-looking cell
                    for row in data_rows:
                        t = row.xpath('string()')
                        if re.search(r'[0-9][0-9,\. ]+[0-9]', t):
                            chosen_row = row
                            break

                # If we found a data row, extract values using mapped columns and fallbacks
                if chosen_row is not None:
                    cells = chosen_row.xpath('.//td')
                    # shares
                    if share_col is not None and share_col < len(cells):
                        out['shares'] = _safe_int(cells[share_col].text_content().strip())
                    # value
                    if value_col is not None and value_col < len(cells):
                        out['value'] = _normalize_number(cells[value_col].text_content().strip())
                    # price
                    if price_col is not None and price_col < len(cells):
                        out['price'] = _normalize_number(cells[price_col].text_content().strip())
                    # approximate date of sale
                    if date_col is not None and date_col < len(cells):
                        out['approximate_date_of_sale'] = cells[date_col].text_content().strip()
                    # securities exchange
                    if exchange_col is not None and exchange_col < len(cells):
                        out['securities_exchange'] = cells[exchange_col].text_content().strip()
                    # issuer from this row if present
                    if issuer_col is not None and issuer_col < len(cells):
                        issuer_name = cells[issuer_col].text_content().strip()
                        if issuer_name:
                            out['issuer_name'] = issuer_name

                    # fallback: look for $ amounts in the row
                    if out.get('value') is None:
                        for cell in cells:
                            txt = cell.text_content()
                            if '$' in txt:
                                v = _normalize_number(txt)
                                if v is not None:
                                    out['value'] = v
                                    break

                    # fallback: try to pick up a shares-like number anywhere in the row
                    if out.get('shares') is None:
                        for cell in cells:
                            txt = cell.text_content()
                            m = re.search(r'([0-9][0-9,\. ]+[0-9])', txt)
                            if m:
                                out['shares'] = _safe_int(m.group(1))
                                break
            
            # If we don't have data yet, try finding any suitable table
            if not any(v is not None for v in (out["shares"], out["value"])):
                sec_tables = root.xpath("//table[.//tr/td[1][contains(., 'Common') or contains(., 'Stock') or contains(., 'Class A')]]")

                if sec_tables:
                    # Get data rows with securities info
                    data_rows = []
                    for row in sec_tables[0].xpath(".//tr"):
                        txt = row.xpath("string()").lower()
                        if any(x in txt for x in ('common', 'stock', 'class a', 'class b')):
                            data_rows.append(row)
                    
                    if data_rows:
                        cells = data_rows[0].xpath(".//td")
                        
                        # Look for shares in cells that:
                        # 1. Follow a header containing 'Amount', 'Number', or 'Shares'
                        # 2. Have preceding cell with title "Common" or "Stock"
                        # 3. Contain only numbers and basic punctuation
                        for i, cell in enumerate(cells):
                            if i == 0:  # Skip first cell (security name)
                                continue
                            txt = cell.text_content().strip()
                            if len(txt) > 20:  # Skip long text
                                continue
                            # Look for number-like content
                            if re.match(r'^[\d,. ]+$', txt):
                                if i > 0:
                                    prev = cells[i-1].text_content().lower()
                                    if any(x in prev for x in ('common', 'stock', 'shares', 'number', 'amount')):
                                        try:
                                            shares = _safe_int(txt)
                                            if shares and shares > 100:
                                                out["shares"] = shares
                                                break
                                        except Exception:
                                            continue
                        
                        # Look for value - try a few approaches:
                        # 1. Column header has "Value" or "Price" and number follows
                        # 2. Number has $ symbol 
                        # 3. Number follows word "value" or "worth" in text
                        for i, cell in enumerate(cells):
                            txt = cell.text_content().strip()
                            if len(txt) > 30:  # Skip long text
                                continue
                            # Explicit $ amount
                            if '$' in txt:
                                try:
                                    out["value"] = _normalize_number(txt)
                                    break
                                except Exception:
                                    continue
                            # Look for value after relevant header
                            if i > 0:
                                prev = cells[i-1].text_content().lower()
                                if any(x in prev for x in ('value', 'price', 'worth', 'amount')):
                                    try:
                                        val = _normalize_number(txt)
                                        if val and val > 1000:  # Likely a dollar value if >1000
                                            out["value"] = val
                                            break
                                    except Exception:
                                        continue
            
            # If we have shares and value but no price, calculate price
            if out.get("shares") and out.get("value") and not out.get("price"):
                try:
                    out["price"] = out["value"] / out["shares"]
                except Exception:
                    pass
            
            # Form 144 is specifically for proposed sales
            out["transaction_type"] = "sell"
            
            # Verify this is a Form 144 notice of proposed sale
            doc_text = " ".join(root.xpath("//text()")).lower()
            if not ("form 144" in doc_text and "notice of proposed sale" in doc_text):
                # If this isn't really a Form 144 notice of sale, clear everything
                out = {"transaction_type": None, "shares": None, "price": None, "value": None, "reporting_owner": None}
                out["transaction_type"] = "sell"
            
            # If we found shares and price but no value, compute it
            if out.get("value") is None and out.get("shares") is not None and out.get("price") is not None:
                try:
                    out["value"] = float(out["shares"]) * float(out["price"])
                except Exception:
                    pass
            
            if any(v is not None for v in out.values()):
                return out  # return early if we got any values from XML
            
        except Exception as e:
            logger.debug("XML parsing failed, falling back to text: %s", e)
    
    # Fallback to text-based extraction for HTML or failed XML
    lowered = text.lower()
    
    # transaction type from text
    if "disposition" in lowered or "sold" in lowered or "sale" in lowered or "disposed" in lowered:
        out["transaction_type"] = "sell"
    elif "acquisition" in lowered or "purchase" in lowered or "bought" in lowered or "acquired" in lowered:
        out["transaction_type"] = "buy"
    
    # reporting owner from text
    m = re.search(r"reporting owner[:\s]{1,20}([A-Z0-9a-z \.,&\-()]{2,200})", text, re.IGNORECASE)
    if m:
        out["reporting_owner"] = m.group(1).strip()
    
    # shares from text
    m = re.search(r"number of shares[:\s]*([0-9,]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([0-9,]+)\s+shares", text, re.IGNORECASE)
    if m:
        out["shares"] = _safe_int(m.group(1))
    
    # price from text
    m = re.search(r"price\s*(?:per share)?[:\s]*\$?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    if m:
        out["price"] = _normalize_number(m.group(1))
    
    # transaction value from text
    m = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:total|value|amount)?", text)
    if m:
        out["value"] = _normalize_number(m.group(1))
    
    # compute value if missing but we have shares and price
    if out.get("value") is None and out.get("shares") is not None and out.get("price") is not None:
        try:
            out["value"] = float(out["shares"]) * float(out["price"])
        except Exception:
            pass
    
    return out


def _process_sec_form144_entries(entries: List[Dict], session: requests.Session | None = None) -> List[Dict]:
    """Turn RSS/Atom entries for SEC Form 144 feed into structured records.

    This is best-effort: EDGAR filings are not strictly uniform in presentation. The function
    will attempt to fetch the filing document and extract transaction_type, shares and value.
    """
    session = session or requests.Session()
    processed = []
    index_lists = _get_index_lists(session)

    for e in entries:
        try:
            index_url = e.get("url")
            if not index_url:
                continue
            logger.info("Processing SEC entry %s", index_url)
            index_html = _request_with_retries(index_url, session=session, headers=SITE_HEADERS.get("sec_form_144"))
            doc_url = _find_filing_document_link(index_html, index_url)
            if not doc_url:
                logger.info("Could not locate filing document for %s; skipping structured parse", index_url)
                # keep the raw entry but mark as unparsed
                e.update({"parsed": False})
                processed.append(e)
                continue
            filing_html = _request_with_retries(doc_url, session=session, headers=SITE_HEADERS.get("sec_form_144"))
            # pass the raw filing HTML/XML into the extractor so the XML parsing branch
            # can operate on the original document structure (tables, captions, etc.)
            extracted = _extract_from_filing_text(filing_html)

            # issuer heuristics: from entry title or from index page
            issuer = None
            cik = None
            # try to get from feed raw entry
            raw = e.get("raw")
            if raw:
                issuer = getattr(raw, "title", None) or getattr(raw, "summary", None)
                # published/updated
                filing_date = getattr(raw, "published", None) or getattr(raw, "updated", None)
            else:
                filing_date = None

            # try to find CIK in index_html
            m = re.search(r"CIK\s*#?:?\s*([0-9]{8,10})", index_html)
            if m:
                cik = m.group(1)

            record = {
                "source": "sec_form_144",
                "title": e.get("title"),
                "issuer": issuer,
                "cik": cik,
                "filing_date": filing_date,
                "filing_index_url": index_url,
                "filing_document_url": doc_url,
                "parsed": True,
            }
            record.update(extracted)

            # determine approximate ticker by matching issuer text against index lists (best-effort)
            matched_indices = []
            ticker_guess = None
            issuer_text = (issuer or "").upper()
            for idx_name, tickers in index_lists.items():
                if not tickers:
                    continue
                for t in tickers:
                    if t in issuer_text or (len(t) > 1 and t.replace(".", "") in issuer_text):
                        matched_indices.append(idx_name)
                        ticker_guess = t
                        break
            record["matched_indices"] = matched_indices
            record["ticker_guess"] = ticker_guess

            # filter: if index lists are non-empty and none matched, skip adding unless no index lists available
            any_index_lists = any(len(v) for v in index_lists.values())
            if any_index_lists and not matched_indices:
                logger.info("Filing at %s does not match tracked indices; skipping", index_url)
                continue

            processed.append(record)
        except Exception as err:
            logger.exception("Error processing SEC entry %s: %s", e.get("url"), err)
            # include original entry as fallback
            e.update({"parsed": False})
            processed.append(e)

    return processed
