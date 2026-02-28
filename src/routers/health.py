"""Health check router with Kubernetes-compatible probe endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from version import __version__

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    """Response model for liveness probe endpoint."""

    status: str = Field(description="Liveness status")


class ReadinessResponse(BaseModel):
    """Response model for readiness probe endpoint."""

    status: str = Field(description="Readiness status")


class StartupResponse(BaseModel):
    """Response model for startup probe endpoint."""

    status: str = Field(description="Startup status")


class HealthResponse(BaseModel):
    """Response model for combined health check endpoint."""

    status: str = Field(description="Service health status")
    version: str = Field(description="Application version")
    timestamp: str = Field(description="Current UTC timestamp")


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> LivenessResponse:
    """Kubernetes liveness probe endpoint.

    Indicates whether the application process is running.
    If this check fails, Kubernetes will restart the container.

    Returns:
        Liveness status response.
    """
    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def readiness_probe() -> ReadinessResponse:
    """Kubernetes readiness probe endpoint.

    Indicates whether the application is ready to serve traffic.
    If this check fails, Kubernetes removes the pod from service endpoints.

    Returns:
        Readiness status response.
    """
    return ReadinessResponse(status="ok")


@router.get(
    "/startup",
    response_model=StartupResponse,
    status_code=status.HTTP_200_OK,
)
async def startup_probe() -> StartupResponse:
    """Kubernetes startup probe endpoint.

    Indicates whether the application has completed initialization.
    Used for slow-starting containers to delay liveness/readiness checks.

    Returns:
        Startup status response.
    """
    return StartupResponse(status="ok")


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    """Combined health check endpoint.

    Returns comprehensive health information including service status,
    version, and current timestamp.

    Returns:
        Health status response.
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
