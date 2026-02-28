"""GitHub user model for webhook payloads."""

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user representation in webhook payloads.

    Attributes:
        login: GitHub username.
        id: Unique user identifier.
        avatar_url: URL to the user's avatar image.
        type: User type (e.g., User, Bot, Organization).
    """

    login: str = Field(..., description="GitHub username")
    id: int = Field(..., description="Unique user identifier")
    avatar_url: str | None = Field(
        default=None,
        description="URL to the user's avatar image",
    )
    type: str = Field(
        default="User",
        description="User type (e.g., User, Bot)",
    )
