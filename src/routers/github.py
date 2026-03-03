"""GitHub webhook router."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from pydantic import ValidationError

from config import Settings, get_settings
from logging_config import get_logger
from models.github_event import (
    GitHubWebhookResponse,
    PRReviewRequest,
    PRReviewResponse,
)
from models.github_pull_request import GitHubPullRequest
from models.pr_review import PRContext
from services.github_api import GitHubAPIClient, GitHubAPIError
from services.github_signature import GitHubSignatureVerifier
from services.claude_code_reviewer import (
    ClaudeCodeError,
    ClaudeCodeReviewer,
)
from services.event_store import get_event_store
from services.sns_publisher import SNSPublisher

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["github"])


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
) -> GitHubSignatureVerifier:
    """Get signature verifier instance.

    Args:
        settings: Application settings.

    Returns:
        Configured signature verifier.
    """
    return GitHubSignatureVerifier(
        settings.github_webhook_secret,
    )


@router.post(
    "/github",
    response_model=GitHubWebhookResponse,
    status_code=status.HTTP_200_OK,
)
async def handle_github_webhook(
    request: Request,
    publisher: Annotated[
        SNSPublisher, Depends(get_publisher)
    ],
    verifier: Annotated[
        GitHubSignatureVerifier, Depends(get_verifier)
    ],
    x_github_event: Annotated[
        str | None, Header()
    ] = None,
    x_hub_signature_256: Annotated[
        str | None, Header()
    ] = None,
    x_github_delivery: Annotated[
        str | None, Header()
    ] = None,
) -> GitHubWebhookResponse:
    """Handle incoming GitHub webhook events.

    Verifies the webhook signature, parses the event, and
    publishes to SNS for downstream processing.

    Args:
        request: The incoming HTTP request.
        publisher: SNS publisher service.
        verifier: Signature verifier service.
        x_github_event: GitHub event type header.
        x_hub_signature_256: Webhook signature header.

    Returns:
        Response with processing status and message ID.

    Raises:
        HTTPException: On signature failure or publish error.
    """
    body = await request.body()

    if not verifier.verify(
        body, x_hub_signature_256 or ""
    ):
        logger.error(
            "GitHub webhook signature verification failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    payload = await request.json()
    payload["postComment"] = True
    event_type = (
        x_github_event
        or payload.get("action", "unknown")
    )

    logger.info(
        "Received GitHub event: type=%s, payload=%s",
        event_type,
        payload,
    )

    store = get_event_store()
    store.add(
        event_type=event_type,
        payload=payload,
        delivery_id=x_github_delivery or "",
    )

    if "pull_request" in payload:
        try:
            pull_request = (
                GitHubPullRequest.model_validate(
                    payload["pull_request"]
                )
            )
            logger.info(
                "Validated pull request: number=%d, title=%s",
                pull_request.number,
                pull_request.title,
            )
        except ValidationError as e:
            logger.error(
                "Invalid pull request payload: %s", str(e),
            )
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"Invalid pull request payload: {e}"
                ),
            ) from e

    try:
        message_id = await publisher.publish_github_event(
            event_type, payload,
        )

        if message_id:
            return GitHubWebhookResponse(
                status="accepted",
                message_id=message_id,
                event_type=event_type,
            )

        logger.error(
            "Failed to publish GitHub event to SNS",
        )
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Failed to publish event",
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("Error processing GitHub webhook")
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Internal server error",
        )


def get_github_api_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GitHubAPIClient:
    """Get GitHub API client instance.

    Args:
        settings: Application settings.

    Returns:
        Configured GitHub API client.
    """
    return GitHubAPIClient(
        base_url=settings.github_base_url,
        token=settings.github_token or None,
        timeout=settings.github_api_timeout,
    )


def get_claude_reviewer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClaudeCodeReviewer:
    """Get Claude Code reviewer instance.

    Args:
        settings: Application settings.

    Returns:
        Configured Claude Code reviewer.
    """
    return ClaudeCodeReviewer(
        claude_code_path=(
            settings.claude_code_path or None
        ),
        timeout=settings.claude_code_timeout,
        model=settings.claude_code_model or None,
    )


@router.post(
    "/github/review",
    response_model=PRReviewResponse,
    status_code=status.HTTP_200_OK,
)
async def review_pull_request(
    request_body: PRReviewRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    api_client: Annotated[
        GitHubAPIClient, Depends(get_github_api_client)
    ],
    reviewer: Annotated[
        ClaudeCodeReviewer, Depends(get_claude_reviewer)
    ],
) -> PRReviewResponse:
    """Review a GitHub pull request using Claude Code.

    Fetches the PR diff from GitHub API and generates a code
    review using Claude Code CLI. Optionally posts the review
    as a PR comment.

    Args:
        request_body: PR review request with owner, repo,
            and PR number.
        settings: Application settings.
        api_client: GitHub API client.
        reviewer: Claude Code reviewer service.

    Returns:
        PRReviewResponse with review results.

    Raises:
        HTTPException: If review is disabled, API calls fail,
            or review fails.
    """
    if not settings.code_review_enabled:
        logger.warning(
            "Code review requested but feature is disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Code review feature is disabled",
        )

    if not settings.github_base_url:
        logger.error("GitHub base URL not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub API not configured",
        )

    logger.info(
        "Starting PR review: owner=%s, repo=%s, pr=%d",
        request_body.owner,
        request_body.repo,
        request_body.pr_number,
    )

    try:
        diff = await api_client.get_pr_diff(
            owner=request_body.owner,
            repo=request_body.repo,
            pr_number=request_body.pr_number,
        )
    except GitHubAPIError as e:
        logger.error(
            "Failed to fetch PR diff: owner=%s, "
            "repo=%s, pr=%d, error=%s",
            request_body.owner,
            request_body.repo,
            request_body.pr_number,
            str(e),
        )
        status_code = (
            e.status_code
            if e.status_code
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to fetch PR diff: {e}",
        ) from e

    pr_context = PRContext(
        pr_id=request_body.pr_number,
        title=f"PR-{request_body.pr_number}",
        author="",
        source_branch="",
        target_branch="",
        repository_slug=request_body.repo,
        owner=request_body.owner,
    )

    try:
        review_result = await reviewer.review_diff(
            context=pr_context,
            diff=diff,
            custom_prompt=request_body.custom_prompt,
        )
    except ClaudeCodeError as e:
        logger.error(
            "Claude Code review failed: pr=%d, error=%s",
            request_body.pr_number,
            str(e),
        )
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=f"Code review failed: {e}",
        ) from e

    review_markdown = reviewer.format_review_as_markdown(
        review_result,
    )
    comment_posted = False

    if request_body.post_comment:
        try:
            await api_client.post_pr_comment(
                owner=request_body.owner,
                repo=request_body.repo,
                pr_number=request_body.pr_number,
                comment_text=review_markdown,
            )
            comment_posted = True
            logger.info(
                "Posted review comment: pr=%d",
                request_body.pr_number,
            )
        except GitHubAPIError as e:
            logger.error(
                "Failed to post review comment: "
                "pr=%d, error=%s",
                request_body.pr_number,
                str(e),
            )

    logger.info(
        "PR review completed: pr=%d, files=%d, "
        "comments=%d, approved=%s",
        request_body.pr_number,
        review_result.files_reviewed,
        len(review_result.comments),
        review_result.approval_recommendation,
    )

    return PRReviewResponse(
        status="completed",
        pr_number=review_result.pr_id,
        repository=review_result.repository,
        owner=review_result.project,
        summary=review_result.summary,
        files_reviewed=review_result.files_reviewed,
        approval_recommendation=(
            review_result.approval_recommendation
        ),
        comment_count=len(review_result.comments),
        comment_posted=comment_posted,
        review_markdown=review_markdown,
    )
