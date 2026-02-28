"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


class TestLivenessProbe:
    """Tests for liveness probe endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, async_client: AsyncClient) -> None:
        """Test liveness probe returns 200 status."""
        response = await async_client.get("/health/live")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_ok_status(self, async_client: AsyncClient) -> None:
        """Test liveness probe returns ok status."""
        response = await async_client.get("/health/live")
        data = response.json()
        assert data["status"] == "ok"


class TestReadinessProbe:
    """Tests for readiness probe endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, async_client: AsyncClient) -> None:
        """Test readiness probe returns 200 status."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_ok_status(self, async_client: AsyncClient) -> None:
        """Test readiness probe returns ok status."""
        response = await async_client.get("/health/ready")
        data = response.json()
        assert data["status"] == "ok"


class TestStartupProbe:
    """Tests for startup probe endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, async_client: AsyncClient) -> None:
        """Test startup probe returns 200 status."""
        response = await async_client.get("/health/startup")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_ok_status(self, async_client: AsyncClient) -> None:
        """Test startup probe returns ok status."""
        response = await async_client.get("/health/startup")
        data = response.json()
        assert data["status"] == "ok"


class TestCombinedHealthCheck:
    """Tests for combined health check endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, async_client: AsyncClient) -> None:
        """Test health check returns 200 status."""
        response = await async_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_healthy_status(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test health check returns healthy status."""
        response = await async_client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_includes_version(self, async_client: AsyncClient) -> None:
        """Test health check includes version information."""
        response = await async_client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] is not None

    @pytest.mark.asyncio
    async def test_includes_timestamp(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test health check includes timestamp."""
        response = await async_client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None
