"""Tests for GitHub API client error handling."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.github_api import GitHubAPIClient, GitHubAPIError


class TestGitHubAPIClientRequestErrors:
    """Tests for request error handling in GitHubAPIClient."""

    @pytest.fixture
    def client(self) -> GitHubAPIClient:
        """Create test client."""
        return GitHubAPIClient(
            base_url="https://api.github.com",
            token="ghp_test_token",
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_get_pr_files_request_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test get_pr_files handles request errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError(
                    "Connection failed",
                )
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_files("org", "repo", 1)

            assert "Request error" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_pr_files_http_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test get_pr_files handles HTTP errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )

            mock_response = MagicMock()
            mock_response.status_code = 404

            def raise_for_status():
                raise httpx.HTTPStatusError(
                    "Not found",
                    request=httpx.Request(
                        "GET", "http://test",
                    ),
                    response=httpx.Response(404),
                )

            mock_response.raise_for_status = (
                raise_for_status
            )
            mock_client.get = AsyncMock(
                return_value=mock_response,
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_files("org", "repo", 1)

            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pr_commits_request_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test get_pr_commits handles request errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError("Timeout"),
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_commits(
                    "org", "repo", 1,
                )

            assert "Request error" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_pr_commits_http_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test get_pr_commits handles HTTP errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )

            mock_response = MagicMock()
            mock_response.status_code = 403

            def raise_for_status():
                raise httpx.HTTPStatusError(
                    "Forbidden",
                    request=httpx.Request(
                        "GET", "http://test",
                    ),
                    response=httpx.Response(403),
                )

            mock_response.raise_for_status = (
                raise_for_status
            )
            mock_client.get = AsyncMock(
                return_value=mock_response,
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_commits(
                    "org", "repo", 1,
                )

            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_post_pr_comment_request_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test post_pr_comment handles request errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )
            mock_client.post = AsyncMock(
                side_effect=httpx.RequestError(
                    "Network error",
                )
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.post_pr_comment(
                    "org", "repo", 1, "Comment",
                )

            assert "Request error" in str(exc.value)

    @pytest.mark.asyncio
    async def test_post_pr_comment_http_error(
        self, client: GitHubAPIClient,
    ) -> None:
        """Test post_pr_comment handles HTTP errors."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(
                return_value=None,
            )

            mock_response = MagicMock()
            mock_response.status_code = 401

            def raise_for_status():
                raise httpx.HTTPStatusError(
                    "Unauthorized",
                    request=httpx.Request(
                        "POST", "http://test",
                    ),
                    response=httpx.Response(401),
                )

            mock_response.raise_for_status = (
                raise_for_status
            )
            mock_client.post = AsyncMock(
                return_value=mock_response,
            )
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.post_pr_comment(
                    "org", "repo", 1, "Comment",
                )

            assert exc.value.status_code == 401
