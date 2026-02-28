"""Tests for Jira webhook endpoint."""

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
async def test_jira_webhook_accepts_valid_signature(
    async_client: AsyncClient,
    jira_secret: str,
) -> None:
    """Test Jira webhook accepts valid signature."""
    payload = {"webhookEvent": "jira:issue_created", "issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, jira_secret)

    response = await async_client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Atlassian-Webhook-Signature": signature,
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_jira_webhook_returns_message_id(
    async_client: AsyncClient,
    jira_secret: str,
) -> None:
    """Test Jira webhook returns SNS message ID."""
    payload = {"webhookEvent": "jira:issue_updated"}
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, jira_secret)

    response = await async_client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Atlassian-Webhook-Signature": signature,
        },
    )

    data = response.json()
    assert data["status"] == "accepted"
    assert data["message_id"] is not None


@pytest.mark.asyncio
async def test_jira_webhook_rejects_invalid_signature(
    async_client: AsyncClient,
) -> None:
    """Test Jira webhook rejects invalid signature."""
    payload = {"webhookEvent": "jira:issue_created"}
    body = json.dumps(payload).encode("utf-8")

    response = await async_client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Atlassian-Webhook-Signature": "sha256=invalid",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jira_webhook_rejects_missing_signature(
    async_client: AsyncClient,
) -> None:
    """Test Jira webhook rejects missing signature."""
    payload = {"webhookEvent": "jira:issue_created"}
    body = json.dumps(payload).encode("utf-8")

    response = await async_client.post(
        "/webhooks/jira",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jira_webhook_extracts_event_type_from_payload(
    async_client: AsyncClient,
    jira_secret: str,
) -> None:
    """Test Jira webhook extracts event type from payload."""
    payload = {
        "webhookEvent": "jira:issue_deleted",
        "issue": {"key": "TEST-2"},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body, jira_secret)

    response = await async_client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Atlassian-Webhook-Signature": signature,
        },
    )

    assert response.status_code == 200
