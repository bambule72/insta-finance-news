# Parser Architecture Documentation

## Overview

The scraper has been refactored into a modular parser architecture that makes it easy to add support for new SEC form types. This document describes the architecture and how to extend it.

## Architecture Components

### 1. Generic Form Fetcher (`src/news_scraper/form_fetcher.py`)

The generic form fetcher handles fetching and parsing ANY SEC form type:

**Key Function:**

- `fetch_sec_form(form_type, limit)` - Fetches RSS feed, parses entries using appropriate parser
- `_deduplicate_entries(entries)` - Removes duplicate filings based on `document_url`

**Features:**

- Works with any registered form type (144, 8-K, 4, etc.)
- Captures `accepted_date` from RSS feed metadata
- Automatic deduplication
- Proper error handling with `RequestException`
- Session management for HTTP requests

### 2. Base Parser (`src/news_scraper/parsers/base.py`)

The `BaseFormParser` abstract base class provides:

**Required Methods:**

- `form_type` property - Returns the SEC form type (e.g., "144", "8-K")
- `parse()` method - Parses filing HTML and returns structured data

**Shared Utilities:**

- `normalize_number()` - Convert string to float
- `safe_int()` - Convert string to int safely
- `normalize_date()` - Convert dates to ISO format (YYYY-MM-DD)
- `normalize_exchange()` - Standardize exchange names
- `find_filing_document_link()` - Extract filing URL from index page
- `lookup_ticker()` - Lookup ticker symbol by company name

### 3. Form-Specific Parsers

Each SEC form type has its own parser class:

**Form 144 Parser** (`src/news_scraper/parsers/form144.py`)

- Handles insider intent to sell filings
- Extracts: shares, price, value, reporting owner, dates, exchange
- **Normalizes dates to ISO 8601 format** (YYYY-MM-DD)
- **Rounds prices to 2 decimal places**
- Auto-registers with the parser registry

**Future Parsers:**

- Form 8-K - Material events (to be implemented)
- Form 4 - Insider transactions (to be implemented)
- Form 13D - Activist ownership (to be implemented)

### 4. Parser Registry (`src/news_scraper/parsers/__init__.py`)

The registry manages form-specific parsers:

```python
from src.news_scraper.parsers import get_parser
from src.news_scraper.form_fetcher import fetch_sec_form

# Fetch Form 144 filings (uses registered Form144Parser automatically)
filings = fetch_sec_form("144", limit=10)

# Or use parser directly
parser = get_parser("144")
result = parser.parse(html, index_url, doc_url)
```

**Key Functions:**

- `register_parser(form_type, parser_class)` - Register a new parser
- `get_parser(form_type)` - Get parser instance for a form type
- `get_supported_forms()` - List all supported form types

### 5. Type System (`src/news_scraper/scraper_types.py`)

Structured type definitions using TypedDict:

**Base Types:**

- `BaseFormEntry` - Common fields (issuer, ticker, URLs, accepted_date)

**Form-Specific Types:**

- `Form144Entry` - Extends base with shares, price, value, owner, transaction dates
- `Form8KEntry` - Extends base with event type, description (future)
- `Form4Entry` - Extends base with transaction details (future)

**Union Type:**

- `FormEntry` - Union of all form types for flexibility

**Key Fields:**

- `accepted_date` - ISO 8601 timestamp from SEC RSS feed (e.g., "2025-01-15T14:30:00-05:00")
- `date_of_transaction` - Normalized to ISO 8601 date format (e.g., "2025-01-15")
- `price` - Rounded to 2 decimal places
- `document_url` - Used for deduplication

## How to Add a New Form Parser

### Step 1: Create the Parser Class

Create a new file `src/news_scraper/parsers/form<TYPE>.py`:

```python
from .base import BaseFormParser
from ..scraper_types import Form8KEntry

class Form8KParser(BaseFormParser):
    @property
    def form_type(self) -> str:
        return "8-K"

    def parse(self, filing_html: str, index_url: str, document_url: str) -> Form8KEntry:
        out: Form8KEntry = {
            "form_type": "8-K",
            "issuer_name": None,
            "ticker": None,
            "event_type": None,
            "event_description": None,
            "items": None,
            "index_url": index_url,
            "document_url": document_url,
            "source": "sec_form_8k",
        }

        # Your parsing logic here
        # Use self.normalize_date(), self.normalize_number(), etc.

        return out

# Register the parser
from . import register_parser
register_parser("8-K", Form8KParser)
```

### Step 2: Define the Type

Add to `src/news_scraper/scraper_types.py`:

```python
class Form8KEntry(BaseFormEntry, total=False):
    """Form 8-K specific fields (material events)."""
    event_type: Optional[str]
    event_description: Optional[str]
    items: Optional[list[str]]
```

Update the FormEntry union:

```python
FormEntry = Union[Form144Entry, Form8KEntry, Form4Entry]
```

### Step 3: Use Generic Form Fetcher

The generic fetcher automatically handles RSS parsing and deduplication:

```python
from src.news_scraper.form_fetcher import fetch_sec_form

# That's it! The fetcher will:
# - Look up your registered parser
# - Fetch the RSS feed for Form 8-K
# - Parse each entry using Form8KParser
# - Deduplicate by document_url
# - Populate accepted_date from RSS metadata
filings = fetch_sec_form("8-K", limit=10)
```

Or add a convenience function in `scraper.py`:

```python
def get_latest_sec_form_8k(limit: int = 10) -> List[Form8KEntry]:
    """Fetch the latest SEC Form 8-K filings."""
    return fetch_sec_form("8-K", limit)
```

### Step 4: Add Tests

Create `tests/test_form8k.py`:

```python
from src.news_scraper.parsers.form8k import Form8KParser

def test_form8k_parsing():
    html = '''<html>...</html>'''
    parser = Form8KParser()
    out = parser.parse(html, "http://example.com/index", "http://example.com/doc")
    assert out.get('event_type') is not None
```

## Benefits of This Architecture

1. **Modularity**: Each form type has isolated parsing logic
2. **Reusability**: Shared utilities in the base class
3. **Testability**: Easy to unit test individual parsers
4. **Extensibility**: Add new forms without modifying existing code
5. **Type Safety**: Strong typing with TypedDict for each form
6. **Maintainability**: Clear separation of concerns
7. **DRY Principle**: Generic form fetcher eliminates code duplication
8. **Automatic Features**: New parsers automatically get deduplication, RSS parsing, and accepted_date population

## Current Status

✅ **Implemented:**

- Generic form fetcher (`form_fetcher.py`)
- Base parser infrastructure with shared utilities
- Form 144 parser with date normalization and price rounding
- Parser registry with auto-registration
- Type system with BaseFormEntry and Form144Entry
- Automatic deduplication by document_url
- accepted_date field from RSS feed metadata
- All tests passing (9/9)

🔜 **Next Steps:**

- Implement Form 8-K parser (highest market impact)
- Implement Form 4 parser (insider trading)
- Implement Form 13D parser (activist ownership)
- Add form-specific test fixtures for new parsers

## References

- [SEC Forms Overview](sec-forms-overview.md) - Market impact ranking
- [Generic Form Fetcher](../src/news_scraper/form_fetcher.py) - Handles any SEC form type
- [Base Parser](../src/news_scraper/parsers/base.py) - Shared utilities
- [Form 144 Parser](../src/news_scraper/parsers/form144.py) - Example implementation
- [Parser Registry](../src/news_scraper/parsers/__init__.py) - Parser registration and lookup
