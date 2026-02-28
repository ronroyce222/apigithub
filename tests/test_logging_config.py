"""Tests for logging configuration."""

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from logging_config import SyslogFormatter, get_logger, setup_logging


class TestSyslogFormatter:
    """Tests for SyslogFormatter class."""

    def test_format_includes_timestamp(self) -> None:
        """Test that format includes UTC timestamp."""
        formatter = SyslogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "Z" in formatted
        assert "INFO" in formatted
        assert "[test]" in formatted
        assert "Test message" in formatted

    def test_format_level_alignment(self) -> None:
        """Test that log level is properly aligned."""
        formatter = SyslogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "WARNING" in formatted

    def test_format_with_args(self) -> None:
        """Test format with message arguments."""
        formatter = SyslogFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=10,
            msg="Value: %s",
            args=("test_value",),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "Value: test_value" in formatted
        assert "[test.module]" in formatted


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default_level(self) -> None:
        """Test setup_logging with default INFO level."""
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_debug_level(self) -> None:
        """Test setup_logging with DEBUG level."""
        setup_logging("DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_warning_level(self) -> None:
        """Test setup_logging with WARNING level."""
        setup_logging("WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_setup_logging_creates_handler(self) -> None:
        """Test that setup_logging creates console handler."""
        setup_logging("INFO")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1

    def test_setup_logging_uses_syslog_formatter(self) -> None:
        """Test that setup_logging uses SyslogFormatter."""
        setup_logging("INFO")
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert isinstance(handler.formatter, SyslogFormatter)
                break

    def test_setup_logging_suppresses_uvicorn(self) -> None:
        """Test that uvicorn loggers are suppressed."""
        setup_logging("DEBUG")
        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_error = logging.getLogger("uvicorn.error")
        assert uvicorn_access.level == logging.WARNING
        assert uvicorn_error.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_correct_name(self) -> None:
        """Test that get_logger returns logger with correct name."""
        logger = get_logger("my.custom.logger")
        assert logger.name == "my.custom.logger"

    def test_get_logger_same_instance(self) -> None:
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("same.name")
        logger2 = get_logger("same.name")
        assert logger1 is logger2
