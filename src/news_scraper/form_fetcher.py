"""Generic SEC form fetcher - fetches and parses any supported SEC form type."""

from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
import feedparser
import requests

from .parsers import get_parser
from .logger import setup_logger

logger = setup_logger(__name__)


def fetch_sec_form(
    form_type: str,
    feed_url: str,
    headers: Dict[str, str] | None = None,
    limit: int = 10,
    session: requests.Session | None = None
) -> List[Dict[str, Any]]:
    """Generic function to fetch and parse any SEC form type.
    
    Args:
        form_type: SEC form type (e.g., '144', '8-K', '4')
        feed_url: SEC RSS/Atom feed URL for this form type
        headers: Optional HTTP headers for SEC requests
        limit: Maximum number of entries to fetch
        session: Optional requests session
        
    Returns:
        List of parsed form entries (type depends on form_type)
    """
    session = session or requests.Session()
    
    # Get the appropriate parser for this form type
    try:
        parser = get_parser(form_type)
    except ValueError as e:
        logger.error(f"No parser available for form type {form_type}: {e}")
        return []
    
    # Fetch the RSS/Atom feed
    try:
        resp = session.get(feed_url, timeout=10, headers=headers)
        resp.raise_for_status()
        feed_body = resp.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch feed {feed_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching feed {feed_url}: {e}")
        return []
    
    # Parse the feed
    parsed = feedparser.parse(feed_body)
    entries = getattr(parsed, 'entries', [])[:limit]
    
    results: List[Dict[str, Any]] = []
    
    for entry in entries:
        index_url = getattr(entry, 'link', None) or getattr(entry, 'id', None)
        if not index_url:
            continue
        
        # Extract filing acceptance date from RSS entry if available
        accepted_date = None
        
        # Try different date fields that feedparser might expose
        for date_field in ['updated', 'published', 'updated_parsed', 'published_parsed']:
            if hasattr(entry, date_field):
                date_val = getattr(entry, date_field)
                if date_val:
                    accepted_date = date_val
                    break
        
        # Normalize the date to ISO format if present
        if accepted_date:
            try:
                # If it's a time struct, convert it
                if hasattr(accepted_date, 'tm_year'):
                    dt = datetime(*accepted_date[:6])
                    accepted_date = dt.isoformat()
                # If it's already a string in ISO-like format, keep it
                elif isinstance(accepted_date, str):
                    # Try to parse and re-format to ensure consistency
                    for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S %Z']:
                        try:
                            dt = datetime.strptime(accepted_date, fmt)
                            accepted_date = dt.isoformat()
                            break
                        except (ValueError, TypeError):
                            continue
            except Exception as e:
                logger.debug(f"Date parsing failed: {e}, keeping original: {accepted_date}")
        
        try:
            # Fetch the index page
            index_resp = session.get(index_url, timeout=10, headers=headers)
            index_resp.raise_for_status()
            index_html = index_resp.text
            
            # Find the actual filing document
            doc_url = parser.find_filing_document_link(index_html, index_url)
            if not doc_url:
                logger.debug(f"Could not find filing document link in {index_url}")
                continue
            
            # Fetch the filing document
            filing_resp = session.get(doc_url, timeout=10, headers=headers)
            filing_resp.raise_for_status()
            filing_html = filing_resp.text
            
            # Parse the filing
            parsed_entry = parser.parse(filing_html, index_url, doc_url)
            
            # Add accepted_date if we found it (overwrite even if None was set)
            if accepted_date:
                parsed_entry['accepted_date'] = accepted_date
            
            # Only include entries with at least some data
            if parsed_entry and any(v is not None for v in parsed_entry.values()):
                results.append(parsed_entry)
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Network error processing entry {index_url}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to process entry {index_url}: {e}")
            continue
    
    # Deduplicate by document URL
    return _deduplicate_entries(results)


def _deduplicate_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate filings based on document URL."""
    seen_urls = set()
    deduped = []
    
    for entry in entries:
        doc_url = entry.get("document_url")
        if doc_url and doc_url not in seen_urls:
            seen_urls.add(doc_url)
            deduped.append(entry)
    
    return deduped
