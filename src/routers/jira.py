"""Jira webhook router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from config import Settings, get_settings
from logging_config import get_logger
from models.jira_event import JiraWebhookResponse
from services.jira_signature import JiraSignatureVerifier
from services.sns_publisher import SNSPublisher

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["jira"])


def get_publisher(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SNSPublisher:
    """Get SNS publisher instance.

    Args:
        settings: Application settings.

    Returns:
        Configured SNS publisher.
    """
    return SNSPublisher(settings)


def get_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JiraSignatureVerifier:
    """Get signature verifier instance.

    Args:
        settings: Application settings.

    Returns:
        Configured signature verifier.
    """
    return JiraSignatureVerifier(settings.jira_webhook_secret)


@router.post(
    "/jira",
    response_model=JiraWebhookResponse,
    status_code=status.HTTP_200_OK,
)
async def handle_jira_webhook(
    request: Request,
    publisher: Annotated[SNSPublisher, Depends(get_publisher)],
    verifier: Annotated[JiraSignatureVerifier, Depends(get_verifier)],
    x_atlassian_webhook_signature: Annotated[str | None, Header()] = None,
) -> JiraWebhookResponse:
    """Handle incoming Jira webhook events.

    Verifies the webhook signature, parses the event, and publishes
    to SNS for downstream processing.

    Args:
        request: The incoming HTTP request.
        publisher: SNS publisher service.
        verifier: Signature verifier service.
        x_atlassian_webhook_signature: Jira signature header.

    Returns:
        Response with processing status and message ID.

    Raises:
        HTTPException: If signature verification fails or publishing fails.
    """
    body = await request.body()

    if not verifier.verify(body, x_atlassian_webhook_signature or ""):
        logger.error("Jira webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    payload = await request.json()
    event_type = payload.get("webhookEvent", "unknown")

    logger.info("Received Jira event: type=%s", event_type)

    try:
        message_id = await publisher.publish_jira_event(event_type, payload)

        if message_id:
            return JiraWebhookResponse(
                status="accepted",
                message_id=message_id,
            )

        logger.error("Failed to publish Jira event to SNS")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish event",
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("Error processing Jira webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
