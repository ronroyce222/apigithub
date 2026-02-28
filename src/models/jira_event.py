"""Jira webhook event models."""

from typing import Any

from pydantic import BaseModel, Field


class JiraEvent(BaseModel):
    """Model for Jira webhook events.

    Accepts any JSON payload from Jira webhooks while providing
    a structured interface for common fields.
    """

    model_config = {"extra": "allow"}

    webhook_event: str | None = Field(
        default=None,
        alias="webhookEvent",
        description="The webhook event type",
    )
    issue: dict[str, Any] | None = Field(
        default=None,
        description="Issue information",
    )
    user: dict[str, Any] | None = Field(
        default=None,
        description="User who triggered the event",
    )
    changelog: dict[str, Any] | None = Field(
        default=None,
        description="Change details for update events",
    )


class JiraWebhookResponse(BaseModel):
    """Response model for Jira webhook endpoint."""

    status: str = Field(description="Processing status")
    message_id: str | None = Field(
        default=None,
        description="SNS message ID if published",
    )
