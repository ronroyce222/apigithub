"""Pydantic model for stored GitHub webhook events."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class StoredEvent(BaseModel):
    """Represents a stored GitHub webhook event.

    Captures key fields from incoming webhook payloads for
    display in the events viewer.
    """

    event_type: str = Field(
        description="GitHub event type from X-GitHub-Event header",
    )
    action: str = Field(
        default="",
        description="Action that triggered the event",
    )
    repository: str = Field(
        default="",
        description="Full repository name (owner/repo)",
    )
    sender: str = Field(
        default="",
        description="GitHub username that triggered the event",
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event was received",
    )
    delivery_id: str = Field(
        default="",
        description="GitHub delivery ID from X-GitHub-Delivery",
    )
    payload_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of key payload fields",
    )
