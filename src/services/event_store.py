"""In-memory event store for GitHub webhook events."""

from collections import deque
from typing import Any

from logging_config import get_logger
from models.stored_event import StoredEvent

logger = get_logger(__name__)

_event_store: "EventStore | None" = None


class EventStore:
    """Thread-safe in-memory store for recent webhook events.

    Uses a bounded deque to keep the most recent N events,
    automatically discarding oldest entries when full.

    Args:
        max_size: Maximum number of events to retain.
    """

    def __init__(self, max_size: int = 100) -> None:
        self._events: deque[StoredEvent] = deque(
            maxlen=max_size,
        )

    def add(
        self,
        event_type: str,
        payload: dict[str, Any],
        delivery_id: str = "",
    ) -> StoredEvent:
        """Extract key fields from payload and store the event.

        Args:
            event_type: GitHub event type header value.
            payload: Full webhook payload dictionary.
            delivery_id: GitHub delivery ID header value.

        Returns:
            The newly created StoredEvent.
        """
        repo_data = payload.get("repository", {}) or {}
        sender_data = payload.get("sender", {}) or {}

        summary_keys = [
            "action",
            "ref",
            "before",
            "after",
            "compare",
        ]
        payload_summary = {
            k: payload[k]
            for k in summary_keys
            if k in payload
        }

        event = StoredEvent(
            event_type=event_type,
            action=payload.get("action", ""),
            repository=repo_data.get("full_name", ""),
            sender=sender_data.get("login", ""),
            delivery_id=delivery_id,
            payload_summary=payload_summary,
        )

        self._events.appendleft(event)

        logger.info(
            "Stored event: type=%s, repo=%s, sender=%s",
            event.event_type,
            event.repository,
            event.sender,
        )

        return event

    def get_all(self) -> list[StoredEvent]:
        """Return all stored events, newest first.

        Returns:
            List of stored events ordered by most recent.
        """
        return list(self._events)

    def clear(self) -> None:
        """Remove all stored events."""
        self._events.clear()

    @property
    def count(self) -> int:
        """Return the number of stored events."""
        return len(self._events)


def get_event_store() -> EventStore:
    """Get or create the singleton EventStore instance.

    Lazily initializes the store on first call, reading
    max size from application config.

    Returns:
        The singleton EventStore instance.
    """
    global _event_store
    if _event_store is None:
        from config import get_settings

        settings = get_settings()
        max_size = getattr(
            settings, "event_store_max_size", 100
        )
        _event_store = EventStore(max_size=max_size)
        logger.info(
            "Initialized event store: max_size=%d",
            max_size,
        )
    return _event_store
