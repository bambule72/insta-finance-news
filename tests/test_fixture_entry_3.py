from pathlib import Path
from src.news_scraper.parsers.form144 import Form144Parser


def test_entry_3_fixture_parsing():
    fp = Path(__file__).parent / "fixtures" / "form144" / "entry_3.html"
    txt = fp.read_text(encoding='utf-8', errors='ignore')
    parser = Form144Parser()
    out = parser.parse(txt, "http://example.com/index", "http://example.com/doc")

    # These values should be present in the fixture (see file)
    assert out.get('shares') == 600000
    assert out.get('value') == 128406000.0
    assert out.get('shares_outstanding') == 706349563
    assert out.get('approximate_date_of_sale') == '2025-10-31'  # Should be normalized to ISO format
    # securities_exchange in the fixture is 'NYSE'
    assert out.get('securities_exchange') == 'NYSE'
