"""Tests for output format functionality in main.py."""

import json
import types
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from main import scrape_news


@pytest.fixture
def app():
    """Create a Flask app context for tests."""
    app = Flask(__name__)
    return app


def test_json_format_default(app):
    """Test that JSON is the default format when no format parameter is provided."""
    with app.app_context():
        # Mock request with no args
        request = MagicMock()
        request.args = {}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {
                    "form_type": "144",
                    "transaction_type": "sell",
                    "shares": 1000,
                    "price": 50.0,
                    "reporting_owner": "John Doe",
                    "issuer_name": "Test Corp",
                    "ticker": "TEST",
                    "source": "sec_form_144"
                }
            ]
            
            response = scrape_news(request)
            
            # Check that response is JSON
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"
            assert data["count"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["ticker"] == "TEST"


def test_json_format_explicit(app):
    """Test explicit JSON format parameter."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'json'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {
                    "form_type": "144",
                    "ticker": "AAPL",
                    "source": "sec_form_144"
                }
            ]
            
            response = scrape_news(request)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"
            assert data["count"] == 1


def test_table_format(app):
    """Test table format output."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'table'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {
                    "form_type": "144",
                    "ticker": "AAPL",
                    "shares": 1000,
                    "price": 150.0,
                    "source": "sec_form_144"
                },
                {
                    "form_type": "144",
                    "ticker": "GOOGL",
                    "shares": 500,
                    "price": 2800.0,
                    "source": "sec_form_144"
                }
            ]
            
            response = scrape_news(request)
            
            # Check that response is plain text
            assert response.status_code == 200
            assert response.mimetype == 'text/plain'
            
            # Check that table contains expected data
            table_text = response.get_data(as_text=True)
            assert "form_type" in table_text
            assert "ticker" in table_text
            assert "AAPL" in table_text
            assert "GOOGL" in table_text
            assert "1000" in table_text
            assert "500" in table_text


def test_table_format_empty_results(app):
    """Test table format with no results."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'table'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = []
            
            response = scrape_news(request)
            
            assert response.status_code == 200
            assert response.mimetype == 'text/plain'
            table_text = response.get_data(as_text=True)
            assert "No results found" in table_text


def test_invalid_format_defaults_to_json(app):
    """Test that invalid format parameter defaults to JSON."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'xml'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {"ticker": "MSFT", "source": "sec_form_144"}
            ]
            
            response = scrape_news(request)
            
            # Should default to JSON
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"


def test_format_parameter_case_insensitive(app):
    """Test that format parameter is case-insensitive."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'TABLE'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {"ticker": "TSLA", "source": "sec_form_144"}
            ]
            
            response = scrape_news(request)
            
            # Should work with uppercase
            assert response.status_code == 200
            assert response.mimetype == 'text/plain'


def test_error_handling_json_format(app):
    """Test error handling in JSON format."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'json'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.side_effect = Exception("Test error")
            
            response, status_code = scrape_news(request)
            
            assert status_code == 500
            data = response.get_json()
            assert data["status"] == "error"
            assert "Test error" in data["message"]


def test_error_handling_table_format(app):
    """Test error handling in table format."""
    with app.app_context():
        request = MagicMock()
        request.args = {'format': 'table'}
        
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.side_effect = Exception("Test error")
            
            response = scrape_news(request)
            
            assert response.status_code == 500
            assert response.mimetype == 'text/plain'
            error_text = response.get_data(as_text=True)
            assert "Error: Test error" in error_text


def test_none_request_defaults_to_json(app):
    """Test that None request defaults to JSON format."""
    with app.app_context():
        with patch('main.get_latest_news') as mock_get_news:
            mock_get_news.return_value = [
                {"ticker": "NVDA", "source": "sec_form_144"}
            ]
            
            response = scrape_news(None)
            
            # Should default to JSON
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"
