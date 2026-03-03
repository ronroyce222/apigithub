"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All configuration is loaded from environment variables for secure
    handling of secrets and flexible deployment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for SNS",
    )
    github_sns_topic_arn: str = Field(
        ...,
        description="SNS topic ARN for GitHub events",
    )
    github_sqs_queue_url: str = Field(
        default="",
        description="SQS queue URL for GitHub events",
    )
    github_webhook_secret: str = Field(
        ...,
        description="Secret for GitHub webhook signature verification",
    )
    localstack_endpoint: Optional[str] = Field(
        default=None,
        description="LocalStack endpoint URL for testing",
    )
    use_localstack: bool = Field(
        default=False,
        description="Use LocalStack instead of real AWS",
    )

    # GitHub API settings for PR code review
    github_base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL",
    )
    github_token: str = Field(
        default="",
        description="GitHub personal access token for authentication",
    )
    github_api_timeout: float = Field(
        default=30.0,
        description="Timeout for GitHub API requests in seconds",
    )

    # Claude Code settings
    claude_code_path: str = Field(
        default="",
        description="Path to Claude Code CLI executable",
    )
    claude_code_model: str = Field(
        default="",
        description="Claude model to use for code reviews",
    )
    claude_code_timeout: float = Field(
        default=300.0,
        description="Timeout for Claude Code execution in seconds",
    )
    code_review_enabled: bool = Field(
        default=True,
        description="Enable PR code review functionality",
    )

    # SSL settings
    ssl_certfile: Optional[str] = Field(
        default=None,
        description="Path to SSL certificate file",
    )
    ssl_keyfile: Optional[str] = Field(
        default=None,
        description="Path to SSL private key file",
    )

    # Event store settings
    event_store_max_size: int = Field(
        default=100,
        description="Max events to retain in memory",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Singleton Settings instance loaded from environment.
    """
    return Settings()
