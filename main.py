from flask import jsonify, Request
from src.news_scraper.scraper import get_latest_news


def scrape_news(request: Request):
    """Google Cloud Function entry point.

    Returns a JSON list of scraped items.
    """
    try:
        results = get_latest_news()
        return jsonify({"status": "ok", "count": len(results), "items": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Local runner via Functions Framework: `functions-framework --target=scrape_news`
    from flask import Flask

    app = Flask(__name__)

    @app.route("/")
    def _():
        return scrape_news(None)

    app.run(debug=True, port=8080)
