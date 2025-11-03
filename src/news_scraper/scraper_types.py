"""Type definitions for the scraper module."""

from typing import TypedDict, Optional

class FormEntry(TypedDict, total=False):
    """Form 144 entry type definition."""
    transaction_type: Optional[str]
    shares: Optional[int]
    price: Optional[float]
    value: Optional[float]
    reporting_owner: Optional[str]
    approximate_date_of_sale: Optional[str]
    securities_exchange: Optional[str]
    shares_outstanding: Optional[int]
    issuer_name: Optional[str]
    ticker: Optional[str]
    index_url: Optional[str]
    document_url: Optional[str]
    source: Optional[str]