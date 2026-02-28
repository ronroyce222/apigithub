"""Tests for Claude Code reviewer service."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from models.pr_review import (
    CodeReviewResult,
    PRContext,
    ReviewComment,
    ReviewSeverity,
)
from services.claude_code_reviewer import ClaudeCodeError, ClaudeCodeReviewer


@pytest.fixture
def pr_context():
    """Create sample PR context."""
    return PRContext(
        pr_id=123,
        title="Add new feature",
        description="This PR adds a cool feature.",
        author="developer",
        source_branch="feature/new-thing",
        target_branch="main",
        repository_slug="test-repo",
        owner="TEST",
    )


@pytest.fixture
def sample_diff():
    """Create sample diff content."""
    return """diff --git a/src/example.py b/src/example.py
index abc123..def456 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,5 +1,7 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
"""


@pytest.fixture
def sample_json_review():
    """Create sample JSON review output."""
    return json.dumps({
        "summary": "Good code quality with minor suggestions.",
        "approval_recommendation": True,
        "files_reviewed": 1,
        "comments": [
            {
                "file_path": "src/example.py",
                "line_number": 3,
                "severity": "info",
                "message": "Consider adding a docstring.",
                "suggestion": "Add documentation.",
            },
            {
                "file_path": "src/example.py",
                "line_number": 5,
                "severity": "warning",
                "message": "Magic string detected.",
                "suggestion": "Use a constant.",
            },
        ],
    })


class TestClaudeCodeReviewer:
    """Tests for ClaudeCodeReviewer class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.object(
            ClaudeCodeReviewer, "_find_claude_code", return_value="/usr/bin/claude"
        ):
            reviewer = ClaudeCodeReviewer()
            assert reviewer.claude_code_path == "/usr/bin/claude"
            assert reviewer.timeout == 300.0
            assert reviewer.model is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        reviewer = ClaudeCodeReviewer(
            claude_code_path="/custom/claude",
            timeout=600.0,
            model="claude-sonnet-4-20250514",
        )
        assert reviewer.claude_code_path == "/custom/claude"
        assert reviewer.timeout == 600.0
        assert reviewer.model == "claude-sonnet-4-20250514"

    def test_find_claude_code_in_path(self):
        """Test finding claude in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            reviewer = ClaudeCodeReviewer()
            assert reviewer.claude_code_path == "/usr/local/bin/claude"

    def test_find_claude_code_common_paths(self):
        """Test finding claude in common paths."""
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=True), \
             patch("os.access", return_value=True):
            reviewer = ClaudeCodeReviewer()
            assert reviewer.claude_code_path == "/usr/local/bin/claude"

    def test_find_claude_code_not_found(self):
        """Test error when claude not found."""
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=False):
            with pytest.raises(ClaudeCodeError) as exc_info:
                ClaudeCodeReviewer()
            assert "not found" in str(exc_info.value)

    def test_build_review_prompt(self, pr_context, sample_diff):
        """Test building review prompt."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        prompt = reviewer._build_review_prompt(pr_context, sample_diff)

        assert "Add new feature" in prompt
        assert "developer" in prompt
        assert "feature/new-thing" in prompt
        assert "main" in prompt
        assert "TEST/test-repo" in prompt
        assert sample_diff in prompt

    def test_build_review_prompt_with_custom(self, pr_context, sample_diff):
        """Test building review prompt with custom prompt."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        custom = "Focus on security only."
        prompt = reviewer._build_review_prompt(pr_context, sample_diff, custom)

        assert "Focus on security only." in prompt
        assert "Add new feature" in prompt

    @pytest.mark.asyncio
    async def test_review_diff_success(
        self, pr_context, sample_diff, sample_json_review
    ):
        """Test successful diff review."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        with patch.object(
            reviewer,
            "_execute_claude_code",
            new_callable=AsyncMock,
            return_value=sample_json_review,
        ):
            result = await reviewer.review_diff(pr_context, sample_diff)

            assert result.pr_id == 123
            assert result.repository == "test-repo"
            assert result.project == "TEST"
            assert result.files_reviewed == 1
            assert result.approval_recommendation is True
            assert len(result.comments) == 2

    @pytest.mark.asyncio
    async def test_review_diff_non_json_output(self, pr_context, sample_diff):
        """Test review with non-JSON output."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        raw_output = "Code looks good. No major issues found."

        with patch.object(
            reviewer,
            "_execute_claude_code",
            new_callable=AsyncMock,
            return_value=raw_output,
        ):
            result = await reviewer.review_diff(pr_context, sample_diff)

            assert result.pr_id == 123
            assert result.files_reviewed == 0
            assert result.raw_review == raw_output

    @pytest.mark.asyncio
    async def test_execute_claude_code_success(self):
        """Test successful Claude Code execution."""
        reviewer = ClaudeCodeReviewer(
            claude_code_path="/usr/bin/claude",
            model="claude-sonnet-4-20250514",
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b"Review output", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("asyncio.wait_for", return_value=(b"Review output", b"")), \
             patch("builtins.open", MagicMock()):
            mock_process.communicate = AsyncMock(
                return_value=(b"Review output", b"")
            )

            with patch("asyncio.wait_for") as mock_wait:
                mock_wait.return_value = (b"Review output", b"")
                result = await reviewer._execute_claude_code(
                    "/tmp/prompt.txt",
                    working_dir="/tmp",
                )
                assert result == "Review output"

    @pytest.mark.asyncio
    async def test_execute_claude_code_failure(self):
        """Test Claude Code execution failure."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        mock_process = MagicMock()
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("asyncio.wait_for", return_value=(b"", b"Error message")), \
             patch("builtins.open", MagicMock()):
            with pytest.raises(ClaudeCodeError) as exc_info:
                await reviewer._execute_claude_code("/tmp/prompt.txt")

            assert exc_info.value.exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_claude_code_timeout(self):
        """Test Claude Code execution timeout."""
        import asyncio

        reviewer = ClaudeCodeReviewer(
            claude_code_path="/usr/bin/claude",
            timeout=1.0,
        )

        mock_process = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch(
                 "asyncio.wait_for",
                 side_effect=asyncio.TimeoutError(),
             ), \
             patch("builtins.open", MagicMock()):
            with pytest.raises(ClaudeCodeError) as exc_info:
                await reviewer._execute_claude_code("/tmp/prompt.txt")

            assert "timed out" in str(exc_info.value)

    def test_parse_review_output_valid_json(self, pr_context, sample_json_review):
        """Test parsing valid JSON output."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        result = reviewer._parse_review_output(pr_context, sample_json_review)

        assert result.summary == "Good code quality with minor suggestions."
        assert result.approval_recommendation is True
        assert len(result.comments) == 2

    def test_parse_review_output_invalid_json(self, pr_context):
        """Test parsing invalid JSON output."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        raw_output = "This is not JSON at all."
        result = reviewer._parse_review_output(pr_context, raw_output)

        assert result.files_reviewed == 0
        assert result.raw_review == raw_output

    def test_parse_review_output_invalid_severity(self, pr_context):
        """Test parsing with invalid severity defaults to INFO."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        json_output = json.dumps({
            "summary": "Test",
            "approval_recommendation": True,
            "files_reviewed": 1,
            "comments": [
                {
                    "file_path": "test.py",
                    "severity": "invalid_severity",
                    "message": "Test",
                },
            ],
        })

        result = reviewer._parse_review_output(pr_context, json_output)
        assert result.comments[0].severity == ReviewSeverity.INFO

    def test_format_review_as_markdown(self, pr_context):
        """Test formatting review as markdown."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        result = CodeReviewResult(
            pr_id=123,
            repository="test-repo",
            project="TEST",
            review_timestamp=datetime.now(timezone.utc),
            summary="Code quality is good.",
            comments=[
                ReviewComment(
                    file_path="src/main.py",
                    line_number=10,
                    severity=ReviewSeverity.WARNING,
                    message="Consider refactoring.",
                    suggestion="Extract method.",
                ),
                ReviewComment(
                    file_path="src/utils.py",
                    severity=ReviewSeverity.INFO,
                    message="Good implementation.",
                ),
            ],
            files_reviewed=2,
            approval_recommendation=True,
            raw_review="",
        )

        markdown = reviewer.format_review_as_markdown(result)

        assert "## Code Review by Claude Code" in markdown
        assert "TEST/test-repo" in markdown
        assert "Files Reviewed:** 2" in markdown
        assert "Code quality is good." in markdown
        assert "### Findings" in markdown
        assert "`src/main.py` (line 10)" in markdown
        assert "Consider refactoring." in markdown
        assert "Extract method." in markdown
        assert "**Recommendation:** Approved" in markdown

    def test_format_review_as_markdown_no_comments(self, pr_context):
        """Test formatting review with no comments."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        result = CodeReviewResult(
            pr_id=123,
            repository="test-repo",
            project="TEST",
            review_timestamp=datetime.now(timezone.utc),
            summary="Perfect code!",
            comments=[],
            files_reviewed=1,
            approval_recommendation=True,
            raw_review="",
        )

        markdown = reviewer.format_review_as_markdown(result)

        assert "### Findings" not in markdown
        assert "Perfect code!" in markdown


    @pytest.mark.asyncio
    async def test_execute_claude_code_os_error(self):
        """Test Claude Code execution with OSError."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("No such file or directory"),
        ), patch("builtins.open", MagicMock()):
            with pytest.raises(ClaudeCodeError) as exc_info:
                await reviewer._execute_claude_code("/tmp/prompt.txt")

            assert "Failed to execute" in str(exc_info.value)

    def test_parse_review_output_invalid_json_with_braces(self, pr_context):
        """Test parsing output that looks like JSON but is invalid."""
        reviewer = ClaudeCodeReviewer(claude_code_path="/usr/bin/claude")
        # Contains braces but is not valid JSON
        raw_output = "Here is the review: { invalid json content }"
        result = reviewer._parse_review_output(pr_context, raw_output)

        # Should fall back to raw output result
        assert result.files_reviewed == 0
        assert "See raw output" in result.summary
        assert result.raw_review == raw_output


class TestClaudeCodeError:
    """Tests for ClaudeCodeError exception."""

    def test_error_with_exit_code(self):
        """Test error with exit code."""
        error = ClaudeCodeError("Failed", exit_code=1)
        assert str(error) == "Failed"
        assert error.exit_code == 1

    def test_error_without_exit_code(self):
        """Test error without exit code."""
        error = ClaudeCodeError("Not found")
        assert str(error) == "Not found"
        assert error.exit_code is None
