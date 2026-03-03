"""Jira webhook event models."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class JiraEvent(BaseModel):
    """Model for Jira webhook events.

    Accepts any JSON payload from Jira webhooks while providing
    a structured interface for common fields.
    """

    model_config = {"extra": "allow"}

    timestamp: str = Field(
        default=None,
        description="Timestamp of the event",
    )
    webhookEvent: str = Field(
        default=None,
        description="The Jira webhook event type",
    )
    issue_event_type_name: str = Field(
        default=None,
        description="Issue event type name",
    )
    user: dict[str, Any] = Field(
        default=None,
        description="User who triggered the event",
    )
    issue: dict[str, Any] = Field(
        default=None,
        description="Jira issue details",
    )
    changelog: dict[str, Any] = Field(
        default=None,
        description="Change log for the event",
    )


class StoredJiraEvent(BaseModel):
    """Wrapper for stored Jira events with metadata."""

    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when event was received",
    )
    event_type: str = Field(
        description="Jira webhook event type",
    )
    payload: dict[str, Any] = Field(
        description="Raw Jira event payload",
    )


class JiraWebhookResponse(BaseModel):
    """Response model for Jira webhook endpoint."""

    status: str = Field(description="Processing status")
    event_type: str = Field(
        default=None,
        description="Received event type",
    )
