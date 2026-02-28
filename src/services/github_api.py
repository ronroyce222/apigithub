"""GitHub API client for fetching PR information."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        """Initialize GitHubAPIError.

        Args:
            message: Error message.
            status_code: HTTP status code if applicable.
        """
        super().__init__(message)
        self.status_code = status_code


class GitHubAPIClient:
    """Async client for GitHub REST API.

    Fetches PR diffs, files, commits, and posts comments
    using Bearer token authentication.
    """

    def __init__(
        self,
        base_url: str = "https://api.github.com",
        token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the GitHub API client.

        Args:
            base_url: GitHub API base URL.
            token: Personal access token for authentication.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dictionary of HTTP headers.
        """
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> str:
        """Fetch the diff for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            Unified diff string for the PR.

        Raises:
            GitHubAPIError: If the API request fails.
        """
        url = (
            f"{self.base_url}/repos/{owner}/{repo}"
            f"/pulls/{pr_number}"
        )
        headers = self._get_headers()
        headers["Accept"] = "application/vnd.github.diff"

        logger.debug(
            "Fetching PR diff: owner=%s, repo=%s, pr=%d",
            owner,
            repo,
            pr_number,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.get(
                    url, headers=headers,
                )
                response.raise_for_status()
                return response.text

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to fetch PR diff: status=%d, url=%s",
                e.response.status_code,
                url,
            )
            raise GitHubAPIError(
                f"Failed to fetch PR diff:"
                f" {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(
                "Request error fetching PR diff: %s", e,
            )
            raise GitHubAPIError(
                f"Request error: {e}",
            ) from e

    async def get_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Fetch the list of files in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of file information dictionaries.

        Raises:
            GitHubAPIError: If the API request fails.
        """
        url = (
            f"{self.base_url}/repos/{owner}/{repo}"
            f"/pulls/{pr_number}/files"
        )

        logger.debug(
            "Fetching PR files: owner=%s, repo=%s, pr=%d",
            owner,
            repo,
            pr_number,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.get(
                    url, headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to fetch PR files: status=%d, url=%s",
                e.response.status_code,
                url,
            )
            raise GitHubAPIError(
                f"Failed to fetch PR files:"
                f" {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(
                "Request error fetching PR files: %s", e,
            )
            raise GitHubAPIError(
                f"Request error: {e}",
            ) from e

    async def get_pr_commits(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Fetch the commits in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of commit information dictionaries.

        Raises:
            GitHubAPIError: If the API request fails.
        """
        url = (
            f"{self.base_url}/repos/{owner}/{repo}"
            f"/pulls/{pr_number}/commits"
        )

        logger.debug(
            "Fetching PR commits: owner=%s, repo=%s, pr=%d",
            owner,
            repo,
            pr_number,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.get(
                    url, headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to fetch PR commits: status=%d, url=%s",
                e.response.status_code,
                url,
            )
            raise GitHubAPIError(
                f"Failed to fetch PR commits:"
                f" {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(
                "Request error fetching PR commits: %s", e,
            )
            raise GitHubAPIError(
                f"Request error: {e}",
            ) from e

    async def post_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment_text: str,
    ) -> dict[str, Any]:
        """Post a comment on a pull request.

        Uses the issues comments endpoint as GitHub treats PR
        comments as issue comments.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            comment_text: Comment text to post.

        Returns:
            Created comment information dictionary.

        Raises:
            GitHubAPIError: If the API request fails.
        """
        url = (
            f"{self.base_url}/repos/{owner}/{repo}"
            f"/issues/{pr_number}/comments"
        )

        logger.debug(
            "Posting PR comment: owner=%s, repo=%s, pr=%d",
            owner,
            repo,
            pr_number,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={"body": comment_text},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to post PR comment: status=%d, url=%s",
                e.response.status_code,
                url,
            )
            raise GitHubAPIError(
                f"Failed to post PR comment:"
                f" {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(
                "Request error posting PR comment: %s", e,
            )
            raise GitHubAPIError(
                f"Request error: {e}",
            ) from e
