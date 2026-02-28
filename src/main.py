"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pprint import pprint
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from config import get_settings
from logging_config import get_logger, setup_logging
from routers import github, health, jira, home
from version import __version__
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events with retry logic for
    initialization failures.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after successful startup.
    """
    settings = get_settings()
    setup_logging(settings.log_level)

    pprint("Settings in env is: ")
    pprint(settings)

    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            logger.info(
                "1 - Starting webhook server: version=%s, host=%s, port=%d",
                __version__,
                settings.host,
                settings.port,
            )
            break
        except Exception:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.error(
                    "Startup failed, retrying: attempt=%d, delay=%.1fs",
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.critical("Startup failed after max retries")
                raise

    yield

    logger.info("Shutting down webhook server")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    logger.info("Start FastAPI server...")

    app = FastAPI(
        title="Webhook Server",
        description="FastAPI server for GitHub and Jira webhooks",
        version=__version__,
        debug=True,
        lifespan=lifespan,
    )

    logger.info("Adding routes")

    app.include_router(home.router)
    app.include_router(health.router)
    app.include_router(github.router)
    app.include_router(jira.router)

    return app


logger.error("Creating app")

app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    pprint(settings)
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
