"""GitHub webhook signature verification service."""

import hashlib
import hmac

from logging_config import get_logger

logger = get_logger(__name__)


class GitHubSignatureVerifier:
    """Verifies GitHub webhook signatures using HMAC-SHA256.

    GitHub sends a signature in the X-Hub-Signature-256 header
    computed using HMAC-SHA256 with the webhook secret.
    """

    def __init__(self, secret: str) -> None:
        """Initialize the verifier with the webhook secret.

        Args:
            secret: The shared secret configured in GitHub webhooks.
        """
        self._secret = secret.encode("utf-8")

    def verify(self, payload: bytes, signature: str) -> bool:
        """Verify the webhook signature against the payload.

        Args:
            payload: The raw request body bytes.
            signature: The signature from X-Hub-Signature-256.

        Returns:
            True if signature is valid, False otherwise.
        """
        if not signature:
            logger.warning("Missing signature header")
            return False

        if signature.startswith("sha256="):
            signature = signature[7:]

        expected = hmac.new(
            self._secret,
            payload,
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(expected, signature)

        if not is_valid:
            logger.warning("Invalid GitHub webhook signature")

        return is_valid
