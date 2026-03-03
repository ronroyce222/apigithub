"""Tests for GitHub events viewer router."""

import pytest
from httpx import AsyncClient

import services.event_store as event_store_module
from services.event_store import EventStore, get_event_store


@pytest.fixture(autouse=True)
def reset_event_store() -> None:
    """Reset the singleton event store before each test."""
    event_store_module._event_store = None
    yield
    event_store_module._event_store = None


class TestEventsPage:
    """Test GET /github/events HTML page."""

    @pytest.mark.asyncio
    async def test_returns_html(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events page returns HTML content."""
        response = await async_client.get(
            "/github/events",
        )

        assert response.status_code == 200
        assert "text/html" in response.headers[
            "content-type"
        ]

    @pytest.mark.asyncio
    async def test_contains_title(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events page contains expected title."""
        response = await async_client.get(
            "/github/events",
        )

        assert "GitHub Events" in response.text

    @pytest.mark.asyncio
    async def test_contains_auto_refresh(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events page includes auto-refresh script."""
        response = await async_client.get(
            "/github/events",
        )

        assert "setInterval" in response.text


class TestEventsApi:
    """Test GET /github/events/api JSON endpoint."""

    @pytest.mark.asyncio
    async def test_returns_json(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events API returns JSON response."""
        response = await async_client.get(
            "/github/events/api",
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "events" in data

    @pytest.mark.asyncio
    async def test_empty_store_returns_zero(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events API returns zero for empty store."""
        response = await async_client.get(
            "/github/events/api",
        )

        data = response.json()
        assert data["total"] == 0
        assert data["events"] == []

    @pytest.mark.asyncio
    async def test_returns_stored_events(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events API returns previously stored events."""
        store = get_event_store()
        store.add(
            "push",
            {
                "action": "completed",
                "repository": {"full_name": "o/r"},
                "sender": {"login": "user1"},
            },
            "delivery-abc",
        )

        response = await async_client.get(
            "/github/events/api",
        )

        data = response.json()
        assert data["total"] == 1
        event = data["events"][0]
        assert event["event_type"] == "push"
        assert event["action"] == "completed"
        assert event["repository"] == "o/r"
        assert event["sender"] == "user1"
        assert event["delivery_id"] == "delivery-abc"

    @pytest.mark.asyncio
    async def test_multiple_events_newest_first(
        self, async_client: AsyncClient,
    ) -> None:
        """Test events API returns newest events first."""
        store = get_event_store()
        store.add("first", {})
        store.add("second", {})

        response = await async_client.get(
            "/github/events/api",
        )

        data = response.json()
        assert data["total"] == 2
        assert data["events"][0]["event_type"] == "second"
        assert data["events"][1]["event_type"] == "first"
