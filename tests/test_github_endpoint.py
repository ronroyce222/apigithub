"""Tests for GitHub webhook and review endpoints."""

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from models.pr_review import (
    CodeReviewResult,
    ReviewComment,
    ReviewSeverity,
)


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


class TestGitHubWebhook:
    """Tests for the /webhooks/github endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_accepts_valid_signature(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook accepts valid HMAC-SHA256 signature."""
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
        data = response.json()
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_webhook_returns_message_id(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook returns SNS message ID on success."""
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
    async def test_webhook_rejects_invalid_signature(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test webhook returns 401 for invalid signature."""
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
    async def test_webhook_rejects_missing_signature(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test webhook returns 401 when signature missing."""
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
    async def test_webhook_uses_event_from_header(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook uses X-GitHub-Event header."""
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

    @pytest.mark.asyncio
    async def test_webhook_uses_action_from_payload(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook extracts action from payload."""
        payload = {"action": "synchronize"}
        body = json.dumps(payload).encode("utf-8")
        signature = create_signature(body, github_secret)

        response = await async_client.post(
            "/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_webhook_handles_pull_request_opened(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook processes pull_request opened event."""
        payload = {
            "action": "opened",
            "sender": {
                "login": "developer",
                "id": 12345,
            },
            "pull_request": {
                "id": 1,
                "number": 123,
                "title": "Add new feature",
                "state": "open",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "head": {
                    "ref": "feature/new-feature",
                    "sha": "abc123",
                },
                "base": {"ref": "main", "sha": "def456"},
                "user": {"login": "developer", "id": 1},
            },
            "repository": {
                "id": 1,
                "name": "my-repo",
                "full_name": "org/my-repo",
                "owner": {"login": "org", "id": 1},
            },
        }
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
        data = response.json()
        assert data["status"] == "accepted"
        assert data["message_id"] is not None

    @pytest.mark.asyncio
    async def test_webhook_handles_pull_request_updated(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook processes pull_request synchronize."""
        payload = {
            "action": "synchronize",
            "sender": {"login": "developer", "id": 1},
            "pull_request": {
                "id": 2,
                "number": 456,
                "title": "Updated PR",
                "state": "open",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "head": {"ref": "feature", "sha": "aaa"},
                "base": {"ref": "main", "sha": "bbb"},
                "user": {"login": "developer", "id": 1},
            },
        }
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

    @pytest.mark.asyncio
    async def test_webhook_handles_push_event(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook processes push event."""
        payload = {
            "ref": "refs/heads/main",
            "before": "abc123",
            "after": "def456",
            "repository": {
                "id": 1,
                "name": "my-repo",
                "full_name": "org/my-repo",
                "owner": {"login": "org", "id": 1},
            },
            "sender": {"login": "developer", "id": 1},
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
    async def test_webhook_handles_minimal_payload(
        self,
        async_client: AsyncClient,
        github_secret: str,
    ) -> None:
        """Test webhook accepts minimal valid payload."""
        payload = {}
        body = json.dumps(payload).encode("utf-8")
        signature = create_signature(body, github_secret)

        response = await async_client.post(
            "/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": signature,
            },
        )

        assert response.status_code == 200


class TestGitHubReviewEndpoint:
    """Tests for the /webhooks/github/review endpoint."""

    @pytest.fixture
    def mock_review_result(self) -> CodeReviewResult:
        """Create a mock code review result."""
        return CodeReviewResult(
            pr_id=123,
            repository="my-repo",
            project="org",
            review_timestamp=datetime.now(),
            summary="Code looks good overall.",
            comments=[
                ReviewComment(
                    file_path="file.py",
                    line_number=10,
                    severity=ReviewSeverity.INFO,
                    message="Consider adding a docstring.",
                    suggestion=None,
                )
            ],
            files_reviewed=1,
            approval_recommendation=True,
            raw_review="Raw review output",
        )

    @pytest.fixture
    def mock_settings_disabled(self) -> MagicMock:
        """Create mock settings with code review disabled."""
        settings = MagicMock()
        settings.code_review_enabled = False
        settings.github_base_url = "https://api.github.com"
        settings.github_token = "ghp_test_token"
        settings.github_api_timeout = 30.0
        settings.claude_code_path = "/usr/bin/claude"
        settings.claude_code_timeout = 300.0
        settings.claude_code_model = "claude-3"
        return settings

    @pytest.fixture
    def mock_settings_no_url(self) -> MagicMock:
        """Create mock settings with no GitHub URL."""
        settings = MagicMock()
        settings.code_review_enabled = True
        settings.github_base_url = ""
        settings.github_token = ""
        settings.github_api_timeout = 30.0
        settings.claude_code_path = "/usr/bin/claude"
        settings.claude_code_timeout = 300.0
        settings.claude_code_model = "claude-3"
        return settings

    @pytest.fixture
    def mock_settings_enabled(self) -> MagicMock:
        """Create mock settings with code review enabled."""
        settings = MagicMock()
        settings.code_review_enabled = True
        settings.github_base_url = "https://api.github.com"
        settings.github_token = "ghp_test_token"
        settings.github_api_timeout = 30.0
        settings.claude_code_path = "/usr/bin/claude"
        settings.claude_code_timeout = 300.0
        settings.claude_code_model = "claude-3"
        return settings

    @pytest.mark.asyncio
    async def test_review_returns_503_when_disabled(
        self,
        mock_sns_client: AsyncMock,
        mock_settings_disabled: MagicMock,
    ) -> None:
        """Test review returns 503 when disabled."""
        from main import app
        from routers.github import get_settings

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_disabled
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                    },
                )

                assert response.status_code == 503
                detail = response.json()["detail"]
                assert "disabled" in detail.lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_returns_503_when_not_configured(
        self,
        mock_sns_client: AsyncMock,
        mock_settings_no_url: MagicMock,
    ) -> None:
        """Test review returns 503 when API not configured."""
        from main import app
        from routers.github import get_settings

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_no_url
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                    },
                )

                assert response.status_code == 503
                detail = response.json()["detail"]
                assert "not configured" in detail.lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_success(
        self,
        mock_sns_client: AsyncMock,
        mock_review_result: CodeReviewResult,
        mock_settings_enabled: MagicMock,
    ) -> None:
        """Test successful PR review."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_claude_reviewer,
            get_settings,
        )

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            return_value="diff --git a/f.py b/f.py\n+new"
        )
        mock_api.post_pr_comment = AsyncMock(
            return_value=None,
        )

        mock_reviewer = MagicMock()
        mock_reviewer.review_diff = AsyncMock(
            return_value=mock_review_result,
        )
        mock_reviewer.format_review_as_markdown = (
            MagicMock(
                return_value="## Code Review\n\nGood."
            )
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_reviewer
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["pr_number"] == 123
                assert data["repository"] == "my-repo"
                assert data["owner"] == "org"
                assert data["files_reviewed"] == 1
                assert data["approval_recommendation"] is True
                assert data["comment_count"] == 1
                assert data["comment_posted"] is False
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_with_post_comment(
        self,
        mock_sns_client: AsyncMock,
        mock_review_result: CodeReviewResult,
        mock_settings_enabled: MagicMock,
    ) -> None:
        """Test PR review with comment posting enabled."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_claude_reviewer,
            get_settings,
        )

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            return_value="diff --git a/f.py b/f.py\n+new"
        )
        mock_api.post_pr_comment = AsyncMock(
            return_value=None,
        )

        mock_reviewer = MagicMock()
        mock_reviewer.review_diff = AsyncMock(
            return_value=mock_review_result,
        )
        mock_reviewer.format_review_as_markdown = (
            MagicMock(
                return_value="## Code Review\n\nGood."
            )
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_reviewer
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                        "post_comment": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["comment_posted"] is True
                mock_api.post_pr_comment.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_with_custom_prompt(
        self,
        mock_sns_client: AsyncMock,
        mock_review_result: CodeReviewResult,
        mock_settings_enabled: MagicMock,
    ) -> None:
        """Test PR review with custom prompt."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_claude_reviewer,
            get_settings,
        )

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            return_value="diff --git a/f.py b/f.py\n+new"
        )

        mock_reviewer = MagicMock()
        mock_reviewer.review_diff = AsyncMock(
            return_value=mock_review_result,
        )
        mock_reviewer.format_review_as_markdown = (
            MagicMock(return_value="## Code Review")
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_reviewer
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                        "custom_prompt": "Focus on security",
                    },
                )

                assert response.status_code == 200
                mock_reviewer.review_diff.assert_called_once()
                call_kwargs = (
                    mock_reviewer.review_diff.call_args[1]
                )
                assert call_kwargs["custom_prompt"] == (
                    "Focus on security"
                )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_validates_required_fields(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test review validates required request fields."""
        response = await async_client.post(
            "/webhooks/github/review",
            json={"owner": "org"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_review_validates_pr_number_type(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test review validates pr_number is an integer."""
        response = await async_client.post(
            "/webhooks/github/review",
            json={
                "owner": "org",
                "repo": "my-repo",
                "pr_number": "not-an-int",
            },
        )

        assert response.status_code == 422


class TestGitHubReviewErrorHandling:
    """Tests for error handling in the review endpoint."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings with review enabled."""
        settings = MagicMock()
        settings.code_review_enabled = True
        settings.github_base_url = "https://api.github.com"
        settings.github_token = "ghp_test_token"
        settings.github_api_timeout = 30.0
        settings.claude_code_path = "/usr/bin/claude"
        settings.claude_code_timeout = 300.0
        settings.claude_code_model = "claude-3"
        return settings

    @pytest.mark.asyncio
    async def test_review_handles_github_api_error(
        self,
        mock_sns_client: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test review handles GitHub API errors."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_settings,
        )
        from services.github_api import GitHubAPIError

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            side_effect=GitHubAPIError(
                "Not found", status_code=404,
            )
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 999,
                    },
                )

                assert response.status_code == 404
                detail = response.json()["detail"]
                assert "Failed to fetch PR diff" in detail
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_handles_api_error_no_status(
        self,
        mock_sns_client: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test review returns 502 when no status code."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_settings,
        )
        from services.github_api import GitHubAPIError

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            side_effect=GitHubAPIError(
                "Connection failed", status_code=None,
            )
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                    },
                )

                assert response.status_code == 502
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_handles_claude_code_error(
        self,
        mock_sns_client: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test review handles Claude Code errors."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_claude_reviewer,
            get_settings,
        )
        from services.claude_code_reviewer import (
            ClaudeCodeError,
        )

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            return_value="diff --git a/f.py b/f.py"
        )

        mock_reviewer = MagicMock()
        mock_reviewer.review_diff = AsyncMock(
            side_effect=ClaudeCodeError("Review timed out")
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_reviewer
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                    },
                )

                assert response.status_code == 500
                detail = response.json()["detail"]
                assert "Code review failed" in detail
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_continues_on_comment_failure(
        self,
        mock_sns_client: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test review completes when comment posting fails."""
        from main import app
        from routers.github import (
            get_github_api_client,
            get_claude_reviewer,
            get_settings,
        )
        from services.github_api import GitHubAPIError

        mock_api = MagicMock()
        mock_api.get_pr_diff = AsyncMock(
            return_value="diff --git a/f.py b/f.py"
        )
        mock_api.post_pr_comment = AsyncMock(
            side_effect=GitHubAPIError(
                "Forbidden", status_code=403,
            )
        )

        mock_reviewer = MagicMock()
        mock_reviewer.review_diff = AsyncMock(
            return_value=CodeReviewResult(
                pr_id=123,
                repository="my-repo",
                project="org",
                review_timestamp=datetime.now(),
                summary="Code looks good.",
                comments=[],
                files_reviewed=1,
                approval_recommendation=True,
                raw_review="",
            )
        )
        mock_reviewer.format_review_as_markdown = (
            MagicMock(
                return_value="## Review\n\nGood."
            )
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_reviewer
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json={
                        "owner": "org",
                        "repo": "my-repo",
                        "pr_number": 123,
                        "post_comment": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["comment_posted"] is False
        finally:
            app.dependency_overrides.clear()
