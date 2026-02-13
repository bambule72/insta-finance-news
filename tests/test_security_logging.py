"""Tests for security event logging functionality."""

import json
import logging
from io import StringIO
from typing import Dict

import pytest

from src.news_scraper.logger import (
    SecurityEventLogger,
    get_security_logger,
    setup_logger,
)


class TestSecurityEventLogger:
    """Test the SecurityEventLogger class."""
    
    def test_logger_initialization(self):
        """Test that security logger initializes correctly."""
        logger = SecurityEventLogger(name="test_security")
        assert logger.logger.name == "test_security"
        assert len(logger.logger.handlers) == 1
        assert logger.logger.level == logging.INFO
    
    def test_event_types_defined(self):
        """Test that all event types are defined."""
        assert SecurityEventLogger.AUTH == "AUTH"
        assert SecurityEventLogger.ACCESS == "ACCESS"
        assert SecurityEventLogger.COMPLIANCE == "COMPLIANCE"
        assert SecurityEventLogger.ERROR == "ERROR"
    
    def test_log_event_structure(self, caplog):
        """Test that log_event creates properly structured JSON."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_event(
                SecurityEventLogger.ACCESS,
                "test_action",
                {"key": "value", "count": 42}
            )
        
        # Get the log message
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        # Parse the JSON from the message
        event = json.loads(record.message)
        
        # Verify structure
        assert "timestamp" in event
        assert event["event_type"] == "ACCESS"
        assert event["action"] == "test_action"
        assert "details" in event
        assert event["details"]["key"] == "value"
        assert event["details"]["count"] == 42
    
    def test_log_api_access(self, caplog):
        """Test logging of API access events."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_api_access(
                "https://example.com/api",
                {"User-Agent": "test", "From": "test@example.com"},
                "initiated"
            )
        
        assert len(caplog.records) == 1
        event = json.loads(caplog.records[0].message)
        
        assert event["event_type"] == "ACCESS"
        assert event["action"] == "api_request"
        assert event["details"]["url"] == "https://example.com/api"
        assert event["details"]["status"] == "initiated"
        assert "User-Agent" in event["details"]["headers"]
        assert "From" in event["details"]["headers"]
    
    def test_log_api_access_sanitizes_headers(self, caplog):
        """Test that sensitive headers are not logged."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_api_access(
                "https://example.com/api",
                {
                    "User-Agent": "test",
                    "Authorization": "Bearer secret123",  # Should be filtered
                    "X-API-Key": "secret_key",  # Should be filtered
                    "From": "test@example.com"
                }
            )
        
        event = json.loads(caplog.records[0].message)
        headers = event["details"]["headers"]
        
        # Only safe headers should be present
        assert "User-Agent" in headers
        assert "From" in headers
        assert "Authorization" not in headers
        assert "X-API-Key" not in headers
    
    def test_log_compliance_check(self, caplog):
        """Test logging of compliance checks."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_compliance_check(
                "robots.txt",
                "https://example.com",
                "allowed",
                {"user_agent": "test-bot"}
            )
        
        assert len(caplog.records) == 1
        event = json.loads(caplog.records[0].message)
        
        assert event["event_type"] == "COMPLIANCE"
        assert event["action"] == "compliance_check"
        assert event["details"]["check_type"] == "robots.txt"
        assert event["details"]["url"] == "https://example.com"
        assert event["details"]["result"] == "allowed"
        assert event["details"]["user_agent"] == "test-bot"
    
    def test_log_security_error(self, caplog):
        """Test logging of security errors."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.WARNING, logger="test_security"):
            logger.log_security_error(
                "authentication_failed",
                "Invalid credentials provided",
                {"attempt": 3, "source": "192.168.1.1"}
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        event = json.loads(record.message)
        
        # Check it was logged at WARNING level
        assert record.levelno == logging.WARNING
        
        assert event["event_type"] == "ERROR"
        assert event["action"] == "security_error"
        assert event["details"]["error_type"] == "authentication_failed"
        assert event["details"]["message"] == "Invalid credentials provided"
        assert event["details"]["attempt"] == 3
    
    def test_log_event_without_details(self, caplog):
        """Test that events can be logged without details."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_event(
                SecurityEventLogger.COMPLIANCE,
                "rate_limit_check"
            )
        
        assert len(caplog.records) == 1
        event = json.loads(caplog.records[0].message)
        
        assert event["event_type"] == "COMPLIANCE"
        assert event["action"] == "rate_limit_check"
        assert "details" not in event
    
    def test_get_security_logger_singleton(self):
        """Test that get_security_logger returns a singleton."""
        logger1 = get_security_logger()
        logger2 = get_security_logger()
        
        assert logger1 is logger2
        assert isinstance(logger1, SecurityEventLogger)
    
    def test_timestamp_format(self, caplog):
        """Test that timestamps are in ISO 8601 format with UTC."""
        logger = SecurityEventLogger(name="test_security")
        
        with caplog.at_level(logging.INFO, logger="test_security"):
            logger.log_event(SecurityEventLogger.ACCESS, "test")
        
        event = json.loads(caplog.records[0].message)
        timestamp = event["timestamp"]
        
        # Should end with Z for UTC
        assert timestamp.endswith("Z")
        # Should contain time separator
        assert "T" in timestamp
        # Should be parseable
        from datetime import datetime
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None


class TestSetupLogger:
    """Test the standard logger setup function."""
    
    def test_setup_logger_basic(self):
        """Test that setup_logger works correctly."""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logger_idempotent(self):
        """Test that calling setup_logger multiple times doesn't add handlers."""
        logger1 = setup_logger("test_idempotent")
        handler_count1 = len(logger1.handlers)
        
        logger2 = setup_logger("test_idempotent")
        handler_count2 = len(logger2.handlers)
        
        assert handler_count1 == handler_count2
        assert logger1 is logger2
