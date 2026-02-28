"""Tests for SNS publisher service."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Settings
from services.sns_publisher import SNSPublisher


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        aws_region="us-east-1",
        github_sns_topic_arn="arn:aws:sns:us-east-1:123:github",
        github_webhook_secret="test-secret",
        use_localstack=True,
        localstack_endpoint="http://localhost:4566",
    )


@pytest.fixture
def mock_sns() -> AsyncMock:
    """Create mock SNS client."""
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(
        return_value={"MessageId": "test-message-123"}
    )
    return mock_client


@pytest.mark.asyncio
async def test_publish_github_event_returns_message_id(
    settings: Settings,
    mock_sns: AsyncMock,
) -> None:
    """Test publishing GitHub event returns message ID."""
    publisher = SNSPublisher(settings)

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
            {"test": "payload"},
        )

    assert result == "test-message-123"


@pytest.mark.asyncio
async def test_publish_github_event_includes_attributes(
    settings: Settings,
    mock_sns: AsyncMock,
) -> None:
    """Test GitHub event includes correct message attributes."""
    publisher = SNSPublisher(settings)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_sns)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        publisher._session,
        "client",
        return_value=mock_context,
    ):
        await publisher.publish_github_event(
            "pull_request", {"test": "data"},
        )

    call_kwargs = mock_sns.publish.call_args.kwargs
    assert call_kwargs["MessageAttributes"]["source"]["StringValue"] == \
        "github"
    assert call_kwargs["MessageAttributes"]["event_type"]["StringValue"] == \
        "pull_request"


@pytest.mark.asyncio
async def test_publisher_uses_localstack_endpoint(settings: Settings) -> None:
    """Test publisher uses LocalStack endpoint when configured."""
    publisher = SNSPublisher(settings)

    config = await publisher._get_client_config()

    assert config["endpoint_url"] == "http://localhost:4566"
    assert config["region_name"] == "us-east-1"
