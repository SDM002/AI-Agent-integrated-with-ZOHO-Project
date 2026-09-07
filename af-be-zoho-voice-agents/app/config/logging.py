"""
# Set up logging system for the application (controls format, level, and output style)
# Helps track app behavior and debug issues using structured logs
"""
import logging
import structlog
from app.config.settings import SETTINGS

RENDERERS = {
    "console": structlog.dev.ConsoleRenderer,
    "json":    structlog.processors.JSONRenderer,
}
# Configure structured logging (format, level, context, and output style)
def setup_logging() -> None:
    log_level = getattr(logging, SETTINGS.LOG_LEVEL.upper())
    renderer  = RENDERERS[SETTINGS.LOG_RENDERER]

    logging.basicConfig(format="%(message)s", level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars, # Inject request/context data into logs
            structlog.processors.add_log_level, # Add log level field
            structlog.processors.TimeStamper(fmt="iso"), # Add timestamp (ISO format)
            renderer(),                                  # Apply selected output format
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level), # Filter logs by level
        context_class=dict,                    # Store log context as dictionary
        logger_factory=structlog.PrintLoggerFactory(),  # Basic logger output backend
    )

logger = structlog.get_logger()
