"""Pytest fixtures and configuration."""

import hashlib
import hmac
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault(
    "GITHUB_SNS_TOPIC_ARN",
    "arn:aws:sns:us-east-1:000000000000:github-events",
)
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-github-secret")
os.environ.setdefault("USE_LOCALSTACK", "true")
os.environ.setdefault("LOCALSTACK_ENDPOINT", "http://localhost:4566")
os.environ.setdefault(
    "GITHUB_SQS_QUEUE_URL",
    "http://localhost:4566/000000000000/github-events-queue",
)


@pytest.fixture
def github_secret() -> str:
    """Get GitHub webhook secret for testing."""
    return os.environ["GITHUB_WEBHOOK_SECRET"]


@pytest.fixture
def mock_sns_client() -> Generator[AsyncMock, None, None]:
    """Mock SNS client for testing without LocalStack."""
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(
        return_value={"MessageId": "test-message-id-123"}
    )

    @asynccontextmanager
    async def mock_client_context(*args, **kwargs):
        yield mock_client

    mock_session = MagicMock()
    mock_session.client = mock_client_context

    with patch("services.sns_publisher.aioboto3.Session") as patched:
        patched.return_value = mock_session
        yield mock_client


@pytest.fixture
def mock_sqs_client() -> Generator[AsyncMock, None, None]:
    """Mock SQS client for testing without LocalStack."""
    mock_client = AsyncMock()
    mock_client.send_message = AsyncMock(
        return_value={"MessageId": "test-sqs-message-id-123"}
    )
    mock_client.receive_message = AsyncMock(
        return_value={
            "Messages": [
                {
                    "MessageId": "test-sqs-message-id-123",
                    "ReceiptHandle": "test-receipt-handle",
                    "Body": '{"test": "message"}',
                }
            ]
        }
    )
    mock_client.delete_message = AsyncMock(return_value={})

    @asynccontextmanager
    async def mock_sqs_client_context(*args, **kwargs):
        yield mock_client

    mock_session = MagicMock()
    mock_session.client = mock_sqs_client_context

    with patch("aioboto3.Session") as patched:
        patched.return_value = mock_session
        yield mock_client


@pytest.fixture
async def async_client(
    mock_sns_client: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with mocked SNS."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


def create_signature(payload: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for testing.

    Args:
        payload: The request body bytes.
        secret: The webhook secret.

    Returns:
        The signature prefixed with 'sha256='.
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"
