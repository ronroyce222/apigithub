"""SNS publisher service with async support and retry logic."""

import asyncio
import json
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from config import Settings
from logging_config import get_logger

logger = get_logger(__name__)


class SNSPublisher:
    """Async SNS publisher with exponential backoff retry.

    Publishes webhook events to SNS topics using aioboto3 for async
    operations. Uses IAM roles for authentication (no credentials).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the publisher with application settings.

        Args:
            settings: Application settings containing AWS configuration.
        """
        self._settings = settings
        self._session = aioboto3.Session()
        self._max_retries = 3
        self._base_delay = 0.5

    async def _get_client_config(self) -> dict[str, Any]:
        """Get the boto3 client configuration.

        Returns:
            Dictionary of client configuration options.
        """
        config: dict[str, Any] = {
            "region_name": self._settings.aws_region,
        }

        if (
            self._settings.use_localstack
            and self._settings.localstack_endpoint
        ):
            config["endpoint_url"] = self._settings.localstack_endpoint

        return config

    async def _publish_with_retry(
        self,
        topic_arn: str,
        message: str,
        attributes: dict[str, Any],
    ) -> str | None:
        """Publish message to SNS with exponential backoff retry.

        Args:
            topic_arn: The SNS topic ARN to publish to.
            message: The message body as JSON string.
            attributes: Message attributes for filtering.

        Returns:
            The message ID if successful, None otherwise.
        """
        client_config = await self._get_client_config()

        for attempt in range(self._max_retries):
            try:
                async with self._session.client(
                    "sns",
                    **client_config,
                ) as sns_client:
                    response = await sns_client.publish(
                        TopicArn=topic_arn,
                        Message=message,
                        MessageAttributes=attributes,
                    )
                    message_id = response.get("MessageId")
                    logger.info(
                        "Published message to SNS: topic=%s, message_id=%s, message=%s",
                        topic_arn,
                        message_id,
                        message,
                    )
                    return message_id

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                logger.error(
                    "SNS publish failed: topic=%s, error=%s, attempt=%d",
                    topic_arn,
                    error_code,
                    attempt + 1,
                )

                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        return None

    async def publish_github_event(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str | None:
        """Publish a GitHub webhook event to SNS.

        Args:
            event_type: The GitHub event type (e.g., pull_request).
            payload: The webhook payload as a dictionary.

        Returns:
            The SNS message ID if successful, None otherwise.
        """
        message = json.dumps(payload)
        attributes = {
            "source": {
                "DataType": "String",
                "StringValue": "github",
            },
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            },
        }

        return await self._publish_with_retry(
            self._settings.github_sns_topic_arn,
            message,
            attributes,
        )

