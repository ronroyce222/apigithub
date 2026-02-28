"""Tests for exception classes."""

import os
import sys
from http import HTTPStatus

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exceptions import AuthError
from exceptions.Response401 import ResponseModel401
from exceptions.badrequest import (
    BadRequestException,
    InvalidAPIVersion,
    MissingAPIVersion,
    MissingJWTToken,
)
from exceptions.database import (
    DatabaseConnectionException,
    DatabaseFetchException,
    DatabaseGeneralException,
    DatabaseHealthException,
    DatabaseUpsertException,
)
from exceptions.missingjwt import MissingJWTTokenException
from exceptions.nocontent import NoContentException


class TestAuthError:
    """Tests for AuthError exception."""

    def test_default_values(self) -> None:
        """Test AuthError with default values."""
        error = AuthError()
        assert error.code == HTTPStatus.UNAUTHORIZED
        assert error.msg == "Unauthorized"
        assert error.details == ""
        assert error.data_source_id == -1

    def test_custom_values(self) -> None:
        """Test AuthError with custom values."""
        error = AuthError(
            code=HTTPStatus.FORBIDDEN,
            msg="Custom message",
            details="Some details",
            data_source_id=42,
        )
        assert error.code == HTTPStatus.FORBIDDEN
        assert error.msg == "Custom message"
        assert error.details == "Some details"
        assert error.data_source_id == 42

    def test_default_msg_from_status(self) -> None:
        """Test that default message comes from HTTP status."""
        error = AuthError(code=HTTPStatus.NOT_FOUND)
        assert error.msg == "Not Found"


class TestResponseModel401:
    """Tests for ResponseModel401 model."""

    def test_model_fields(self) -> None:
        """Test ResponseModel401 fields."""
        response = ResponseModel401(status_code=401, message="Unauthorized")
        assert response.status_code == 401
        assert response.message == "Unauthorized"


class TestBadRequestExceptions:
    """Tests for bad request exception classes."""

    def test_bad_request_exception(self) -> None:
        """Test BadRequestException."""
        exc = BadRequestException("Invalid input")
        assert exc.message == "Invalid input"
        assert str(exc) == "Invalid input"

    def test_missing_api_version(self) -> None:
        """Test MissingAPIVersion exception."""
        exc = MissingAPIVersion("API version required")
        assert exc.message == "API version required"
        assert str(exc) == "API version required"

    def test_invalid_api_version(self) -> None:
        """Test InvalidAPIVersion exception."""
        exc = InvalidAPIVersion("Invalid API version: v999")
        assert exc.message == "Invalid API version: v999"
        assert str(exc) == "Invalid API version: v999"

    def test_missing_jwt_token(self) -> None:
        """Test MissingJWTToken exception."""
        exc = MissingJWTToken("JWT token missing")
        assert exc.message == "JWT token missing"
        assert str(exc) == "JWT token missing"


class TestDatabaseExceptions:
    """Tests for database exception classes."""

    def test_database_health_exception(self) -> None:
        """Test DatabaseHealthException."""
        exc = DatabaseHealthException("Database health check failed")
        assert str(exc) == "Database health check failed"

    def test_database_upsert_exception(self) -> None:
        """Test DatabaseUpsertException."""
        exc = DatabaseUpsertException("Upsert failed")
        assert str(exc) == "Upsert failed"

    def test_database_general_exception(self) -> None:
        """Test DatabaseGeneralException."""
        exc = DatabaseGeneralException("General database error")
        assert str(exc) == "General database error"

    def test_database_fetch_exception(self) -> None:
        """Test DatabaseFetchException."""
        exc = DatabaseFetchException("Fetch failed")
        assert str(exc) == "Fetch failed"

    def test_database_connection_exception(self) -> None:
        """Test DatabaseConnectionException."""
        exc = DatabaseConnectionException("Connection refused")
        assert str(exc) == "Connection refused"


class TestMissingJWTTokenException:
    """Tests for MissingJWTTokenException."""

    def test_exception_raises(self) -> None:
        """Test MissingJWTTokenException can be raised."""
        with pytest.raises(MissingJWTTokenException):
            raise MissingJWTTokenException()


class TestNoContentException:
    """Tests for NoContentException."""

    def test_exception_can_be_created(self) -> None:
        """Test NoContentException can be instantiated."""
        exc = NoContentException()
        assert isinstance(exc, Exception)

    def test_exception_raises(self) -> None:
        """Test NoContentException can be raised."""
        with pytest.raises(NoContentException):
            raise NoContentException()
