"""Tests for GitHub API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from services.github_api import GitHubAPIClient, GitHubAPIError


class TestGitHubAPIClient:
    """Tests for GitHubAPIClient."""

    def test_init_with_token(self):
        """Test client initialization with token."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
            token="ghp_test123",
            timeout=60.0,
        )
        assert client.base_url == "https://api.github.com"
        assert client.token == "ghp_test123"
        assert client.timeout == 60.0

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped."""
        client = GitHubAPIClient(
            base_url="https://api.github.com/",
        )
        assert client.base_url == "https://api.github.com"

    def test_get_headers_with_token(self):
        """Test headers include Bearer auth with token."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
            token="ghp_test123",
        )
        headers = client._get_headers()
        assert headers["Authorization"] == (
            "Bearer ghp_test123"
        )
        assert "Accept" in headers

    def test_get_headers_without_token(self):
        """Test headers without token have no auth."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
        )
        headers = client._get_headers()
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_get_pr_diff_success(self):
        """Test successful PR diff fetch."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
            token="ghp_test123",
        )

        mock_response = MagicMock()
        mock_response.text = "diff content"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            result = await client.get_pr_diff(
                owner="org",
                repo="test-repo",
                pr_number=123,
            )

            assert result == "diff content"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pr_diff_http_error(self):
        """Test PR diff fetch with HTTP error."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_response.raise_for_status.side_effect = (
                http_error
            )
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_diff(
                    owner="org",
                    repo="test-repo",
                    pr_number=999,
                )

            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pr_files_success(self):
        """Test successful PR files fetch."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"filename": "file1.py", "status": "modified"},
            {"filename": "file2.py", "status": "added"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            result = await client.get_pr_files(
                owner="org",
                repo="test-repo",
                pr_number=123,
            )

            assert len(result) == 2
            assert result[0]["filename"] == "file1.py"

    @pytest.mark.asyncio
    async def test_get_pr_commits_success(self):
        """Test successful PR commits fetch."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"sha": "abc123", "commit": {"message": "First"}},
            {"sha": "def456", "commit": {"message": "Second"}},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            result = await client.get_pr_commits(
                owner="org",
                repo="test-repo",
                pr_number=123,
            )

            assert len(result) == 2
            assert result[0]["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_post_pr_comment_success(self):
        """Test successful PR comment post."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
            token="ghp_test123",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 456,
            "body": "Test comment",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            result = await client.post_pr_comment(
                owner="org",
                repo="test-repo",
                pr_number=123,
                comment_text="Test comment",
            )

            assert result["id"] == 456
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test handling of request errors."""
        client = GitHubAPIClient(
            base_url="https://api.github.com",
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = (
                httpx.RequestError("Connection failed")
            )
            mock_client.__aenter__.return_value = (
                mock_client
            )
            mock_client.__aexit__.return_value = None
            mock_cls.return_value = mock_client

            with pytest.raises(GitHubAPIError) as exc:
                await client.get_pr_diff(
                    owner="org",
                    repo="test-repo",
                    pr_number=123,
                )

            assert "Request error" in str(exc.value)


class TestGitHubAPIError:
    """Tests for GitHubAPIError exception."""

    def test_error_with_status_code(self):
        """Test error with status code."""
        error = GitHubAPIError(
            "Not found", status_code=404,
        )
        assert str(error) == "Not found"
        assert error.status_code == 404

    def test_error_without_status_code(self):
        """Test error without status code."""
        error = GitHubAPIError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.status_code is None
