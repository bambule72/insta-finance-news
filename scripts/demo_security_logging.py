#!/usr/bin/env python3
"""Demo script to showcase security logging functionality."""

import sys
import logging
from src.news_scraper.logger import get_security_logger, SecurityEventLogger

def main():
    # Configure root logger to show all logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
    )
    
    print("=" * 70)
    print("Security Event Logging Demonstration")
    print("=" * 70)
    print()
    
    # Get the security logger
    security_logger = get_security_logger()
    
    print("1. Logging API Access Event")
    print("-" * 70)
    security_logger.log_api_access(
        url="https://www.sec.gov/cgi-bin/browse-edgar",
        headers={
            "User-Agent": "insta-finance-news/0.1",
            "From": "admin@example.com",
            "Accept": "application/atom+xml"
        },
        status="initiated"
    )
    print()
    
    print("2. Logging API Success")
    print("-" * 70)
    security_logger.log_api_access(
        url="https://www.sec.gov/cgi-bin/browse-edgar",
        headers={"User-Agent": "insta-finance-news/0.1"},
        status="success_status_200"
    )
    print()
    
    print("3. Logging Compliance Check (robots.txt)")
    print("-" * 70)
    security_logger.log_compliance_check(
        check_type="robots.txt",
        url="https://www.sec.gov",
        result="allowed",
        details={"user_agent": "insta-finance-news/0.1"}
    )
    print()
    
    print("4. Logging Security Error")
    print("-" * 70)
    security_logger.log_security_error(
        error_type="request_timeout",
        message="Request timed out after 10 seconds",
        details={
            "url": "https://example.com/api",
            "timeout": 10,
            "retry_count": 3
        }
    )
    print()
    
    print("5. Demonstrating Header Sanitization")
    print("-" * 70)
    print("Input headers include sensitive data:")
    print("  - User-Agent: safe-bot")
    print("  - Authorization: Bearer secret123 [SENSITIVE]")
    print("  - X-API-Key: supersecret [SENSITIVE]")
    print()
    print("Security log output (sensitive headers filtered):")
    security_logger.log_api_access(
        url="https://api.example.com/data",
        headers={
            "User-Agent": "safe-bot",
            "Authorization": "Bearer secret123",  # Will be filtered
            "X-API-Key": "supersecret",  # Will be filtered
            "From": "admin@example.com"
        },
        status="initiated"
    )
    print()
    
    print("6. Custom Security Event")
    print("-" * 70)
    security_logger.log_event(
        event_type=SecurityEventLogger.COMPLIANCE,
        action="rate_limit_check",
        details={
            "host": "www.sec.gov",
            "requests_per_second": 1.0,
            "compliant": True
        }
    )
    print()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("All security events are logged in structured JSON format,")
    print("making them easy to parse, analyze, and integrate with SIEM tools.")
    print()
    print("See docs/security-logging.md for full documentation.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
