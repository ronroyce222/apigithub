"""GitHub pull request model for webhook payloads."""

from pydantic import BaseModel, Field

from models.github_ref import GitHubRef
from models.github_user import GitHubUser


class GitHubPullRequest(BaseModel):
    """GitHub pull request representation in webhook payloads.

    Attributes:
        id: Unique pull request identifier.
        number: PR number within the repository.
        title: Pull request title.
        body: Pull request description body.
        state: PR state (open, closed).
        draft: Whether the PR is a draft.
        locked: Whether the PR is locked.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        head: Source branch reference.
        base: Target branch reference.
        user: The pull request author.
        html_url: URL to the pull request page.
        merged: Whether the PR has been merged.
        mergeable: Whether the PR can be merged.
    """

    id: int = Field(
        ...,
        description="Unique pull request identifier",
    )
    number: int = Field(
        ...,
        description="PR number within the repository",
    )
    title: str = Field(..., description="Pull request title")
    body: str | None = Field(
        default=None,
        description="Pull request description body",
    )
    state: str = Field(
        ...,
        description="PR state (open, closed)",
    )
    draft: bool = Field(
        default=False,
        description="Whether the PR is a draft",
    )
    locked: bool = Field(
        default=False,
        description="Whether the PR is locked",
    )
    created_at: str = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: str = Field(
        ...,
        description="Last update timestamp",
    )
    head: GitHubRef = Field(
        ...,
        description="Source branch reference",
    )
    base: GitHubRef = Field(
        ...,
        description="Target branch reference",
    )
    user: GitHubUser = Field(
        ...,
        description="The pull request author",
    )
    html_url: str | None = Field(
        default=None,
        description="URL to the pull request page",
    )
    merged: bool = Field(
        default=False,
        description="Whether the PR has been merged",
    )
    mergeable: bool | None = Field(
        default=None,
        description="Whether the PR can be merged",
    )
