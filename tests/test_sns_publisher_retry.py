"""Tests for SNS publisher retry logic."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Settings
from services.sns_publisher import SNSPublisher


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        aws_region="us-east-1",
        github_sns_topic_arn="arn:aws:sns:us-east-1:123:github",
        jira_sns_topic_arn="arn:aws:sns:us-east-1:123:jira",
        github_webhook_secret="test-secret",
        jira_webhook_secret="test-secret",
        use_localstack=False,
    )


@pytest.fixture
def settings_no_localstack() -> Settings:
    """Create test settings without localstack."""
    return Settings(
        aws_region="us-west-2",
        github_sns_topic_arn="arn:aws:sns:us-west-2:123:github",
        jira_sns_topic_arn="arn:aws:sns:us-west-2:123:jira",
        github_webhook_secret="secret",
        jira_webhook_secret="secret",
        use_localstack=False,
    )


@pytest.mark.asyncio
async def test_get_client_config_without_localstack(
    settings_no_localstack: Settings,
) -> None:
    """Test client config without LocalStack."""
    publisher = SNSPublisher(settings_no_localstack)
    config = await publisher._get_client_config()

    assert config["region_name"] == "us-west-2"
    assert "endpoint_url" not in config


@pytest.mark.asyncio
async def test_publish_with_retry_success_first_attempt(
    settings: Settings,
) -> None:
    """Test successful publish on first attempt."""
    publisher = SNSPublisher(settings)

    mock_sns = AsyncMock()
    mock_sns.publish = AsyncMock(return_value={"MessageId": "msg-123"})

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_sns)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        publisher._session,
        "client",
        return_value=mock_context,
    ):
        result = await publisher.publish_github_event(
            "pull_request",
            {"test": "data"},
        )

    assert result == "msg-123"
    assert mock_sns.publish.call_count == 1


@pytest.mark.asyncio
async def test_publish_with_retry_on_client_error(
    settings: Settings,
) -> None:
    """Test retry logic when ClientError occurs."""
    publisher = SNSPublisher(settings)
    publisher._base_delay = 0.01  # Speed up test

    mock_sns = AsyncMock()
    error_response = {"Error": {"Code": "ServiceUnavailable"}}
    mock_sns.publish = AsyncMock(
        side_effect=[
            ClientError(error_response, "Publish"),
            {"MessageId": "msg-after-retry"},
        ]
    )

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_sns)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        publisher._session,
        "client",
        return_value=mock_context,
    ):
        result = await publisher.publish_github_event(
            "pull_request",
            {"data": "value"},
        )

    assert result == "msg-after-retry"
    assert mock_sns.publish.call_count == 2


@pytest.mark.asyncio
async def test_publish_with_retry_max_retries_exceeded(
    settings: Settings,
) -> None:
    """Test that ClientError is raised after max retries."""
    publisher = SNSPublisher(settings)
    publisher._base_delay = 0.01  # Speed up test
    publisher._max_retries = 2

    mock_sns = AsyncMock()
    error_response = {"Error": {"Code": "InternalError"}}
    mock_sns.publish = AsyncMock(
        side_effect=ClientError(error_response, "Publish")
    )

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_sns)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        publisher._session,
        "client",
        return_value=mock_context,
    ):
        with pytest.raises(ClientError):
            await publisher.publish_github_event(
                "pull_request",
                {"data": "value"},
            )

    assert mock_sns.publish.call_count == 2


@pytest.mark.asyncio
async def test_publish_jira_with_retry(settings: Settings) -> None:
    """Test Jira publish with retry logic."""
    publisher = SNSPublisher(settings)
    publisher._base_delay = 0.01

    mock_sns = AsyncMock()
    error_response = {"Error": {"Code": "Throttling"}}
    mock_sns.publish = AsyncMock(
        side_effect=[
            ClientError(error_response, "Publish"),
            {"MessageId": "jira-msg-123"},
        ]
    )

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_sns)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        publisher._session,
        "client",
        return_value=mock_context,
    ):
        result = await publisher.publish_jira_event(
            "jira:issue_created",
            {"issue": {"key": "TEST-1"}},
        )

    assert result == "jira-msg-123"
    assert mock_sns.publish.call_count == 2


@pytest.mark.asyncio
async def test_publisher_init(settings: Settings) -> None:
    """Test SNSPublisher initialization."""
    publisher = SNSPublisher(settings)
    assert publisher._settings == settings
    assert publisher._max_retries == 3
    assert publisher._base_delay == 0.5
