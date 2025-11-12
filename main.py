from flask import jsonify, Request, Response
from tabulate import tabulate
from src.news_scraper.scraper import get_latest_news


def scrape_news(request: Request):
    """Google Cloud Function entry point.

    Accepts a 'format' query parameter:
    - 'json' (default): Returns data as JSON
    - 'table': Returns data as a human-readable ASCII table
    """
    try:
        results = get_latest_news()
        
        # Get format parameter, default to 'json'
        output_format = 'json'
        if request and hasattr(request, 'args'):
            output_format = request.args.get('format', 'json').lower()
        
        # Validate format parameter, default to 'json' if invalid
        if output_format not in ['json', 'table']:
            output_format = 'json'
        
        if output_format == 'table':
            # Convert results to table format
            if not results:
                table_output = "No results found."
            else:
                # Extract headers from the first item
                headers = list(results[0].keys())
                # Extract rows
                rows = [[item.get(key, '') for key in headers] for item in results]
                # Generate table
                table_output = tabulate(rows, headers=headers, tablefmt='plain')
            
            return Response(table_output, mimetype='text/plain')
        else:
            # Default JSON format
            return jsonify({"status": "ok", "count": len(results), "items": results})
    except Exception as e:
        # Return error in appropriate format
        output_format = 'json'
        if request and hasattr(request, 'args'):
            output_format = request.args.get('format', 'json').lower()
        
        if output_format == 'table':
            return Response(f"Error: {str(e)}", mimetype='text/plain', status=500)
        else:
            return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Local runner via Functions Framework: `functions-framework --target=scrape_news`
    from flask import Flask, request as flask_request

    app = Flask(__name__)

    @app.route("/")
    def _():
        return scrape_news(flask_request)

    app.run(debug=True, port=8080)
