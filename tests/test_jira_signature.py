"""Tests for Jira signature verification service."""

import hashlib
import hmac
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.jira_signature import JiraSignatureVerifier


@pytest.fixture
def verifier() -> JiraSignatureVerifier:
    """Create signature verifier with test secret."""
    return JiraSignatureVerifier("test-secret")


@pytest.fixture
def test_payload() -> bytes:
    """Create test payload bytes."""
    return b'{"webhookEvent": "jira:issue_created"}'


def create_valid_signature(payload: bytes, secret: str) -> str:
    """Create valid HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_verify_accepts_valid_signature(
    verifier: JiraSignatureVerifier,
    test_payload: bytes,
) -> None:
    """Test verifier accepts valid signature."""
    signature = create_valid_signature(test_payload, "test-secret")

    result = verifier.verify(test_payload, signature)

    assert result is True


def test_verify_accepts_signature_with_prefix(
    verifier: JiraSignatureVerifier,
    test_payload: bytes,
) -> None:
    """Test verifier accepts signature with sha256= prefix."""
    signature = create_valid_signature(test_payload, "test-secret")
    prefixed = f"sha256={signature}"

    result = verifier.verify(test_payload, prefixed)

    assert result is True


def test_verify_rejects_invalid_signature(
    verifier: JiraSignatureVerifier,
    test_payload: bytes,
) -> None:
    """Test verifier rejects invalid signature."""
    result = verifier.verify(test_payload, "invalid-signature")

    assert result is False


def test_verify_rejects_empty_signature(
    verifier: JiraSignatureVerifier,
    test_payload: bytes,
) -> None:
    """Test verifier rejects empty signature."""
    result = verifier.verify(test_payload, "")

    assert result is False


def test_verify_rejects_wrong_secret(
    verifier: JiraSignatureVerifier,
    test_payload: bytes,
) -> None:
    """Test verifier rejects signature from wrong secret."""
    signature = create_valid_signature(test_payload, "wrong-secret")

    result = verifier.verify(test_payload, signature)

    assert result is False


def test_verify_rejects_modified_payload(
    verifier: JiraSignatureVerifier,
) -> None:
    """Test verifier rejects signature for modified payload."""
    original = b'{"webhookEvent": "jira:issue_created"}'
    modified = b'{"webhookEvent": "jira:issue_deleted"}'
    signature = create_valid_signature(original, "test-secret")

    result = verifier.verify(modified, signature)

    assert result is False
