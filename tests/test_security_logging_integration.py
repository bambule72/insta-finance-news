"""Integration test demonstrating security logging in real scraper scenarios."""

import json
import logging
from unittest.mock import Mock, patch

import pytest

from src.news_scraper.scraper import _request_with_retries
from src.news_scraper.form_fetcher import fetch_sec_form


class TestSecurityLoggingIntegration:
    """Integration tests for security logging across modules."""
    
    def test_request_with_retries_logs_access_and_success(self, caplog):
        """Test that successful requests log access events."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test content</html>"
        mock_session.get.return_value = mock_response
        
        headers = {"User-Agent": "test-bot", "From": "test@example.com"}
        
        with caplog.at_level(logging.INFO, logger="security_events"):
            result = _request_with_retries(
                "https://example.com/test",
                session=mock_session,
                headers=headers
            )
        
        assert result == "<html>Test content</html>"
        
        # Should have 2 security log entries: initiation and success
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        assert len(security_logs) == 2
        
        # Check initiation log
        init_event = json.loads(security_logs[0].message)
        assert init_event["event_type"] == "ACCESS"
        assert init_event["action"] == "api_request"
        assert init_event["details"]["url"] == "https://example.com/test"
        assert init_event["details"]["status"] == "initiated"
        assert "User-Agent" in init_event["details"]["headers"]
        
        # Check success log
        success_event = json.loads(security_logs[1].message)
        assert success_event["event_type"] == "ACCESS"
        assert success_event["details"]["status"] == "success_status_200"
    
    def test_request_with_retries_logs_failures(self, caplog):
        """Test that failed requests log security errors."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Connection timeout")
        
        with caplog.at_level(logging.INFO, logger="security_events"):
            with pytest.raises(Exception, match="Connection timeout"):
                _request_with_retries(
                    "https://example.com/fail",
                    session=mock_session,
                    retries=2,
                    backoff=0.01  # Fast for testing
                )
        
        # Should have initial access log + final error log
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        assert len(security_logs) >= 2
        
        # Check error log
        error_logs = [r for r in security_logs if r.levelno == logging.WARNING]
        assert len(error_logs) == 1
        
        error_event = json.loads(error_logs[0].message)
        assert error_event["event_type"] == "ERROR"
        assert error_event["action"] == "security_error"
        assert error_event["details"]["error_type"] == "request_failed"
        assert "Failed after 2 attempts" in error_event["details"]["message"]
        assert "Connection timeout" in error_event["details"]["error"]
    
    def test_fetch_sec_form_logs_parser_errors(self, caplog):
        """Test that parser errors are logged as security events."""
        # Test with invalid form type (no parser available)
        with caplog.at_level(logging.INFO, logger="security_events"):
            result = fetch_sec_form(
                form_type="INVALID",
                feed_url="https://www.sec.gov/feed",
                limit=5
            )
        
        assert result == []
        
        # Should log parser not found error
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        error_logs = [json.loads(r.message) for r in security_logs 
                     if r.levelno == logging.WARNING]
        
        assert len(error_logs) >= 1
        parser_errors = [e for e in error_logs 
                        if e["details"].get("error_type") == "parser_not_found"]
        assert len(parser_errors) == 1
        assert parser_errors[0]["details"]["form_type"] == "INVALID"
    
    def test_fetch_sec_form_logs_network_errors(self, caplog):
        """Test that network errors in form fetching are logged."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Network error")
        
        with caplog.at_level(logging.INFO, logger="security_events"):
            result = fetch_sec_form(
                form_type="144",
                feed_url="https://www.sec.gov/feed",
                session=mock_session,
                limit=5
            )
        
        assert result == []
        
        # Should log initial access and then error
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        assert len(security_logs) >= 2
        
        # Check that we logged the access
        access_logs = [json.loads(r.message) for r in security_logs 
                      if "ACCESS" in json.loads(r.message)["event_type"]]
        assert len(access_logs) >= 1
        assert "fetching_sec_form_144" in access_logs[0]["details"]["status"]
        
        # Check that we logged the error
        error_logs = [json.loads(r.message) for r in security_logs 
                     if r.levelno == logging.WARNING]
        assert len(error_logs) >= 1
        
        # Find the unexpected_error event
        unexpected_errors = [e for e in error_logs 
                           if e["details"].get("error_type") == "unexpected_error"]
        assert len(unexpected_errors) == 1
        assert "Network error" in unexpected_errors[0]["details"]["error"]
        assert unexpected_errors[0]["details"]["form_type"] == "144"
    
    def test_security_logs_are_json_parseable(self, caplog):
        """Test that all security logs produce valid JSON."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "test"
        mock_session.get.return_value = mock_response
        
        with caplog.at_level(logging.INFO, logger="security_events"):
            _request_with_retries("https://test.com", session=mock_session)
        
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        
        # All security logs should be valid JSON
        for log_record in security_logs:
            try:
                event = json.loads(log_record.message)
                # All events should have these required fields
                assert "timestamp" in event
                assert "event_type" in event
                assert "action" in event
            except json.JSONDecodeError as e:
                pytest.fail(f"Security log is not valid JSON: {log_record.message}\nError: {e}")
    
    def test_security_logs_sanitize_sensitive_headers(self, caplog):
        """Test that security logs don't expose sensitive headers."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "test"
        mock_session.get.return_value = mock_response
        
        # Include both safe and sensitive headers
        headers = {
            "User-Agent": "safe-bot",
            "From": "safe@example.com",
            "Authorization": "Bearer secret123",
            "X-API-Key": "super-secret-key",
            "Cookie": "session=abc123"
        }
        
        with caplog.at_level(logging.INFO, logger="security_events"):
            _request_with_retries("https://test.com", session=mock_session, headers=headers)
        
        security_logs = [r for r in caplog.records if r.name == "security_events"]
        
        # Check all logged events
        for log_record in security_logs:
            event = json.loads(log_record.message)
            if "headers" in event.get("details", {}):
                logged_headers = event["details"]["headers"]
                
                # Safe headers should be present
                assert "User-Agent" in logged_headers
                assert "From" in logged_headers
                
                # Sensitive headers should NOT be present
                assert "Authorization" not in logged_headers
                assert "X-API-Key" not in logged_headers
                assert "Cookie" not in logged_headers
