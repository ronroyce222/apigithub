"""GitHub webhook event models."""

from typing import Any

from pydantic import BaseModel, Field


class GitHubEvent(BaseModel):
    """Model for GitHub webhook events.

    Accepts any JSON payload from GitHub webhooks while providing
    a structured interface for common fields.
    """

    model_config = {"extra": "allow"}

    action: str = Field(
        default=None,
        description="The action that triggered the event",
    )
    sender: dict[str, Any] = Field(
        default=None,
        description="User who triggered the event",
    )
    repository: dict[str, Any] = Field(
        default=None,
        description="Repository information",
    )


class GitHubWebhookResponse(BaseModel):
    """Response model for GitHub webhook endpoint."""

    status: str = Field(description="Processing status")
    message_id: str = Field(
        default=None,
        description="SNS message ID if published",
    )


class PRReviewRequest(BaseModel):
    """Request model for PR code review endpoint."""

    owner: str = Field(description="GitHub repository owner")
    repo: str = Field(description="Repository name")
    pr_number: int = Field(description="Pull request number")
    post_comment: bool = Field(
        default=False,
        description="Whether to post review as PR comment",
    )
    custom_prompt: str | None = Field(
        default=None,
        description="Optional custom review prompt",
    )


class PRReviewResponse(BaseModel):
    """Response model for PR code review endpoint."""

    status: str = Field(description="Review status")
    pr_number: int = Field(description="Pull request number")
    repository: str = Field(description="Repository name")
    owner: str = Field(description="Repository owner")
    summary: str = Field(description="Review summary")
    files_reviewed: int = Field(
        description="Number of files reviewed",
    )
    approval_recommendation: bool = Field(
        description="Whether PR is recommended for approval",
    )
    comment_count: int = Field(
        default=0,
        description="Number of review comments",
    )
    comment_posted: bool = Field(
        default=False,
        description="Whether review was posted as PR comment",
    )
    review_markdown: str | None = Field(
        default=None,
        description="Markdown-formatted review for display",
    )
