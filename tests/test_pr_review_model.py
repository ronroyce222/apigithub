"""Tests for PR review models."""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.pr_review import (
    CodeReviewResult,
    PRContext,
    ReviewComment,
    ReviewSeverity,
)


class TestReviewSeverity:
    """Tests for ReviewSeverity enum."""

    def test_info_value(self) -> None:
        """Test INFO severity value."""
        assert ReviewSeverity.INFO.value == "info"

    def test_warning_value(self) -> None:
        """Test WARNING severity value."""
        assert ReviewSeverity.WARNING.value == "warning"

    def test_error_value(self) -> None:
        """Test ERROR severity value."""
        assert ReviewSeverity.ERROR.value == "error"

    def test_critical_value(self) -> None:
        """Test CRITICAL severity value."""
        assert ReviewSeverity.CRITICAL.value == "critical"


class TestReviewComment:
    """Tests for ReviewComment model."""

    def test_minimal_comment(self) -> None:
        """Test ReviewComment with minimal fields."""
        comment = ReviewComment(file_path="test.py", message="Test message")
        assert comment.file_path == "test.py"
        assert comment.message == "Test message"
        assert comment.line_number is None
        assert comment.severity == ReviewSeverity.INFO
        assert comment.suggestion is None

    def test_full_comment(self) -> None:
        """Test ReviewComment with all fields."""
        comment = ReviewComment(
            file_path="src/main.py",
            line_number=42,
            severity=ReviewSeverity.ERROR,
            message="Missing error handling",
            suggestion="Add try-except block",
        )
        assert comment.file_path == "src/main.py"
        assert comment.line_number == 42
        assert comment.severity == ReviewSeverity.ERROR
        assert comment.suggestion == "Add try-except block"


class TestCodeReviewResult:
    """Tests for CodeReviewResult model."""

    def test_minimal_result(self) -> None:
        """Test CodeReviewResult with minimal fields."""
        result = CodeReviewResult(
            pr_id=123,
            repository="my-repo",
            project="org",
            review_timestamp=datetime.now(timezone.utc),
            summary="Good PR",
        )
        assert result.pr_id == 123
        assert result.repository == "my-repo"
        assert result.project == "org"
        assert result.summary == "Good PR"
        assert result.comments == []
        assert result.files_reviewed == 0
        assert result.approval_recommendation is False
        assert result.raw_review == ""

    def test_result_with_comments(self) -> None:
        """Test CodeReviewResult with comments."""
        comments = [
            ReviewComment(file_path="a.py", message="Comment 1"),
            ReviewComment(file_path="b.py", message="Comment 2"),
        ]
        result = CodeReviewResult(
            pr_id=456,
            repository="repo",
            project="org",
            review_timestamp=datetime.now(timezone.utc),
            summary="Review summary",
            comments=comments,
            files_reviewed=5,
            approval_recommendation=True,
            raw_review="Raw output",
        )
        assert len(result.comments) == 2
        assert result.files_reviewed == 5
        assert result.approval_recommendation is True
        assert result.raw_review == "Raw output"


class TestPRContext:
    """Tests for PRContext model."""

    def test_minimal_context(self) -> None:
        """Test PRContext with minimal fields."""
        context = PRContext(
            pr_id=1,
            title="Test PR",
            author="user",
            source_branch="feature",
            target_branch="main",
            repository_slug="repo",
            owner="org",
        )
        assert context.pr_id == 1
        assert context.title == "Test PR"
        assert context.description is None
        assert context.clone_url is None
        assert context.pr_url is None

    def test_full_context(self) -> None:
        """Test PRContext with all fields."""
        context = PRContext(
            pr_id=42,
            title="Full PR",
            description="PR description",
            author="developer",
            source_branch="feature/new",
            target_branch="develop",
            repository_slug="my-repo",
            owner="org",
            clone_url="https://github.com/org/my-repo.git",
            pr_url="https://github.com/org/my-repo/pull/42",
        )
        assert context.description == "PR description"
        assert context.clone_url == "https://github.com/org/my-repo.git"
        assert context.pr_url == "https://github.com/org/my-repo/pull/42"

    def test_from_github_event_minimal(self) -> None:
        """Test from_github_event with minimal event data."""
        event = {"pull_request": {}}
        context = PRContext.from_github_event(event)
        assert context.pr_id == 0
        assert context.title == ""
        assert context.author == ""
        assert context.source_branch == ""
        assert context.target_branch == ""
        assert context.repository_slug == ""
        assert context.owner == ""

    def test_from_github_event_full(self) -> None:
        """Test from_github_event with full event data."""
        event = {
            "pull_request": {
                "number": 123,
                "title": "My PR Title",
                "body": "PR description text",
                "user": {"login": "john-doe", "id": 1},
                "head": {
                    "ref": "feature/branch",
                    "sha": "abc123",
                },
                "base": {
                    "ref": "main",
                    "sha": "def456",
                },
                "html_url": (
                    "https://github.com/org/my-repo/pull/123"
                ),
            },
            "repository": {
                "name": "my-repo",
                "full_name": "org/my-repo",
                "owner": {"login": "org", "id": 1},
                "clone_url": (
                    "https://github.com/org/my-repo.git"
                ),
            },
        }
        context = PRContext.from_github_event(event)
        assert context.pr_id == 123
        assert context.title == "My PR Title"
        assert context.description == "PR description text"
        assert context.author == "john-doe"
        assert context.source_branch == "feature/branch"
        assert context.target_branch == "main"
        assert context.repository_slug == "my-repo"
        assert context.owner == "org"
        assert context.clone_url == (
            "https://github.com/org/my-repo.git"
        )
        assert "pull/123" in context.pr_url

    def test_from_github_event_no_clone_url(self) -> None:
        """Test from_github_event when clone URL is missing."""
        event = {
            "pull_request": {"number": 1},
            "repository": {
                "name": "repo",
                "owner": {"login": "org"},
            },
        }
        context = PRContext.from_github_event(event)
        assert context.clone_url is None

    def test_from_github_event_no_pr_url(self) -> None:
        """Test from_github_event when PR URL is missing."""
        event = {
            "pull_request": {"number": 1},
            "repository": {
                "name": "repo",
                "owner": {"login": "org"},
            },
        }
        context = PRContext.from_github_event(event)
        assert context.pr_url is None
