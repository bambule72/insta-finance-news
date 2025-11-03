"""Test deduplication of SEC Form 144 filings based on document URL."""
from __future__ import annotations

import pytest
from src.news_scraper.form_fetcher import fetch_sec_form, _deduplicate_entries

# Sample filing items with duplicate document URLs
SAMPLE_FILINGS = [
    # Both point to same document for Dorman Products, Inc.
    {
        "transaction_type": "sell",
        "shares": 12493,
        "price": 135.37,
        "value": 1691200.1,
        "reporting_owner": "Hession David",
        "issuer_name": "Dorman Products, Inc.",
        "index_url": "https://www.sec.gov/Archives/edgar/data/1769146/000095013025000227/0000950130-25-000227-index.htm",
        "document_url": "https://www.sec.gov/Archives/edgar/data/868780/000095013025000227/xsl144X01/primary_doc.xml",
        "source": "sec_form_144"
    },
    {
        "transaction_type": "sell",
        "shares": 12493,
        "price": 135.37,
        "value": 1691200.1,
        "reporting_owner": "Hession David",
        "issuer_name": "Dorman Products, Inc.",
        "index_url": "https://www.sec.gov/Archives/edgar/data/868780/000095013025000227/0000950130-25-000227-index.htm", 
        "document_url": "https://www.sec.gov/Archives/edgar/data/868780/000095013025000227/xsl144X01/primary_doc.xml",
        "source": "sec_form_144"
    },
    # Different document URLs - should both be kept
    {
        "transaction_type": "sell",
        "shares": 100000,
        "price": 19.91,
        "value": 1991000.0,
        "reporting_owner": "Craig Hunsaker",
        "issuer_name": "Alphatec Holdings Inc",
        "index_url": "https://www.sec.gov/Archives/edgar/data/1509282/000150928225000006/0001509282-25-000006-index.htm",
        "document_url": "https://www.sec.gov/Archives/edgar/data/1350653/000150928225000006/xsl144X01/primary_doc.xml",
        "source": "sec_form_144"
    },
    {
        "transaction_type": "sell", 
        "shares": 120000,
        "price": 141.30,
        "value": 16956384.0,
        "reporting_owner": "MICHAEL IVAS",
        "issuer_name": "AMPHENOL CORPORATION",
        "index_url": "https://www.sec.gov/Archives/edgar/data/1648860/000195004725008339/0001950047-25-008339-index.htm",
        "document_url": "https://www.sec.gov/Archives/edgar/data/820313/000195004725008339/xsl144X01/primary_doc.xml",
        "source": "sec_form_144"
    }
]

def test_dedup_form144_entries():
    """Test that filings are deduped properly by document URL."""
    deduped = _deduplicate_entries(SAMPLE_FILINGS)

    # Should keep 3 unique entries (by document_url)
    assert len(deduped) == 3

    # Verify all document URLs are unique
    doc_urls = {e["document_url"] for e in deduped}
    assert len(doc_urls) == len(deduped)

    # First item in list should be kept when dupes exist
    dorman_items = [e for e in deduped if "Dorman Products" in e["issuer_name"]]
    assert len(dorman_items) == 1
    assert dorman_items[0]["index_url"].startswith("https://www.sec.gov/Archives/edgar/data/1769146/")

    # Items with unique document URLs are preserved
    assert any(e["issuer_name"] == "Alphatec Holdings Inc" for e in deduped)
    assert any(e["issuer_name"] == "AMPHENOL CORPORATION" for e in deduped)