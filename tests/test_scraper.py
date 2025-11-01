import types

import pytest

from src.news_scraper import scraper


class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")


def test_extract_from_html_simple(monkeypatch):
    html = """
    <html>
      <head><meta name="description" content="Market summary"></head>
      <body>
        <h1>Major stock indexes end higher after rally</h1>
        <p>Short summary here.</p>
      </body>
    </html>
    """

    def fake_get(url, timeout=10):
        return DummyResponse(html)

    session = types.SimpleNamespace()
    session.get = fake_get

    items = scraper._extract_from_html(html, "https://example.com")
    assert items
    assert any("Major stock indexes" in it["title"] for it in items)


def test_fetch_site_network_error(monkeypatch):
    def fake_get(url, timeout=10):
        raise Exception("Network down")

    class S:
        get = staticmethod(fake_get)

    with pytest.raises(Exception):
        scraper._request_with_retries("https://nope.example", session=S())
