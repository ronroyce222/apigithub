"""Health check router with Kubernetes-compatible probe endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=[""])


class HomeResponse(BaseModel):
    """Response model for liveness probe endpoint."""

    status: str = Field(description="Liveness status")


@router.get(
    "/",
    status_code=200,
)
async def home() -> HomeResponse:
    return HomeResponse(status="ok")
