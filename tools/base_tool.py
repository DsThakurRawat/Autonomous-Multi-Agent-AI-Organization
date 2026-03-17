"""
Base Tool - Abstract base class for all execution tools.
All tools are sandboxed, timed, audited, and observed.
"""

import asyncio
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class ToolResult:
    """Standardized result type from any tool execution."""

    def __init__(
        self,
        success: bool,
        output: str,
        error: Optional[str] = None,
        exit_code: int = 0,
        duration_ms: float = 0.0,
        artifacts: List[str] = None,  # Paths to generated files
        metadata: Dict[str, Any] = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.duration_ms = duration_ms
        self.artifacts = artifacts or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output[:5000] if self.output else "",  # Truncate for memory
            "error": self.error,
            "exit_code": self.exit_code,
            "duration_ms": round(self.duration_ms, 2),
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }

    @property
    def failed(self) -> bool:
        return not self.success


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    Every tool:
    - Has a name and description
    - Runs in an async context
    - Returns a ToolResult
    - Logs all executions (for audit)
    - Has a configurable timeout
    - Can run in dry-run mode (no side effects)
    """

    NAME: str = "base_tool"
    DESCRIPTION: str = "Base tool"
    TIMEOUT_S: int = 120  # Default 2-minute timeout

    def __init__(self, dry_run: bool = False, working_dir: Optional[str] = None):
        self.dry_run = dry_run
        self.working_dir = working_dir or os.getcwd()
        logger.info("Tool initialized", tool=self.NAME, dry_run=dry_run)

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        """Execute the tool. Must be overridden by subclasses."""
        ...

    async def __call__(self, **kwargs) -> ToolResult:
        """Callable interface with timing and logging."""
        start = time.monotonic()
        logger.info(
            "Tool started",
            tool=self.NAME,
            dry_run=self.dry_run,
            **{k: str(v)[:80] for k, v in kwargs.items()},
        )
        try:
            result = await asyncio.wait_for(self.run(**kwargs), timeout=self.TIMEOUT_S)
            duration = (time.monotonic() - start) * 1000
            result.duration_ms = duration
            logger.info(
                "Tool completed",
                tool=self.NAME,
                success=result.success,
                duration_ms=round(duration, 2),
            )
            return result
        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            logger.error("Tool timed out", tool=self.NAME, timeout_s=self.TIMEOUT_S)
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{self.NAME}' timed out after {self.TIMEOUT_S}s",
                exit_code=-1,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("Tool failed with exception", tool=self.NAME, error=str(e))
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                duration_ms=duration,
            )

    async def _run_subprocess(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute a subprocess command safely.
        Captures stdout/stderr, enforces timeout, logs everything.
        """
        working_dir = cwd or self.working_dir
        timeout_s = timeout or self.TIMEOUT_S
        full_env = {**os.environ, **(env or {})}

        if self.dry_run:
            cmd_str = " ".join(cmd)
            return ToolResult(
                success=True,
                output=f"[DRY RUN] Would execute: {cmd_str}",
                metadata={"command": cmd, "cwd": working_dir},
            )

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=full_env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
            duration = (time.monotonic() - start) * 1000

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0
            return ToolResult(
                success=success,
                output=stdout_str,
                error=stderr_str if not success else None,
                exit_code=proc.returncode or 0,
                duration_ms=duration,
                metadata={"command": cmd, "cwd": working_dir},
            )

        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(
                success=False,
                output="",
                error=f"Subprocess timed out after {timeout_s}s: {' '.join(cmd)}",
                exit_code=-1,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                duration_ms=duration,
            )
