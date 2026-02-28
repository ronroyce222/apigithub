"""Tests for main application module."""

import os
import sys
import runpy
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app_returns_fastapi(self) -> None:
        """Test that create_app returns a FastAPI instance."""
        from main import app
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_has_routers(self) -> None:
        """Test that app has all routers included."""
        from main import app

        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes
        assert "/health/live" in routes
        assert "/health/ready" in routes
        assert "/health/startup" in routes
        assert "/webhooks/github" in routes

    def test_app_metadata(self) -> None:
        """Test app metadata."""
        from main import app

        assert app.title == "Webhook Server"
        assert "webhook" in app.description.lower()


class TestLifespan:
    """Tests for lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self) -> None:
        """Test successful startup."""
        from main import lifespan, app

        async with lifespan(app):
            pass

    @pytest.mark.asyncio
    async def test_lifespan_with_startup_retry(self) -> None:
        """Test lifespan handles startup with retry."""
        from main import lifespan
        from fastapi import FastAPI

        test_app = FastAPI()

        with patch("main.setup_logging"):
            async with lifespan(test_app):
                pass

    @pytest.mark.asyncio
    async def test_lifespan_startup_retry_then_success(self) -> None:
        """Test lifespan retries on failure then succeeds."""
        from main import lifespan
        from fastapi import FastAPI

        test_app = FastAPI()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Startup failed")
            # Second call succeeds

        with patch("main.setup_logging"), \
             patch("main.logger") as mock_logger, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_logger.info = MagicMock(side_effect=side_effect)
            mock_logger.error = MagicMock()
            mock_logger.critical = MagicMock()

            async with lifespan(test_app):
                pass

            # Verify retry was attempted
            assert call_count >= 2

    @pytest.mark.asyncio
    async def test_lifespan_startup_max_retries_exceeded(self) -> None:
        """Test lifespan raises after max retries exceeded."""
        from main import lifespan
        from fastapi import FastAPI

        test_app = FastAPI()

        with patch("main.setup_logging"), \
             patch("main.logger") as mock_logger, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_logger.info = MagicMock(
                side_effect=RuntimeError("Persistent failure")
            )
            mock_logger.error = MagicMock()
            mock_logger.critical = MagicMock()

            with pytest.raises(RuntimeError, match="Persistent failure"):
                async with lifespan(test_app):
                    pass

            # Verify critical log was called
            mock_logger.critical.assert_called()


class TestMainEntryPoint:
    """Tests for main module entry point."""

    def test_main_entry_point(self) -> None:
        """Test the if __name__ == '__main__' block via runpy."""
        main_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "main.py"
        )

        with patch("uvicorn.run") as mock_run:
            try:
                runpy.run_path(main_path, run_name="__main__")
            except SystemExit:
                pass  # uvicorn.run might cause SystemExit

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert "main:app" in str(call_kwargs)
