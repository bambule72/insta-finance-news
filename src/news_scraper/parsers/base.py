"""Base parser class for SEC form parsers."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import re
import datetime
import urllib.parse
from bs4 import BeautifulSoup

from ..logger import setup_logger

logger = setup_logger(__name__)


class BaseFormParser(ABC):
    """Abstract base class for SEC form parsers.
    
    Each form-specific parser should inherit from this class and implement
    the parse() method for extracting structured data from that form type.
    """
    
    @property
    @abstractmethod
    def form_type(self) -> str:
        """Return the SEC form type this parser handles (e.g., '144', '8-K')."""
        pass
    
    @abstractmethod
    def parse(self, filing_html: str, index_url: str, document_url: str) -> Dict[str, Any]:
        """Parse filing HTML and extract structured data.
        
        Args:
            filing_html: The HTML/XML content of the filing document
            index_url: The EDGAR index page URL
            document_url: The actual filing document URL
            
        Returns:
            Dictionary containing extracted form data (specific type depends on form)
        """
        pass
    
    # Shared utility methods
    
    @staticmethod
    def normalize_number(s: str) -> Optional[float]:
        """Normalize a number string to float."""
        if not s:
            return None
        s = s.replace(",", "").replace("$", "").strip()
        try:
            return float(s)
        except Exception:
            # Try to strip non-numeric
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
            if m:
                return float(m.group(1))
        return None
    
    @staticmethod
    def safe_int(s: str) -> Optional[int]:
        """Convert string to int safely."""
        v = BaseFormParser.normalize_number(s)
        return int(v) if v is not None else None
    
    @staticmethod
    def normalize_date(date_str: str) -> str:
        """Normalize date strings to ISO format (YYYY-MM-DD).
        
        Supports common formats: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD
        Returns original string if parsing fails.
        """
        if not date_str:
            return date_str
            
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                dt = datetime.datetime.strptime(date_str.strip(), fmt)
                return dt.date().isoformat()
            except Exception:
                continue
        return date_str.strip()
    
    @staticmethod
    def find_filing_document_link(index_html: str, index_url: str) -> Optional[str]:
        """Find the actual filing document link from an EDGAR index page.
        
        Args:
            index_html: HTML content of the EDGAR index page
            index_url: URL of the index page (for resolving relative links)
            
        Returns:
            Absolute URL to the filing document, or None if not found
        """
        soup = BeautifulSoup(index_html, "lxml")
        
        # Skip index pages themselves
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith("-index.htm"):
                continue
            
            low = href.lower()
            text = a.get_text(" ", strip=True).lower()
            
            # Prefer XML links with form indicators
            if ".xml" in low and ("144" in low or "form" in low or "8-k" in low):
                return urllib.parse.urljoin("https://www.sec.gov", href)
            
            # Look for form-specific patterns in href or link text
            if any(pattern in low or pattern in text for pattern in ["144", "form 144", "form144", "form-144", "8-k", "form 8-k"]):
                return urllib.parse.urljoin("https://www.sec.gov", href)
        
        # Fallback: first .xml then .htm/.txt
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith("-index.htm"):
                continue
            if ".xml" in href:
                return urllib.parse.urljoin("https://www.sec.gov", href)
            if ".htm" in href or ".txt" in href:
                return urllib.parse.urljoin("https://www.sec.gov", href)
        
        return None
    
    @staticmethod
    def normalize_exchange(exchange: str) -> str:
        """Normalize exchange names to standard abbreviations."""
        if not exchange:
            return exchange
            
        exchange = exchange.strip().upper()
        exchange_map = {
            'NASDAQ GLOBAL MARKET': 'NASDAQ',
            'NASDAQ GLOBAL SELECT MARKET': 'NASDAQ',
            'NASDAQ CAPITAL MARKET': 'NASDAQ',
            'NASDAQ STOCK MARKET': 'NASDAQ',
            'NYSE MKT': 'NYSE',
            'NEW YORK STOCK EXCHANGE': 'NYSE',
            'NYSE AMERICAN': 'NYSE',
        }
        return exchange_map.get(exchange, exchange)
    
    def lookup_ticker(self, issuer_name: str) -> Optional[str]:
        """Lookup ticker symbol for an issuer name.
        
        Args:
            issuer_name: Company name to lookup
            
        Returns:
            Ticker symbol if found, None otherwise
        """
        if not issuer_name:
            return None
            
        try:
            from .. import company_tickers
            return company_tickers.find_ticker_by_name(issuer_name)
        except Exception as e:
            logger.debug(f"Ticker lookup failed for {issuer_name}: {e}")
            return None
