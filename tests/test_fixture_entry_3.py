from pathlib import Path
from src.news_scraper.scraper import _extract_from_filing_text


def test_entry_3_fixture_parsing():
    fp = Path(__file__).parent / "fixtures" / "form144" / "entry_3.html"
    txt = fp.read_text(encoding='utf-8', errors='ignore')
    out = _extract_from_filing_text(txt)

    # These values should be present in the fixture (see file)
    assert out.get('shares') == 600000
    assert out.get('value') == 128406000.0
    assert out.get('shares_outstanding') == 706349563
    assert out.get('approximate_date_of_sale') == '10/31/2025'
    # securities_exchange in the fixture is 'NYSE'
    assert out.get('securities_exchange') == 'NYSE'
