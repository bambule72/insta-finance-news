"""Type definitions for the scraper module."""

from typing import TypedDict, Optional, Union


class BaseFormEntry(TypedDict, total=False):
    """Base fields common to all SEC form entries."""
    issuer_name: Optional[str]
    ticker: Optional[str]
    index_url: Optional[str]
    document_url: Optional[str]
    source: Optional[str]
    filing_date: Optional[str]
    accepted_date: Optional[str]  # SEC acceptance timestamp
    form_type: Optional[str]


class Form144Entry(BaseFormEntry, total=False):
    """Form 144 specific fields (insider sales)."""
    transaction_type: Optional[str]
    shares: Optional[int]
    price: Optional[float]
    value: Optional[float]
    reporting_owner: Optional[str]
    approximate_date_of_sale: Optional[str]
    securities_exchange: Optional[str]
    shares_outstanding: Optional[int]


class Form8KEntry(BaseFormEntry, total=False):
    """Form 8-K specific fields (material events)."""
    event_type: Optional[str]
    event_description: Optional[str]
    items: Optional[list[str]]


class Form4Entry(BaseFormEntry, total=False):
    """Form 4 specific fields (insider transactions)."""
    reporting_owner: Optional[str]
    transaction_type: Optional[str]
    transaction_date: Optional[str]
    shares: Optional[int]
    price: Optional[float]
    value: Optional[float]
    ownership_type: Optional[str]


# Union type for all supported forms
FormEntry = Union[Form144Entry, Form8KEntry, Form4Entry]

# Legacy alias for backward compatibility
# Keep this to avoid breaking existing code
LegacyFormEntry = Form144Entry