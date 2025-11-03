"""Helper to fetch and cache SEC company tickers mapping."""
import requests
import json
import os
from datetime import datetime, timedelta
import time
from typing import Dict, Optional

# Cache company tickers for 24 hours
CACHE_TTL = timedelta(hours=24)
_company_tickers: Dict = {}
_last_fetch: Optional[datetime] = None

def get_company_tickers() -> Dict:
    """Fetch company tickers from SEC or return cached version if fresh.
    
    Returns a dict mapping CIK -> {cik_str, ticker, title} from SEC's JSON endpoint.
    Caches results for 24 hours to avoid hitting the endpoint too often.
    """
    global _company_tickers, _last_fetch
    
    now = datetime.now()
    if _last_fetch and _company_tickers and (now - _last_fetch) < CACHE_TTL:
        return _company_tickers

    # First try to read from file cache
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    cache_file = os.path.join(cache_dir, "company_tickers.json")
    
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                _company_tickers = json.load(f)
                _last_fetch = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if (now - _last_fetch) < CACHE_TTL:
                    return _company_tickers
    except Exception:
        pass
    
    try:
        # Use required SEC headers
        headers = {
            "User-Agent": "insta-finance-news/0.1 (+max.schoenenberger@gmx.de)",
            "Accept": "application/json",
            "From": "max.schoenenberger@gmx.de"
        }
        
        # Fetch with retries and backoff
        for attempt in range(3):
            try:
                resp = requests.get("https://www.sec.gov/files/company_tickers.json", 
                                headers=headers, timeout=10)
                resp.raise_for_status()
                _company_tickers = resp.json()
                _last_fetch = now
                
                # Save to cache file
                try:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(cache_file, "w") as f:
                        json.dump(_company_tickers, f)
                except Exception:
                    pass  # Ignore cache write failures
                    
                return _company_tickers
            except requests.exceptions.RequestException:
                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
            
    except Exception as e:
        # On error, return cached version from memory or file
        if _company_tickers:
            return _company_tickers
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
    return {}

def normalize_company_name(name: str) -> str:
    """Normalize a company name for comparison by removing common suffixes and whitespace."""
    if not name:
        return ""
    
    # Convert to lowercase and strip whitespace
    name = name.lower().strip()
    
    # Remove common suffixes and state designations
    suffixes = [
        " inc", " inc.", " incorporated",
        " corp", " corp.", " corporation",
        " co", " co.", " company",
        " ltd", " ltd.", " limited",
        " plc", " l.p.", " lp", " llc",
        " /de/", " (de)", " delaware",
        " /fl/", " (fl)", " florida",
        " /ny/", " (ny)", " new york",
        " /ca/", " (ca)", " california",
        " holdings", " holding",
        " international", " intl",
        " group", " technologies",
        " tech", " financial"
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            
    # Also remove state codes in middle of name
    state_codes = ["/de/", "/ny/", "/ca/", "/fl/", "(de)", "(ny)", "(ca)", "(fl)"]
    for code in state_codes:
        name = name.replace(code, " ")
            
    return name.strip()

def find_ticker_by_name(company_name: str) -> Optional[str]:
    """Find a ticker symbol by matching company name against SEC's tickers.json.
    
    Args:
        company_name: Company name to search for (e.g. from Form 144 filing)
        
    Returns:
        Ticker symbol if found, None otherwise
    """
    if not company_name:
        return None
        
    # Normalize search name
    search = normalize_company_name(company_name)
        
    # Get fresh mapping
    tickers = get_company_tickers()
    
    # Try exact match first (normalized)
    for entry in tickers.values():
        if normalize_company_name(entry["title"]) == search:
            return entry["ticker"]
    
    # Try component match - all words in search appear in title or vice versa
    search_words = set(search.split())
    if len(search_words) > 1:  # Only try component match if we have multiple words
        for entry in tickers.values():
            title_words = set(normalize_company_name(entry["title"]).split())
            if search_words.issubset(title_words) or title_words.issubset(search_words):
                return entry["ticker"]
    
    return None