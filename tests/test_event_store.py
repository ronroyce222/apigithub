"""Tests for EventStore service."""

from unittest.mock import patch

import pytest

from models.stored_event import StoredEvent
from services.event_store import EventStore, get_event_store
import services.event_store as event_store_module


@pytest.fixture
def store() -> EventStore:
    """Create a fresh EventStore for each test."""
    return EventStore(max_size=5)


@pytest.fixture
def sample_payload() -> dict:
    """Return a sample GitHub webhook payload."""
    return {
        "action": "opened",
        "ref": "refs/heads/main",
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "testuser"},
    }


class TestEventStoreAdd:
    """Test EventStore.add method."""

    def test_add_returns_stored_event(
        self, store: EventStore, sample_payload: dict,
    ) -> None:
        """Test add returns a StoredEvent instance."""
        event = store.add("push", sample_payload, "del-1")

        assert isinstance(event, StoredEvent)
        assert event.event_type == "push"
        assert event.action == "opened"
        assert event.repository == "owner/repo"
        assert event.sender == "testuser"
        assert event.delivery_id == "del-1"

    def test_add_extracts_summary_keys(
        self, store: EventStore, sample_payload: dict,
    ) -> None:
        """Test add extracts expected summary keys."""
        event = store.add("push", sample_payload)

        assert "action" in event.payload_summary
        assert "ref" in event.payload_summary

    def test_add_handles_missing_payload_fields(
        self, store: EventStore,
    ) -> None:
        """Test add handles empty payload gracefully."""
        event = store.add("ping", {})

        assert event.event_type == "ping"
        assert event.action == ""
        assert event.repository == ""
        assert event.sender == ""

    def test_add_handles_none_nested_fields(
        self, store: EventStore,
    ) -> None:
        """Test add handles None repository and sender."""
        payload = {
            "action": "test",
            "repository": None,
            "sender": None,
        }
        event = store.add("push", payload)

        assert event.repository == ""
        assert event.sender == ""

    def test_add_increments_count(
        self, store: EventStore, sample_payload: dict,
    ) -> None:
        """Test count increases with each add."""
        assert store.count == 0
        store.add("push", sample_payload)
        assert store.count == 1
        store.add("push", sample_payload)
        assert store.count == 2


class TestEventStoreOrdering:
    """Test EventStore ordering behavior."""

    def test_newest_first_ordering(
        self, store: EventStore,
    ) -> None:
        """Test events are returned newest first."""
        store.add("first", {"action": "a"})
        store.add("second", {"action": "b"})
        store.add("third", {"action": "c"})

        events = store.get_all()

        assert events[0].event_type == "third"
        assert events[1].event_type == "second"
        assert events[2].event_type == "first"


class TestEventStoreMaxSize:
    """Test EventStore bounded size behavior."""

    def test_respects_max_size(self, store: EventStore) -> None:
        """Test oldest events are dropped at max capacity."""
        for i in range(7):
            store.add(f"event-{i}", {})

        assert store.count == 5
        events = store.get_all()
        assert events[0].event_type == "event-6"
        assert events[-1].event_type == "event-2"

    def test_get_all_returns_list(
        self, store: EventStore,
    ) -> None:
        """Test get_all returns a plain list."""
        store.add("push", {})
        result = store.get_all()

        assert isinstance(result, list)


class TestEventStoreClear:
    """Test EventStore.clear method."""

    def test_clear_removes_all_events(
        self, store: EventStore,
    ) -> None:
        """Test clear empties the store."""
        store.add("push", {})
        store.add("push", {})
        store.clear()

        assert store.count == 0
        assert store.get_all() == []


class TestGetEventStoreSingleton:
    """Test get_event_store singleton accessor."""

    def test_returns_event_store_instance(self) -> None:
        """Test get_event_store returns EventStore."""
        event_store_module._event_store = None
        try:
            store = get_event_store()
            assert isinstance(store, EventStore)
        finally:
            event_store_module._event_store = None

    def test_returns_same_instance(self) -> None:
        """Test get_event_store returns singleton."""
        event_store_module._event_store = None
        try:
            store1 = get_event_store()
            store2 = get_event_store()
            assert store1 is store2
        finally:
            event_store_module._event_store = None
