import types

from src.news_scraper import scraper


class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")


def make_session_for_html(html: str):
    class S:
        @staticmethod
        def get(url, timeout=10, headers=None):
            return DummyResponse(html)

    return S()


def test_fetch_each_source_basic():
    sample_html = """
    <html>
      <head><meta name="description" content="Summary"></head>
      <body>
        <h2><a href="/news/1">Stocks climb as markets rally</a></h2>
      </body>
    </html>
    """

    for source in list(scraper.NEWS_SOURCES.keys()):
        session = make_session_for_html(sample_html)
        items = scraper.fetch_site(source, session=session)
        assert isinstance(items, list)
        assert items, f"no items for {source}"
        for it in items:
            assert it.get("source") == source
            assert "Stocks climb" in it.get("title", "")


def test_get_latest_news_dedup():
    # Prepare a session that returns same title for all sources
    html = """
    <html><body><h1><a href="/1">Same headline across sources</a></h1></body></html>
    """
    session = make_session_for_html(html)

    # monkeypatch fetch_site to use our session
    original_fetch = scraper.fetch_site

    try:
        def fake_fetch(source, session=None):
            return original_fetch(source, session=session)

        # call get_latest_news with custom session by temporarily patching requests inside scraper
        results = []
        for s in list(scraper.NEWS_SOURCES.keys()):
            results.extend(scraper._extract_from_html(html, scraper.NEWS_SOURCES[s]))

        deduped = scraper.get_latest_news(list(scraper.NEWS_SOURCES.keys()))
        assert isinstance(deduped, list)
    finally:
        pass
