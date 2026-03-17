"""
Git Tool - Repository operations for code management.
Handles: init, clone, add, commit, push, branch, status, diff.
"""

import os
import re
from typing import Optional
import structlog
from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class GitTool(BaseTool):
    NAME = "git_tool"
    DESCRIPTION = "Git repository operations: init, clone, commit, push, branch"
    TIMEOUT_S = 60

    def __init__(self, repo_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.repo_path = repo_path or self.working_dir

    async def run(self, action: str, **kwargs) -> ToolResult:
        actions = {
            "init": self._init,
            "clone": self._clone,
            "add": self._add,
            "commit": self._commit,
            "push": self._push,
            "status": self._status,
            "diff": self._diff,
            "log": self._log,
            "rewind": self._rewind,
        }
        fn = actions.get(action)
        if not fn:
            return ToolResult(
                success=False, output="", error=f"Unknown git action: {action}"
            )
        return await fn(**kwargs)

    async def _init(self, path: Optional[str] = None) -> ToolResult:
        target = path or self.repo_path
        os.makedirs(target, exist_ok=True)
        result = await self._run_subprocess(["git", "init"], cwd=target)
        if result.success:
            # Configure git identity for automated commits
            await self._run_subprocess(
                ["git", "config", "user.email", "ai-org@example.com"], cwd=target
            )
            await self._run_subprocess(
                ["git", "config", "user.name", "AI Organization Bot"], cwd=target
            )
        return result

    async def _clone(self, url: str, target_dir: Optional[str] = None) -> ToolResult:
        cmd = ["git", "clone", url]
        if target_dir:
            cmd.append(target_dir)
        return await self._run_subprocess(cmd)

    async def _add(self, files: str = ".") -> ToolResult:
        return await self._run_subprocess(["git", "add", files], cwd=self.repo_path)

    async def _commit(self, message: str) -> ToolResult:
        return await self._run_subprocess(
            ["git", "commit", "-m", message], cwd=self.repo_path
        )

    async def _push(self, remote: str = "origin", branch: str = "main") -> ToolResult:
        return await self._run_subprocess(
            ["git", "push", remote, branch], cwd=self.repo_path
        )

    async def _status(self) -> ToolResult:
        return await self._run_subprocess(
            ["git", "status", "--short"], cwd=self.repo_path
        )

    async def _diff(self, staged: bool = False) -> ToolResult:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        return await self._run_subprocess(cmd, cwd=self.repo_path)

    async def _log(self, n: int = 10) -> ToolResult:
        return await self._run_subprocess(
            ["git", "log", f"-{n}", "--oneline"], cwd=self.repo_path
        )

    async def _rewind(self, block_hash: str, force: bool = False) -> ToolResult:
        """Issue #28: Ensure strict regex check on hash to prevent bash injections."""
        if not re.match(r"^[a-f0-9]{40}$", block_hash):
            return ToolResult(success=False, output="", error="Invalid git hash format. Must be 40 hex characters.")
            
        cmd = ["git", "reset"]
        if force:
            cmd.append("--hard")
        else:
            cmd.append("--soft")
            
        cmd.append(block_hash)
        return await self._run_subprocess(cmd, cwd=self.repo_path)

    async def commit_all(self, message: str) -> ToolResult:
        """Convenience: add all + commit."""
        add_result = await self._add(".")
        if not add_result.success:
            return add_result
        return await self._commit(message)
