"""
Linter Tool — Code quality enforcement via ruff and black.
Runs static analysis, auto-formatting, and returns structured reports.
"""

import json
import structlog
from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class LinterTool(BaseTool):
    NAME = "linter_tool"
    DESCRIPTION = "Python code linting (ruff) and formatting (black)"
    TIMEOUT_S = 60

    async def run(self, path: str, fix: bool = False, **kwargs) -> ToolResult:
        """
        Run linting and formatting on a path.

        Args:
            path: File or directory to lint
            fix:  Auto-fix linting issues if possible
        """
        lint_result = await self._run_ruff(path, fix=fix)
        format_result = await self._run_black(path, check_only=(not fix))

        combined_output = f"=== RUFF ===\n{lint_result.output}\n\n=== BLACK ===\n{format_result.output}"
        success = (
            lint_result.success or fix
        )  # If fix mode, success even if changes made

        return ToolResult(
            success=success,
            output=combined_output,
            error="\n".join(filter(None, [lint_result.error, format_result.error]))
            or None,
            metadata={
                "lint_issues": self._count_issues(lint_result.output),
                "formatted": format_result.success,
                "path": path,
            },
        )

    async def _run_ruff(self, path: str, fix: bool) -> ToolResult:
        cmd = ["python", "-m", "ruff", "check", path]
        if fix:
            cmd.append("--fix")
        # Prefer ruff binary if available
        try:
            from shutil import which

            if which("ruff"):
                cmd = ["ruff", "check", path]
                if fix:
                    cmd.append("--fix")
        except Exception:
            pass
        return await self._run_subprocess(cmd)

    async def _run_black(self, path: str, check_only: bool) -> ToolResult:
        cmd = ["python", "-m", "black", path]
        if check_only:
            cmd.append("--check")
        try:
            from shutil import which

            if which("black"):
                cmd = ["black", path]
                if check_only:
                    cmd.append("--check")
        except Exception:
            pass
        return await self._run_subprocess(cmd)

    def _count_issues(self, ruff_output: str) -> int:
        lines = ruff_output.strip().splitlines() if ruff_output else []
        return sum(
            1
            for line in lines
            if line.strip() and not line.startswith("Found") and ": " in line
        )


class SecurityScanTool(BaseTool):
    """
    Security scanning tool using bandit (Python SAST).
    Identifies common vulnerabilities: SQLi, hardcoded secrets, weak crypto, etc.
    """

    NAME = "security_scan_tool"
    DESCRIPTION = "Python security scanning via bandit (SAST)"
    TIMEOUT_S = 120

    async def run(self, path: str, severity: str = "medium", **kwargs) -> ToolResult:
        """
        Run security scan.

        Args:
            path:     File or directory to scan
            severity: Minimum severity to report: "low" | "medium" | "high"
        """

        cmd = [
            "python",
            "-m",
            "bandit",
            "-r",
            path,
            "-f",
            "json",
            f"-l{'l' * (['low','medium','high'].index(severity) + 1)}",
        ]

        result = await self._run_subprocess(cmd)

        # Parse JSON output
        issues = []
        high_count = medium_count = low_count = 0

        try:
            data = json.loads(result.output or "{}")
            for issue in data.get("results", []):
                sev = issue.get("issue_severity", "").upper()
                if sev == "HIGH":
                    high_count += 1
                elif sev == "MEDIUM":
                    medium_count += 1
                else:
                    low_count += 1
                issues.append(
                    {
                        "severity": sev,
                        "confidence": issue.get("issue_confidence", ""),
                        "text": issue.get("issue_text", ""),
                        "file": issue.get("filename", ""),
                        "line": issue.get("line_number", 0),
                        "cwe": issue.get("issue_cwe", {}).get("id", ""),
                    }
                )
        except (json.JSONDecodeError, Exception):
            pass

        # Fail if any high-severity issues found
        scan_success = high_count == 0

        return ToolResult(
            success=scan_success,
            output=result.output or "No output",
            error=(
                f"{high_count} high-severity issues found" if high_count > 0 else None
            ),
            metadata={
                "high_severity": high_count,
                "medium_severity": medium_count,
                "low_severity": low_count,
                "total_issues": len(issues),
                "issues": issues[:20],  # First 20 for display
                "scanned_path": path,
            },
        )
