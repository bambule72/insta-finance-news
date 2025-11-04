"""Form 144 parser - Insider intent to sell restricted/control securities."""

from __future__ import annotations
from typing import Dict, Any, Optional, cast
import re
from lxml import etree, html
from bs4 import BeautifulSoup

from .base import BaseFormParser
from ..scraper_types import Form144Entry
from ..logger import setup_logger

logger = setup_logger(__name__)


class Form144Parser(BaseFormParser):
    """Parser for SEC Form 144 filings.
    
    Extracts transaction details including:
    - Reporting owner (insider)
    - Shares to be sold
    - Aggregate value
    - Price per share (computed if not present)
    - Approximate date of sale
    - Securities exchange
    - Shares outstanding
    """
    
    @property
    def form_type(self) -> str:
        return "144"
    
    def parse(self, filing_html: str, index_url: str, document_url: str) -> Dict[str, Any]:
        """Parse Form 144 filing and extract transaction details.
        
        Args:
            filing_html: The HTML/XML content of the filing
            index_url: The EDGAR index page URL
            document_url: The actual filing document URL
            
        Returns:
            Form144Entry with extracted data
        """
        # Initialize output with all possible keys
        out: Form144Entry = {
            "form_type": "144",
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
            "accepted_date": None,
            "index_url": index_url,
            "document_url": document_url,
            "source": "sec_form_144",
        }
        
        # Try structured parsing with lxml
        try:
            head_text = filing_html[:200].lower()
            if filing_html.strip().startswith("<?xml") or "<xml" in head_text:
                root = etree.fromstring(filing_html.encode("utf-8"))
            else:
                root = html.fromstring(filing_html)
            
            # Extract issuer name
            self._extract_issuer_name(root, out)
            
            # Extract table data (shares, price, value, etc.)
            self._extract_table_data(root, out)
            
            # Extract reporting owner
            self._extract_reporting_owner(root, out)
            
        except Exception as e:
            logger.debug(f"Structured parsing failed: {e}")
        
        # Fallback text-based extraction
        self._extract_from_text(filing_html, out)
        
        # Post-processing
        self._compute_missing_values(out)
        self._normalize_fields(out)
        self._lookup_ticker_if_needed(out)
        
        return cast(Dict[str, Any], out)
    
    def _extract_issuer_name(self, root, out: Form144Entry) -> None:
        """Extract issuer name from the document."""
        issuer_cells = root.xpath(".//td[contains(., 'Name of Issuer') or contains(., 'Name of Issuer:')]")
        if not issuer_cells:
            return
        
        for cell in issuer_cells:
            parent = cell.getparent()
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
                        return
            
            # Fallback: remove label from cell's own text
            text_all = ''.join(cell.itertext()).strip()
            text_all = re.sub(r'(?i)name of issuer[:\s]*', '', text_all).strip()
            if text_all:
                out['issuer_name'] = text_all
                return
    
    def _extract_table_data(self, root, out: Form144Entry) -> None:
        """Extract shares, price, value from tables."""
        tables = root.xpath('.//table')
        
        for tbl in tables:
            txt = ' '.join(tbl.xpath('.//text()'))
            if not re.search(r'number of shares|aggregate market value|price per share|title of the class|title of the security', txt, re.IGNORECASE):
                continue
            
            rows = tbl.xpath('.//tr')
            header_cells = None
            header_index = None
            
            # Find header row
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
                # Map data rows using header positions
                for r in rows[header_index + 1:]:
                    cells = [c.text_content().strip() for c in r.xpath('.//td')]
                    if not cells:
                        continue
                    
                    for idx, h in enumerate(header_cells):
                        val = cells[idx].strip() if idx < len(cells) else ''
                        if not val:
                            continue
                        
                        lh = h.lower()
                        
                        # Match headers to fields (ordered to prevent interference)
                        if re.search(r'number of shares or other units outstanding|shares outstanding|\boutstanding\b', lh):
                            if out.get('shares_outstanding') is None:
                                out['shares_outstanding'] = self.safe_int(val)
                        elif re.search(r'number of shares or other units to be sold|to be sold|number of shares to be sold', lh):
                            if out.get('shares') is None:
                                out['shares'] = self.safe_int(val)
                        elif re.search(r'number of shares|^shares$|\bshares\b', lh):
                            if out.get('shares') is None:
                                out['shares'] = self.safe_int(val)
                        elif re.search(r'price per share|price\b|per share', lh):
                            if out.get('price') is None:
                                out['price'] = self.normalize_number(val)
                        elif re.search(r'aggregate market value|aggregate market|market value|value', lh):
                            if out.get('value') is None:
                                out['value'] = self.normalize_number(val)
                        elif re.search(r'approximate date of sale|date of sale|approximate date', lh):
                            if out.get('approximate_date_of_sale') is None:
                                out['approximate_date_of_sale'] = val
                        elif re.search(r'name the securities exchange|securities exchange|exchange', lh):
                            if out.get('securities_exchange') is None:
                                out['securities_exchange'] = val
                    
                    # Stop if we found numeric data
                    if any(out.get(k) for k in ('shares', 'price', 'value')):
                        return
    
    def _extract_reporting_owner(self, root, out: Form144Entry) -> None:
        """Extract reporting owner name."""
        owner_cells = root.xpath(".//td[contains(., 'Name of Reporting') or contains(., 'Name of Person') or contains(., 'Name of Person for Whose Account')]")
        if not owner_cells:
            return
        
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
                        return
            
            # Fallback: remove label from own text
            text_all = ''.join(cell.itertext()).strip()
            text_all = re.sub(r'(?i)name of person for whose account the securities are to be sold[:\s]*', '', text_all).strip()
            if text_all and text_all.lower() not in ('name of person for whose account the securities are to be sold', 'name of reporting'):
                out['reporting_owner'] = text_all
                return
    
    def _extract_from_text(self, text: str, out: Form144Entry) -> None:
        """Fallback text-based extraction using regex."""
        lowered = text.lower()
        
        # Transaction type
        if out.get("transaction_type") is None:
            if "disposition" in lowered or "sold" in lowered or "sale" in lowered or "disposed" in lowered:
                out["transaction_type"] = "sell"
            elif "acquisition" in lowered or "purchase" in lowered or "bought" in lowered or "acquired" in lowered:
                out["transaction_type"] = "buy"
        
        # Reporting owner
        if out.get("reporting_owner") is None:
            m = re.search(r"reporting owner[:\s]{1,20}([A-Za-z0-9 \.,&()\-]{2,200})", text, re.IGNORECASE)
            if m:
                out["reporting_owner"] = m.group(1).strip()
        
        # Shares
        if out.get('shares') is None:
            m = re.search(r"number of shares[:\s]*([0-9,]+)", text, re.IGNORECASE)
            if not m:
                m = re.search(r"([0-9,]+)\s+shares", text, re.IGNORECASE)
            if m:
                out["shares"] = self.safe_int(m.group(1))
        
        # Price
        if out.get('price') is None:
            m = re.search(r"price\s*(?:per share)?[:\s]*\$?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
            if m:
                out["price"] = self.normalize_number(m.group(1))
        
        # Value
        if out.get('value') is None:
            m = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:total|value|amount)?", text)
            if m:
                out["value"] = self.normalize_number(m.group(1))
        
        # Shares outstanding
        if out.get('shares_outstanding') is None:
            m = re.search(r"(?:number of shares|shares) outstanding[:\s]*([0-9,]+)", text, re.IGNORECASE)
            if m:
                out["shares_outstanding"] = self.safe_int(m.group(1))
    
    def _compute_missing_values(self, out: Form144Entry) -> None:
        """Compute price or value if one is missing."""
        try:
            shares = out.get("shares")
            price = out.get("price")
            value = out.get("value")
            
            # Compute value if missing
            if value is None and shares is not None and price is not None:
                out["value"] = float(shares) * float(price)
            
            # Compute price if missing
            if price is None and shares is not None and value is not None:
                if float(shares) != 0:
                    out["price"] = float(value) / float(shares)
        except Exception:
            pass
    
    def _normalize_fields(self, out: Form144Entry) -> None:
        """Normalize date and exchange fields."""
        # Normalize date
        date_val = out.get("approximate_date_of_sale")
        if date_val:
            out["approximate_date_of_sale"] = self.normalize_date(date_val)
        
        # Round price to 2 decimals
        price_val = out.get("price")
        if price_val is not None:
            try:
                out["price"] = round(float(price_val), 2)
            except Exception:
                pass
        
        # Normalize exchange
        exchange_val = out.get("securities_exchange")
        if exchange_val:
            out["securities_exchange"] = self.normalize_exchange(exchange_val)
    
    def _lookup_ticker_if_needed(self, out: Form144Entry) -> None:
        """Lookup ticker if we have issuer name but no ticker."""
        issuer = out.get("issuer_name")
        if issuer and not out.get("ticker"):
            ticker = self.lookup_ticker(issuer)
            if ticker:
                out["ticker"] = ticker


# Register this parser
from . import register_parser
register_parser("144", Form144Parser)
