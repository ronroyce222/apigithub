"""Tests for webhook endpoint error handling."""

import hashlib
import hmac
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def create_signature(payload: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for testing."""
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


class TestGitHubWebhookErrors:
    """Tests for GitHub webhook error handling."""

    @pytest.mark.asyncio
    async def test_github_webhook_publish_returns_none(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook returns 500 when publish returns None."""
        payload = {"action": "opened"}
        body = json.dumps(payload).encode("utf-8")
        signature = create_signature(body, github_secret)

        with patch(
            "routers.github.SNSPublisher"
        ) as mock_publisher_class:
            mock_publisher = AsyncMock()
            mock_publisher.publish_github_event = AsyncMock(
                return_value=None
            )
            mock_publisher_class.return_value = mock_publisher

            response = await async_client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": signature,
                },
            )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_github_webhook_publish_exception(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook returns 500 when publish raises."""
        payload = {"action": "opened"}
        body = json.dumps(payload).encode("utf-8")
        signature = create_signature(body, github_secret)

        with patch(
            "routers.github.SNSPublisher"
        ) as mock_publisher_class:
            mock_publisher = AsyncMock()
            mock_publisher.publish_github_event = AsyncMock(
                side_effect=RuntimeError("Unexpected error")
            )
            mock_publisher_class.return_value = mock_publisher

            response = await async_client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": signature,
                },
            )

        assert response.status_code == 500


