"""Pull request code review models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReviewSeverity(str, Enum):
    """Severity levels for review comments."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewComment(BaseModel):
    """Individual review comment model."""

    file_path: str = Field(description="Path to the file being reviewed")
    line_number: int | None = Field(
        default=None,
        description="Line number for the comment",
    )
    severity: ReviewSeverity = Field(
        default=ReviewSeverity.INFO,
        description="Severity level of the comment",
    )
    message: str = Field(description="Review comment message")
    suggestion: str | None = Field(
        default=None,
        description="Suggested code fix if applicable",
    )


class CodeReviewResult(BaseModel):
    """Result of a code review."""

    pr_id: int = Field(description="Pull request number")
    repository: str = Field(description="Repository name")
    project: str = Field(description="Repository owner")
    review_timestamp: datetime = Field(description="When the review was done")
    summary: str = Field(description="Overall review summary")
    comments: list[ReviewComment] = Field(
        default_factory=list,
        description="List of review comments",
    )
    files_reviewed: int = Field(
        default=0,
        description="Number of files reviewed",
    )
    approval_recommendation: bool = Field(
        default=False,
        description="Whether the PR is recommended for approval",
    )
    raw_review: str = Field(
        default="",
        description="Raw review output from Claude Code",
    )


class PRContext(BaseModel):
    """Context information extracted from a PR event."""

    pr_id: int = Field(description="Pull request number")
    title: str = Field(description="PR title")
    description: str | None = Field(
        default=None,
        description="PR description",
    )
    author: str = Field(description="PR author username")
    source_branch: str = Field(description="Source branch name")
    target_branch: str = Field(description="Target branch name")
    repository_slug: str = Field(description="Repository name")
    owner: str = Field(description="Repository owner")
    clone_url: str | None = Field(
        default=None,
        description="Repository clone URL",
    )
    pr_url: str | None = Field(
        default=None,
        description="URL to the PR",
    )

    @classmethod
    def from_github_event(
        cls, event: dict[str, Any],
    ) -> "PRContext":
        """Create PRContext from a GitHub webhook event.

        Args:
            event: Raw GitHub webhook event payload.

        Returns:
            PRContext instance with extracted information.
        """
        pr_data = event.get("pull_request", {})
        head = pr_data.get("head", {})
        base = pr_data.get("base", {})
        repo = event.get("repository", {})
        repo_owner = repo.get("owner", {})

        return cls(
            pr_id=pr_data.get("number", 0),
            title=pr_data.get("title", ""),
            description=pr_data.get("body"),
            author=pr_data.get("user", {}).get("login", ""),
            source_branch=head.get("ref", ""),
            target_branch=base.get("ref", ""),
            repository_slug=repo.get("name", ""),
            owner=repo_owner.get("login", ""),
            clone_url=repo.get("clone_url"),
            pr_url=pr_data.get("html_url"),
        )
