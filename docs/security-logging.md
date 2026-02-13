# Security Event Logging

## Overview

The insta-finance-news scraper includes enhanced security event logging to provide audit trails, security monitoring, and compliance tracking for all security-sensitive operations.

## Features

### Structured Logging
- All security events are logged in **JSON format** for easy parsing and analysis
- Timestamps use **ISO 8601 format with UTC timezone**
- Events include structured metadata (event_type, action, details)

### Event Types

The security logging system categorizes events into four types:

1. **AUTH** - Authentication and authorization events
2. **ACCESS** - Data and resource access events (API calls, file access)
3. **COMPLIANCE** - Compliance-related events (robots.txt checks, rate limiting)
4. **ERROR** - Security-relevant errors (failed requests, parsing errors)

### Header Sanitization

The security logger automatically **sanitizes sensitive headers** to prevent logging of credentials:
- ✅ **Logged**: User-Agent, From, Accept
- ❌ **Filtered**: Authorization, X-API-Key, Cookie, and other sensitive headers

## Usage

### Basic Usage

```python
from src.news_scraper.logger import get_security_logger

# Get the global security logger instance
security_logger = get_security_logger()

# Log an API access event
security_logger.log_api_access(
    url="https://www.sec.gov/api/endpoint",
    headers={"User-Agent": "bot", "From": "admin@example.com"},
    status="initiated"
)

# Log a compliance check
security_logger.log_compliance_check(
    check_type="robots.txt",
    url="https://example.com",
    result="allowed",
    details={"user_agent": "mybot"}
)

# Log a security error
security_logger.log_security_error(
    error_type="authentication_failed",
    message="Invalid credentials",
    details={"attempt": 3, "source_ip": "192.168.1.1"}
)
```

### Custom Events

For custom security events, use the generic `log_event` method:

```python
security_logger.log_event(
    event_type=SecurityEventLogger.ACCESS,
    action="custom_action",
    details={"key": "value"},
    level=logging.INFO
)
```

## Log Format

All security events follow this JSON structure:

```json
{
  "timestamp": "2026-02-13T09:18:42.661079Z",
  "event_type": "ACCESS",
  "action": "api_request",
  "details": {
    "url": "https://www.sec.gov/feed",
    "status": "success_status_200",
    "headers": {
      "User-Agent": "insta-finance-news/0.1",
      "From": "admin@example.com"
    }
  }
}
```

### Field Descriptions

- **timestamp**: ISO 8601 UTC timestamp of when the event occurred
- **event_type**: Category of security event (AUTH, ACCESS, COMPLIANCE, ERROR)
- **action**: Specific action being performed (e.g., "api_request", "compliance_check")
- **details**: Event-specific context and metadata (URLs, headers, error messages, etc.)

## Automated Logging

The scraper automatically logs security events for:

### API/Resource Access
- All HTTP requests to external APIs (SEC, financial news sites)
- Request initiation with URL and safe headers
- Successful responses with status codes
- Failed requests after retry exhaustion

### SEC Form Fetching
- SEC feed access with form type
- Parser availability checks
- Network errors and timeouts
- Unexpected errors with full context

### Error Handling
- Network failures with retry information
- Parser errors with form type details
- Unexpected exceptions with error messages

## Parsing and Analysis

Since logs are in JSON format, they can be easily parsed and analyzed:

### Using Python

```python
import json

with open("app.log") as f:
    for line in f:
        if "SECURITY" in line:
            # Extract JSON from log line
            json_start = line.index("{")
            event = json.loads(line[json_start:])
            
            if event["event_type"] == "ERROR":
                print(f"Security error: {event['details']}")
```

### Using jq (command line)

```bash
# Extract all security events
grep "SECURITY" app.log | sed 's/.*SECURITY.*{/{/' | jq .

# Count events by type
grep "SECURITY" app.log | sed 's/.*SECURITY.*{/{/' | jq -r .event_type | sort | uniq -c

# Find all errors
grep "SECURITY" app.log | sed 's/.*SECURITY.*{/{/' | jq 'select(.event_type == "ERROR")'

# Get all failed API requests
grep "SECURITY" app.log | sed 's/.*SECURITY.*{/{/' | \
  jq 'select(.details.error_type == "request_failed")'
```

## Integration with Monitoring Tools

The structured JSON format makes it easy to integrate with monitoring and SIEM tools:

- **ELK Stack**: Ship logs to Elasticsearch for indexing and Kibana visualization
- **Splunk**: Parse JSON events for real-time monitoring and alerting
- **CloudWatch Logs**: Use CloudWatch Logs Insights to query security events
- **Datadog**: Send logs to Datadog for APM and security monitoring

## Best Practices

### Do:
✅ Use security logging for all external API access  
✅ Log failed authentication/authorization attempts  
✅ Include relevant context in the `details` field  
✅ Use appropriate event types for categorization  
✅ Log compliance checks (robots.txt, rate limits)  

### Don't:
❌ Log sensitive data (passwords, API keys, tokens)  
❌ Log full request/response bodies containing PII  
❌ Use security logging for general debug information  
❌ Include personally identifiable information (PII)  

## Testing

The security logging implementation includes comprehensive tests:

```bash
# Run security logging tests
PYTHONPATH=/path/to/project pytest tests/test_security_logging.py -xvs

# Run integration tests
PYTHONPATH=/path/to/project pytest tests/test_security_logging_integration.py -xvs
```

Test coverage includes:
- Logger initialization and configuration
- Structured JSON event creation
- Header sanitization
- All event type methods (AUTH, ACCESS, COMPLIANCE, ERROR)
- Integration with scraper modules
- End-to-end scenarios

## Configuration

The security logger uses Python's standard `logging` module and can be configured via environment variables or code:

```python
import logging

# Increase security logging verbosity
logging.getLogger("security_events").setLevel(logging.DEBUG)

# Add file handler for security events
security_handler = logging.FileHandler("security_events.log")
security_handler.setFormatter(
    logging.Formatter("%(asctime)s SECURITY [%(name)s] %(message)s")
)
logging.getLogger("security_events").addHandler(security_handler)
```

## Compliance and Audit

The security logging system helps meet various compliance requirements:

- **SOC 2**: Provides audit trails for access and changes
- **GDPR**: Helps track data access (ensure no PII is logged)
- **SEC Compliance**: Documents all SEC API access with proper headers
- **General Audit**: Maintains comprehensive logs of all security-relevant operations

## Examples

### Monitoring Failed Requests

```python
# In your monitoring script
import json

failed_requests = []
with open("app.log") as f:
    for line in f:
        if "SECURITY" in line and "request_failed" in line:
            json_start = line.index("{")
            event = json.loads(line[json_start:])
            failed_requests.append({
                "url": event["details"]["url"],
                "error": event["details"]["error"],
                "timestamp": event["timestamp"]
            })

# Alert if too many failures
if len(failed_requests) > 10:
    send_alert(f"High failure rate: {len(failed_requests)} requests failed")
```

### Tracking SEC API Usage

```bash
# Count SEC API requests by status
grep "SECURITY.*sec.gov" app.log | sed 's/.*SECURITY.*{/{/' | \
  jq -r .details.status | sort | uniq -c

# Find rate limiting patterns
grep "SECURITY.*sec.gov" app.log | sed 's/.*SECURITY.*{/{/' | \
  jq -r '.timestamp' | cut -d'T' -f2 | cut -d':' -f1 | sort | uniq -c
```

## Troubleshooting

### No Security Logs Appearing

Check that the security logger is being initialized:
```python
from src.news_scraper.logger import get_security_logger
security_logger = get_security_logger()
```

### JSON Parsing Errors

Ensure you're extracting only the JSON portion of log lines:
```bash
# Correct: extract from first {
grep "SECURITY" app.log | sed 's/.*SECURITY.*{/{/' | jq .

# Incorrect: includes log prefix
grep "SECURITY" app.log | jq .  # Will fail
```

### Missing Event Details

Use the `details` parameter to add context:
```python
security_logger.log_api_access(
    url=url,
    headers=headers,
    status="initiated"
)
# Not: security_logger.log_api_access(url)  # Missing context
```
