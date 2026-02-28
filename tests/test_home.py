"""Tests for home router."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_home_returns_200(async_client: AsyncClient) -> None:
    """Test home endpoint returns 200."""
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_home_returns_ok_status(async_client: AsyncClient) -> None:
    """Test home endpoint returns ok status."""
    response = await async_client.get("/")
    data = response.json()
    assert data["status"] == "ok"
