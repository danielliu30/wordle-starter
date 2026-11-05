"""
Logging Configuration

Configures structlog for structured JSON logging.
All logs include request_id when available for distributed tracing.
"""
import structlog
import logging
import sys


def configure_logging():
    """
    Configure structured logging with JSON format.
    
    Sets up:
    - Logs to stdout in JSON format
    - Includes request_id from context when available
    - Sets up log level
    - Uses ISO timestamp format
    
    Benefits:
    - Machine-readable logs for log aggregation (ELK, CloudWatch, etc.)
    - Request_id enables distributed tracing
    - JSON format enables structured querying
    """
    # Configure standard logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Merge contextvars (like request_id) into log entries
            structlog.contextvars.merge_contextvars,
            # Add log level (INFO, WARNING, ERROR, etc.)
            structlog.processors.add_log_level,
            # Add ISO timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Render as JSON
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Get logger instance for use in modules
logger = structlog.get_logger()
