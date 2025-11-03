from src.news_scraper.scraper import _extract_from_filing_text


def test_price_computed_from_value_and_shares():
    html = '''
    <html><body>
    <table>
      <tr><th>Title of the Class of Securities To Be Sold</th><th>Number of Shares or Other Units To Be Sold</th><th>Aggregate Market Value</th></tr>
      <tr><td>Common</td><td>1000</td><td>50000.00</td></tr>
    </table>
    </body></html>
    '''
    out = _extract_from_filing_text(html)
    # shares and value should be parsed
    assert out.get('shares') == 1000
    assert out.get('value') == 50000.0
    # price should be computed as value / shares
    assert out.get('price') == 50.0
    # ensure no stray 'total_value' key
    assert 'total_value' not in out


def test_price_computed_when_value_present_but_price_missing_and_shares_nonzero():
    # Another variant: HTML table with the data
    html = '''
    <html><body>
    <table>
      <tr><th>Title of the Class of Securities To Be Sold</th><th>Number of Shares or Other Units To Be Sold</th><th>Aggregate Market Value</th></tr>
      <tr><td>Common</td><td>2500</td><td>$125000.00</td></tr>
    </table>
    </body></html>
    '''
    out = _extract_from_filing_text(html)
    assert out.get('shares') == 2500
    assert out.get('value') == 125000.0
    assert out.get('price') == 50.0
    assert 'total_value' not in out
