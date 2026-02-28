"""Tests for PR code review endpoint."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from httpx import ASGITransport, AsyncClient

from config import get_settings
from main import app
from models.github_event import PRReviewRequest, PRReviewResponse
from models.pr_review import (
    CodeReviewResult,
    ReviewComment,
    ReviewSeverity,
)
from routers.github import (
    get_github_api_client,
    get_claude_reviewer,
)
from services.github_api import GitHubAPIClient, GitHubAPIError
from services.claude_code_reviewer import ClaudeCodeError, ClaudeCodeReviewer


@pytest.fixture
def mock_settings_review_enabled():
    """Create mock settings with code review enabled."""
    settings = MagicMock()
    settings.github_base_url = "https://api.github.com"
    settings.github_token = "ghp_test_token"
    settings.github_api_timeout = 30.0
    settings.claude_code_path = "/usr/bin/claude"
    settings.claude_code_model = "claude-sonnet-4-20250514"
    settings.claude_code_timeout = 300.0
    settings.code_review_enabled = True
    return settings


@pytest.fixture
def mock_settings_review_disabled():
    """Create mock settings with code review disabled."""
    settings = MagicMock()
    settings.github_base_url = "https://api.github.com"
    settings.github_token = "ghp_test_token"
    settings.github_api_timeout = 30.0
    settings.claude_code_path = "/usr/bin/claude"
    settings.claude_code_model = ""
    settings.claude_code_timeout = 300.0
    settings.code_review_enabled = False
    return settings


@pytest.fixture
def mock_settings_no_github_url():
    """Create mock settings without GitHub URL."""
    settings = MagicMock()
    settings.github_base_url = ""
    settings.github_token = ""
    settings.github_api_timeout = 30.0
    settings.claude_code_path = "/usr/bin/claude"
    settings.claude_code_model = ""
    settings.claude_code_timeout = 300.0
    settings.code_review_enabled = True
    return settings


@pytest.fixture
def sample_diff():
    """Sample diff content for testing."""
    return """diff --git a/src/example.py b/src/example.py
index abc123..def456 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,5 +1,7 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
+
+def goodbye():
+    print("Goodbye!")
"""


@pytest.fixture
def sample_review_result():
    """Sample code review result."""
    return CodeReviewResult(
        pr_id=123,
        repository="test-repo",
        project="org",
        review_timestamp=datetime.now(timezone.utc),
        summary="Code looks good with minor improvements needed.",
        comments=[
            ReviewComment(
                file_path="src/example.py",
                line_number=5,
                severity=ReviewSeverity.INFO,
                message="Consider adding a docstring.",
                suggestion="Add a descriptive docstring.",
            ),
        ],
        files_reviewed=1,
        approval_recommendation=True,
        raw_review="Raw review content",
    )


@pytest.fixture
def pr_review_request():
    """Sample PR review request."""
    return {
        "owner": "org",
        "repo": "test-repo",
        "pr_number": 123,
        "post_comment": False,
    }


class TestPRReviewRequest:
    """Tests for PRReviewRequest model."""

    def test_valid_request(self):
        """Test creating valid PR review request."""
        request = PRReviewRequest(
            owner="org",
            repo="test-repo",
            pr_number=123,
        )
        assert request.owner == "org"
        assert request.repo == "test-repo"
        assert request.pr_number == 123
        assert request.post_comment is False
        assert request.custom_prompt is None

    def test_request_with_custom_prompt(self):
        """Test PR review request with custom prompt."""
        request = PRReviewRequest(
            owner="org",
            repo="test-repo",
            pr_number=456,
            post_comment=True,
            custom_prompt="Focus on security issues.",
        )
        assert request.post_comment is True
        assert request.custom_prompt == "Focus on security issues."


class TestPRReviewResponse:
    """Tests for PRReviewResponse model."""

    def test_valid_response(self):
        """Test creating valid PR review response."""
        response = PRReviewResponse(
            status="completed",
            pr_number=123,
            repository="test-repo",
            owner="org",
            summary="Code review complete.",
            files_reviewed=5,
            approval_recommendation=True,
            comment_count=3,
        )
        assert response.status == "completed"
        assert response.pr_number == 123
        assert response.files_reviewed == 5
        assert response.approval_recommendation is True


class TestReviewPullRequestEndpoint:
    """Tests for the review pull request endpoint."""

    @pytest.mark.asyncio
    async def test_review_pr_success(
        self,
        mock_settings_review_enabled,
        sample_diff,
        sample_review_result,
        pr_review_request,
    ):
        """Test successful PR review."""
        mock_api_client = AsyncMock(spec=GitHubAPIClient)
        mock_api_client.get_pr_diff.return_value = sample_diff

        mock_claude_reviewer = MagicMock(spec=ClaudeCodeReviewer)
        mock_claude_reviewer.review_diff = AsyncMock(
            return_value=sample_review_result
        )
        mock_claude_reviewer.format_review_as_markdown.return_value = (
            "## Code Review\nLooks good!"
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api_client
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_claude_reviewer
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=pr_review_request,
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "completed"
            assert data["pr_number"] == 123
            assert data["files_reviewed"] == 1
            assert data["approval_recommendation"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_disabled(
        self,
        mock_settings_review_disabled,
        pr_review_request,
    ):
        """Test PR review when feature is disabled."""
        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_disabled
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=pr_review_request,
                )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "disabled" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_no_github_url(
        self,
        mock_settings_no_github_url,
        pr_review_request,
    ):
        """Test PR review when GitHub URL not configured."""
        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_no_github_url
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=pr_review_request,
                )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "not configured" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_github_api_error(
        self,
        mock_settings_review_enabled,
        pr_review_request,
    ):
        """Test PR review when GitHub API fails."""
        mock_api_client = AsyncMock(spec=GitHubAPIClient)
        mock_api_client.get_pr_diff.side_effect = GitHubAPIError(
            "Not found",
            status_code=404,
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api_client
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=pr_review_request,
                )

            assert response.status_code == 404
            assert "Failed to fetch PR diff" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_claude_error(
        self,
        mock_settings_review_enabled,
        sample_diff,
        pr_review_request,
    ):
        """Test PR review when Claude Code fails."""
        mock_api_client = AsyncMock(spec=GitHubAPIClient)
        mock_api_client.get_pr_diff.return_value = sample_diff

        mock_claude_reviewer = MagicMock(spec=ClaudeCodeReviewer)
        mock_claude_reviewer.review_diff = AsyncMock(
            side_effect=ClaudeCodeError("Timeout")
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api_client
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_claude_reviewer
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=pr_review_request,
                )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Code review failed" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_with_comment_post(
        self,
        mock_settings_review_enabled,
        sample_diff,
        sample_review_result,
    ):
        """Test PR review with comment posting enabled."""
        request_with_comment = {
            "owner": "org",
            "repo": "test-repo",
            "pr_number": 123,
            "post_comment": True,
        }

        mock_api_client = AsyncMock(spec=GitHubAPIClient)
        mock_api_client.get_pr_diff.return_value = sample_diff
        mock_api_client.post_pr_comment.return_value = {"id": 456}

        mock_claude_reviewer = MagicMock(spec=ClaudeCodeReviewer)
        mock_claude_reviewer.review_diff = AsyncMock(
            return_value=sample_review_result
        )
        mock_claude_reviewer.format_review_as_markdown.return_value = (
            "## Code Review\nLooks good!"
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api_client
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_claude_reviewer
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=request_with_comment,
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["comment_posted"] is True
            mock_api_client.post_pr_comment.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_review_pr_comment_post_failure(
        self,
        mock_settings_review_enabled,
        sample_diff,
        sample_review_result,
    ):
        """Test PR review continues when comment posting fails."""
        request_with_comment = {
            "owner": "org",
            "repo": "test-repo",
            "pr_number": 123,
            "post_comment": True,
        }

        mock_api_client = AsyncMock(spec=GitHubAPIClient)
        mock_api_client.get_pr_diff.return_value = sample_diff
        mock_api_client.post_pr_comment.side_effect = GitHubAPIError(
            "Forbidden",
            status_code=403,
        )

        mock_claude_reviewer = MagicMock(spec=ClaudeCodeReviewer)
        mock_claude_reviewer.review_diff = AsyncMock(
            return_value=sample_review_result
        )
        mock_claude_reviewer.format_review_as_markdown.return_value = (
            "## Code Review\nLooks good!"
        )

        app.dependency_overrides[get_settings] = (
            lambda: mock_settings_review_enabled
        )
        app.dependency_overrides[get_github_api_client] = (
            lambda: mock_api_client
        )
        app.dependency_overrides[get_claude_reviewer] = (
            lambda: mock_claude_reviewer
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhooks/github/review",
                    json=request_with_comment,
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["comment_posted"] is False
        finally:
            app.dependency_overrides.clear()
