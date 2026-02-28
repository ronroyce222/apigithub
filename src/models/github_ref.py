"""GitHub git reference model for webhook payloads."""

from pydantic import BaseModel, Field

from models.github_repository import GitHubRepository


class GitHubRef(BaseModel):
    """GitHub git reference (branch/tag) in PR payloads.

    Attributes:
        ref: Branch or tag name.
        sha: Commit SHA at the tip of the ref.
        repo: Repository containing this ref.
    """

    ref: str = Field(..., description="Branch or tag name")
    sha: str = Field(
        ...,
        description="Commit SHA at the tip of the ref",
    )
    repo: GitHubRepository | None = Field(
        default=None,
        description="Repository containing this ref",
    )
