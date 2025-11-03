import glob
import os

from src.news_scraper.parsers.form144 import Form144Parser


def test_form144_fixtures_extraction():
    """Run the Form 144 extractor on saved fixture HTML files and ensure we extract something useful.

    This is intentionally permissive: we assert that at least one of the key fields
    (shares, value, price or approximate_date_of_sale) is present for each fixture.
    """
    base = os.path.join(os.path.dirname(__file__), "fixtures", "form144")
    files = sorted(glob.glob(os.path.join(base, "entry_*.html")))
    assert files, f"No fixtures found in {base}"

    parser = Form144Parser()
    failures = []
    for fp in files:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        out = parser.parse(txt, "http://example.com/index", "http://example.com/doc")
        # consider extraction successful if any of these fields is present
        if not any(out.get(k) for k in ("shares", "value", "price", "approximate_date_of_sale")):
            failures.append((os.path.basename(fp), out))

    assert not failures, f"Extraction failed for fixtures: {failures}"
