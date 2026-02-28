"""Claude Code integration service for PR code reviews."""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from models.pr_review import (
    CodeReviewResult,
    PRContext,
    ReviewComment,
    ReviewSeverity,
)

logger = logging.getLogger(__name__)


class ClaudeCodeError(Exception):
    """Exception raised for Claude Code execution errors."""

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
    ) -> None:
        """
        Initialize ClaudeCodeError.

        Args:
            message: Error message.
            exit_code: Process exit code if applicable.
        """
        super().__init__(message)
        self.exit_code = exit_code


class ClaudeCodeReviewer:
    """
    Service for generating code reviews using Claude Code CLI.

    Executes Claude Code in a subprocess to analyze PR diffs and generate
    structured code review feedback.
    """

    DEFAULT_REVIEW_PROMPT = """
You are reviewing a pull request. Analyze the following diff and provide a
thorough code review. Focus on:

1. Code quality and best practices
2. Potential bugs or logic errors
3. Security vulnerabilities
4. Performance issues
5. Code style and maintainability
6. Missing tests or documentation

For each issue found, specify:
- The file path and line number (if applicable)
- Severity: info, warning, error, or critical
- A clear description of the issue
- A suggested fix when possible

At the end, provide:
- A summary of the overall code quality
- Whether you recommend approving this PR
- Total number of files reviewed

Format your response as valid JSON with this structure:
{
    "summary": "Overall review summary",
    "approval_recommendation": true/false,
    "files_reviewed": number,
    "comments": [
        {
            "file_path": "path/to/file.py",
            "line_number": 42,
            "severity": "warning",
            "message": "Description of the issue",
            "suggestion": "Suggested fix"
        }
    ]
}
"""

    def __init__(
        self,
        claude_code_path: str | None = None,
        timeout: float = 300.0,
        model: str | None = None,
    ) -> None:
        """
        Initialize the Claude Code reviewer.

        Args:
            claude_code_path: Path to claude CLI executable.
            timeout: Maximum execution time in seconds.
            model: Claude model to use (e.g., 'claude-sonnet-4-20250514').
        """
        self.claude_code_path = claude_code_path or self._find_claude_code()
        self.timeout = timeout
        self.model = model

    def _find_claude_code(self) -> str:
        """
        Find the Claude Code CLI executable.

        Returns:
            Path to the claude executable.

        Raises:
            ClaudeCodeError: If claude is not found.
        """
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path

        common_paths = [
            "/usr/local/bin/claude",
            "/opt/homebrew/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            os.path.expanduser("~/.npm-global/bin/claude"),
        ]

        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        raise ClaudeCodeError(
            "Claude Code CLI not found. Please install it or provide the path."
        )

    def _build_review_prompt(
        self,
        context: PRContext,
        diff: str,
        custom_prompt: str | None = None,
    ) -> str:
        """
        Build the full review prompt with context.

        Args:
            context: PR context information.
            diff: The PR diff content.
            custom_prompt: Optional custom review prompt.

        Returns:
            Complete prompt string for Claude Code.
        """
        prompt = custom_prompt or self.DEFAULT_REVIEW_PROMPT

        header = f"""
Pull Request Review Request
===========================
Title: {context.title}
Author: {context.author}
Source Branch: {context.source_branch}
Target Branch: {context.target_branch}
Repository: {context.owner}/{context.repository_slug}
"""

        if context.description:
            header += f"\nDescription:\n{context.description}\n"

        header += f"\n\nDiff:\n```diff\n{diff}\n```\n\n"

        return header + prompt

    async def review_diff(
        self,
        context: PRContext,
        diff: str,
        custom_prompt: str | None = None,
        working_dir: str | None = None,
    ) -> CodeReviewResult:
        """
        Generate a code review for the given diff.

        Args:
            context: PR context information.
            diff: The PR diff content to review.
            custom_prompt: Optional custom review prompt.
            working_dir: Optional working directory for claude execution.

        Returns:
            CodeReviewResult with the review findings.

        Raises:
            ClaudeCodeError: If the review execution fails.
        """
        logger.info(
            "Starting code review: pr_id=%d, repo=%s",
            context.pr_id,
            context.repository_slug,
        )

        prompt = self._build_review_prompt(context, diff, custom_prompt)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
        ) as prompt_file:
            prompt_file.write(prompt)
            prompt_file_path = prompt_file.name

        try:
            raw_output = await self._execute_claude_code(
                prompt_file_path,
                working_dir,
            )

            return self._parse_review_output(context, raw_output)

        finally:
            Path(prompt_file_path).unlink(missing_ok=True)

    async def _execute_claude_code(
        self,
        prompt_file: str,
        working_dir: str | None = None,
    ) -> str:
        """
        Execute Claude Code CLI with the given prompt.

        Args:
            prompt_file: Path to the prompt file.
            working_dir: Optional working directory.

        Returns:
            Raw output from Claude Code.

        Raises:
            ClaudeCodeError: If execution fails.
        """
        cmd = [
            self.claude_code_path,
            "--print",
            "--dangerously-skip-permissions",
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        with open(prompt_file, "r") as f:
            prompt_content = f.read()

        cmd.extend(["-p", prompt_content])

        logger.debug("Executing Claude Code: cmd=%s", " ".join(cmd[:3]))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                logger.error(
                    "Claude Code failed: exit_code=%d, stderr=%s",
                    process.returncode,
                    error_msg,
                )
                raise ClaudeCodeError(
                    f"Claude Code execution failed: {error_msg}",
                    exit_code=process.returncode,
                )

            return stdout.decode("utf-8", errors="replace")

        except asyncio.TimeoutError as e:
            logger.error("Claude Code timed out after %f seconds", self.timeout)
            raise ClaudeCodeError(
                f"Claude Code execution timed out after {self.timeout}s"
            ) from e
        except OSError as e:
            logger.error("Failed to execute Claude Code: %s", e)
            raise ClaudeCodeError(f"Failed to execute Claude Code: {e}") from e

    def _parse_review_output(
        self,
        context: PRContext,
        raw_output: str,
    ) -> CodeReviewResult:
        """
        Parse the raw Claude Code output into a structured result.

        Args:
            context: PR context information.
            raw_output: Raw output from Claude Code.

        Returns:
            Parsed CodeReviewResult.
        """
        logger.debug("Parsing review output: length=%d", len(raw_output))

        json_match = re.search(
            r"\{[\s\S]*\}",
            raw_output,
            re.MULTILINE,
        )

        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return self._build_result_from_json(context, parsed, raw_output)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from output, using raw")

        return CodeReviewResult(
            pr_id=context.pr_id,
            repository=context.repository_slug,
            project=context.owner,
            review_timestamp=datetime.now(timezone.utc),
            summary="Review completed. See raw output for details.",
            comments=[],
            files_reviewed=0,
            approval_recommendation=False,
            raw_review=raw_output,
        )

    def _build_result_from_json(
        self,
        context: PRContext,
        parsed: dict,
        raw_output: str,
    ) -> CodeReviewResult:
        """
        Build CodeReviewResult from parsed JSON.

        Args:
            context: PR context information.
            parsed: Parsed JSON dictionary.
            raw_output: Original raw output.

        Returns:
            Populated CodeReviewResult.
        """
        comments = []
        for comment_data in parsed.get("comments", []):
            severity_str = comment_data.get("severity", "info").lower()
            try:
                severity = ReviewSeverity(severity_str)
            except ValueError:
                severity = ReviewSeverity.INFO

            comments.append(
                ReviewComment(
                    file_path=comment_data.get("file_path", "unknown"),
                    line_number=comment_data.get("line_number"),
                    severity=severity,
                    message=comment_data.get("message", ""),
                    suggestion=comment_data.get("suggestion"),
                )
            )

        return CodeReviewResult(
            pr_id=context.pr_id,
            repository=context.repository_slug,
            project=context.owner,
            review_timestamp=datetime.now(timezone.utc),
            summary=parsed.get("summary", ""),
            comments=comments,
            files_reviewed=parsed.get("files_reviewed", 0),
            approval_recommendation=parsed.get(
                "approval_recommendation", False
            ),
            raw_review=raw_output,
        )

    def format_review_as_markdown(self, result: CodeReviewResult) -> str:
        """
        Format the review result as Markdown for posting as a PR comment.

        Args:
            result: The code review result.

        Returns:
            Markdown-formatted review string.
        """
        lines = [
            "## Code Review by Claude Code",
            "",
            f"**Repository:** {result.project}/{result.repository}",
            f"**Files Reviewed:** {result.files_reviewed}",
            f"**Review Date:** {result.review_timestamp.isoformat()}",
            "",
            "### Summary",
            "",
            result.summary,
            "",
        ]

        if result.comments:
            lines.extend(["### Findings", ""])

            severity_order = [
                ReviewSeverity.CRITICAL,
                ReviewSeverity.ERROR,
                ReviewSeverity.WARNING,
                ReviewSeverity.INFO,
            ]

            for severity in severity_order:
                severity_comments = [
                    c for c in result.comments if c.severity == severity
                ]
                if severity_comments:
                    emoji = {
                        ReviewSeverity.CRITICAL: "CRITICAL",
                        ReviewSeverity.ERROR: "ERROR",
                        ReviewSeverity.WARNING: "WARNING",
                        ReviewSeverity.INFO: "INFO",
                    }.get(severity, "")

                    lines.append(f"#### {emoji}")
                    lines.append("")

                    for comment in severity_comments:
                        location = f"`{comment.file_path}`"
                        if comment.line_number:
                            location += f" (line {comment.line_number})"

                        lines.append(f"- **{location}**: {comment.message}")
                        if comment.suggestion:
                            lines.append(f"  - *Suggestion:* {comment.suggestion}")
                    lines.append("")

        recommendation = "Approved" if result.approval_recommendation else "Not Approved"
        lines.extend([
            "---",
            f"**Recommendation:** {recommendation}",
        ])

        return "\n".join(lines)
