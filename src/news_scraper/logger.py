import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def setup_logger(name: str = "news_scraper") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class SecurityEventLogger:
    """Logger for security-sensitive events with structured output."""
    
    # Security event types
    AUTH = "AUTH"           # Authentication/authorization events
    ACCESS = "ACCESS"       # Data/resource access events
    COMPLIANCE = "COMPLIANCE"  # Compliance-related events (robots.txt, rate limiting)
    ERROR = "ERROR"         # Security-relevant errors
    
    def __init__(self, name: str = "security_events"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            # Use simple format for security logger
            fmt = logging.Formatter("%(asctime)s SECURITY [%(name)s] %(message)s")
            handler.setFormatter(fmt)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_event(
        self,
        event_type: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO
    ) -> None:
        """Log a structured security event.
        
        Args:
            event_type: Type of security event (AUTH, ACCESS, COMPLIANCE, ERROR)
            action: Description of the action being performed
            details: Additional context (URLs, headers, results, etc.)
            level: Logging level (default: INFO)
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_type": event_type,
            "action": action,
        }
        if details:
            event["details"] = details
        
        # Log as JSON for machine parsing
        self.logger.log(level, json.dumps(event))
    
    def log_api_access(self, url: str, headers: Optional[Dict[str, str]] = None, status: str = "initiated") -> None:
        """Log external API/resource access."""
        details = {"url": url, "status": status}
        if headers:
            # Sanitize headers - only log non-sensitive ones
            safe_headers = {k: v for k, v in headers.items() if k.lower() in ["user-agent", "from", "accept"]}
            if safe_headers:
                details["headers"] = safe_headers
        self.log_event(self.ACCESS, "api_request", details)
    
    def log_compliance_check(self, check_type: str, url: str, result: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log compliance-related checks (robots.txt, rate limiting)."""
        event_details = {"check_type": check_type, "url": url, "result": result}
        if details:
            event_details.update(details)
        self.log_event(self.COMPLIANCE, "compliance_check", event_details)
    
    def log_security_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log security-relevant errors."""
        event_details = {"error_type": error_type, "message": message}
        if details:
            event_details.update(details)
        self.log_event(self.ERROR, "security_error", event_details, level=logging.WARNING)


# Global security logger instance
_security_logger: Optional[SecurityEventLogger] = None


def get_security_logger() -> SecurityEventLogger:
    """Get or create the global security event logger."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityEventLogger()
    return _security_logger
