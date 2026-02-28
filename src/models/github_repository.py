"""GitHub repository model for webhook payloads."""

from pydantic import BaseModel, Field

from models.github_user import GitHubUser


class GitHubRepository(BaseModel):
    """GitHub repository representation in webhook payloads.

    Attributes:
        id: Unique repository identifier.
        name: Repository name.
        full_name: Full repository name (owner/repo).
        private: Whether the repository is private.
        owner: Repository owner.
        clone_url: HTTPS clone URL.
        html_url: URL to the repository page.
    """

    id: int = Field(..., description="Unique repository identifier")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(
        ...,
        description="Full repository name (owner/repo)",
    )
    private: bool = Field(
        default=False,
        description="Whether the repository is private",
    )
    owner: GitHubUser = Field(
        ...,
        description="Repository owner",
    )
    clone_url: str | None = Field(
        default=None,
        description="HTTPS clone URL",
    )
    html_url: str | None = Field(
        default=None,
        description="URL to the repository page",
    )
