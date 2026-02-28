"""Logging configuration with enhanced syslog format."""

import logging
import sys
from datetime import datetime, timezone


class SyslogFormatter(logging.Formatter):
    """Enhanced syslog-style formatter.

    Formats log messages in an enhanced syslog format with timestamp,
    hostname placeholder, application name, PID, and structured message.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record in enhanced syslog format.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message string.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()

        return f"{timestamp}Z {level:<8} [{logger_name}] {message}"


def setup_logging(level: str = "INFO") -> None:
    """Configure application logging.

    Sets up logging with enhanced syslog format for all handlers.

    Args:
        level: The logging level as a string (DEBUG, INFO, WARNING, etc.).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(SyslogFormatter())

    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: The name for the logger, typically __name__.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
