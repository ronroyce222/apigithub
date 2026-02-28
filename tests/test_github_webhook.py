"""Tests for GitHub webhook endpoint."""

import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient


def create_signature(payload: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for testing."""
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


@pytest.mark.asyncio
async def test_github_webhook_accepts_valid_signature(
    async_client: AsyncClient,
    github_secret: str,
) -> None:
    """Test GitHub webhook accepts valid signature."""
    payload = {
        "action": "opened",
        "sender": {"login": "test-user"},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, github_secret)

    response = await async_client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_github_webhook_returns_message_id(
    async_client: AsyncClient,
    github_secret: str,
) -> None:
    """Test GitHub webhook returns SNS message ID."""
    payload = {"action": "opened"}
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, github_secret)

    response = await async_client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
        },
    )

    data = response.json()
    assert data["status"] == "accepted"
    assert data["message_id"] is not None


@pytest.mark.asyncio
async def test_github_webhook_rejects_invalid_signature(
    async_client: AsyncClient,
) -> None:
    """Test GitHub webhook rejects invalid signature."""
    payload = {"action": "opened"}
    body = json.dumps(payload).encode("utf-8")

    response = await async_client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_rejects_missing_signature(
    async_client: AsyncClient,
) -> None:
    """Test GitHub webhook rejects missing signature."""
    payload = {"action": "opened"}
    body = json.dumps(payload).encode("utf-8")

    response = await async_client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_uses_event_header(
    async_client: AsyncClient,
    github_secret: str,
) -> None:
    """Test GitHub webhook uses X-GitHub-Event header."""
    payload = {"sender": {"login": "test-user"}}
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, github_secret)

    response = await async_client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 200
