"""Tests for StoredEvent pydantic model."""

from datetime import datetime, timezone

import pytest

from models.stored_event import StoredEvent


class TestStoredEventDefaults:
    """Test StoredEvent default field values."""

    def test_minimal_creation(self) -> None:
        """Test creating event with only required field."""
        event = StoredEvent(event_type="push")

        assert event.event_type == "push"
        assert event.action == ""
        assert event.repository == ""
        assert event.sender == ""
        assert event.delivery_id == ""
        assert event.payload_summary == {}

    def test_received_at_defaults_to_utc_now(self) -> None:
        """Test received_at defaults to current UTC time."""
        before = datetime.now(timezone.utc)
        event = StoredEvent(event_type="push")
        after = datetime.now(timezone.utc)

        assert before <= event.received_at <= after


class TestStoredEventFields:
    """Test StoredEvent field assignment."""

    def test_all_fields_populated(self) -> None:
        """Test creating event with all fields set."""
        ts = datetime.now(timezone.utc)
        event = StoredEvent(
            event_type="pull_request",
            action="opened",
            repository="owner/repo",
            sender="testuser",
            received_at=ts,
            delivery_id="abc-123",
            payload_summary={"ref": "main"},
        )

        assert event.event_type == "pull_request"
        assert event.action == "opened"
        assert event.repository == "owner/repo"
        assert event.sender == "testuser"
        assert event.received_at == ts
        assert event.delivery_id == "abc-123"
        assert event.payload_summary == {"ref": "main"}


class TestStoredEventSerialization:
    """Test StoredEvent serialization."""

    def test_model_dump_contains_all_fields(self) -> None:
        """Test model_dump includes all expected keys."""
        event = StoredEvent(event_type="push")
        data = event.model_dump()

        expected_keys = {
            "event_type",
            "action",
            "repository",
            "sender",
            "received_at",
            "delivery_id",
            "payload_summary",
        }
        assert set(data.keys()) == expected_keys

    def test_json_mode_serializes_datetime(self) -> None:
        """Test model_dump with json mode serializes datetime."""
        event = StoredEvent(event_type="push")
        data = event.model_dump(mode="json")

        assert isinstance(data["received_at"], str)
